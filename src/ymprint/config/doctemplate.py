from enum import StrEnum
import pathlib
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
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

class FrameConfig(BaseModel):
    """
    One frame of a slide layout. 'box' is [x, y, width, height] measured from the
    top-left of the page template's content box. Values <= 1 are fractions of the
    content box; values > 1 are points.
    """
    box: tuple[float, float, float, float]
    valign: Literal['top', 'middle', 'bottom'] = 'top'
    overflow: Literal['shrink', 'error', 'truncate'] = 'shrink'

    @model_validator(mode='before')
    @classmethod
    def _accept_bare_box(cls, value):
        # A frame may be written as just its box: `left: [0, 0, 0.5, 1]`
        if isinstance(value, (list, tuple)):
            return {'box': value}
        return value

    @field_validator('box')
    @classmethod
    def _check_box(cls, box):
        x, y, width, height = box
        if x < 0 or y < 0 or width <= 0 or height <= 0:
            raise ValueError(
                f"A frame box is [x, y, width, height] with x, y >= 0 and a positive "
                f"width and height. Got: {list(box)!r}"
            )
        return box

    def resolve(self, content_width: float, content_height: float) -> tuple[float, float, float, float]:
        """
        Returns (x, y, width, height) in points within a content box of the given size,
        with y measured from the *bottom* (ReportLab's convention).
        """
        x, y, width, height = self.box
        x = x * content_width if x <= 1 else x
        width = width * content_width if width <= 1 else width
        y = y * content_height if y <= 1 else y
        height = height * content_height if height <= 1 else height
        return x, content_height - y - height, width, height


# Layouts available in every slide deck. A user layout of the same name replaces one.
BUILTIN_LAYOUTS: dict[str, dict] = {
    'default': {
        'body': [0, 0, 1, 1],
    },
    'title': {
        'title': {'box': [0, 0, 1, 0.55], 'valign': 'bottom'},
        'body': [0, 0.6, 1, 0.4],
    },
    'two-column': {
        'title': [0, 0, 1, 0.22],
        'left': [0, 0.25, 0.48, 0.75],
        'right': [0.52, 0.25, 0.48, 0.75],
    },
}


class PageSizeMixin:
    # Either a named ReportLab page size (e.g. 'a4', 'letter') or an explicit
    # [width, height] in points (e.g. [960, 540] for a 16:9 slide).
    page_size: str | tuple[float, float] = Field(alias='page-size')

    @field_validator('page_size', mode='before')
    @classmethod
    def _check_page_size(cls, value):
        if isinstance(value, (list, tuple)):
            if len(value) != 2 or not all(
                isinstance(dim, (int, float)) and not isinstance(dim, bool) and dim > 0
                for dim in value
            ):
                raise ValueError(
                    f"An explicit page-size must be [width, height] with two positive "
                    f"numbers in points, e.g. [960, 540]. Got: {list(value)!r}"
                )
            return tuple(float(dim) for dim in value)
        return value

class LandscapeMixin:
    landscape: bool = Field(default = False)


class DocConfig(PageSizeMixin, LandscapeMixin, BaseModel):
    templates: dict[str, TemplateConfig]
    # Slide mode: every top-level heading becomes one slide (its own page).
    slides: bool = False
    # Named slide layouts: {layout name: {frame name: FrameConfig}}
    layouts: dict[str, dict[str, FrameConfig]] = Field(default_factory=dict)

    @property
    def all_layouts(self) -> dict[str, dict[str, FrameConfig]]:
        """Built-in layouts overlaid with the document's own layouts."""
        builtins = {
            name: {frame: FrameConfig.model_validate(spec) for frame, spec in frames.items()}
            for name, frames in BUILTIN_LAYOUTS.items()
        }
        return builtins | self.layouts

    def get_layout(self, name: str) -> dict[str, FrameConfig]:
        layouts = self.all_layouts
        if name not in layouts:
            raise ValueError(
                f"Slide layout {name!r} not found. Available layouts: {sorted(layouts)}"
            )
        return layouts[name]

    @property
    def page_dims(self):
        # An explicit [width, height] is used exactly as written; `landscape` only
        # rotates named page sizes.
        if isinstance(self.page_size, tuple):
            return self.page_size
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
