import pathlib
from PIL import Image as PillowImg
from reportlab.platypus import Image, Table, Paragraph
from . import register_block
from . import blockstyles


def convert_image_block(block_key: str, block_value: dict, context: dict) -> list[Table]:
    key = block_key
    value = block_value
    scale_ratio = value.get('scale_ratio', 1)
    source_path = pathlib.Path(context['source_path']).parent
    image_path = source_path / pathlib.Path(value['path'])
    if not image_path.exists():
        raise FileNotFoundError(
            f"The image file for block '{key}' was not found: {str(image_path)}"
        )
    styles = context['styles']['rl']['_style']
    caption_textstyle = blockstyles.get_text_styles().get(f'image_caption')
    caption = value['caption']
    img_width, img_height = get_photo_size(image_path)
    aspect = img_height / img_width
    available_width = context['frames']['all_pages']['width']
    available_height = context['frames']['all_pages']['height']

    if img_width > available_width * scale_ratio:
        scaled_width = available_width
        scaled_height = scaled_width * aspect
    elif img_height > available_height * scale_ratio:
        scaled_height = available_height * 0.9
        scaled_width = scaled_height / aspect
    else:
        scaled_width = img_width * scale_ratio
        scaled_height = img_height * scale_ratio
    image_flowable = Image(str(image_path), width=scaled_width, height=scaled_height)
    caption_para = Paragraph(caption, style=caption_textstyle)
    table_data = [[image_flowable], [caption_para]]
    col_width = scaled_width
    table = Table(table_data, colWidths=[col_width])
    return [table]


def get_photo_size(file_path: str | pathlib.Path) -> tuple[float, float]:
    """
    Returns the width and height of the image at 'file_path'.
    """
    img = PillowImg.open(file_path)
    return img.size


def get_photo_dpi(file_path: str | pathlib.Path) -> tuple:
    """
    Returns the dpi of an image.
    """
    img = PillowImg.open(file_path)
    return img.info.get('dpi', (150.**0.5, 150.**0.5))


register_block('_img', convert_image_block)