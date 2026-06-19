from reportlab.platypus import HRFlowable
from . import register_block
from ..config.helpers import parse_width


def convert_hrule(obj: dict, context: dict) -> list[HRFlowable]:
    params = obj.get("_hrule") or {}
    color=params.get("color", "#111111")
    linecap = params.get("cap", 'round')
    width = parse_width(params.get("width", 0.8))
    thickness = params.get('thickness', 1)
    return [HRFlowable(
        width=width,
        color=color,
        lineCap=linecap,
        thickness=thickness
    )]

register_block("_hrule", convert_hrule)