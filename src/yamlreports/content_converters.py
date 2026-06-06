
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


    

def convert_paragraph(value: str, context: dict, text_style: str = "body"):
     
    """Returns a Paragraph obj"""
    style = "body"
    style = context["styles"]["rl"][text_style]
    para = Paragraph(value, style=style)
    return para