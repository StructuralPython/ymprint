from reportlab.platypus import Table, Paragraph, Spacer, KeepTogether
from . import register_block
from typing import Callable, Any
from . import blockstyles
from ..story_builder import build_story

def convert_admonition_block(block_key: str, block_value: Any, context: dict) -> list[KeepTogether | Spacer]:
    # Need an admonition block style or style modification
    heading = block_value['heading']
    body = block_value['body']

    heading_flowables = [Paragraph(heading, style=context['styles']['rl']['h1'],)]
    body_flowables = build_story(body, context)

    available_width = context['frames']['all_pages']['width']
    width_ratio = 0.8
    block_width = width_ratio * available_width
    slide_tablestyle = ()
    table = Table(
        data=[[heading_flowables], [body_flowables]],
        colWidths=[block_width],
        rowHeights=[0.2, 0.8],
        style=slide_tablestyle,
    )    
    return [KeepTogether(table), Spacer(1, 10)]