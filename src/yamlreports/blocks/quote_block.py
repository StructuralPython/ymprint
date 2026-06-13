from reportlab.platypus import Table, Paragraph
from . import register_block
from typing import Callable



def convert_quote_block(obj: dict, context: dict) -> list[Table]:
    # Need an admonition block style or style modification
    available_width = context['frames']['all_pages']['width']
    width_ratio = 0.8
    block_width = width_ratio * available_width
    style = context["styles"]["rl"]['_style']['body']
    notice = Paragraph(text="<b>Info</b>", style=style)
    key = next(iter(obj.keys()))
    value = obj[key]
    content = Paragraph(text=value, style=style)
    table = Table(
        data=[[notice], [content]],
        colWidths=[block_width],
    )    
    return [table]


register_block("_quote", convert_quote_block)