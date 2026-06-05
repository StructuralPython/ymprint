from typing import Union, Optional

from reportlab.platypus import (
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    ListFlowable,
    ListItem,
    HRFlowable,
    KeepTogether,
)

YAML_Values: Union[str, list, dict, float, int]

def check_for_paragraph(value: YAML_Values, context: dict) -> bool:

    """Returns True if the value should be interpreted as a Paragrpah"""
    return isinstance(value, str)
    

def convert_paragraph(value: YAML_Values, context: dict, text_style: str = "body"):
     
    """Returns a Paragraph obj"""
    style = "body"
    style = context["styles"]["rl"][heading_style]
    para = Paragraph(value, style=style)
    return para