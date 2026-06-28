from reportlab.platypus import HRFlowable
from . import register_block
from ..config.helpers import parse_width, YMPrintValueError
from typing import Any
import pathlib

import json

def convert_loadjson_block(block_key: str, block_value: dict, context: dict) -> list:
    """
    Loads a JSON file into the vars in the context
    """
    file_path = pathlib.Path(block_value['path'])
    source_path = pathlib.Path(context['source_path']).resolve()
    json_path = source_path.parent / file_path
    if not json_path.exists():
        raise YMPrintValueError(
            f"The loadjson block {block_key} file path does not exist: {json_path}"
        )
    with open(json_path, 'r') as file:
        data = json.load(file)
    namespace = block_value.get('namespace')
    if namespace is not None:
        context['vars'][namespace] = data
    else:
        context['vars'] = context['vars'].update(**data)
        
    return []


register_block("_loadjson", convert_loadjson_block)