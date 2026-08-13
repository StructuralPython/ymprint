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

class BulletStyle(SymbolMixin, SpacingMixin, TextStyle):
    indent_bullet: float = Field(alias='indent-bullet')
    indent_text: float = Field(alias='indent-text')


class BodyTextStyle(SpacingMixin, TextStyle):
    bullets: BulletStyle


def _deep_merge(base: dict, override: dict) -> dict:
    """
    Returns a new dict: 'override' recursively merged onto 'base'. Nested dicts are
    merged key-by-key; any other value in 'override' replaces the base value.
    """
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class StyleFamily(BaseModel):
    """A complete text family: a body paragraph style plus a derived heading family."""
    model_config = ConfigDict(populate_by_name=True)
    body: BodyTextStyle
    headings: HeadingStyle

    def build_sheet(self) -> StyleSheet1:
        """
        Returns a reportlab StyleSheet1 with a 'body' style and derived 'h1'..'h6'
        heading styles.
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


class ReportStyles(StyleFamily):
    # Named text families. Each value is a *sparse* override of the default family
    # (this instance's body + headings); unspecified fields are inherited.
    styles: dict[str, dict] = Field(default_factory=dict)

    @property
    def default_family(self) -> StyleFamily:
        return StyleFamily(body=self.body, headings=self.headings)

    def build(self) -> StyleSheet1:
        """Returns the default family's stylesheet (back-compat)."""
        return self.default_family.build_sheet()

    def build_families(self) -> dict[str, tuple["StyleFamily", StyleSheet1]]:
        """
        Returns a mapping of style name -> (StyleFamily, StyleSheet1). The 'default'
        family is always present; each named style under 'styles' is deep-merged onto
        the default family before being validated and built.
        """
        default_family = self.default_family
        families: dict[str, tuple[StyleFamily, StyleSheet1]] = {
            "default": (default_family, default_family.build_sheet())
        }
        base_raw = default_family.model_dump(by_alias=True)
        for name, override in self.styles.items():
            merged = _deep_merge(base_raw, override or {})
            family = StyleFamily.model_validate(merged)
            families[name] = (family, family.build_sheet())
        return families