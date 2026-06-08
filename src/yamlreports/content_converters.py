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
from yamlreports.config.docstyles import ReportStyles

RLFlowables: TypeAlias = Union[Paragraph, Spacer, Table, KeepTogether, Image]


def convert_paragraph(value: str, context: dict, text_style: str = "body") -> list[Paragraph]:
    """Returns a Paragraph obj"""
    style = "body"
    style = context["styles"]["rl"]['_style'][text_style]
    para = Paragraph(value, style=style)
    return [para]

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
    bullet_content = [
        Paragraph(f'<bullet color="{bullet_color_hex}"><b>{bul_symbol}</b></bullet>{elem}', bullet_style)
        for elem in value
    ]
    return bullet_content

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
    bullet_content = [
        Paragraph(f'<bullet color="{bullet_color_hex}"><b>{idx}.</b></bullet>{elem}', bullet_style)
        for idx, elem in enumerate(value.values())
    ]
    return bullet_content

# Test
def convert_table(value: list[dict], context: dict) -> list[Table]:
    table_style = context['tablestyles']['rl']['_tablestyle']
    column_headers = list(value[0].keys())
    table_data = [column_headers]
    table_data.extend([[cell for cell in row.values()] for row in value])
    return [Table(table_data, style=table_style)]
