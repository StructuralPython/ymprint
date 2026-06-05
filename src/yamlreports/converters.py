from typing import Union, Optional

from reportlab.platypus import (
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    ListFlowable,
    ListItem,
    HRFlowable,
    def KeepTogether,
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

def check_for_subelements(
    value: YAML_Values, context: dict):
    if (
        isinstance(value, list)
        and any([isinstance(elem, str) for elem in value])
        and any([isinstance(elem, dict) for elem in value])
        ):
        return True
    else:
        return False
        
  