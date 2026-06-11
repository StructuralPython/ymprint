from pydantic import BaseModel, Field, ConfigDict
from typing import TypeAlias
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.styles import StyleSheet1

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
    spacing: float = Field(alias="spacing")


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

    def build(self) -> StyleSheet1:
        """
        Returns a reportlab.lib.style.ParagraphStyle
        """
        leading = self.body.spacing * self.body.size
        # leading = self.body.size * 1.2
        pstyle = ParagraphStyle(
            "body",
            fontName=self.body.font,
            fontSize=self.body.size,
            leading=leading,
            bulletFontName=self.body.bullets.font,
            bulletFontSize=self.body.bullets.size,
            textColor=self.body.rl_color,
        )
        # The so-called "Major Thirds"
        # This 'ratio-name' may be selectable in the future
        heading_ratios = {
            "h1": 2.986,
            "h2": 2.488,
            "h3": 2.074,
            "h4": 1.728,
            "h5": 1.440,
            "h6": 1.2,
        }
        stylesheet = StyleSheet1()
        stylesheet.add(pstyle)
        for tag, ratio in heading_ratios.items():
            heading_size = self.body.size * ratio
            # print(f"{self.body.spacing=}")
            heading_leading = self.body.spacing * heading_size
            # heading_leading = 1.2 * heading_size
            heading_style = ParagraphStyle(
                tag,
                fontName=self.headings.font,
                fontSize=heading_size,
                leading=heading_leading,
                textColor=self.headings.rl_color,
                spaceBefore=heading_size / 1.5,
                spaceAfter=heading_size/4
            )
            stylesheet.add(heading_style)
       
        return stylesheet