from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class Margins(BaseModel):
    top: float
    left: float
    right: float
    bottom: float


class DocConfig(BaseModel):
    # Enable population by field name so you can instantiate using either 
    # the python attribute name OR the YAML hyphenated alias.
    model_config = ConfigDict(populate_by_name=True)

    page_size: str = Field(..., alias="page-size")
    landscape: bool
    margins: Margins
    background: str
    
    # Self-reference to the Doc model itself for the 'first-page'
    # Wrapped in Optional because the nested first-page won't have its own first-page
    first_page: Optional["DocConfig"] = Field(default=None, alias="first-page")


# CRITICAL: This compiles the forward reference ("Doc") now that the class is defined.
DocConfig.model_rebuild()