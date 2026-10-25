from reportlab.platypus import HRFlowable
from ..config.helpers import parse_width, YMPrintValueError
from typing import Any
import pathlib

import json

def convert_loadjson_block(block_key: str, block_value: dict, context: dict) -> list:
    """
    Loads a JSON file into the vars in the context
    """
    file_path = pathlib.Path(block_value['path'])
    json_path = pathlib.Path(context['base_dir']).resolve() / file_path
    if not json_path.exists():
        raise YMPrintValueError(
            f"The loadjson block {block_key} file path does not exist: {json_path}"
        )
    with open(json_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    namespace = block_value.get('namespace')
    if namespace is not None:
        context['vars'][namespace] = data
    else:
        context['vars'].update(data)
        
    return []
