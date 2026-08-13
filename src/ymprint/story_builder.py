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

# Explicit list constructs. These are intercepted structurally in build_story
# (not registered blocks): a bare YAML list is a sequence of content items, while
# bullets/numbers are opt-in via these codes. A trailing `_suffix` is allowed for
# uniqueness within a mapping, consistent with other block codes.
LIST_BLOCK_PATTERN = re.compile(r"^_(ul|ol)(?:_|$)")


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


def build_story(source_data: dict | list, context: dict, level: int = 0) -> list:
    """
    Returns a list of Flowables generated from 'source_data' and 'context'
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

        # Explicit unordered / ordered lists are structural, intercepted before any
        # heading or block dispatch.
        list_block = _extract_list_block(k, v)
        if list_block is not None:
            kind, items = list_block
            if kind == "ul":
                story.extend(convert_ul(items, context))
            else:
                story.extend(convert_ol(items, context))
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
                    heading = convert_paragraph(k, context, heading_style_name)
                    story.extend(heading)

        if check_for_variable(v, context):
            raise YMPrintSyntaxException(
                f"The variable syntax of $VAR is intended to be used with in custom blocks only. "
                "To evaluate a string representation of the variable use the {{VAR}} syntax instead."
            )
        if check_for_paragraph(v, context):
            paragraph = convert_paragraph(v, context)
            story.extend(paragraph)
        elif check_for_tables(v, context):
            table = convert_table(v, context)
            story.extend(table)
        elif isinstance(v, (list, dict)):
            # A bare list/mapping is a sequence of content items: strings become
            # paragraphs, mappings become subsections. Bullets/numbers require _ul/_ol.
            story.extend(build_story(v, context, level=level + 1))
            continue
        else:
            continue
    return story