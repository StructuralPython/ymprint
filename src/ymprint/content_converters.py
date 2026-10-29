from collections import ChainMap
from collections.abc import Mapping
from itertools import cycle
from typing import Optional, TypeAlias, Union
from reportlab.platypus import (
    Paragraph,
    Spacer,
    Table,
    Image,
    HRFlowable,
    ListFlowable,
    KeepTogether,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from jinja2 import Template, Environment, DebugUndefined
from ymprint.config.docstyles import ReportStyles
from .markdown.inline import convert_inline_markdown


RLFlowables: TypeAlias = Union[Paragraph, Spacer, Table, KeepTogether, Image]
jinja_env = Environment(undefined=DebugUndefined)


def render_template(text: str, variables: dict) -> str:
    """
    Returns 'text' rendered as a Jinja template with 'variables'.

    The variables are used as the template's context directly rather than
    copied (as Template.render does), so a lazily loaded `_data` source is only
    read when the template actually uses it.
    """
    template = jinja_env.from_string(text)
    context = template.new_context(ChainMap(variables, template.globals), shared=True)
    try:
        return jinja_env.concat(template.root_render_func(context))
    except Exception:
        return jinja_env.handle_exception()

def _family_sheet(context: dict, current_style: str):
    """Returns the reportlab StyleSheet1 for the active text style family."""
    families = context["styles"].get("families")
    if families is not None and current_style in families:
        return families[current_style]["rl"]
    # Back-compat: fall back to the single default stylesheet.
    return context["styles"]["rl"]["_style"]


def _family_model(context: dict, current_style: str):
    """Returns the ymprint StyleFamily model for the active text style family."""
    families = context["styles"].get("families")
    if families is not None and current_style in families:
        return families[current_style]["ymprint"]
    return context["styles"]["ymprint"]


def _wants_underline(context: dict, text_style: str, current_style: str) -> bool:
    """Whether the active family's style for this role requests an underline."""
    family = _family_model(context, current_style)
    if text_style.startswith("h"):
        return bool(getattr(family.headings, "underline", False))
    return bool(getattr(family.body, "underline", False))


def convert_paragraph(value: str, context: dict, text_style: str = "body", current_style: str = "default") -> list[Paragraph]:
    """Returns a Paragraph obj"""
    style = _family_sheet(context, current_style)[text_style]
    underline = _wants_underline(context, text_style, current_style)
    paragraphs = value.split("\n")
    paras = []
    for para in paragraphs:
        para_md = convert_inline_markdown(para)
        rendered = render_template(para_md, context['vars'])
        if underline:
            rendered = f"<u>{rendered}</u>"
        rl_para = Paragraph(rendered, style=style)
        paras.append(rl_para)

        paras.append(Spacer(1, 5))
    return paras

# Test
def convert_ul(value: list[str], context: dict, level: int = 0, current_style: str = "default") -> list[ListFlowable]:
    ymp_style = _family_model(context, current_style)
    text_spacing = ymp_style.body.spacing
    text_size = ymp_style.body.size
    space_around = text_spacing * text_size / 2
    sheet = _family_sheet(context, current_style)
    # Size the bullet marker to the active body text size so it tracks the text
    # style (rather than the fixed `bullets.size` from config).
    bullet_style = ParagraphStyle('ul-item', parent=sheet['body'], bulletFontSize=text_size)
    bul_symbols = ymp_style.body.bullets.symbols
    level_index = level % len(bul_symbols)
    bul_symbol = bul_symbols[level_index]
    bul_color = ymp_style.body.bullets.rl_color
    bullet_color_hex = "#{:02x}{:02x}{:02x}".format(
        int(bul_color.red),
        int(bul_color.green),
        int(bul_color.blue),
    )
    bullet_contents = []
    for elem in value:
        if isinstance(elem, list):
            # A list item that is itself a list is a nested list: append the nested
            # ListFlowable (not the wrapping python list) so ReportLab indents it.
            sub_bullets = convert_ul(elem, context, level=level + 1, current_style=current_style)
            bullet_contents.extend(sub_bullets)
        else:
            para_md = convert_inline_markdown(elem)
            rendered = render_template(para_md, context['vars'])
            bullet_content = Paragraph(f'<bullet color="{bullet_color_hex}"><b>{bul_symbol}</b></bullet>{rendered}', bullet_style)
            bullet_contents.append(bullet_content)
            
    return [ListFlowable(bullet_contents, start=0, bulletType='bullet', spaceAfter=space_around)]

# Test
def convert_ol(value: list | dict, context: dict, level: int = 0, current_style: str = "default") -> list[ListFlowable]:
    sheet = _family_sheet(context, current_style)
    ymp_style = _family_model(context, current_style)
    # Size the number to the active body text size so it matches the text style.
    bullet_style = ParagraphStyle(
        'ol-item', parent=sheet['body'], bulletFontSize=ymp_style.body.size
    )
    bul_color = ymp_style.body.bullets.rl_color
    bullet_color_hex = "#{:02x}{:02x}{:02x}".format(
        int(bul_color.red),
        int(bul_color.green),
        int(bul_color.blue),
    )
    # Accept a list (positional numbering) or a mapping (back-compat: numbered by
    # insertion order, keys ignored).
    items = list(value.values()) if isinstance(value, dict) else value
    bullet_contents = []
    number = 1
    for elem in items:
        if isinstance(elem, (list, dict)):
            # A nested ordered list: append the nested ListFlowable itself so
            # ReportLab indents it (rather than a wrapping python list).
            sub_bullets = convert_ol(elem, context, level=level + 1, current_style=current_style)
            bullet_contents.extend(sub_bullets)
            continue
        para_md = convert_inline_markdown(elem)
        rendered = render_template(para_md, context['vars'])
        bullet_content = Paragraph(f'<bullet color="{bullet_color_hex}">{number}. </bullet>{rendered}', bullet_style)
        bullet_contents.append(bullet_content)
        number += 1
    return [ListFlowable(bullet_contents, start=0, bulletType='bullet')]

def is_table_data(value) -> bool:
    """Whether 'value' is tabular data: a non-empty list of mappings (the rows)."""
    return (
        isinstance(value, list)
        and len(value) > 0
        and all(isinstance(row, Mapping) for row in value)
    )


def table_columns(rows: list[Mapping]) -> list:
    """The column names of 'rows': every key, in order of first appearance."""
    return list(dict.fromkeys(key for row in rows for key in row))


def format_cell(value, spec: Optional[str] = None) -> str:
    """Returns a cell value as text, with the format string 'spec' (e.g. "{:.2f}") if given."""
    if value is None:
        return ""
    if spec is not None:
        return spec.format(value)
    return str(value)


def convert_table(value: list[dict], context: dict, templated: bool = True) -> list[Table]:
    """
    Returns a Table of the rows in 'value', one column per key.

    'templated': render each cell as a Jinja template. True for tables written
    in the YAML; False for data computed at render time (a `$var`), whose cells
    are values to show as they are, not templates.
    """
    table_style = context['tablestyles']['rl']['_tablestyle']
    column_headers = table_columns(value)
    table_data = [column_headers]
    for row in value:
        inner = []
        for column in column_headers:
            cell = row.get(column)
            if templated:
                inner.append(render_template(str(cell), context['vars']))
            else:
                inner.append(format_cell(cell))
        table_data.append(inner)
    return [Table(table_data, style=table_style)]
