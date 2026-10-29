
from .content_checks import (
    check_for_paragraph,
    check_for_tables,
    check_for_variable,
)
from .content_converters import (
    convert_paragraph,
    convert_table,
    is_table_data,
    convert_ul,
    convert_ol,
)
from .exceptions import YMPrintSyntaxException
from .blocks import convert_blocks, get_variable_name
from .blocks.registry import parse_block_key
from .slides import build_slide, _extract_slide_directive, _misplaced_directive_message

TEXTSTYLE_BLOCK = "_textstyle"

# Explicit list constructs. These are intercepted structurally in build_story
# (not registered blocks): a bare YAML list is a sequence of content items, while
# bullets/numbers are opt-in via these codes. A trailing `_id` is allowed for
# uniqueness within a mapping, consistent with other block codes.
LIST_BLOCK_CODES = {"_ul": "ul", "_ol": "ol"}


def _list_kind(key):
    parsed = parse_block_key(key)
    return LIST_BLOCK_CODES.get(parsed[0]) if parsed is not None else None


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
    kind = _list_kind(k)
    if kind is not None:
        return kind, v
    if k is None and isinstance(v, dict) and len(v) == 1:
        (only_key, only_value), = v.items()
        kind = _list_kind(only_key)
        if kind is not None:
            return kind, only_value
    return None


def _leading_textstyle(value, context: dict):
    """
    If `value`'s leading content item(s) are `_textstyle` switches, returns the
    style name they select (the last one in the leading run), else None.

    This lets a section heading adopt a text style assigned at the top of its own
    content — writing `_textstyle` as the first item under a heading restyles the
    whole section, heading included.
    """
    if isinstance(value, dict):
        items = list(value.items())
    elif isinstance(value, list):
        items = [(None, elem) for elem in value]
    else:
        return None
    resolved = None
    for k, v in items:
        style_name = _extract_textstyle(k, v)
        if style_name is None:
            break
        resolved = _resolve_style(style_name, context)
    return resolved


def _slide_mode(context: dict) -> bool:
    doctemplate = context.get("doctemplate", {}).get("ymprint")
    return bool(getattr(doctemplate, "slides", False))


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
    registered_blocks = context["blocks"]
    # In slide mode each top-level heading is one slide on its own page.
    slides_at_this_level = level == 0 and _slide_mode(context)
    slide_count = 0

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

        # `_slide` / `_frame` are consumed by the slide builder at the top of a slide's
        # content. Reaching here means one was used somewhere else.
        directive = _extract_slide_directive(k, v)
        if directive is not None:
            raise YMPrintSyntaxException(_misplaced_directive_message(directive[0], context))

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
            parsed = parse_block_key(k)
            if parsed is not None and parsed[0] in registered_blocks:
                story.extend(convert_blocks(k, v, context))
                continue
            else:
                if heading_level == 0:
                    heading_level = 1
                if slides_at_this_level:
                    story.extend(build_slide(k, v, context, current_style, first=slide_count == 0))
                    slide_count += 1
                    continue
                heading_style_name = f"h{heading_level}"
                if check_for_paragraph(k, context):
                    # If this section's content opens with a `_textstyle` switch, the
                    # heading adopts that style too, so the whole section (title
                    # included) is styled uniformly.
                    heading_style = _leading_textstyle(v, context) or current_style
                    heading = convert_paragraph(k, context, heading_style_name, heading_style)
                    story.extend(heading)

        story.extend(build_content(v, context, level, current_style))
    return story


def build_content(value, context: dict, level: int = 0, current_style: str = "default") -> list:
    """
    Returns the flowables for a section's content 'value' (the value under a heading,
    or a single list item) found at 'level'.
    """
    if check_for_variable(value, context):
        return convert_variable(value, context)
    if check_for_paragraph(value, context):
        return convert_paragraph(value, context, "body", current_style)
    if check_for_tables(value, context):
        return convert_table(value, context)
    if isinstance(value, (list, dict)):
        # A bare list/mapping is a sequence of content items: strings become
        # paragraphs, mappings become subsections. Bullets/numbers require _ul/_ol.
        return build_story(value, context, level=level + 1, current_style=current_style)
    return []


def convert_variable(value: str, context: dict) -> list:
    """
    Returns the flowables for a `$var` used as content. Tabular data (a list of
    mappings) renders as a table; anything else is an error.
    """
    name = get_variable_name(value)
    variables = context["vars"]
    if name not in variables:
        raise YMPrintSyntaxException(f"{value} is used as content but no variable {name!r} is defined.")
    data = variables[name]
    if is_table_data(data):
        return convert_table(data, context, templated=False)
    raise YMPrintSyntaxException(
        f"{value} is a {type(data).__name__}, but a $VAR used as content must be a table: "
        "a list of mappings (one per row). To show a value as text, use {{" + name + "}} instead."
    )
