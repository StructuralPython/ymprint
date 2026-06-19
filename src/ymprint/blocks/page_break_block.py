from reportlab.platypus import PageBreak
from . import register_block



def convert_page_break(block_key: str, block_value: Any, context: dict) -> list[PageBreak]:
    return [PageBreak()]


register_block("_pagebreak", convert_page_break)