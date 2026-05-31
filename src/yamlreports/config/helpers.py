from reportlab.lib import colors

def convert_color(self) -> colors.Color:
    """
    Converts self.color into a ReportLab Color
    """
    # For named colors
    if hasattr(colors, self.color):
        return getattr(colors, self.color)
    if isinstance(self.color, str):
        return colors.HexColor(self.color.lstrip("#"))
    # Fallback
    return colors.Color(0, 0, 0)