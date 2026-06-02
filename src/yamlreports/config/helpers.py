from reportlab.lib import colors
from reportlab.lib import pagesizes as rl_pagesizes

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
    if page_spec.upper() in rl_pagesizes:
        page_dims = getattr(rl_pagesizes, self.page_size.upper())
    else:
        raise ValueError(f"Page size of {self.page_size.upper()} not found. Page sizes available: {[attr for attr in dir(rl_pagesizes)]}")