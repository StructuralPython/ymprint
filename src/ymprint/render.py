"""
The render pipeline: one document in, one PDF out, with the application's hooks
run around it. `Ymprint.render` is the public entry point; this module holds the
pieces it is built from.
"""
from __future__ import annotations

import copy
import pathlib
from dataclasses import dataclass, field
from io import BytesIO
from typing import TYPE_CHECKING, Any, Callable, Literal, Optional

from .blocks.registry import BlockRegistry
from .config import DocConfig
from .config.config_loaders import load_report_config
from .config.font_registry import register_fonts
from .config.pdf_postprocessing import background_paths, load_pdf_backgrounds, fill_forms_and_bake, overlay_pdf_background
from .context_builder import build_context, rebuild_styles
from .data_sources import YM_VAR, DataCatalog, DocumentVars, YmContext, build_document_vars
from .errors import YmprintAuthoringError
from .exports import evaluate_exports
from .exceptions import YMPrintSyntaxException
from .story_builder import build_story
from .yaml_loader import load_yaml

if TYPE_CHECKING:
    from .app import Ymprint

RenderMode = Literal["convert", "live", "api", "build"]


@dataclass
class RenderEvent:
    """What is being rendered, and why. Passed to every render hook."""

    app: "Ymprint"
    # The document file; None when the document was supplied as data.
    source: Optional[pathlib.Path]
    destination: pathlib.Path
    # Relative paths in the document resolve against this directory.
    base_dir: pathlib.Path
    # The config layers in effect, lowest priority first.
    config_paths: tuple[pathlib.Path, ...]
    # The watched file whose change triggered this render (live mode); None for
    # the initial live render and for convert/API renders.
    trigger: Optional[pathlib.Path] = None
    mode: RenderMode = "api"
    # Variables merged over the document's own `_vars`. A before_render hook can
    # fill this to feed data into the document without writing it to disk.
    vars: dict = field(default_factory=dict)
    # The parameter set of this render, when the document is rendered once per
    # parameter set (its `_render` entry has a `for_each`); `ym.params`.
    params: dict = field(default_factory=dict)
    # Where the PDF is actually written, when not 'destination'. Live mode sets
    # this to a local preview copy when the destination is locked.
    output: Optional[pathlib.Path] = None
    # The directory of the project config; the document's directory when there
    # is none. `ym.project_root` in the document.
    project_root: Optional[pathlib.Path] = None
    # Set by the render: the files the document read (its `_data` sources, files
    # read directly, images and background PDFs), for live mode and build tools
    # that track dependencies.
    inputs: set[pathlib.Path] = field(default_factory=set)
    # Set by the render: the values of the document's `_export`, or None when it
    # has none.
    exports: Optional[dict] = None

    @property
    def pdf(self) -> pathlib.Path:
        """The PDF this render wrote."""
        return self.output_path

    @property
    def initial(self) -> bool:
        return self.trigger is None

    @property
    def output_path(self) -> pathlib.Path:
        return self.output if self.output is not None else self.destination


RenderHook = Callable[[RenderEvent], None]
ContextHook = Callable[[RenderEvent, dict], None]


@dataclass
class RenderHooks:
    """The hooks an application runs on every render, in registration order."""

    before_render: list[RenderHook] = field(default_factory=list)
    on_context: list[ContextHook] = field(default_factory=list)
    after_render: list[RenderHook] = field(default_factory=list)


class RenderCallbackError(Exception):
    """A render hook raised an exception."""

    def __init__(self, stage: str, callback: Callable, original: BaseException):
        name = getattr(callback, "__qualname__", repr(callback))
        super().__init__(f"{stage} hook {name} raised {type(original).__name__}: {original}")
        self.stage = stage
        self.callback = callback
        self.original = original


def run_hooks(stage: str, hooks: list[Callable], *args: Any) -> None:
    """
    Calls each hook with 'args'. A hook's exception is wrapped in
    RenderCallbackError, except YmprintAuthoringError, which passes through so it
    is reported like any other authoring error.
    """
    for hook in hooks:
        try:
            hook(*args)
        except YmprintAuthoringError:
            raise
        except Exception as exc:
            raise RenderCallbackError(stage, hook, exc) from exc


def load_source(source: Optional[pathlib.Path], data: Optional[dict]) -> dict:
    """
    Returns the document as a fresh dict: copied from 'data' when given (a
    document supplied as data, or a source file already read once for several
    renders), else read from 'source'.
    """
    name = source.name if source is not None else "<data>"
    if data is not None:
        # The pipeline pops config and `_vars` out of the document; copy so the
        # caller's dict is left as it was and can be rendered again.
        source_data = copy.deepcopy(data)
    else:
        if not source.exists():
            raise FileNotFoundError(f"The source YAML file at {str(source)} does not exist")
        source_data = load_yaml(source)
    if not source_data:
        # An empty document (or one with no content) loads as None. Report it as an
        # authoring error so the CLI/live mode shows it instead of crashing with a
        # raw TypeError further down.
        raise YMPrintSyntaxException(
            f"The document {name!r} is empty. Add some content to render it."
        )
    return source_data


def render_document(
    event: RenderEvent,
    data: Optional[dict],
    blocks: BlockRegistry,
    hooks: RenderHooks,
) -> None:
    """
    Runs one render: before_render hooks, load and build the context, on_context
    hooks, build the PDF, then after_render hooks.

    A failing before_render or on_context hook aborts the render (its output may
    be an input to the document); after_render hooks only run once the PDF has
    been written.

    An exception that escapes the render carries the event as `render_event`,
    so a caller such as live mode can still watch the files read before it.
    """
    try:
        _run_render(event, data, blocks, hooks)
    except Exception as exc:
        exc.render_event = event
        raise


def _run_render(
    event: RenderEvent,
    data: Optional[dict],
    blocks: BlockRegistry,
    hooks: RenderHooks,
) -> None:
    run_hooks("before_render", hooks.before_render, event)

    source_data = load_source(event.source, data)
    register_fonts()
    export_declarations = source_data.pop("_export", None) if isinstance(source_data, dict) else None
    document_vars = document_variables(event, source_data)
    catalog = document_vars.catalog
    project_root = document_vars[YM_VAR].project_root
    textstyles, tablestyles, doc_data = load_report_config(source_data, list(event.config_paths))
    doctemplate = DocConfig.model_validate(doc_data['_doc'])
    context = build_context(
        source_data,
        textstyles,
        doc_data,
        tablestyles,
        document_vars,
        event.source,
        event.destination,
        list(event.config_paths),
        blocks=blocks,
        base_dir=event.base_dir,
        data=catalog,
        project_root=project_root,
    )

    try:
        _build_pdf(event, context, doctemplate, hooks, export_declarations)
    finally:
        # The data files, images and JSON the document read, recorded even when
        # the render fails part way so they can still be watched.
        event.inputs |= catalog.inputs()

    run_hooks("after_render", hooks.after_render, event)


def _build_pdf(
    event: RenderEvent,
    context: dict,
    doctemplate: DocConfig,
    hooks: RenderHooks,
    export_declarations: Any,
) -> None:
    if hooks.on_context:
        run_hooks("on_context", hooks.on_context, event, context)
        # Hooks may have changed the style models; rebuild what is derived from them.
        rebuild_styles(context)

    # Backgrounds are recorded before the story is built, so a missing or
    # half-written background is still watched when the render fails.
    event.inputs |= {path for path in background_paths(context).values() if path is not None}

    story = build_story(context["content"], context)
    if export_declarations is not None:
        event.exports = evaluate_exports(export_declarations, context["vars"], describe_render(event))
    rl_doc, page_template_map = doctemplate.build(event.destination)
    rl_report_buffer = BytesIO()
    rl_doc.build(story, filename=rl_report_buffer)
    rl_report_buffer.seek(0)
    # page_template_map is now populated with {page_index: template_name}
    pdf_backgrounds = load_pdf_backgrounds(context)
    populated_backgrounds = fill_forms_and_bake(context['vars'], pdf_backgrounds)
    overlay_pdf_background(
        rl_report_buffer,
        populated_backgrounds,
        event.output_path,
        context,
        page_template_map,
    )


def describe_render(event: RenderEvent) -> str:
    """Names the document of a render, and its parameter set, for error messages."""
    name = event.source.name if event.source is not None else "the document"
    if event.params:
        name += " (" + ", ".join(f"{k}={v}" for k, v in event.params.items()) + ")"
    return name


def document_variables(event: RenderEvent, source_data: dict) -> DocumentVars:
    """
    Returns the variables of the render 'event' describes: the document's
    `_vars` and `_data` (popped from 'source_data'), the config's `_data`, `ym`,
    and event.vars.
    """
    document_data = None
    if isinstance(source_data, dict):
        document_data = source_data.pop("_data", None)
        if "_render" in source_data:
            raise YMPrintSyntaxException(
                "`_render` belongs in the project config (*.ymprint.yml), not in the document."
            )
    project_root = event.project_root or event.base_dir
    catalog = DataCatalog.from_config(
        event.config_paths, document_data, event.base_dir, event.source, project_root
    )
    ym = YmContext(
        project_root=project_root, source=event.source, params=dict(event.params), catalog=catalog
    )
    return build_document_vars(
        extract_vars(source_data),
        event.vars,
        catalog,
        ym,
        where=event.source.name if event.source is not None else "the document",
    )


def extract_vars(source_data: dict) -> dict:
    if "_vars" in source_data:
        return source_data.pop("_vars") or {}
    return {}
