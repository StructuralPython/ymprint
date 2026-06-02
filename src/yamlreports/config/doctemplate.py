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
        if hasattr(rl_pagesizes, self.page_size.upper()):
            page_dims = get_pagesize(self.page_size)
            # page_dims = getattr(rl_pagesizes, self.page_size.upper())
        else:
            raise ValueError(f"Page size of {self.page_size.upper()} not found. Page sizes available: {[attr for attr in dir(rl_pagesizes) if attr.isupper()]}")
        doc = BaseDocTemplate(
            str(destination),
            pagesize = page_dims,
            leftMargin = self.margins.left,
            rightMargin = self.margins.right,
            topMargin = self.margins.top,
            bottomMargin=self.margins.bottom,
            title=title,
            author=author,
        )
        page_width, page_height = page_dims
        main_frame = Frame(
            x1=self.margins.left,
            y1=self.margins.bottom,
            width = page_width - self.margins.left - self.margins.right,
            height = page_height - self.margins.top - self.margins.bottom,
            id='main',
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0
        )
        frames = [main_frame]
        if self.first_page is not None:
            first_frame = Frame(
                x1=self.first_page.margins.left,
                y1=self.first_page.margins.bottom,
                width=page_width - self.first_page.margins.left - self.first_page.margins.right,
                height=page_height - self.first_page.margins.top - self.first_page.margins.bottom,
                id='first',
                leftPadding=0,
                rightPadding=0,
                topPadding=0,
                bottomPadding=0,
            )
            frames = [first_frame, main_frame]
        
        page_template = PageTemplate(
            id='report',
            pagesize=(page_width, page_height),
            frames=frames,
        )
        doc.addPageTemplates([page_template])
        return doc



# CRITICAL: This compiles the forward reference ("Doc") now that the class is defined.
DocConfig.model_rebuild()