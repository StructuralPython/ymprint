from reportlab.lib import colors
from reportlab.lib import pagesizes as rl_pagesizes
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY

_ALIGNMENTS = {
    "left": TA_LEFT,
    "center": TA_CENTER,
    "centre": TA_CENTER,
    "right": TA_RIGHT,
    "justify": TA_JUSTIFY,
    "justified": TA_JUSTIFY,
}


def convert_alignment(align_spec: str | None) -> int:
    """
    Converts an alignment name (left/center/right/justify) into a ReportLab
    alignment constant. None or unset defaults to left-aligned.
    """
    if align_spec is None:
        return TA_LEFT
    key = str(align_spec).strip().lower()
    if key not in _ALIGNMENTS:
        raise YMPrintValueError(
            f"Alignment {align_spec!r} is not recognized. "
            f"Choose from: {sorted(set(_ALIGNMENTS) - {'centre', 'justified'})}."
        )
    return _ALIGNMENTS[key]


def convert_color(color_spec: str) -> colors.Color:
    """
    Converts self.color into a ReportLab Color
    """
    # For named colors
    if hasattr(colors, color_spec):
        return getattr(colors, color_spec)
    if isinstance(color_spec, str) and color_spec.startswith("#"):
        return colors.HexColor(color_spec)
    # Fallback
    return colors.Color(0, 0, 0)


def get_pagesize(page_spec: str) -> tuple[float, float]:
    if page_spec.upper() in dir(rl_pagesizes):
        page_dims = getattr(rl_pagesizes, page_spec.upper())
        return page_dims
    else:
        raise ValueError(f"Page size of {page_spec.upper()} not found. Page sizes available: {[attr for attr in dir(rl_pagesizes)]}")
    

def parse_width(value: float) -> str:
    """
    Interprets 'value' as either a ratio or a size in points
    """
    if value <= 1.0:
        return f"{value * 100}%"
    else:
        return value
    

class YMPrintValueError(ValueError):
    pass