import re

from .content_checks import (
    check_for_paragraph,
    check_for_tables,
    check_for_variable,
)
from .content_converters import (
    convert_paragraph,
    convert_table,
    convert_ul,
    convert_ol,
)
from .exceptions import YMPrintSyntaxException
from .blocks import get_block_callable, list_blocks, convert_blocks

TEXTSTYLE_BLOCK = "_textstyle"

# Explicit list constructs. These are intercepted structurally in build_story
# (not registered blocks): a bare YAML list is a sequence of content items, while
# bullets/numbers are opt-in via these codes. A trailing `_suffix` is allowed for
# uniqueness within a mapping, consistent with other block codes.
LIST_BLOCK_PATTERN = re.compile(r"^_(ul|ol)(?:_|$)")


def _extract_textstyle(k, v):
    """
    Returns the style name if this element is a `_textstyle` switch, else None.
    Handles both the mapping-key form (`_textstyle: name`) and the single-key
    list-item form (`- _textstyle: name`).
    """
    if k == TEXTSTYLE_BLOCK:
        return v
    if k is None and isinstance(v, dict) and list(v.keys()) == [TEXTSTYLE_BLOCK]:
        return v[TEXTSTYLE_BLOCK]
    return None


def _resolve_style(style_name, context: dict) -> str:
    families = context["styles"].get("families", {})
    if style_name in families:
        return style_name
    raise YMPrintSyntaxException(
        f"Text style {style_name!r} not found. Available styles: {list(families.keys())}"
    )


def _extract_list_block(k, v):
    """
    Returns (kind, items) when this element is a `_ul`/`_ol` construct, else None.
    Handles both the heading-value form (`_ul: [...]`) and the single-key list-item
    form (`- _ul: [...]`).
    """
    key = value = None
    if isinstance(k, str) and LIST_BLOCK_PATTERN.match(k):
        key, value = k, v
    elif k is None and isinstance(v, dict) and len(v) == 1:
        (only_key, only_value), = v.items()
        if isinstance(only_key, str) and LIST_BLOCK_PATTERN.match(only_key):
            key, value = only_key, only_value
    if key is None:
        return None
    kind = LIST_BLOCK_PATTERN.match(key).group(1)
    return kind, value


def build_story(source_data: dict | list, context: dict, level: int = 0, current_style: str = "default") -> list:
    """
    Returns a list of Flowables generated from 'source_data' and 'context'.

    'current_style' is the active text style family for this frame. It is a plain
    parameter (not shared state): a `_textstyle` switch updates it for the rest of
    this frame's siblings and is inherited by descendant frames, then reverts
    automatically when the frame returns.
    """
    story = []
    if isinstance(source_data, dict):
        source_iter = source_data.items()
    elif isinstance(source_data, list):
        source_iter = iter(source_data)
    registered_blocks = list_blocks()

    for elem in source_iter:
        # print(f"{level=} | {elem=}")
        if isinstance(elem, tuple):
            k, v = elem
        else:
            k = None
            v = elem

        # Intercept a text-style switch before any other dispatch. It changes parse
        # state (the active family) rather than producing a flowable.
        style_name = _extract_textstyle(k, v)
        if style_name is not None:
            current_style = _resolve_style(style_name, context)
            continue

        # Explicit unordered / ordered lists are structural, intercepted before any
        # heading or block dispatch. They honour the active text style.
        list_block = _extract_list_block(k, v)
        if list_block is not None:
            kind, items = list_block
            if kind == "ul":
                story.extend(convert_ul(items, context, current_style=current_style))
            else:
                story.extend(convert_ol(items, context, current_style=current_style))
            continue

        if k is not None:
            heading_level = level
            if str(k).startswith(tuple(registered_blocks)):
                story.extend(convert_blocks(k, v, context))
                continue
            else:
                if heading_level == 0:
                    heading_level = 1
                heading_style_name = f"h{heading_level}"
                if check_for_paragraph(k, context):
                    heading = convert_paragraph(k, context, heading_style_name, current_style)
                    story.extend(heading)

        if check_for_variable(v, context):
            raise YMPrintSyntaxException(
                f"The variable syntax of $VAR is intended to be used with in custom blocks only. "
                "To evaluate a string representation of the variable use the {{VAR}} syntax instead."
            )
        if check_for_paragraph(v, context):
            paragraph = convert_paragraph(v, context, "body", current_style)
            story.extend(paragraph)
        elif check_for_tables(v, context):
            table = convert_table(v, context)
            story.extend(table)
        elif isinstance(v, (list, dict)):
            # A bare list/mapping is a sequence of content items: strings become
            # paragraphs, mappings become subsections. Bullets/numbers require _ul/_ol.
            story.extend(build_story(v, context, level=level + 1, current_style=current_style))
            continue
        else:
            continue
    return story
