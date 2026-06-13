from reportlab.platypus import PageBreak
from . import register_block



def convert_page_break(obj: dict, context: dict) -> list[PageBreak]:
    # Need an admonition block style or style modification
    return [PageBreak()]


register_block("_pagebreak", convert_page_break)