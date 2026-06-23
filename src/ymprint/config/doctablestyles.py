from typing import List, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator
from reportlab.platypus import TableStyle as RLTableStyle

# Import the core text style class as requested
from .docstyles import TextStyle
from .helpers import convert_color


# --- Mixins ---
class BoldMixin:
    bold: bool


# --- Specialized Text Styles ---
class HeaderTextStyle(BoldMixin, TextStyle):
    pass


# --- Structural Models ---
class CellPadding(BaseModel):
    top: float
    left: float
    right: float
    bottom: float


class RowColors(BaseModel):
    even: str
    odd: str


class HeaderRow(BaseModel):
    color: str
    lines: List[Literal["above", "below", "between"]]
    
    @property
    def rl_color(self):
        return convert_color(self.color)


class BodyRows(BaseModel):
    color: str | RowColors
    lines: List[Literal["above", "below", "between"]]

    @property
    def rl_color(self):
        if isinstance(self.color, str):
            return convert_color(self.color)
        elif isinstance(self.color, RowColors):
            return [convert_color(self.color.odd), convert_color(self.color.even)]


class Headers(BaseModel):
    text: HeaderTextStyle
    row: HeaderRow


class Body(BaseModel):
    text: TextStyle
    rows: BodyRows


# --- Main Style Container Model ---
class TableStyle(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cell_padding: CellPadding = Field(..., alias="cell-padding")
    headers: Headers
    body: Body

    def build(self) -> RLTableStyle:
        """
        Returns a ReportLab TableStyle Object
        """
        if self.headers.text.bold:
            fontname = f"{self.headers.text.font.title()}-Bold"
        else:
            fontname = self.headers.text.font.title()
        print(f"{self.headers.row.color=}")
        table_commands = [
            # HEADER STYLES
            ("BACKGROUND", (0, 0), (-1, 0), self.headers.row.color),
            ("TEXTCOLOR", (0, 0), (-1, 0), self.headers.text.color),
            ("FONTNAME", (0, 0), (-1, 0), fontname),
            ("FONTSIZE", (0, 0), (-1, 0), self.headers.text.size),
            ("LEADING", (0, 0), (-1, 0), self.headers.text.size * 1.4),
            # BODY STYLES
            ("FONTNAME", (0, 1), (-1, -1), self.body.text.font),
            ("FONTSIZE", (0, 1), (-1, -1), self.body.text.size),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), self.body.rows.rl_color),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), self.cell_padding.top),
            ("BOTTOMPADDING", (0, 0), (-1, -1), self.cell_padding.bottom),
            ("LEFTPADDING", (0, 0), (-1, -1), self.cell_padding.left),
            ("RIGHTPADDING", (0, 0), (-1, -1), self.cell_padding.right),
        ]
        return RLTableStyle(table_commands)