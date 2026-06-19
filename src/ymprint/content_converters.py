from typing import TypeAlias, Union
from reportlab.platypus import (
    Paragraph,
    Spacer,
    Table,
    Image,
    HRFlowable,
    KeepTogether,
)
from reportlab.lib.units import mm
from jinja2 import Template, Environment, DebugUndefined
from ymprint.config.docstyles import ReportStyles

RLFlowables: TypeAlias = Union[Paragraph, Spacer, Table, KeepTogether, Image]
jinja_env = Environment(undefined=DebugUndefined)

def convert_paragraph(value: str, context: dict, text_style: str = "body") -> list[Paragraph]:
    """Returns a Paragraph obj"""
    style = context["styles"]["rl"]['_style'][text_style]
    paragraphs = value.split("\n")
    paras = []
    for para in paragraphs:
        template = jinja_env.from_string(para)
        rendered = template.render(context['vars'])
        rl_para = Paragraph(rendered, style=style)
        paras.append(rl_para)
        paras.append(Spacer(1, 5))
    return paras

# Test
def convert_ul(value: list[str], context: dict) -> list[Paragraph]:
    sheet = context['styles']['rl']['_style']
    bullet_style = sheet['body']
    bul_context = context['styles']['yaml']['_style']['body']['bullets']
    bul_symbol = bul_context['symbol']
    ymp_style: ReportStyles = context['styles']['ymprint']
    bul_color = ymp_style.body.bullets.rl_color
    bullet_color_hex = "#{:02x}{:02x}{:02x}".format(
        int(bul_color.red),
        int(bul_color.green),
        int(bul_color.blue),
    )
    bullet_contents = []
    for elem in value:
        template = jinja_env.from_string(elem)
        rendered = template.render(context['vars'])
        bullet_content = Paragraph(f'<bullet color="{bullet_color_hex}"><b>{bul_symbol}</b></bullet>{rendered}', bullet_style)
        bullet_contents.append(bullet_content)
            
    return bullet_contents

# Test
def convert_ol(value: dict, context: dict) -> list[Paragraph]:
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
        template = jinja_env.from_string(elem)
        rendered = template.render(context['vars'])
        bullet_content = Paragraph(f'<bullet color="{bullet_color_hex}"><b>{idx}.</b></bullet>{rendered}', bullet_style)
        bullet_contents.append(bullet_content)
    return bullet_contents

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
        table_data.extend(inner)
    return [Table(table_data, style=table_style)]
