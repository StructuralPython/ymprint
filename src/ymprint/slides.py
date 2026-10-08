"""
Slide mode: renders a top-level section as one slide whose content is placed into
the named frames of a slide layout (see design/slides.md).
"""
import re
from dataclasses import dataclass, field

from reportlab.platypus import Flowable, KeepInFrame
from reportlab.platypus.doctemplate import LayoutError

from .content_checks import check_for_paragraph
from .exceptions import YMPrintSyntaxException

# `_slide` (per-slide settings) and `_frame` (route content to a frame) are structural
# directives, not registered blocks. A trailing `_suffix` is allowed for uniqueness
# within a mapping, consistent with other block codes.
SLIDE_DIRECTIVE_PATTERN = re.compile(r"^_(slide|frame)(?:_|$)")

SLIDE_SETTINGS = ("layout",)


def _extract_slide_directive(k, v):
    """
    Returns (kind, value) when this element is a `_slide`/`_frame` directive, else
    None. Handles both the mapping-key form (`_frame: right`) and the single-key
    list-item form (`- _frame: right`).
    """
    key = value = None
    if isinstance(k, str) and SLIDE_DIRECTIVE_PATTERN.match(k):
        key, value = k, v
    elif k is None and isinstance(v, dict) and len(v) == 1:
        (only_key, only_value), = v.items()
        if isinstance(only_key, str) and SLIDE_DIRECTIVE_PATTERN.match(only_key):
            key, value = only_key, only_value
    if key is None:
        return None
    return SLIDE_DIRECTIVE_PATTERN.match(key).group(1), value


def _misplaced_directive_message(kind: str, context: dict) -> str:
    doctemplate = context["doctemplate"]["ymprint"]
    if not getattr(doctemplate, "slides", False):
        return (
            f"`_{kind}` only works in slide mode. Add `slides: true` under `_doc` "
            f"to make each top-level heading a slide."
        )
    if kind == "slide":
        return "`_slide` must be the first item of a slide's content."
    return (
        "`_frame` must be used directly in a slide's content, not inside a "
        "sub-section or block."
    )


@dataclass
class SlideFrame:
    name: str
    x: float
    y: float
    width: float
    height: float
    valign: str
    overflow: str
    flowables: list = field(default_factory=list)


class SlideFlowable(Flowable):
    """
    Fills a page's content box and draws each frame's flowables at the frame's
    position. Each frame's content is fitted with KeepInFrame using the frame's
    overflow mode.
    """

    def __init__(self, title: str, width: float, height: float, frames: list[SlideFrame]):
        super().__init__()
        self.title = title
        self.width = width
        self.height = height
        self.frames = frames
        self._placed = []

    def wrap(self, availWidth, availHeight):
        self._placed = []
        for frame in self.frames:
            if not frame.flowables:
                continue
            fitted = KeepInFrame(
                frame.width, frame.height, frame.flowables,
                mode=frame.overflow, name=frame.name,
            )
            try:
                _, fitted_height = fitted.wrapOn(self.canv, frame.width, frame.height)
            except LayoutError as exc:
                raise YMPrintSyntaxException(
                    f"The content of frame {frame.name!r} on slide {self.title!r} does "
                    f"not fit (overflow: {frame.overflow}). Trim the content, enlarge "
                    f"the frame, or set the frame's overflow to 'shrink'."
                ) from exc
            self._placed.append((frame, fitted, min(fitted_height, frame.height)))
        return self.width, self.height

    def draw(self):
        for frame, fitted, fitted_height in self._placed:
            slack = frame.height - fitted_height
            offset = {"top": slack, "middle": slack / 2, "bottom": 0}[frame.valign]
            fitted.drawOn(self.canv, frame.x, frame.y + offset)


def _items_of(value) -> tuple[list[tuple], bool]:
    """
    Returns the slide content as (key, value) pairs (key is None for list items) and
    whether it was written as a mapping.
    """
    if isinstance(value, dict):
        return list(value.items()), True
    if isinstance(value, list):
        return [(None, elem) for elem in value], False
    if value is None:
        return [], False
    return [(None, value)], False


def _rebuild(items: list[tuple], is_mapping: bool):
    """Inverse of _items_of for one frame's share of the content."""
    if is_mapping:
        return {k: v for k, v in items}
    return [v for _, v in items]


def _parse_slide_settings(value, title) -> dict:
    if value is None:
        return {}
    if isinstance(value, str):
        return {"layout": value}
    if isinstance(value, dict):
        unknown = [key for key in value if key not in SLIDE_SETTINGS]
        if unknown:
            raise YMPrintSyntaxException(
                f"Unknown `_slide` setting(s) {unknown} on slide {title!r}. "
                f"Available settings: {list(SLIDE_SETTINGS)}"
            )
        return dict(value)
    raise YMPrintSyntaxException(
        f"`_slide` on slide {title!r} takes a layout name or a mapping of settings. "
        f"Got: {value!r}"
    )


def _frame_context(context: dict, x: float, y: float, width: float, height: float) -> dict:
    """A copy of 'context' whose current content box is the given frame."""
    frames = dict(context["frames"])
    frames["current"] = {"anchor": [x, y], "width": width, "height": height}
    return {**context, "frames": frames}


def build_slide(title, value, context: dict, current_style: str) -> list:
    """
    Returns the flowables for one slide: the section 'title' and its content 'value',
    placed into the frames of the slide's layout.
    """
    from .story_builder import _extract_textstyle, _resolve_style, build_content
    from .content_converters import convert_paragraph

    doctemplate = context["doctemplate"]["ymprint"]
    items, is_mapping = _items_of(value)

    # Leading `_slide` / `_textstyle` items configure the whole slide.
    settings = {}
    slide_style = current_style
    start = 0
    for k, v in items:
        style_name = _extract_textstyle(k, v)
        directive = _extract_slide_directive(k, v)
        if style_name is not None:
            slide_style = _resolve_style(style_name, context)
        elif directive is not None and directive[0] == "slide":
            settings = _parse_slide_settings(directive[1], title)
        else:
            break
        start += 1

    layout_name = settings.get("layout") or "default"
    try:
        layout = doctemplate.get_layout(layout_name)
    except ValueError as exc:
        raise YMPrintSyntaxException(f"Slide {title!r}: {exc}") from exc

    frame_names = list(layout)
    content_frames = [name for name in frame_names if name != "title"] or frame_names
    title_frame = "title" if "title" in layout else content_frames[0]

    # Route the content into frames, switching on each `_frame` directive.
    shares = {name: [] for name in frame_names}
    current_frame = content_frames[0]
    for k, v in items[start:]:
        directive = _extract_slide_directive(k, v)
        if directive is None:
            shares[current_frame].append((k, v))
            continue
        kind, frame_name = directive
        if kind == "slide":
            raise YMPrintSyntaxException(
                f"`_slide` must be the first item of slide {title!r}."
            )
        if frame_name not in layout:
            raise YMPrintSyntaxException(
                f"Frame {frame_name!r} not found in layout {layout_name!r} on slide "
                f"{title!r}. Available frames: {frame_names}"
            )
        current_frame = frame_name

    template_name = doctemplate.template_names[0]
    box_width = context["frames"][template_name]["width"]
    box_height = context["frames"][template_name]["height"]

    frames = []
    for name in frame_names:
        frame_config = layout[name]
        x, y, width, height = frame_config.resolve(box_width, box_height)
        frame_context = _frame_context(context, x, y, width, height)
        flowables = []
        if name == title_frame and check_for_paragraph(title, context):
            flowables.extend(convert_paragraph(title, frame_context, "h1", slide_style))
        if shares[name]:
            flowables.extend(
                build_content(_rebuild(shares[name], is_mapping), frame_context, 0, slide_style)
            )
        frames.append(
            SlideFrame(
                name=name, x=x, y=y, width=width, height=height,
                valign=frame_config.valign, overflow=frame_config.overflow,
                flowables=flowables,
            )
        )
    return [SlideFlowable(str(title), box_width, box_height, frames)]
