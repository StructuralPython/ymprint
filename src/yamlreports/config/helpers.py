from reportlab.lib import colors

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