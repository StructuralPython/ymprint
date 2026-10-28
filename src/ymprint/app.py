"""
The Ymprint application: a block registry, render hooks and default config
bundled together, so a document type can be built as its own application on top
of ymprint::

    from ymprint import Ymprint, RenderEvent

    app = Ymprint(name="calcsheet", config_path=HERE / "config")

    @app.block("_beam")
    def beam_block(block_key, block_value, context):
        ...  # -> list[Flowable]

    @app.before_render
    def load_design_data(event: RenderEvent) -> None:
        event.vars["project"] = fetch_project(event.source)

    app.render("report.yml")
"""
from __future__ import annotations

import pathlib
from typing import Callable, Optional, Sequence

from .blocks.builtin import BUILTIN_BLOCKS
from .blocks.registry import BlockConverter, BlockRegistry
from .config.config_loaders import locate_config_file
from .render import ContextHook, RenderEvent, RenderHook, RenderHooks, RenderMode, render_document

PathLike = str | pathlib.Path
ConfigPaths = PathLike | Sequence[PathLike]

# A minimal, valid starter document written when the user opts to initialize a new
# file in live mode. It renders to a one-heading, one-paragraph PDF. `{title}` is
# replaced with the file's stem.
STARTER_DOCUMENT = """\
{title}:
  - >
    Start writing your report here. This paragraph sits under the heading above.
    Edit this file and save — live mode will hot-reload the PDF.
"""


class Ymprint:
    """
    A ymprint application.

    'name': the application's name, used as its CLI name.
    'config_path': the application's own config file or directory (its house
        style). It sits above ymprint's defaults and below any config found next
        to the document or passed explicitly.
    'builtin_blocks': start from a copy of ymprint's built-in blocks (True) or
        from an empty registry (False).
    'starter_document': the document live mode offers to create when the source
        does not exist; `{title}` is replaced with the file's stem.
    """

    def __init__(
        self,
        name: str = "ym",
        *,
        config_path: Optional[PathLike] = None,
        builtin_blocks: bool = True,
        starter_document: str = STARTER_DOCUMENT,
    ):
        self.name = name
        self.starter_document = starter_document
        self.config_path = pathlib.Path(config_path) if config_path is not None else None
        self.blocks: BlockRegistry = BUILTIN_BLOCKS.copy() if builtin_blocks else BlockRegistry()
        self.hooks = RenderHooks()

    def __repr__(self) -> str:
        return f"Ymprint(name={self.name!r})"

    # --- blocks ------------------------------------------------------------------

    def register_block(self, code: str, convert: BlockConverter, *, override: bool = False) -> None:
        """Adds a block to this application. See BlockRegistry.register."""
        self.blocks.register(code, convert, override=override)

    def block(self, code: str, *, override: bool = False) -> Callable[[BlockConverter], BlockConverter]:
        """Decorator form of register_block()."""
        return self.blocks.block(code, override=override)

    # --- hooks -------------------------------------------------------------------

    def before_render(self, fn: RenderHook) -> RenderHook:
        """
        Registers fn(event) to run before every render. It may fill event.vars or
        regenerate the document's input files. If it raises, the render is skipped.
        """
        self.hooks.before_render.append(fn)
        return fn

    def on_context(self, fn: ContextHook) -> ContextHook:
        """
        Registers fn(event, context) to run once the config is loaded and the
        render context is built, before the document content is rendered. It may
        change context['vars'], context['content'] and context['frames'] in place,
        and change or replace the style models context['styles']['ymprint'] and
        context['tablestyles']['ymprint']; the ReportLab styles are rebuilt from
        them after the hooks run.
        """
        self.hooks.on_context.append(fn)
        return fn

    def after_render(self, fn: RenderHook) -> RenderHook:
        """Registers fn(event) to run after every render that wrote the PDF."""
        self.hooks.after_render.append(fn)
        return fn

    # --- rendering ---------------------------------------------------------------

    def config_layers(
        self,
        base_dir: pathlib.Path,
        config_path: Optional[ConfigPaths] = None,
        discover_config: bool = True,
    ) -> tuple[pathlib.Path, ...]:
        """
        Returns the config layers for a document in 'base_dir', lowest priority
        first: this app's config, the nearest *.ymprint.yml at or above
        'base_dir' (if 'discover_config'), then 'config_path' (one path, or a
        sequence of them, lowest priority first).
        """
        candidates = [self.config_path]
        if discover_config:
            candidates.append(locate_config_file(base_dir.resolve()))
        if isinstance(config_path, (str, pathlib.Path)):
            config_path = [config_path]
        candidates.extend(pathlib.Path(p) for p in config_path or ())
        layers: list[pathlib.Path] = []
        for path in candidates:
            if path is None:
                continue
            # The same file can turn up twice (a document inside the app's config
            # directory); keep it once, at its highest priority.
            layers = [p for p in layers if p.resolve() != path.resolve()]
            layers.append(path)
        return tuple(layers)

    def render(
        self,
        source: PathLike | dict,
        destination: Optional[PathLike] = None,
        config_path: Optional[ConfigPaths] = None,
        *,
        base_dir: Optional[PathLike] = None,
        discover_config: bool = True,
        trigger: Optional[PathLike] = None,
        mode: RenderMode = "api",
        output: Optional[PathLike] = None,
    ) -> RenderEvent:
        """
        Renders 'source' to a PDF and returns the RenderEvent describing it.

        'source': a YAML document path, or the document as a dict.
        'destination': the PDF to write. Defaults to the source path with a .pdf
            suffix; required when 'source' is a dict.
        'config_path': an explicit config file or directory (or a sequence of
            them), the highest-priority config layer(s).
        'base_dir': where relative paths in the document resolve. Defaults to the
            source file's directory, or the current directory for a dict.
        'discover_config': look for a *.ymprint.yml at or above 'base_dir'.
        'trigger', 'mode': passed through to the hooks on the RenderEvent.
        'output': write the PDF here instead of 'destination'; hooks still see
            'destination' as the document's target.
        """
        if isinstance(source, dict):
            data = source
            source_path = None
            if destination is None:
                raise ValueError("A destination is required when rendering a document from data.")
            default_base_dir = pathlib.Path.cwd()
        else:
            data = None
            source_path = pathlib.Path(source).resolve()
            if destination is None:
                destination = source_path.parent / f"{source_path.stem}.pdf"
            default_base_dir = source_path.parent
        base_dir = pathlib.Path(base_dir) if base_dir is not None else default_base_dir

        event = RenderEvent(
            app=self,
            source=source_path,
            destination=pathlib.Path(destination),
            base_dir=base_dir,
            config_paths=self.config_layers(base_dir, config_path, discover_config),
            trigger=pathlib.Path(trigger) if trigger is not None else None,
            mode=mode,
            output=pathlib.Path(output) if output is not None else None,
        )
        render_document(event, data, self.blocks, self.hooks)
        return event

    def live(
        self,
        source: PathLike,
        destination: Optional[PathLike] = None,
        config_path: Optional[ConfigPaths] = None,
        *,
        watch: Sequence[PathLike] = (),
    ) -> int:
        """
        Renders 'source', opens it in Okular and re-renders on every change to it,
        its config or the 'watch' files. Blocks until Ctrl+C; returns an exit code.
        """
        if isinstance(source, dict):
            raise TypeError("Live mode watches a document file; it cannot render a dict source.")
        from .cli.live import run_live
        return run_live(self, source, destination, config_path, watch=watch)

    def cli(self):
        """
        Returns a new Typer app with `convert` and `live` commands for this
        application. Point a console script at it, e.g. in pyproject.toml:

            [project.scripts]
            calcsheet = "calcsheet:cli"     # where cli = app.cli()
        """
        from .cli.main import build_cli
        return build_cli(self)


# The application behind `ym` and the module-level helpers like load_report.
default_app = Ymprint()
