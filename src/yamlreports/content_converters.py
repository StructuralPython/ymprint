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

RLFlowables: TypeAlias = Union[Paragraph, Spacer, Table, KeepTogether, Image]


def convert_paragraph(value: str, context: dict, text_style: str = "body") -> list[Paragraph]:
    """Returns a Paragraph obj"""
    style = "body"
    style = context["styles"]["rl"][text_style]
    para = Paragraph(value, style=style)
    return [para]

# Test
def convert_ul(value: list[str], context: dict) -> list[Paragraph]:
    sheet = context['style']['rl']
    bullet_style = sheet['bullet']
    bullet_spec = sheet.get_spec("bullet")
    bul = context['style']['yaml']['_style']['body']['bullets']['symbol']
    bullet_color_hex = "#{:02x}{:02x}{:02x}".format(
        int(bullet_spec.bullet_color[0]),
        int(bullet_spec.bullet_color[1]),
        int(bullet_spec.bullet_color[2]),
    ) if bullet_spec and bullet_spec.bullet_color else "black"
    bullet_content = [
        Paragraph(f'<bullet color="{bullet_color_hex}"><b>{bul}</b></bullet>{elem}', bullet_style)
        for elem in value
    ]
    return bullet_content

# Test
def convert_ol(value: dict, context: dict) -> list[Paragraph]:
    sheet = context['style']['rl']
    bullet_style = sheet['bullet']
    bullet_spec = sheet.get_spec("bullet")
    bullet_color_hex = "#{:02x}{:02x}{:02x}".format(
        int(bullet_spec.bullet_color[0]),
        int(bullet_spec.bullet_color[1]),
        int(bullet_spec.bullet_color[2]),
    ) if bullet_spec and bullet_spec.bullet_color else "black"
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
    table_data.extend([[cell for cell in row] for row in value])
    return [Table(table_data, style=table_style)]
