from reportlab.platypus import Spacer



def convert_spacer(block_key: str, block_value: float, context: dict) -> list[Spacer]:
    return [Spacer(width=1, height=block_value)]
