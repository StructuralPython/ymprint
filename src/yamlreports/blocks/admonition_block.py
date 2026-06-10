from reportlab.platypus import Table, Paragraph
from . import register_block
from typing import Callable



def convert_info_block(obj: dict, context: dict) -> list[Table]:

    return [Table(data=[])]





register_block("_info", convert_info_block)