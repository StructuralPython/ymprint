from pydantic import BaseModel, Field, ConfigDict
from typing import TypeAlias
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors

from .helpers import convert_color


class TextStyle(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    font: str
    size: int
    color: str

    @property
    def rl_color(self):
        return convert_color(self.color)


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

    def build(self) -> ParagraphStyle:
        """
        Returns a reportlab.lib.style.ParagraphStyle
        """
        leading = self.body.spacing * self.body.size
        pstyle = ParagraphStyle(
            "name",
            fontName=self.body.font,
            fontSize=self.body.size,
            leading=leading,
            bulletFontName=self.body.bullets.font,
            bulletFontSize=self.body.bullets.size,
            textColor=self.body.rl_color,
        )
        return pstyle


StyleContainer: dict[str, ReportStyles]