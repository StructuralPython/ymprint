"""
`ym build`: build a project's documents and scripts in dependency order.

The graph is declared once and recorded, never listed by hand:

- **Steps** are the documents matched by `_build.documents` in the project
  config, every producer named in a `_data` entry's `from:` (documents and
  `.py` scripts), and every document with a `_render` entry.
- **What a step produces** is declared by `from:`.
- **What a step reads** is recorded while it runs: every data source it uses
  (`{{ design }}`, `_py`, `ymprint.project.data()`, `ym.path()`), with a hash
  of each file read, saved to <build dir>/.ym/deps.json.

When a step reads a data source, its producers are brought up to date first,
so even a first build, with nothing recorded, runs in a valid order. A step is
stale when it has never been built or last failed, its source or any file it
read last time changed, an output is missing, or the ymprint or plugin
versions changed. A producer that re-runs and writes the same data does not
make its readers stale.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import runpy
import sys
import time
from dataclasses import dataclass, field
from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Callable, Literal, Optional

from .data_sources import DATA_ACCESS_HOOK, DataSource, config_declarations, config_file, resolve_build_dir
from .errors import YmprintAuthoringError
from .fanout import render_specs
from .plugins import plugin_versions
from .project import CURRENT_SCRIPT, Project

if TYPE_CHECKING:
    from .app import Ymprint

DOCUMENT_SUFFIXES = {".yml", ".yaml"}
SCRIPT_SUFFIXES = {".py"}
RECORDS_VERSION = 1

StepKind = Literal["document", "script"]
StepStatus = Literal["built", "up-to-date", "failed", "planned"]


class BuildError(YmprintAuthoringError):
    """The project cannot be built as declared (a missing file, an empty glob, a cycle)."""


@dataclass(frozen=True)
class Step:
    """A document or script that the build runs."""

    path: pathlib.Path
    kind: StepKind
    # The path relative to the project root, as shown and recorded.
    id: str


@dataclass
class StepResult:
    step: Step
    status: StepStatus
    reasons: list[str] = field(default_factory=list)
    # Time spent in this step itself, not in the producers it waited for.
    seconds: float = 0.0
    detail: str = ""
    error: Optional[BaseException] = None
    # One line per failure, e.g. "B03: KeyError: 'Zx'".
    failures: list[str] = field(default_factory=list)


@dataclass
class BuildSummary:
    results: list[StepResult]
    seconds: float

    @property
    def ok(self) -> bool:
        return all(r.status != "failed" for r in self.results)

    def count(self, status: StepStatus) -> int:
        return sum(1 for r in self.results if r.status == status)


def file_hash(path: pathlib.Path) -> Optional[str]:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except (FileNotFoundError, IsADirectoryError):
        return None


def tool_versions() -> dict[str, str]:
    """The versions that, when changed, make every step stale."""
    from . import __version__

    versions = {"ymprint": __version__, **plugin_versions()}
    try:
        versions["ym-handcalcs"] = version("ym-handcalcs")
    except PackageNotFoundError:
        pass
    return versions


class Build:
    """
    One `ym build` run over the project containing 'start'.

    'force': rebuild every step (once), ignoring what is recorded.
    'dry_run': only work out what would be built, and why.
    'report': called with each StepResult as the step finishes.
    """

    def __init__(
        self,
        app: "Ymprint",
        start: Optional[pathlib.Path] = None,
        *,
        force: bool = False,
        dry_run: bool = False,
        report: Optional[Callable[[StepResult], None]] = None,
    ):
        self.app = app
        layers = (app.config_path,) if app.config_path is not None else ()
        self.project = Project.find(pathlib.Path(start or pathlib.Path.cwd()), extra_layers=layers)
        self.root = self.project.root
        self.force = force
        self.dry_run = dry_run
        self.report = report or (lambda result: None)
        self.catalog = self.project.catalog()
        self.build_dir = resolve_build_dir(self.project.config_paths, self.root)
        self.records_path = self.build_dir / ".ym" / "deps.json"
        self.records = self._load_records()
        self.versions = tool_versions()
        self.steps = self._discover_steps()
        self.results: dict[pathlib.Path, StepResult] = {}
        self.order: list[StepResult] = []
        self._stack: list[Step] = []
        # Per running step: {"data": {name: files}, "child_seconds": float}.
        self._frames: list[dict] = []

    # --- the graph ---------------------------------------------------------------

    def relative(self, path: pathlib.Path) -> str:
        try:
            return path.resolve().relative_to(self.root).as_posix()
        except ValueError:
            return path.resolve().as_posix()

    def _step(self, path: pathlib.Path, why: str) -> Step:
        path = path.resolve()
        if path.suffix in DOCUMENT_SUFFIXES:
            kind: StepKind = "document"
        elif path.suffix in SCRIPT_SUFFIXES:
            kind = "script"
        else:
            raise BuildError(f"{why} {self.relative(path)}, which is not a document (.yml) or a script (.py).")
        if not path.is_file():
            raise BuildError(f"{why} {self.relative(path)}, which does not exist.")
        return Step(path=path, kind=kind, id=self.relative(path))

    def _discover_steps(self) -> dict[pathlib.Path, Step]:
        steps: dict[pathlib.Path, Step] = {}
        for settings, declared_in in config_declarations(self.project.config_paths, "_build"):
            patterns = settings.get("documents") or [] if isinstance(settings, dict) else []
            if isinstance(patterns, str):
                patterns = [patterns]
            for pattern in patterns:
                matches = sorted(p for p in declared_in.parent.glob(str(pattern)) if p.is_file())
                if not matches:
                    raise BuildError(
                        f"`_build.documents` pattern {pattern!r} in {declared_in.name} matches no files."
                    )
                for match in matches:
                    step = self._step(match, f"`_build.documents` pattern {pattern!r} matches")
                    steps[step.path] = step
        for source in self.catalog.sources.values():
            for producer in source.producers:
                step = self._step(producer, f"`_data` entry {source.name!r} names producer")
                steps[step.path] = step
        for document in render_specs(self.project.config_paths):
            step = self._step(document, "`_render` has an entry for")
            steps[step.path] = step
        return dict(sorted(steps.items(), key=lambda item: item[1].id))

    def produces(self, step: Step) -> list[DataSource]:
        return [s for s in self.catalog.sources.values() if step.path in s.producers]

    def producers_of(self, source: DataSource) -> list[Step]:
        return [self.steps[p] for p in source.producers if p in self.steps]

    def resolve_target(self, target: str | pathlib.Path) -> Step:
        path = pathlib.Path(target).resolve()
        return self.steps.get(path) or self._step(path, "The build target is")

    # --- records -----------------------------------------------------------------

    def _load_records(self) -> dict:
        try:
            records = json.loads(self.records_path.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
        if records.get("version") != RECORDS_VERSION:
            return {}
        return records.get("steps", {})

    def _save_records(self) -> None:
        from .exports import write_json_atomic

        write_json_atomic(self.records_path, {"version": RECORDS_VERSION, "steps": self.records})

    def stale_reasons(self, step: Step) -> list[str]:
        """Why 'step' must run (empty when it is up to date), bringing its producers up to date first."""
        if self.force:
            return ["--all"]
        record = self.records.get(step.id)
        if record is None:
            return ["never built"]
        if not record.get("ok"):
            return ["last build failed"]
        if record.get("versions") != self.versions:
            return ["ymprint or plugin version changed"]
        if file_hash(step.path) != record.get("source"):
            return ["source changed"]
        reasons = []
        for name in record.get("data", []):
            source = self.catalog.sources.get(name)
            if source is None:
                reasons.append(f"data source {name!r} is no longer declared")
                continue
            for producer in self.producers_of(source):
                if producer.path == step.path:
                    continue
                result = self.ensure(producer)
                if self.dry_run and result.status == "planned":
                    reasons.append(f"{name} may change ({producer.id} is stale)")
        # Produced data is named by its source, not by where ymprint stores it.
        produced = {
            self.relative(path): name
            for name in record.get("data", [])
            if name in self.catalog.sources and self.catalog.sources[name].producers
            for path in self.catalog.sources[name].files()
        }
        for relative, digest in record.get("inputs", {}).items():
            if file_hash(self.root / relative) != digest:
                reasons.append(f"{produced.get(relative, relative)} changed")
        for relative in record.get("outputs", []):
            if not (self.root / relative).exists():
                reasons.append(f"{relative} missing")
        return list(dict.fromkeys(reasons))

    # --- running -----------------------------------------------------------------

    def ensure(self, step: Step) -> StepResult:
        """Brings 'step' up to date (running it if it is stale) and returns its result."""
        if step.path in self.results:
            return self.results[step.path]
        if step in self._stack:
            cycle = " → ".join(s.id for s in self._stack[self._stack.index(step):] + [step])
            raise BuildError(f"Dependency cycle: {cycle}")
        self._stack.append(step)
        try:
            reasons = self.stale_reasons(step)
        finally:
            self._stack.pop()
        if not reasons:
            result = StepResult(step, "up-to-date")
        elif self.dry_run:
            result = StepResult(step, "planned", reasons)
        else:
            result = self._run(step, reasons)
        self.results[step.path] = result
        self.order.append(result)
        self.report(result)
        return result

    def _on_access(self, source: DataSource) -> None:
        """Called whenever a running step reads a data source: record it, then produce it."""
        if self._frames:
            self._frames[-1]["data"][source.name] = source.files()
        for producer in self.producers_of(source):
            current = self._stack[-1] if self._stack else None
            if producer == current:
                raise BuildError(f"{producer.id} reads {source.name!r}, which it produces itself.")
            result = self.ensure(producer)
            if result.status == "failed":
                raise BuildError(f"{source.name!r} could not be produced: {producer.id} failed.")

    def _run(self, step: Step, reasons: list[str]) -> StepResult:
        result = StepResult(step, "built", reasons)
        frame = {"data": {}, "child_seconds": 0.0}
        files: set[pathlib.Path] = set()
        outputs: list[pathlib.Path] = []
        self._stack.append(step)
        self._frames.append(frame)
        token = DATA_ACCESS_HOOK.set(self._on_access)
        start = time.perf_counter()
        try:
            if step.kind == "document":
                run = self.app.render_all(step.path, mode="build")
                files |= run.inputs
                outputs = [i.destination for i in run.instances] + run.written
                if run.spec is not None and run.spec.fans_out:
                    result.detail = f"{len(run.results)} documents"
                if run.failures:
                    result.status = "failed"
                    result.failures = [f.describe() for f in run.failures] + run.notes
            else:
                self._run_script(step)
                outputs = [s.output_for(step.path) for s in self.produces(step)]
        except Exception as exc:
            result.status = "failed"
            result.error = exc
        finally:
            DATA_ACCESS_HOOK.reset(token)
            self._frames.pop()
            self._stack.pop()
        elapsed = time.perf_counter() - start
        result.seconds = elapsed - frame["child_seconds"]
        if self._frames:
            self._frames[-1]["child_seconds"] += elapsed

        for paths in frame["data"].values():
            files.update(paths)
        for layer in self.app.config_layers(step.path.parent):
            found = config_file(layer)
            if found is not None:
                files.add(found.resolve())
        self.records[step.id] = {
            "ok": result.status == "built",
            "source": file_hash(step.path),
            "versions": self.versions,
            "data": sorted(frame["data"]),
            "inputs": {self.relative(p): file_hash(p) for p in sorted(files)},
            "outputs": sorted(self.relative(p) for p in outputs),
        }
        self._save_records()
        return result

    def _run_script(self, step: Step) -> None:
        """Runs a script in this process, as `python script.py` would, from its own folder's imports."""
        token = CURRENT_SCRIPT.set((self.project, step.path))
        sys.path.insert(0, str(step.path.parent))
        try:
            runpy.run_path(str(step.path), run_name="__main__")
        except SystemExit as exc:
            if exc.code not in (None, 0):
                raise RuntimeError(f"{step.id} exited with code {exc.code}") from exc
        finally:
            sys.path.remove(str(step.path.parent))
            CURRENT_SCRIPT.reset(token)

    def run(self, targets: list[str | pathlib.Path] = ()) -> BuildSummary:
        """Builds 'targets' (and what they need), or every step."""
        start = time.perf_counter()
        steps = [self.resolve_target(t) for t in targets] if targets else list(self.steps.values())
        for step in steps:
            self.ensure(step)
        return BuildSummary(self.order, time.perf_counter() - start)

    # --- the graph, for `ym graph` -------------------------------------------------

    def edges(self) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
        """
        Returns (produces, reads): (step id, data source name) pairs from the
        `from:` declarations, and (data source name, step id) pairs recorded by
        the last build.
        """
        produces = [
            (step.id, source.name) for step in self.steps.values() for source in self.produces(step)
        ]
        reads = [
            (name, step.id)
            for step in self.steps.values()
            for name in self.records.get(step.id, {}).get("data", [])
        ]
        return produces, reads


def format_graph(build: Build, fmt: str = "text") -> str:
    """Returns the project graph as text, Graphviz dot, or a Mermaid flowchart."""
    produces, reads = build.edges()
    steps = [s.id for s in build.steps.values()]
    sources = list(build.catalog.sources)
    if fmt == "dot":
        lines = ["digraph ymprint {", "  rankdir=LR;"]
        lines += [f'  "{s}" [shape=box];' for s in steps]
        lines += [f'  "{n}" [shape=note];' for n in sources]
        lines += [f'  "{a}" -> "{b}";' for a, b in produces + reads]
        return "\n".join(lines + ["}"])
    if fmt == "mermaid":
        ids = {name: f"n{i}" for i, name in enumerate(steps + sources)}
        lines = ["flowchart LR"]
        lines += [f'  {ids[s]}["{s}"]' for s in steps]
        lines += [f'  {ids[n]}[("{n}")]' for n in sources]
        lines += [f"  {ids[a]} --> {ids[b]}" for a, b in produces + reads]
        return "\n".join(lines)
    if fmt != "text":
        raise ValueError(f"Unknown graph format {fmt!r}: use text, dot or mermaid.")
    lines = ["Data sources:"]
    for name, source in build.catalog.sources.items():
        origin = ", ".join(build.relative(p) for p in source.producers) if source.producers else build.relative(source.path)
        arrow = "←" if source.producers else "="
        lines.append(f"  {name} {arrow} {origin}")
    lines.append("Steps:")
    for step in build.steps.values():
        record = build.records.get(step.id)
        if record is None:
            lines.append(f"  {step.id}  (not built yet: what it reads is recorded on the first build)")
        else:
            lines.append(f"  {step.id}  reads: {', '.join(record.get('data', [])) or 'no data sources'}")
    return "\n".join(lines)
