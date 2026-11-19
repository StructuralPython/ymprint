from reportlab.platypus import KeepTogether

from . import content_box
from .code_block_styles import CodeLookError, generic_code_block
from ..errors import BlockError


def convert_code_block(block_key: str, block_value: dict, context: dict) -> list[KeepTogether]:
    """
    `_code`: source shown verbatim. `theme` ("light" or "dark") and `size` (points)
    override the active text style's code settings.
    """
    source = block_value['source']
    caption = block_value.get('caption')
    line_numbers = block_value.get('line_numbers')
    width_ratio = block_value.get('width_ratio', 0.75)
    available_width = content_box(context)['width']
    text_spacing = context['styles']['ymprint'].body.spacing
    text_size = context['styles']['ymprint'].body.size
    space_around = text_spacing * text_size
    try:
        code_block = generic_code_block(
            source, available_width * width_ratio, context, caption=caption,
            show_line_numbers=line_numbers,
            theme=block_value.get('theme'), size=block_value.get('size'),
        )
    except CodeLookError as exc:
        raise BlockError(block_key, str(exc)) from exc
    code_block.spaceBefore = space_around
    code_block.spaceAfter = space_around
    return [KeepTogether(code_block)]
