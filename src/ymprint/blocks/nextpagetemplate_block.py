from typing import Any

from reportlab.platypus import NextPageTemplate

from . import register_block
from ..exceptions import YMPrintSyntaxException


def convert_next_page_template(block_key: str, block_value: Any, context: dict) -> list:
    """
    Sets the page template to switch to at the next page break, without inserting
    a break itself. The value is the name or 0-based index of the page template.
    """
    doctemplate = context['doctemplate']['ymprint']
    try:
        template_id = doctemplate.resolve_template_id(block_value)
    except ValueError as exc:
        raise YMPrintSyntaxException(str(exc)) from exc
    return [NextPageTemplate(template_id)]


register_block("_nextpagetemplate", convert_next_page_template)
