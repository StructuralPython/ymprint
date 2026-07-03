from .content_checks import (
    check_for_paragraph,
    check_for_ordered_nested_lists,
    check_for_subelements,
    check_for_tables,
    check_for_nested_lists,
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
            paragraph = convert_paragraph(v,context)
            story.extend(paragraph)
        elif check_for_nested_lists(v, context):
            ul = convert_ul(v,context)
            story.extend(ul)
        elif check_for_ordered_nested_lists(v, context):
            ol = convert_ol(v,context)
            story.extend(ol)
        elif check_for_tables(v, context):
            table = convert_table(v,context)
            story.extend(table)
        elif check_for_subelements(v, context):
            story.extend(build_story(v, context, level = level + 1))
            continue
        else:
            continue
    return story