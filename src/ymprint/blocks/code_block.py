from reportlab.platypus import Table, KeepTogether
from . import register_block
from .code_block_styles import generic_code_block
from typing import Callable



def convert_code_block(block_key: str, block_value: dict, context: dict) -> list[KeepTogether]:
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
    code_block = generic_code_block(source, available_width * width_ratio, context, caption=caption, show_line_numbers=line_numbers)
    code_block.spaceBefore = space_around
    code_block.spaceAfter = space_around
    return [KeepTogether(code_block)]


register_block("_code", convert_code_block)