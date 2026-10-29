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

import copy
import pathlib
from typing import Callable, Mapping, Optional, Sequence

from .blocks.builtin import BUILTIN_BLOCKS
from .blocks.registry import BlockConverter, BlockRegistry
from .config.config_loaders import locate_config_file
from .fanout import (
    Instance, RenderFailure, RenderRun, RenderSpec, RenderUsageError,
    build_instances, matches, render_specs,
)
from .exports import write_exports
from .render import (
    ContextHook, RenderEvent, RenderHook, RenderHooks, RenderMode,
    document_variables, load_source, render_document,
)

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

    def project_root(self, base_dir: pathlib.Path, discover_config: bool = True) -> pathlib.Path:
        """
        Returns the project root for a document in 'base_dir': the directory of
        the nearest *.ymprint.yml at or above it, or 'base_dir' itself when there
        is none (or 'discover_config' is False).
        """
        base_dir = base_dir.resolve()
        found = locate_config_file(base_dir) if discover_config else None
        return found.parent if found is not None else base_dir

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
        project_root: Optional[PathLike] = None,
        vars: Optional[Mapping] = None,
        params: Optional[Mapping] = None,
    ) -> RenderEvent:
        """
        Renders 'source' to a PDF, once, and returns the RenderEvent describing it.

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
        'project_root': `ym.project_root` in the document. Defaults to the
            directory of the discovered *.ymprint.yml, else 'base_dir'.
        'vars': variables layered over the document's `_vars` (they win).
        'params': the parameter set this render is for (`ym.params`).

        A `_render` entry for the document is not used; see render_all.
        """
        event, data = self._event(
            source, destination, config_path,
            base_dir=base_dir, discover_config=discover_config, trigger=trigger, mode=mode,
            output=output, project_root=project_root, vars=vars, params=params,
        )
        render_document(event, data, self.blocks, self.hooks)
        return event

    def _event(
        self,
        source: PathLike | dict,
        destination: Optional[PathLike],
        config_path: Optional[ConfigPaths],
        *,
        base_dir: Optional[PathLike] = None,
        discover_config: bool = True,
        trigger: Optional[PathLike] = None,
        mode: RenderMode = "api",
        output: Optional[PathLike] = None,
        project_root: Optional[PathLike] = None,
        vars: Optional[Mapping] = None,
        params: Optional[Mapping] = None,
    ) -> tuple[RenderEvent, Optional[dict]]:
        """Returns the RenderEvent for a render, and the document data (None for a path)."""
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
            vars=dict(vars or {}),
            params=dict(params or {}),
            output=pathlib.Path(output) if output is not None else None,
            project_root=(
                pathlib.Path(project_root).resolve() if project_root is not None
                else self.project_root(base_dir, discover_config)
            ),
        )
        return event, data

    def _plan(
        self,
        source: PathLike,
        config_path: Optional[ConfigPaths],
        discover_config: bool,
        mode: RenderMode,
    ) -> tuple[RenderEvent, Optional[RenderSpec], Optional[dict], list[Instance], set[pathlib.Path]]:
        """
        Returns a RenderEvent for the document (its config and project), its
        `_render` entry, its data (read once, when it fans out), its renders,
        and the data files read to work them out.
        """
        source_path = pathlib.Path(source).resolve()
        event, _ = self._event(source_path, None, config_path, discover_config=discover_config, mode=mode)
        spec = render_specs(event.config_paths).get(source_path)
        if spec is None or not spec.fans_out:
            return event, spec, None, build_instances(spec, source_path, {}), set()
        data = load_source(source_path, None)
        variables = document_variables(event, copy.deepcopy(data))
        instances = build_instances(spec, source_path, variables)
        return event, spec, data, instances, variables.catalog.inputs()

    def instances(
        self,
        source: PathLike,
        config_path: Optional[ConfigPaths] = None,
        *,
        only: Optional[Mapping] = None,
        discover_config: bool = True,
    ) -> list[Instance]:
        """
        Returns the renders of the document at 'source' that render_all would
        make: one per parameter set of its `_render` entry (those matching
        'only'), or a single one.
        """
        _, spec, _, instances, _ = self._plan(source, config_path, discover_config, "api")
        if only and (spec is None or not spec.fans_out):
            raise RenderUsageError(_not_parameterized(source))
        return [i for i in instances if matches(i.params, only)]

    def render_all(
        self,
        source: PathLike,
        config_path: Optional[ConfigPaths] = None,
        *,
        destination: Optional[PathLike] = None,
        only: Optional[Mapping] = None,
        discover_config: bool = True,
        mode: RenderMode = "api",
    ) -> RenderRun:
        """
        Renders the document at 'source' as its `_render` entry in the project
        config says: once per parameter set of its `for_each` (only the sets
        matching 'only', e.g. {"member_name": "B02"}), to its `output`.

        A document without a `_render` entry renders once, to 'destination'
        (default: next to the source), and errors propagate as from render().
        With parameter sets, the data is read once, every set is rendered even
        if some fail, and the failures are returned on the RenderRun.

        The document's `_export` values are written to every `_data` entry that
        names it in `from:`: the whole mapping, or with parameter sets, one entry
        per set under its key. They are only written when every set rendered;
        after a failure the stale output is removed instead.
        """
        source_path = pathlib.Path(source).resolve()
        plan_event, spec, data, instances, inputs = self._plan(source_path, config_path, discover_config, mode)
        if spec is None or not spec.fans_out:
            if only:
                raise RenderUsageError(_not_parameterized(source_path))
            instance = instances[0]
            if destination is not None:
                instance = Instance(params={}, destination=pathlib.Path(destination), key="")
            instance.destination.parent.mkdir(parents=True, exist_ok=True)
            event = self.render(
                source_path, instance.destination, config_path, discover_config=discover_config, mode=mode
            )
            run = RenderRun(source_path, spec, instances=[instance], results=[event], inputs=set(event.inputs))
            run.exports = event.exports
            write_exports(run, plan_event)
            return run
        if destination is not None:
            raise RenderUsageError(
                f"{source_path.name} is rendered once per parameter set; its PDFs go where the "
                "`output` of its `_render` entry says, so a destination cannot be given."
            )

        run = RenderRun(
            source_path, spec, instances=[i for i in instances if matches(i.params, only)], inputs=inputs
        )
        for instance in run.instances:
            instance.destination.parent.mkdir(parents=True, exist_ok=True)
            event, _ = self._event(
                source_path, instance.destination, config_path,
                discover_config=discover_config, mode=mode, vars=instance.params, params=instance.params,
            )
            try:
                render_document(event, data, self.blocks, self.hooks)
            except Exception as exc:
                # One failing parameter set must not stop the others.
                run.failures.append(RenderFailure(instance, exc))
            else:
                run.results.append(event)
                run.keys.append(instance.key)
            run.inputs |= event.inputs
        if any(event.exports is not None for event in run.results):
            run.exports = {key: event.exports for key, event in zip(run.keys, run.results)}
        write_exports(run, plan_event, partial=bool(only))
        return run

    def live(
        self,
        source: PathLike,
        destination: Optional[PathLike] = None,
        config_path: Optional[ConfigPaths] = None,
        *,
        watch: Sequence[PathLike] = (),
        vars: Optional[Mapping] = None,
        only: Optional[Mapping] = None,
    ) -> int:
        """
        Renders 'source', opens it in Okular and re-renders on every change to it,
        its config, the data it reads or the 'watch' files. Blocks until Ctrl+C;
        returns an exit code. 'vars' are layered over the document's `_vars`;
        'only' selects one parameter set of a document rendered per set.
        """
        if isinstance(source, dict):
            raise TypeError("Live mode watches a document file; it cannot render a dict source.")
        from .cli.live import run_live
        return run_live(self, source, destination, config_path, watch=watch, vars=vars, only=only)

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


def _not_parameterized(source: PathLike) -> str:
    return (
        f"{pathlib.Path(source).name} is not rendered per parameter set: it has no `_render` entry "
        "with a `for_each` in the project config, so there is nothing to select with 'only'."
    )
