import pathlib
from PIL import Image as PillowImg
from reportlab.platypus import Image, Table, Paragraph
from . import register_block


def check_image_block(key: str, value: dict, context: dict) -> bool:
    print("Img checker running")
    return key.startswith("_img")


def convert_image_block(obj: dict, context: dict) -> list[Table]:
    print("Image block conversion running")
    key = next(iter(obj.keys()))
    value = obj[key]
    source_path = pathlib.Path(context['source_path']).parent
    image_path = source_path / pathlib.Path(value['path'])
    if not image_path.exists():
        raise FileNotFoundError(
            f"The image file for block '{key}' was not found: {str(image_path)}"
        )
    styles = context['styles']['rl']['_style']

    caption = value['caption']
    img_width, img_height = get_photo_size(image_path)
    aspect = img_height / img_width
    available_width = context['frames']['all_pages']['width']
    # dpi_wxh = get_photo_dpi(image_path) or ((150**0.5, 150**0.5))
    # dpi = dpi_wxh[0] * dpi_wxh[1]
    # dppts = dpi / 72 # Dots per point

    if img_width > available_width:
        scaled_width = available_width * 0.5
        scaled_height = scaled_width * aspect
    else:
        scaled_width = img_width
        scaled_height = img_height
    image_flowable = Image(str(image_path), width=scaled_width, height=scaled_height)
    caption_para = Paragraph(caption, style=styles.get('caption', styles.get('body')))
    table_data = [[image_flowable], [caption_para]]
    col_width = available_width
    # col_width_spec = [col_width * page_scale]
    # tbl = Table(table_data, colWidths=col_width_spec, repeatRows=1)
    table = Table(table_data, colWidths=[col_width])
    # tbl.setStyle(TableStyle(table_commands))
    # flowables.append(tbl)
    # flowables.append(Spacer(width=1, height=30))
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