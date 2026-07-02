
from collections import UserDict
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


class Bundle(UserDict):
    def __getattr__(self, key):
        try:
            return self.data[key]
        except KeyError:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{key}'")

    def __setattr__(self, key, value):
        # Prevent infinite loops during initialization
        if key == "data":
            super().__setattr__(key, value)
        else:
            self.data[key] = value

    def __delattr__(self, key):
        try:
            del self.data[key]
        except KeyError:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{key}'")