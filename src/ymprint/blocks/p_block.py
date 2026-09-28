from reportlab.platypus import Paragraph, Spacer
from . import register_block
from ..content_converters import convert_paragraph
from ..exceptions import YMPrintSyntaxException


def _resolve_family(style_name: str, context: dict) -> str:
    """
    Returns 'style_name' if it names a known text style family, else raises.

    Kept local (rather than importing story_builder._resolve_style) to avoid a
    circular import: story_builder imports the block registry from this package.
    """
    families = context["styles"].get("families", {})
    if style_name in families:
        return style_name
    raise YMPrintSyntaxException(
        f"Text style {style_name!r} not found. Available styles: {list(families.keys())}"
    )


def convert_p_block(block_key: str, block_value, context: dict) -> list[Paragraph | Spacer]:
    """
    Renders a standalone paragraph, so an author can emit body text after another
    block without first introducing a heading key.

    'block_value' is either a bare string (the paragraph text, default style) or a
    mapping with:
        content / text : the paragraph text (required)
        style          : a named text style family (default 'default')
    """
    if isinstance(block_value, str):
        text, style_name = block_value, "default"
    elif isinstance(block_value, dict):
        if "content" in block_value:
            text = block_value["content"]
        elif "text" in block_value:
            text = block_value["text"]
        else:
            raise YMPrintSyntaxException(
                f"The '{block_key}' block requires a 'content' (or 'text') attribute."
            )
        style_name = block_value.get("style", "default")
    else:
        raise YMPrintSyntaxException(
            f"The '{block_key}' block value must be a string or a mapping, "
            f"got {type(block_value).__name__}."
        )

    family = _resolve_family(style_name, context)
    return convert_paragraph(str(text), context, "body", family)


register_block("_p", convert_p_block)
