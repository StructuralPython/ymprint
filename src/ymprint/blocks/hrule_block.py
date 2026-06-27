from reportlab.platypus import HRFlowable
from . import register_block
from ..config.helpers import parse_width
from typing import Any


def convert_hrule(block_keyy: str, block_value: dict, context: dict) -> list[HRFlowable]:
    params = block_value or {}
    font_size = context['styles']['ymprint'].body.size
    spacing = context['styles']['ymprint'].body.spacing
    space_around = font_size * spacing
    color=params.get("color", "#111111")
    linecap = params.get("cap", 'square')
    width = parse_width(params.get("width_ratio", 1.0))
    thickness = params.get('thickness', 1)
    return [HRFlowable(
        width=width,
        color=color,
        lineCap=linecap,
        thickness=thickness,
        spaceBefore=space_around,
        spaceAfter=space_around

    )]

register_block("_hrule", convert_hrule)