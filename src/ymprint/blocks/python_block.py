from reportlab.platypus import XPreformatted
from . import register_block
from typing import Callable



def convert_python_block(block_key: str, block_value: dict, context: dict) -> list[XPreformatted]:
    # Need an admonition block style or style modification
    source = block_value['source']
    exec(source, locals=context['vars'])
    if block_value.get("echo", True):
        return []
    return []


register_block("_py", convert_python_block)