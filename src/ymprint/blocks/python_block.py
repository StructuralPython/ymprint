from reportlab.platypus import Table
from . import register_block
from .code_block_styles import python_code_block
from typing import Callable



def convert_python_block(block_key: str, block_value: dict, context: dict) -> list[Table]:
    # Need an admonition block style or style modification
    source = block_value['source']
    caption = block_value.get('caption')
    line_numbers = block_value.get('line_numbers')
    width_ratio = block_value.get('width_ratio', 0.75)
    available_width = context['frames']['all_pages']['width']
    exec(source, locals=context['vars'])
    if block_value.get("echo", True):
        code_block = python_code_block(source, available_width * width_ratio, caption=caption, show_line_numbers=line_numbers)
        return [code_block]
    return []


register_block("_py", convert_python_block)