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

def convert_paragraph(value: str, context: dict, text_style: str = "body") -> list[Paragraph]:
    """Returns a Paragraph obj"""
    style = context["styles"]["rl"]['_style'][text_style]
    paragraphs = value.split("\n")
    paras = []
    for para in paragraphs:
        para_md = convert_inline_markdown(para)
        template = jinja_env.from_string(para_md)
        rendered = template.render(context['vars'])
        print(f"{rendered=}")
        rl_para = Paragraph(rendered, style=style)
        paras.append(rl_para)

        paras.append(Spacer(1, 5))
    return paras

# Test
def convert_ul(value: list[str], context: dict, level: int = 0) -> list[ListFlowable]:
    text_spacing = context['styles']['ymprint'].body.spacing
    text_size = context['styles']['ymprint'].body.size
    space_around = text_spacing * text_size / 2
    sheet = context['styles']['rl']['_style']
    bullet_style: ParagraphStyle = sheet['body']
    # bullet_style.spaceAfter = space_around
    # bullet_style.spaceBefore = space_around
    print(f"{context['styles']['yaml']['_style']=}")
    bul_context = context['styles']['yaml']['_style']['body']['bullets']
    bul_symbols = bul_context['symbols']
    level_index = level % len(bul_symbols)
    bul_symbol = bul_symbols[level_index]
    ymp_style: ReportStyles = context['styles']['ymprint']
    bul_color = ymp_style.body.bullets.rl_color
    bullet_color_hex = "#{:02x}{:02x}{:02x}".format(
        int(bul_color.red),
        int(bul_color.green),
        int(bul_color.blue),
    )
    bullet_contents = []
    for elem in value:
        if isinstance(elem, list):
            sub_bullets = convert_ul(elem, context, level=level + 1)
            bullet_contents.append(sub_bullets)
        else:
            para_md = convert_inline_markdown(elem)
            template = jinja_env.from_string(para_md)
            rendered = template.render(context['vars'])
            bullet_content = Paragraph(f'<bullet color="{bullet_color_hex}"><b>{bul_symbol}</b></bullet>{rendered}', bullet_style)
            bullet_contents.append(bullet_content)
            
    return [ListFlowable(bullet_contents, start=0, bulletType='bullet', spaceAfter=space_around)]

# Test
def convert_ol(value: dict, context: dict, level: int = 0) -> list[ListFlowable]:
    sheet = context['styles']['rl']['_style']
    bullet_style = sheet['body']
    ymp_style: ReportStyles = context['styles']['ymprint']
    bul_color = ymp_style.body.bullets.rl_color
    bullet_color_hex = "#{:02x}{:02x}{:02x}".format(
        int(bul_color.red),
        int(bul_color.green),
        int(bul_color.blue),
    )
    bullet_contents = []
    for idx, elem in enumerate(value.values(), start=1):
        if isinstance(elem, dict):
            sub_bullets = convert_ol(elem, context, level=level + 1)
            bullet_contents.append(sub_bullets)
        else:
            para_md = convert_inline_markdown(elem)
            template = jinja_env.from_string(para_md)
            rendered = template.render(context['vars'])
        bullet_content = Paragraph(f'<bullet color="{bullet_color_hex}">{idx}. </bullet>{rendered}', bullet_style)
        bullet_contents.append(bullet_content)
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
