from reportlab.platypus import Table, Paragraph
from . import register_block
from typing import Callable, Any
from . import blockstyles



def convert_info_block(block_key: str, block_value: Any, context: dict) -> list[Table]:
    # Need an admonition block style or style modification
    available_width = context['frames']['all_pages']['width']
    width_ratio = 0.8
    block_width = width_ratio * available_width
    style = context["styles"]["rl"]['_style']['body']
    value = block_value
    tablestyle = blockstyles.get_table_style('info')
    body_textstyle = blockstyles.get_text_styles().get('admonition_info_body')
    title_textstyle = blockstyles.get_text_styles().get('admonition_info_title')
    notice = Paragraph(text=blockstyles.admonition_title_text('info'), style=title_textstyle)
    content = Paragraph(text=value, style=body_textstyle)
    table = Table(
        data=[[notice], [content]],
        colWidths=[block_width],
        style=tablestyle
    )    
    return [table]


register_block("_info", convert_info_block)