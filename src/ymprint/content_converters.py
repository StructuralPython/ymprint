from itertools import cycle
from typing import TypeAlias, Union
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
        template = jinja_env.from_string(para_md)
        rendered = template.render(context['vars'])
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
    bullet_style: ParagraphStyle = sheet['body']
    # bullet_style.spaceAfter = space_around
    # bullet_style.spaceBefore = space_around
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
            sub_bullets = convert_ul(elem, context, level=level + 1, current_style=current_style)
            bullet_contents.append(sub_bullets)
        else:
            para_md = convert_inline_markdown(elem)
            template = jinja_env.from_string(para_md)
            rendered = template.render(context['vars'])
            bullet_content = Paragraph(f'<bullet color="{bullet_color_hex}"><b>{bul_symbol}</b></bullet>{rendered}', bullet_style)
            bullet_contents.append(bullet_content)
            
    return [ListFlowable(bullet_contents, start=0, bulletType='bullet', spaceAfter=space_around)]

# Test
def convert_ol(value: list | dict, context: dict, level: int = 0, current_style: str = "default") -> list[ListFlowable]:
    sheet = _family_sheet(context, current_style)
    bullet_style = sheet['body']
    ymp_style = _family_model(context, current_style)
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
            sub_bullets = convert_ol(elem, context, level=level + 1, current_style=current_style)
            bullet_contents.append(sub_bullets)
            continue
        para_md = convert_inline_markdown(elem)
        template = jinja_env.from_string(para_md)
        rendered = template.render(context['vars'])
        bullet_content = Paragraph(f'<bullet color="{bullet_color_hex}">{number}. </bullet>{rendered}', bullet_style)
        bullet_contents.append(bullet_content)
        number += 1
    return [ListFlowable(bullet_contents, start=0, bulletType='bullet')]

# Test
def convert_table(value: list[dict], context: dict) -> list[Table]:
    table_style = context['tablestyles']['rl']['_tablestyle']
    column_headers = list(value[0].keys())
    table_data = [column_headers]
    for row in value:
        inner = []
        for cell in row.values():
            template = jinja_env.from_string(str(cell))
            rendered = template.render(context['vars'])
            inner.append(rendered)
        table_data.append(inner)
    return [Table(table_data, style=table_style)]
