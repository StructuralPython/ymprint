from typing import Any

from reportlab.platypus import PageBreak, NextPageTemplate

from . import register_block
from ..exceptions import YMPrintSyntaxException


def convert_page_break(block_key: str, block_value: Any, context: dict) -> list:
    """
    Inserts a page break. If a value is supplied, it is the name or 0-based index
    of the page template to use for the pages that follow the break.
    """
    if block_value is None or block_value == "":
        return [PageBreak()]
    doctemplate = context['doctemplate']['ymprint']
    try:
        template_id = doctemplate.resolve_template_id(block_value)
    except ValueError as exc:
        raise YMPrintSyntaxException(str(exc)) from exc
    return [NextPageTemplate(template_id), PageBreak()]


register_block("_pagebreak", convert_page_break)
