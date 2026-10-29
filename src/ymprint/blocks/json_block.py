from ..config.helpers import YMPrintValueError
from ..data_sources import load_file
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
