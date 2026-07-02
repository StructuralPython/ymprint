from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, BeforeValidator
from typing import TypeAlias, Annotated
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.styles import StyleSheet1

from .helpers import convert_color, YMPrintValueError

from enum import Enum

class HeadingRatio(float, Enum):
    minor_second = 1.067
    major_second = 1.125
    minor_third = 1.2
    major_third = 1.250
    perfect_fourth = 1.333
    augmented_fourth = 1.414
    perfect_fifth = 1.5
    golden_ratio = 1.618

    @classmethod
    def from_ratio_name(cls, ratio_name: str):
        if isinstance(ratio_name, (float, cls)):
            return ratio_name
            
        ratio_name = str(ratio_name).replace(cls.__name__, "").replace(".", "").lower().replace(" ", "_")
        try:
            return cls[ratio_name]
        except KeyError:
            raise YMPrintValueError(
                f"Value of '{ratio_name}' is not a recognized size ratio.\n"
            )
        

class TextStyle(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    font: str
    size: int
    color: str

    @property
    def rl_color(self):
        return convert_color(self.color)
    

class HeadingStyle(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    font: str
    ratio: Annotated[HeadingRatio | float, BeforeValidator(HeadingRatio.from_ratio_name)]
    color: str

    @property
    def rl_color(self):
        return convert_color(self.color)


class SpacingMixin:
    spacing: float = Field(alias="spacing")


class SymbolMixin:
    symbols: str = Field(default="-", alias='symbol')

class BulletStyle(SpacingMixin, TextStyle):
    indent_bullet: float = Field(alias='indent-bullet')
    indent_text: float = Field(alias='indent-text')


class BodyTextStyle(SpacingMixin, TextStyle):
    bullets: BulletStyle

class ReportStyle(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    body: BodyTextStyle
    headings: HeadingStyle

    def build(self) -> StyleSheet1:
        """
        Returns a reportlab.lib.style.ParagraphStyle
        """
        leading = self.body.spacing * self.body.size
        pstyle = ParagraphStyle(
            "body",
            fontName=self.body.font,
            fontSize=self.body.size,
            leading=leading,
            bulletFontName=self.body.bullets.font,
            bulletFontSize=self.body.bullets.size,
            leftIndent=self.body.bullets.indent_bullet,
            bulletIndent=self.body.bullets.indent_text,
            textColor=self.body.rl_color,
        )
        
        # Headings
        heading_ratio = self.headings.ratio
        headings = ['h6', 'h5', 'h4', 'h3', 'h2', 'h1']
        heading_ratios = {heading: heading_ratio**idx for idx, heading in enumerate(headings)}
        stylesheet = StyleSheet1()
        stylesheet.add(pstyle)
        for tag, ratio in heading_ratios.items():
            heading_size = self.body.size * ratio
            heading_leading = self.body.spacing * heading_size
            heading_style = ParagraphStyle(
                tag,
                fontName=self.headings.font,
                fontSize=heading_size,
                leading=heading_leading,
                textColor=self.headings.rl_color,
                spaceBefore=heading_size/4,
                spaceAfter=heading_size/4
            )
            stylesheet.add(heading_style)
       
        return stylesheet