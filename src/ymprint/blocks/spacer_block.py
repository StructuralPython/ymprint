from reportlab.platypus import Spacer
from . import register_block



def convert_page_break(obj: dict, context: dict) -> list[Spacer]:
    return [Spacer(width=1, height=obj['_spacer'])]


register_block("_spacer", convert_page_break)