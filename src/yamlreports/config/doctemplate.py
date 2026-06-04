import pathlib
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate
import reportlab.lib.pagesizes as rl_pagesizes
from .helpers import get_pagesize


class Margins(BaseModel):
    top: float
    left: float
    right: float
    bottom: float

class PageConfig(BaseModel):
    # model_config = ConfigDict(populate_by_name=True)
    margins: Margins
    background: Optional[str] = None

class PageSizeMixin:
    page_size: str = Field(alias='page-size')

class LandscapeMixin:
    landscape: bool = Field(default = True)

class FirstPageMixin:
    first_page: Optional[PageConfig] = Field(default = None, alias='first-page')


class DocConfig(PageConfig, PageSizeMixin, LandscapeMixin, FirstPageMixin):
    pass

    @property
    def page_dims(self):
        if hasattr(rl_pagesizes, self.page_size.upper()):
            page_dims = get_pagesize(self.page_size)
            # page_dims = getattr(rl_pagesizes, self.page_size.upper())
        else:
            raise ValueError(f"Page size of {self.page_size.upper()} not found. Page sizes available: {[attr for attr in dir(rl_pagesizes) if attr.isupper()]}")

    def available_width(self, first_or_others: str):
        if first_or_others == "first":
            if getattr(self, 'first_page', None) is not None:
                return self.page_dims[0] - self.first_page.margins.left - self.first_page.margins.right
            else:
                return self.page_dims[0] - self.margins.left - self.margins.right
        else:
            return self.page_dims[0] - self.margins.left - self.margins.right
        
    def available_height(self, first_or_others: str):
        if first_or_others == "first":
            if getattr(self, 'first_page', None) is not None:
                return self.page_dims[1] - self.first_page.margins.top - self.first_page.margins.bottom
            else:
                self.page_dims[1] - self.margins.top - self.margins.bottom
        else:
            return self.page_dims[1] - self.margins.top - self.margins.bottom
        
    def page_anchor(self, first_or_others: str):
        if first_or_others == 'first':
            if getattr(self, 'first_page', None) is not None:
                return [self.first_page.margins.left, self.first_page.margins.bottom]
            else:
                return []
        else:
            return [self.margins.left, self.margins.bottom]

    
    
    def build(self, destination: str | pathlib.Path, title: str = "", author: str = ""):
        """
        Returns a rl object
        """
        doc = BaseDocTemplate(
            str(destination),
            pagesize = self.page_dims,
            leftMargin = self.margins.left,
            rightMargin = self.margins.right,
            topMargin = self.margins.top,
            bottomMargin=self.margins.bottom,
            title=title,
            author=author,
        )
        page_width, page_height = self.page_dims
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



# # CRITICAL: This compiles the forward reference ("Doc") now that the class is defined.
# DocConfig.model_rebuild()