"""
Rendering one document once per parameter set.

The project config, not the document, says which renders of a document exist
and where they go. The document is a template that just uses its variables:

    # project.ymprint.yml
    _render:
      5-validation/beams/calc.yml:
        for_each: "[m for m in design if m.startswith('B')]"
        as: member_name
        output: build/beams/{{ member_name }}.pdf

`for_each` is a Python expression evaluated with the document's variables
(its `_vars` and `_data`) as globals. Each item is one parameter set: bound to
the name(s) in `as`, or, without `as`, a mapping of variable names to values.
"""
from __future__ import annotations

import pathlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

from jinja2 import Environment, StrictUndefined
from jinja2.exceptions import UndefinedError
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from .data_sources import config_declarations
from .errors import BlockError, PythonBlockError, YmprintAuthoringError
from .render import RenderCallbackError, RenderEvent

RENDER_KEYS = {"for_each", "as", "output", "key"}

_strict_env = Environment(undefined=StrictUndefined)


class RenderUsageError(ValueError):
    """A render was asked for in a way the document's `_render` entry does not allow."""


class RenderSpecError(YmprintAuthoringError):
    """A `_render` entry is invalid, or its parameter sets could not be built."""


@dataclass(frozen=True)
class RenderSpec:
    """One `_render` entry: how a document is rendered, and where to."""

    document: pathlib.Path
    # The config file that declares it; `output` resolves against its directory.
    declared_in: pathlib.Path
    for_each: Optional[str] = None
    as_: tuple[str, ...] = ()
    output: Optional[str] = None
    key: Optional[str] = None

    @property
    def fans_out(self) -> bool:
        return self.for_each is not None


def parse_render_specs(declarations: Any, declared_in: pathlib.Path) -> dict[pathlib.Path, RenderSpec]:
    """Returns {document path: RenderSpec} for the `_render` mapping of one config file."""
    where = str(declared_in)
    if not isinstance(declarations, Mapping):
        raise RenderSpecError(f"`_render` in {where} must be a mapping of document paths to render options.")
    specs = {}
    for document, options in declarations.items():
        options = options or {}
        if not isinstance(options, Mapping):
            raise RenderSpecError(f"`_render` entry {document!r} in {where} must be a mapping of options.")
        unknown = set(options) - RENDER_KEYS
        if unknown:
            raise RenderSpecError(
                f"`_render` entry {document!r} in {where} has unknown option(s) {sorted(unknown)}. "
                f"Choose from: {sorted(RENDER_KEYS)}."
            )
        names = options.get("as") or ()
        if isinstance(names, str):
            names = (names,)
        if any(not isinstance(n, str) or not n.isidentifier() for n in names):
            raise RenderSpecError(f"`as` in `_render` entry {document!r} in {where} must be variable name(s).")
        if names and options.get("for_each") is None:
            raise RenderSpecError(f"`_render` entry {document!r} in {where} has `as` but no `for_each`.")
        path = (declared_in.parent / str(document)).resolve()
        specs[path] = RenderSpec(
            document=path,
            declared_in=declared_in,
            for_each=None if options.get("for_each") is None else str(options["for_each"]),
            as_=tuple(names),
            output=None if options.get("output") is None else str(options["output"]),
            key=None if options.get("key") is None else str(options["key"]),
        )
    return specs


def render_specs(config_paths: Iterable[pathlib.Path]) -> dict[pathlib.Path, RenderSpec]:
    """Returns the `_render` entries of the config layers; a higher layer's entry wins."""
    specs: dict[pathlib.Path, RenderSpec] = {}
    for declarations, path in config_declarations(config_paths, "_render"):
        specs.update(parse_render_specs(declarations, path))
    return specs


@dataclass(frozen=True)
class Instance:
    """One render of a document: its parameter set, PDF and key."""

    params: dict
    destination: pathlib.Path
    # Names this render among the document's renders (e.g. "B01").
    key: str


def render_template_strict(template: str, variables: Mapping, what: str) -> str:
    try:
        return _strict_env.from_string(template).render(variables)
    except UndefinedError as exc:
        raise RenderSpecError(f"{what} {template!r}: {exc}. Available: {sorted(variables)}") from exc


def parameter_sets(spec: RenderSpec, variables: Mapping) -> list[dict]:
    """Evaluates spec.for_each with 'variables' as globals; returns one dict per render."""
    where = f"`for_each` of {spec.document.name}"
    try:
        items = eval(spec.for_each, variables)
    except Exception as exc:
        raise RenderSpecError(f"{where} raised {type(exc).__name__}: {exc}") from exc
    if isinstance(items, (str, bytes)) or not isinstance(items, Iterable):
        raise RenderSpecError(f"{where} must give a list, not {type(items).__name__}.")
    sets = []
    for item in items:
        if len(spec.as_) == 1:
            sets.append({spec.as_[0]: item})
        elif spec.as_:
            if not isinstance(item, Sequence) or isinstance(item, str) or len(item) != len(spec.as_):
                raise RenderSpecError(f"{where}: item {item!r} does not unpack into {list(spec.as_)}.")
            sets.append(dict(zip(spec.as_, item)))
        elif isinstance(item, Mapping) and all(isinstance(k, str) and k.isidentifier() for k in item):
            sets.append(dict(item))
        else:
            raise RenderSpecError(
                f"{where}: item {item!r} is not a mapping of variable names to values. "
                "Give the `_render` entry an `as:` to name each item."
            )
    return sets


def instance_key(spec: RenderSpec, params: dict) -> str:
    if spec.key is not None:
        return render_template_strict(spec.key, params, "`key`")
    return "-".join(str(value) for value in params.values())


def build_instances(spec: Optional[RenderSpec], source: pathlib.Path, variables: Mapping) -> list[Instance]:
    """
    Returns the renders of the document at 'source' under 'spec' (which may be
    None: one render, next to the source).
    """
    if spec is None or not spec.fans_out:
        if spec is not None and spec.output is not None:
            destination = spec.declared_in.parent / render_template_strict(spec.output, {}, "`output`")
        else:
            destination = source.parent / f"{source.stem}.pdf"
        return [Instance(params={}, destination=destination.resolve(), key="")]

    instances = []
    for params in parameter_sets(spec, variables):
        key = instance_key(spec, params)
        if spec.output is not None:
            destination = spec.declared_in.parent / render_template_strict(spec.output, params, "`output`")
        else:
            destination = source.parent / f"{source.stem}-{key}.pdf"
        instances.append(Instance(params=params, destination=destination.resolve(), key=key))

    for attribute in ("destination", "key"):
        seen: dict = {}
        for instance in instances:
            value = getattr(instance, attribute)
            if value in seen:
                raise RenderSpecError(
                    f"Parameter sets {seen[value].params} and {instance.params} of {source.name} "
                    f"have the same {attribute} ({value}). Make `output`/`key` include the parameters."
                )
            seen[value] = instance
    return instances


def matches(params: Mapping, only: Optional[Mapping]) -> bool:
    """Whether a parameter set has every value in 'only' (compared as text)."""
    return all(name in params and str(params[name]) == str(value) for name, value in (only or {}).items())


_scalar_yaml = YAML(typ="safe")


def parse_assignments(pairs: Optional[Sequence[str]], option: str = "--var") -> dict:
    """
    Returns {name: value} for command-line NAME=VALUE pairs. Values are read as
    YAML scalars, so `n=3` is an int and `ok=true` a bool; quote to keep text.
    """
    values = {}
    for pair in pairs or ():
        name, sep, text = pair.partition("=")
        name = name.strip()
        if not sep or not name.isidentifier():
            raise ValueError(f"{option} expects NAME=VALUE, got {pair!r}.")
        try:
            value = _scalar_yaml.load(text) if text.strip() else ""
        except YAMLError:
            value = text
        if isinstance(value, (dict, list)) or value is None:
            value = text
        values[name] = value
    return values


@dataclass
class RenderFailure:
    """A parameter set whose render failed; the others still render."""

    instance: Instance
    error: BaseException

    def describe(self) -> str:
        """A one-line summary, e.g. "B03: KeyError: 'Zx' in _hc block _hc_2"."""
        exc = self.error
        label = self.instance.key or str(self.instance.params)
        if isinstance(exc, PythonBlockError):
            return f"{label}: {exc} in {exc.block_key}"
        if isinstance(exc, RenderCallbackError):
            return f"{label}: {exc}"
        if isinstance(exc, (BlockError, YmprintAuthoringError)):
            return f"{label}: {exc}"
        return f"{label}: {type(exc).__name__}: {exc}"


@dataclass
class RenderRun:
    """The renders of one document: one per parameter set (or just one)."""

    source: pathlib.Path
    spec: Optional[RenderSpec]
    instances: list[Instance] = field(default_factory=list)
    results: list[RenderEvent] = field(default_factory=list)
    failures: list[RenderFailure] = field(default_factory=list)
    # Every data file read: by `for_each` and by each render.
    inputs: set[pathlib.Path] = field(default_factory=set)
    # The key of each result, in order.
    keys: list[str] = field(default_factory=list)
    # The document's exports: its `_export` values, or with parameter sets,
    # {key: values} for every set. None when it has no `_export`.
    exports: Optional[dict] = None
    # The export files written, and notes on exports that were not.
    written: list[pathlib.Path] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures
