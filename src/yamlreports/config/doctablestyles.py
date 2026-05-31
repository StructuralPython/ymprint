from typing import List, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator

# Import the core text style class as requested
from .docstyles import TextStyle


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

    @field_validator("lines")
    @classmethod
    def validate_lines_constraints(cls, v: List[str]) -> List[str]:
        # Validate that there are at most 3 items
        if len(v) > 3:
            raise ValueError("The lines list can contain a maximum of 3 values.")
        # Validate uniqueness so values aren't repeated (e.g., ['above', 'above'])
        if len(set(v)) != len(v):
            raise ValueError("The lines list must contain unique values.")
        return v


class BodyRows(BaseModel):
    color: str | RowColors
    lines: List[Literal["above", "below", "between"]]

    @field_validator("lines")
    @classmethod
    def validate_lines_constraints(cls, v: List[str]) -> List[str]:
        if len(v) > 3:
            raise ValueError("The lines list can contain a maximum of 3 values.")
        if len(set(v)) != len(v):
            raise ValueError("The lines list must contain unique values.")
        return v


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