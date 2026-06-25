from __future__ import annotations
from typing import TYPE_CHECKING, Callable
from io import BytesIO
from copy import deepcopy
import pathlib
from PIL import Image as PillowImg

from reportlab.platypus import Table, Image, Paragraph
from . import register_block
from . import blockstyles

if TYPE_CHECKING:
    from matplotlib.figure import Figure


def convert_matplotfig_block(block_key: str, block_value: dict, context: dict) -> list[Table]:
    fig: Figure = block_value['fig']
    width_ratio = block_value.get('scale_ratio', 0.8)
    scale_ratio = width_ratio
    dpi = block_value.get("dpi", 150)
    fig_buffer = BytesIO()
    fig.savefig(fig_buffer, transparent=True, format='png')
    fig_buffer.seek(0)

    caption_textstyle = blockstyles.get_text_styles().get(f'image_caption')
    caption = block_value.get('caption', "")
    img_width, img_height = get_photo_size(fig_buffer)
    aspect = img_height / img_width
    available_width = context['frames']['all_pages']['width']
    available_height = context['frames']['all_pages']['height']

    if img_width > available_width * scale_ratio:
        scaled_width = available_width * scale_ratio
        scaled_height = scaled_width * aspect
    elif img_height > available_height * scale_ratio:
        scaled_height = available_height * scale_ratio
        scaled_width = scaled_height / aspect
    else:
        scaled_width = img_width * scale_ratio
        scaled_height = img_height * scale_ratio
    image_flowable = Image(fig_buffer, width=scaled_width, height=scaled_height)
    caption_para = Paragraph(caption, style=caption_textstyle)
    table_data = [[image_flowable], [caption_para]]
    col_width = scaled_width
    table = Table(table_data, colWidths=[col_width])
    return [table]


def get_photo_size(file_path: str | pathlib.Path | BytesIO) -> tuple[float, float]:
    """
    Returns the width and height of the image at 'file_path'.
    """
    img = PillowImg.open(file_path)
    size = img.size
    return size

def get_photo_dpi(file_path: str | pathlib.Path | BytesIO) -> tuple:
    """
    Returns the dpi of an image.
    """
    img = PillowImg.open(file_path)
    return img.info.get('dpi', (150.**0.5, 150.**0.5))

register_block("_matplotfig", convert_matplotfig_block)