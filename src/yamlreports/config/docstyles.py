from pydantic import BaseModel, Field, ConfigDict


# --- Base Core Attributes ---
class TextStyle(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    font: str
    size: int
    color: str


# --- Mixin Class ---
class SpacingMixin:
    spacing: int = Field(..., alias="spacing")


# --- Heading Model using Mixin ---
class BodyTextStyle(SpacingMixin, TextStyle):
    pass

class HeadingTextStyle(TextStyle):
    pass

# --- Enclosing Document Style Model ---
class ReportStyles(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    body: BodyTextStyle
    headings: HeadingTextStyle