import pathlib
import re
from PIL import Image as PillowImg
from reportlab.platypus import Image, Table, Paragraph
from . import content_box
from . import blockstyles
from ..errors import BlockError


# A URL scheme such as "https:" or "mailto:". One letter is a Windows drive ("C:").
_URL_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]+:")


class LinkedImage(Image):
    """An image that is also a link: clicking it opens 'link'."""

    def __init__(self, filename, width=None, height=None, *, link: str, **kwargs):
        super().__init__(filename, width=width, height=height, **kwargs)
        self.link = link

    def draw(self):
        super().draw()
        x = getattr(self, '_offs_x', 0)
        y = getattr(self, '_offs_y', 0)
        self.canv.linkURL(
            self.link, (x, y, x + self.drawWidth, y + self.drawHeight), relative=1
        )


def resolve_link(link: str, base_dir: pathlib.Path) -> str:
    """
    Returns the URL an image's 'link' opens. URLs (https:, mailto:, file:, ...)
    are kept as they are. Anything else is a file path, relative to 'base_dir'
    (the document's folder) unless absolute, and becomes a file: URL. The file
    doesn't have to exist when the document is rendered: a video may only be on
    the computer the slides are presented from.
    """
    if _URL_SCHEME.match(link):
        return link
    path = pathlib.Path(link).expanduser()
    if not path.is_absolute():
        path = pathlib.Path(base_dir) / path
    return path.resolve().as_uri()


def convert_image_block(block_key: str, block_value: dict, context: dict) -> list[Table]:
    key = block_key
    value = block_value
    # `width_ratio` is the current name; `scale_ratio` is kept as a deprecated alias
    # so existing documents keep working.
    scale_ratio = value.get('width_ratio', value.get('scale_ratio', 1))
    # `source` is the current name; `src` is kept as a deprecated alias.
    source = value.get('source', value.get('src'))
    if source is None:
        raise BlockError(
            key,
            f"Block {key!r} needs an image path. Add a 'source:' field.",
        )
    image_path = pathlib.Path(context['base_dir']) / pathlib.Path(source)
    if 'data' in context:
        # Recorded even when missing, so live mode re-renders once it exists.
        context['data'].record_file(image_path)
    if not image_path.exists():
        raise FileNotFoundError(
            f"The image file for block '{key}' was not found: {str(image_path)}"
        )
    caption_textstyle = blockstyles.get_text_styles(blockstyles.block_scale(context)).get('image_caption')
    # Caption is optional: when absent/empty, no caption row is rendered.
    caption = value.get('caption')
    img_width, img_height = get_photo_size(image_path)
    aspect = img_height / img_width
    available_width = content_box(context)['width']
    available_height = content_box(context)['height']

    if img_width > available_width * scale_ratio:
        scaled_width = available_width * scale_ratio
        scaled_height = scaled_width * aspect
    elif img_height > available_height * scale_ratio:
        scaled_height = available_height * scale_ratio
        scaled_width = scaled_height / aspect
    else:
        scaled_width = img_width * scale_ratio
        scaled_height = img_height * scale_ratio
    link = value.get('link')
    if link is None:
        image_flowable = Image(str(image_path), width=scaled_width, height=scaled_height)
    elif isinstance(link, str) and link.strip():
        image_flowable = LinkedImage(
            str(image_path), width=scaled_width, height=scaled_height,
            link=resolve_link(link.strip(), context['base_dir']),
        )
    else:
        raise BlockError(
            key,
            f"Block {key!r} has 'link: {link!r}'. Give a URL or a file path, "
            "e.g. 'link: https://example.com' or 'link: videos/demo.mp4'.",
        )
    table_data = [[image_flowable]]
    if caption:
        table_data.append([Paragraph(caption, style=caption_textstyle)])
    col_width = scaled_width
    table = Table(table_data, colWidths=[col_width])
    return [table]


def get_photo_size(file_path: str | pathlib.Path) -> tuple[float, float]:
    """
    Returns the width and height of the image at 'file_path'.
    """
    img = PillowImg.open(file_path)
    size = img.size
    img.close()
    return size

def get_photo_dpi(file_path: str | pathlib.Path) -> tuple:
    """
    Returns the dpi of an image.
    """
    img = PillowImg.open(file_path)
    return img.info.get('dpi', (150.**0.5, 150.**0.5))
