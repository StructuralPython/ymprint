from reportlab.platypus import Table, Paragraph, Spacer
from . import register_block
from typing import Callable, Any
from . import blockstyles

def generate_admonition_block(kind: str) -> Callable:
    """
    Returns a callable to render that particular admonition type
    """
    

    def convert_admonition_block(block_key: str, block_value: Any, context: dict) -> list[Table| Spacer]:
        # Need an admonition block style or style modification
        available_width = context['frames']['all_pages']['width']
        width_ratio = 0.8
        block_width = width_ratio * available_width
        value = block_value
        tablestyle = blockstyles.get_table_style(kind)
        body_textstyle = blockstyles.get_text_styles().get(f'admonition_{kind}_body')
        title_textstyle = blockstyles.get_text_styles().get(f'admonition_{kind}_title')
        notice = Paragraph(text=blockstyles.admonition_title_text(kind), style=title_textstyle)
        content = Paragraph(text=value, style=body_textstyle)
        table = Table(
            data=[[notice], [content]],
            colWidths=[block_width],
            style=tablestyle
        )    
        return [table, Spacer(1, 10)]
    
    return convert_admonition_block


register_block("_info", generate_admonition_block("info"))
register_block("_warning", generate_admonition_block("warning"))
register_block("_danger", generate_admonition_block("danger"))
register_block("_tip", generate_admonition_block("tip"))
register_block("_note", generate_admonition_block("note"))