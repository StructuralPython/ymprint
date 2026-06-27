from reportlab.platypus import Table, Paragraph
from . import register_block
from typing import Callable
from . import blockstyles



def convert_quote_block(block_key: str, block_value: dict, context: dict) -> list[Table]:
    # Need an admonition block style or style modification
    available_width = context['frames']['all_pages']['width']
    width_ratio = 0.8
    block_width = width_ratio * available_width
    styles = blockstyles.get_text_styles()
    quote_para = Paragraph(block_value['quote'], styles["blockquote_body"])
    rows = [[quote_para]]
    attribution = block_value.get('attribution')
    if attribution is not None:
        attr_text = f"\u2014 {attribution}"   # em-dash prefix
        attr_para = Paragraph(attr_text, styles["blockquote_attribution"])
        rows.append([attr_para])
 
    tbl = Table(rows, colWidths=[block_width], style=blockstyles.get_table_style("blockquote"))
    return [tbl]

register_block("_blockquote", convert_quote_block)