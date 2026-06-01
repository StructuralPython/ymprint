import pathlib
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate
import reportlab.lib.pagesizes as rl_pagesizes


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

    def build(self, destination: str | pathlib.Path, title: str = "", author: str = ""):
        """
        Returns a rl object
        """
        doc = BaseDocTemplate(
            str(destination),
            pagesize = self.page_size,
            leftMargin = self.margins.left,
            rightMargin = self.margins.right,
            topMargin = self.margins.top,
            bottomMargin=self.margins.bottom,
            title=title,
            author=author,
        )
        if hasattr(rl_pagesizes, self.page_size.upper()):
            page_dims = getattr(rl_pagesizes, self.page_size.upper())
        else:
            raise ValueError(f"Page size of {self.page_size.upper()} not found. Page sizes available: {[attr for attr in dir(rl_pagesizes) if attr.isupper()]}")
        page_width, page_height = page_dims
        main_frame = Frame(
            x1=self.margins.left,
            y1=self.margins.bottom,
            width = page_width - self.margins.left - self.margins.right,
            height = page_height - self.margins.top - self.margins.bottom,
        )
        if self.first_page is not None:
            pass




    # def build(self, output_path: str, title: str = "", author: str = "") -> BaseDocTemplate:
    #     """
    #     Construct and return a ``BaseDocTemplate`` wired to *output_path*
    #     with a single ``Frame`` that spans the printable area.
    #     """
    #     page_size = _PAGE_SIZES.get(self.page_size.upper(), A4)
    #     page_w, page_h = page_size

    #     doc = BaseDocTemplate(
    #         output_path,
    #         pagesize=page_size,
    #         leftMargin=self.left_margin,
    #         rightMargin=self.right_margin,
    #         topMargin=self.top_margin,
    #         bottomMargin=self.bottom_margin,
    #         title=title,
    #         author=author,
    #     )

    #     # single story frame occupying the full printable area
    #     story_frame = Frame(
    #         x1=self.left_margin,
    #         y1=self.bottom_margin,
    #         width=page_w - self.left_margin - self.right_margin,
    #         height=page_h - self.top_margin - self.bottom_margin,
    #         id="story",
    #         leftPadding=0,
    #         rightPadding=0,
    #         topPadding=0,
    #         bottomPadding=0,
    #     )

    #     page_template = PageTemplate(
    #         id="main",
    #         frames=[story_frame],
    #         onPage=self.draw_page_graphics,
    #     )
    #     doc.addPageTemplates([page_template])

    #     return doc


# CRITICAL: This compiles the forward reference ("Doc") now that the class is defined.
DocConfig.model_rebuild()