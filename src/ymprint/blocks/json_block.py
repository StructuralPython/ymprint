from reportlab.platypus import HRFlowable
from . import register_block
from ..config.helpers import parse_width
from typing import Any
import pathlib

import json

def convert_loadjson_block(block_key: str, block_value: dict, context: dict) -> list:
    """
    Loads a JSON file into the vars in the context
    """
    file_path = pathlib.Path(block_value['path'])
    source_path = pathlib.Path(context['source_path'])
    if not file_path.absolute:
        file_path = source_path.parent / file_path
    with open(file_path, 'r') as file:
        data = json.load(file)
    context['vars'][block_key] = data
        
    return []


register_block("_loadjson", convert_loadjson_block)