from enum import StrEnum
import pathlib
from typing import Optional
from pydantic import BaseModel, Field
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate
import reportlab.lib.pagesizes as rl_pagesizes
from .helpers import get_pagesize


class Margins(BaseModel):
    top: float
    left: float
    right: float
    bottom: float

class RelativeTo(StrEnum):
    CONFIG = 'config'
    SOURCE = 'source'

class PDFBackground(BaseModel):
    filepath: str
    relative_to: Optional[RelativeTo] = Field(alias='relative-to', default=None)

class TemplateConfig(BaseModel):
    """A single named page template: its content margins and optional PDF background."""
    margins: Margins
    background: Optional[PDFBackground] = None

class PageSizeMixin:
    page_size: str = Field(alias='page-size')

class LandscapeMixin:
    landscape: bool = Field(default = False)


class DocConfig(PageSizeMixin, LandscapeMixin, BaseModel):
    templates: dict[str, TemplateConfig]

    @property
    def page_dims(self):
        if hasattr(rl_pagesizes, self.page_size.upper()):
            page_dims = get_pagesize(self.page_size)
            if self.landscape:
                final_page_dims = (page_dims[1], page_dims[0])
            else:
                final_page_dims = page_dims
            return final_page_dims
        else:
            raise ValueError(f"Page size of {self.page_size.upper()} not found. Page sizes available: {[attr for attr in dir(rl_pagesizes) if attr.isupper()]}")

    @property
    def template_names(self) -> list[str]:
        """Template names in declaration order. The first is the starting template."""
        return list(self.templates.keys())

    def resolve_template_id(self, name_or_index: str | int) -> str:
        """
        Returns the template name (used as the ReportLab PageTemplate id) for a
        user-supplied template reference, which may be a name or a 0-based index.
        """
        names = self.template_names
        # bool is an int subclass; reject it explicitly to avoid True/False -> index
        if isinstance(name_or_index, bool):
            raise ValueError(f"Invalid page template reference: {name_or_index!r}")
        if isinstance(name_or_index, int):
            try:
                return names[name_or_index]
            except IndexError:
                raise ValueError(
                    f"Page template index {name_or_index} is out of range. "
                    f"Available templates (by index): {list(enumerate(names))}"
                )
        if isinstance(name_or_index, str):
            if name_or_index in self.templates:
                return name_or_index
            raise ValueError(
                f"Page template {name_or_index!r} not found. Available templates: {names}"
            )
        raise ValueError(f"Invalid page template reference: {name_or_index!r}")

    def available_width(self, template_name: str) -> float:
        template = self.templates[template_name]
        return self.page_dims[0] - template.margins.left - template.margins.right

    def available_height(self, template_name: str) -> float:
        template = self.templates[template_name]
        return self.page_dims[1] - template.margins.top - template.margins.bottom

    def page_anchor(self, template_name: str) -> list[float]:
        template = self.templates[template_name]
        return [template.margins.left, template.margins.bottom]

    def min_available_width(self) -> float:
        """Smallest content width across all templates (safe for sizing flowables)."""
        return min(self.available_width(name) for name in self.template_names)

    def min_available_height(self) -> float:
        """Smallest content height across all templates (safe for sizing flowables)."""
        return min(self.available_height(name) for name in self.template_names)

    def build(self, destination: str | pathlib.Path, title: str = "", author: str = ""):
        """
        Returns a tuple of (BaseDocTemplate, page_template_map).

        'page_template_map' is an initially-empty dict that is populated during
        the ReportLab build with {page_index (0-based): template_name}. Each
        PageTemplate records the template used to render each page so that the
        correct background can be overlaid in post-processing.
        """
        page_width, page_height = self.page_dims
        page_template_map: dict[int, str] = {}

        def make_on_page(template_id: str):
            def _on_page(canvas, doc):
                page_template_map[canvas.getPageNumber() - 1] = template_id
            return _on_page

        page_templates = []
        for name, template in self.templates.items():
            frame = Frame(
                x1=template.margins.left,
                y1=template.margins.bottom,
                width=page_width - template.margins.left - template.margins.right,
                height=page_height - template.margins.top - template.margins.bottom,
                id=f'{name}_frame',
                leftPadding=0,
                rightPadding=0,
                topPadding=0,
                bottomPadding=0,
            )
            page_templates.append(
                PageTemplate(
                    id=name,
                    pagesize=self.page_dims,
                    frames=[frame],
                    onPage=make_on_page(name),
                )
            )

        doc = BaseDocTemplate(
            str(destination),
            pagesize=self.page_dims,
            pageTemplates=page_templates,
            title=title,
            author=author,
            allowSplitting=1
        )

        return doc, page_template_map
