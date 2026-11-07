"""
Heading levels and the PDF outline (bookmarks).

A flowable that should appear in the outline carries `ym_outline = (title, level)`,
set with `mark_outline`. `level` is the heading level, 1 for h1. The doc template
adds a bookmark for each one as it is drawn (`YmprintDocTemplate.afterFlowable`),
so headings from any source (the document, slides, or a block such as `_hc` that
renders its own headings) share one outline.
"""
from __future__ import annotations

from typing import Optional

from reportlab.platypus import BaseDocTemplate, Flowable

OUTLINE_ATTR = "ym_outline"

# Text styles define h1..h6. Deeper headings render as h6.
MAX_HEADING_LEVEL = 6


def heading_style_name(level: int) -> str:
    """The text style for a heading at 'level' (1-based), capped at h6."""
    return f"h{min(max(level, 1), MAX_HEADING_LEVEL)}"


def mark_outline(flowable: Flowable, level: int, title: Optional[str] = None) -> Flowable:
    """
    Returns 'flowable', marked as a heading at 'level' (1 for h1) for the PDF outline.
    'title' defaults to the flowable's plain text (for a Paragraph).
    """
    if title is None:
        get_plain_text = getattr(flowable, "getPlainText", None)
        title = get_plain_text() if get_plain_text is not None else ""
    title = " ".join(str(title).split())
    if title:
        setattr(flowable, OUTLINE_ATTR, (title, max(int(level), 1)))
    return flowable


class YmprintDocTemplate(BaseDocTemplate):
    """A doc template that turns `ym_outline` marks into PDF bookmarks."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 'outline_entries' records (title, level, page) for each bookmark, e.g. for
        # a table of contents.
        self.outline_entries: list[tuple[str, int, int]] = []
        self._outline_level = 0

    def afterFlowable(self, flowable) -> None:
        mark = getattr(flowable, OUTLINE_ATTR, None)
        if mark is None:
            return
        title, level = mark
        # A PDF outline cannot skip a level (an h3 straight after an h1 becomes the
        # h1's child), and its levels start at 0.
        level = min(level, self._outline_level + 1)
        self._outline_level = level
        key = f"ym-outline-{len(self.outline_entries)}"
        top = self._flowable_top(flowable)
        if top is None:
            self.canv.bookmarkPage(key)
        else:
            self.canv.bookmarkHorizontalAbsolute(key, top)
        self.canv.addOutlineEntry(title, key, level=level - 1, closed=False)
        self.outline_entries.append((title, level, self.page))

    def _flowable_top(self, flowable) -> Optional[float]:
        """The y of the top of 'flowable' just drawn in the current frame, if known."""
        frame = getattr(self, "frame", None)
        height = getattr(flowable, "height", None)
        if frame is None or height is None:
            return None
        return frame._y + height + flowable.getSpaceAfter()
