"""
Document exports (`_export`): the values a document produces for later stages.

    _export:
      Vr: $V_r
      section: "{{ design[member_name].section }}"

Exports are evaluated after the document's content is built, so every `_py`
and `_hc` block has run. A `$var` exports the object itself; any other string
is a Jinja template. The `_data` entries that name the document in their
`from:` receive its exports, written whole by ymprint on each full render.
"""
from __future__ import annotations

import json
import numbers
import os
import pathlib
import tempfile
from collections import ChainMap
from collections.abc import Mapping
from typing import Any, Callable

from jinja2 import Environment, StrictUndefined
from jinja2.exceptions import UndefinedError

from .content_checks import check_for_variable
from .errors import YmprintAuthoringError
from .plugins import load_plugins


class ExportError(YmprintAuthoringError):
    """A document's `_export` could not be evaluated or written."""


# --- evaluation ----------------------------------------------------------------

_strict_env = Environment(undefined=StrictUndefined)


def evaluate_exports(declarations: Any, variables: Mapping, where: str) -> dict:
    """
    Returns the values of an `_export` mapping, evaluated against the
    document's 'variables'. 'where' names the document (and parameter set) in
    errors.
    """
    if not isinstance(declarations, Mapping):
        raise ExportError(f"`_export` in {where} must be a mapping of names to values.")
    return {name: _evaluate(value, variables, where, str(name)) for name, value in declarations.items()}


def _evaluate(value: Any, variables: Mapping, where: str, name: str) -> Any:
    if isinstance(value, str) and check_for_variable(value, None):
        var_name = value.lstrip("$")
        if var_name not in variables:
            raise ExportError(f"`_export` {name!r} in {where}: no variable {var_name!r} is defined.")
        return variables[var_name]
    if isinstance(value, str):
        if "{" not in value:
            return value
        try:
            # The variables are the context itself, not a copy, so lazy `_data`
            # sources load only if used (see content_converters.render_template).
            template = _strict_env.from_string(value)
            context = template.new_context(ChainMap(variables, template.globals), shared=True)
            return _strict_env.concat(template.root_render_func(context))
        except UndefinedError as exc:
            raise ExportError(f"`_export` {name!r} in {where}: {exc}.") from exc
    if isinstance(value, Mapping):
        return {k: _evaluate(v, variables, where, f"{name}.{k}") for k, v in value.items()}
    if isinstance(value, list):
        return [_evaluate(v, variables, where, f"{name}[{i}]") for i, v in enumerate(value)]
    return value


# --- serialization -------------------------------------------------------------

Serializer = Callable[[Any], Any]
Decoder = Callable[[dict], Any]

# A serialized value may be a mapping tagged with its type under this key, e.g.
# {"$type": "forallpeople.Physical", ...}; the decoder registered for the tag
# turns it back into the value when the JSON is read.
TYPE_KEY = "$type"

_SERIALIZERS: list[tuple[type, Serializer]] = []
_DECODERS: dict[str, Decoder] = {}


def register_serializer(type_: type, serializer: Serializer) -> None:
    """
    Registers serializer(value) -> JSON-native data for exported values of
    'type_' (and its subclasses). Later registrations take precedence. To be
    read back as the same type, return a mapping tagged with TYPE_KEY and
    register a decoder for the tag.
    """
    _SERIALIZERS.insert(0, (type_, serializer))


def register_decoder(tag: str, decoder: Decoder) -> None:
    """
    Registers decoder(mapping) -> value for JSON mappings whose TYPE_KEY is
    'tag'. Mappings with an unregistered tag are read as plain dicts.
    """
    _DECODERS[tag] = decoder


def decode_typed(mapping: dict) -> Any:
    """The json.load `object_hook`: rebuilds mappings tagged with a registered type."""
    tag = mapping.get(TYPE_KEY)
    if isinstance(tag, str):
        load_plugins()
        decoder = _DECODERS.get(tag)
        if decoder is not None:
            return decoder(mapping)
    return mapping


def to_json_native(value: Any) -> Any:
    """The json.dumps `default` hook: converts what JSON can't hold natively."""
    load_plugins()
    for type_, serializer in _SERIALIZERS:
        if isinstance(value, type_):
            return serializer(value)
    if isinstance(value, os.PathLike):
        return os.fspath(value)
    if isinstance(value, (set, frozenset)):
        return sorted(value, key=str)
    # Only real numbers: other objects with __float__ (a units quantity, say) may
    # give a scaled or display value, which would be written as a wrong number.
    if isinstance(value, numbers.Real):
        return float(value) if not isinstance(value, numbers.Integral) else int(value)
    raise TypeError(
        f"cannot export a {type(value).__name__} ({value!r}); install a plugin that "
        "serializes it, register a serializer (ymprint.exports.register_serializer), "
        "or export a plain number"
    )


def dumps(data: Any) -> str:
    return json.dumps(data, default=to_json_native, indent=2, ensure_ascii=False)


def write_json_atomic(path: pathlib.Path, data: Any, where: str = "") -> None:
    """
    Writes 'data' as JSON to 'path', all at once: to a temporary file next to
    it, then renamed over it, so a reader never sees a half-written file.
    """
    try:
        text = dumps(data)
    except (TypeError, ValueError) as exc:
        raise ExportError(f"Exports of {where or path.name} could not be written: {exc}") from exc
    write_text_atomic(path, text)


def write_text_atomic(path: pathlib.Path, text: str) -> None:
    """Writes 'text' to 'path' via a temporary file renamed over it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            file.write(text)
        os.replace(temp, path)
    except BaseException:
        pathlib.Path(temp).unlink(missing_ok=True)
        raise


# --- writing a document's exports ------------------------------------------------

def write_exports(run, event, partial: bool = False) -> None:
    """
    Writes 'run's exports (a fanout.RenderRun) to the `_data` entries that name
    its document as a producer. 'event' gives the document's config layers and
    project. 'partial' means only some parameter sets were rendered.
    """
    from .data_sources import DataCatalog

    catalog = DataCatalog.from_config(event.config_paths, None, event.base_dir, None, event.project_root)
    targets = catalog.produced_by(run.source)
    if not targets:
        return
    names = ", ".join(repr(t.name) for t in targets)
    if run.results and run.exports is None:
        raise ExportError(
            f"`_data` {names} names {run.source.name} as a producer (`from:`), "
            f"but {run.source.name} has no `_export`."
        )
    if partial:
        run.notes.append(f"Exports for {names} not written: only some parameter sets were rendered.")
        return
    if not run.ok:
        for target in targets:
            target.output_for(run.source).unlink(missing_ok=True)
        run.notes.append(
            f"Exports for {names} not written, and the previous ones removed: "
            "not every parameter set rendered."
        )
        return
    for target in targets:
        output = target.output_for(run.source)
        write_json_atomic(output, run.exports or {}, where=run.source.name)
        run.written.append(output)
