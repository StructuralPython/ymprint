from collections.abc import Mapping

from ..config.helpers import YMPrintValueError
from ..content_converters import render_template
from ..data_sources import load_file
from ..exports import dumps, write_text_atomic
import pathlib


def convert_loadjson_block(block_key: str, block_value: dict, context: dict) -> list:
    """
    Loads a JSON file into the vars in the context.

    Prefer a `_data` entry, which names the file once for the whole project;
    `_loadjson` reads it the same way (cached, path relative to the document).
    """
    file_path = pathlib.Path(block_value['path'])
    json_path = (pathlib.Path(context['base_dir']) / file_path).resolve()
    if 'data' in context:
        # Recorded even when missing, so live mode re-renders once it exists.
        context['data'].record_file(json_path)
    if not json_path.exists():
        raise YMPrintValueError(
            f"The loadjson block {block_key} file path does not exist: {json_path}"
        )
    data = load_file(json_path, "json")
    namespace = block_value.get('namespace')
    if namespace is not None:
        context['vars'][namespace] = data
    else:
        context['vars'].update(data)

    return []


def convert_dumpjson_block(block_key: str, block_value: dict, context: dict) -> list:
    """
    Writes the named vars to a JSON file, the counterpart of `_loadjson`.

    'vars' names variables defined so far in the document; a dotted name
    ("beam.span") is looked up in, and written as, nested mappings. With a
    'namespace', names are looked up inside that mapping and written flat, so
    `_loadjson` with the same namespace reads them back. 'path' may be a
    template and is relative to the document. The file is replaced whole, and
    left untouched when its content would not change (so a document that also
    loads it does not re-render itself forever in live mode).
    """
    if not isinstance(block_value, Mapping) or 'path' not in block_value or 'vars' not in block_value:
        raise YMPrintValueError(f"The {block_key} block needs a `path` and a list of `vars`.")
    names = block_value['vars']
    if isinstance(names, str):
        names = [names]
    if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
        raise YMPrintValueError(f"The {block_key} block's `vars` must be a list of variable names.")

    source = context['vars']
    namespace = block_value.get('namespace')
    if namespace is not None:
        source = _lookup(source, str(namespace), block_key)
        if not isinstance(source, Mapping):
            raise YMPrintValueError(f"The {block_key} block's namespace {namespace!r} is not a mapping.")

    data: dict = {}
    for name in names:
        _insert(data, name.split('.'), _lookup(source, name, block_key), name, block_key)

    path_text = render_template(str(block_value['path']), context['vars'])
    json_path = (pathlib.Path(context['base_dir']) / path_text).resolve()
    try:
        text = dumps(data)
    except (TypeError, ValueError) as exc:
        raise YMPrintValueError(f"The {block_key} block could not write {json_path}: {exc}") from exc
    if not (json_path.exists() and json_path.read_text(encoding="utf-8") == text):
        write_text_atomic(json_path, text)
    return []


def _lookup(source: Mapping, name: str, block_key: str):
    value = source
    for i, part in enumerate(name.split('.')):
        if not isinstance(value, Mapping) or part not in value:
            missing = '.'.join(name.split('.')[:i + 1])
            raise YMPrintValueError(f"The {block_key} block: no variable {missing!r} is defined.")
        value = value[part]
    return value


class _Nested(dict):
    """A mapping made for a dotted name, as opposed to a variable's own dict value."""


def _insert(data: dict, parts: list, value, name: str, block_key: str) -> None:
    for part in parts[:-1]:
        data = data.setdefault(part, _Nested())
        if not isinstance(data, _Nested):
            break
    else:
        if parts[-1] not in data:
            data[parts[-1]] = value
            return
    raise YMPrintValueError(f"The {block_key} block: {name!r} overlaps another name in `vars`.")
