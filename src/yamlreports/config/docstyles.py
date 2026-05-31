from pydantic import BaseModel, Field, ConfigDict
from typing import TypeAlias
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors


class TextStyle(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    font: str
    size: int
    color: str

    @property
    def rlcolor(self) -> colors.Color:
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


class SpacingMixin:
    spacing: int = Field(alias="spacing")


class SymbolMixin:
    symbol: str = Field(default="-")

class BulletStyle(SpacingMixin, TextStyle):
    pass


class BodyTextStyle(SpacingMixin, TextStyle):
    bullets: BulletStyle

class HeadingTextStyle(TextStyle):
    pass

class ReportStyles(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    body: BodyTextStyle
    headings: HeadingTextStyle

    def to_rlstyle(self)  -> ParagraphStyle:
        """
        Returns a reportlab.lib.style.ParagraphStyle
        """
        leading = self.body.spacing * self.body.size
        ParagraphStyle(
            "name",
            fontName=self.body.font,
            fontSize=self.body.size,
            leading=leading,
            bulletFontSize=self.body.bullets.size,
            textColor=self.body.rlcolor,


        )


StyleContainer: dict[str, ReportStyles]