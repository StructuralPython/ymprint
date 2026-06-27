from reportlab.platypus import Table, KeepTogether
from . import register_block
from .code_block_styles import python_code_block
from typing import Callable



def convert_python_block(block_key: str, block_value: dict, context: dict) -> list[KeepTogether]:
    # Need an admonition block style or style modification
    source = block_value['source']
    caption = block_value.get('caption')
    line_numbers = block_value.get('line_numbers')
    width_ratio = block_value.get('width_ratio', 0.75)
    available_width = context['frames']['all_pages']['width']
    text_spacing = context['styles']['ymprint'].body.spacing
    text_size = context['styles']['ymprint'].body.size
    space_around = text_spacing * text_size
    namespace = block_value.get('namespace')
    if namespace is not None:
        context['vars'][namespace] = {}
    local_namespace = context['vars'][namespace] if namespace is not None else context['vars']
    exec(source, globals=context['vars'], locals=local_namespace)
    if block_value.get("echo", True):
        code_block = python_code_block(source, available_width * width_ratio, context, caption=caption, show_line_numbers=line_numbers)
        code_block.spaceBefore = space_around
        code_block.spaceAfter = space_around
        return [KeepTogether(code_block)]
    return []


register_block("_py", convert_python_block)