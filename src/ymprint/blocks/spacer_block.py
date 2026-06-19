from reportlab.platypus import Spacer
from . import register_block



def convert_page_break(block_key: str, block_value: float, context: dict) -> list[Spacer]:
    return [Spacer(width=1, height=block_value)]


register_block("_spacer", convert_page_break)