"""
The `_help` block: help for a block, or a look at a value, drawn as a loud modal over
the page while a document is being written.

    - _help:            # every block and document key
    - _help: _table     # help for one block or key
    - _help: $beam      # a value: its type, size and contents

The block adds a zero-size marker to the story. When the marker is drawn it records
its help on the canvas, under the page number, and when the page ends the doc template
calls `draw_help_pages`, which draws one modal over the page for every `_help` on it.
Help that doesn't fit continues on extra pages inserted after the page; they aren't
document pages, so they get no background and don't count in page numbers.

`ym live` shows the modal, `ym convert` (and a render from Python) warns that a
`_help` is left in, and `ym build` refuses the document.
"""
from __future__ import annotations

import difflib
import inspect
import pathlib
import pprint
import warnings
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Flowable, Frame, Paragraph, Preformatted

from ..content_checks import check_for_variable
from ..errors import BlockError
from .help_texts import HELP_TEXTS
from .registry import BLOCK_CODE_PATTERN, parse_block_key

# The canvas attribute holding {page number: [section, ...]} until the page ends.
HELP_PAGES_ATTR = "_ym_help_pages"

LIST_WORDS = {"", "blocks"}

LEFT_IN_WARNING = (
    "{source} has a `_help` block. It is for writing the document only: remove it "
    "before publishing (`ym build` refuses documents that still have one)."
)

# The look: loud on purpose.
PINK = colors.HexColor("#FF1F8E")
DARK_PINK = colors.HexColor("#7A0A45")
YELLOW = colors.HexColor("#FFE31D")
PAPER = colors.HexColor("#FFF7B8")
INK = colors.HexColor("#1B1B1B")
SHADOW = colors.HexColor("#160F22")


# --- the block ------------------------------------------------------------------


def convert_help_block(block_key: str, block_value, context: dict) -> list:
    """
    Shows help over the page while you write: `_help:` lists every block, `_help: _img`
    explains one block or document key, and `_help: $var` (or any other value) shows
    the value. Remove it before `ym build`, which refuses documents that have one.
    """
    _check_mode(block_key, context)
    page_width, page_height = context["doctemplate"]["ymprint"].page_dims
    section = help_section(block_value, context, Metrics(page_width, page_height))
    return [HelpMarker(section)]


# The block reads `$name` itself, so it can show the variable's name.
convert_help_block.raw_value = True


def _check_mode(block_key: str, context: dict) -> None:
    event = context.get("render_event")
    mode = event.mode if event is not None else "api"
    if mode == "build":
        raise BlockError(
            block_key,
            "`_help` is for writing a document, so `ym build` doesn't build documents "
            "that have one. Remove it, or look at it with `ym live`.",
        )
    if mode == "live" or event is None:
        return
    source = event.source.name if event.source is not None else "The document"
    message = LEFT_IN_WARNING.format(source=source)
    if message in event.warnings:
        return
    event.warnings.append(message)
    if mode == "api":
        # Point at the caller's code, not at ymprint's own frames.
        warnings.warn(message, skip_file_prefixes=(str(pathlib.Path(__file__).parents[1]),))


# --- what to show ---------------------------------------------------------------
#
# A section is {"title": str, "items": [...]}, where an item is one of
#   ("text", str)            a paragraph of plain text
#   ("label", str)           a small label, e.g. "Keys"
#   ("type", str)            a value's type and size, e.g. "dict, 3 items"
#   ("key", name, meaning)   a name and what it means
#   ("pre", str)             preformatted text (examples, values)


def help_section(value, context: dict, metrics: "Metrics") -> dict:
    """Returns the section `_help: value` shows."""
    if value is None or (isinstance(value, str) and value.strip() in LIST_WORDS):
        return block_list(context["blocks"])
    if isinstance(value, str) and value.strip().startswith("_"):
        parsed = parse_block_key(value.strip())
        code = parsed[0] if parsed is not None else value.strip()
        if code in context["blocks"] or code in HELP_TEXTS:
            return block_help(code, context["blocks"])
        if BLOCK_CODE_PATTERN.match(code):
            return unknown_block(code, context["blocks"])
    if check_for_variable(value, context):
        name = value.lstrip("$")
        if name not in context["vars"]:
            return unknown_variable(name, context["vars"])
        return value_section(f"${name}", context["vars"][name], metrics)
    from . import retrieve_block_variables
    from ..content_converters import render_template

    value = retrieve_block_variables(value, context)
    if isinstance(value, str):
        value = render_template(value, context["vars"])
    return value_section("Value", value, metrics)


def _builtin(code: str):
    from .builtin import BUILTIN_BLOCKS

    return BUILTIN_BLOCKS.get(code)


def _help_text(code: str, blocks) -> dict | None:
    """The built-in help for 'code', unless an app has its own block there."""
    text = HELP_TEXTS.get(code)
    if text is None:
        return None
    if text["kind"] == "block" and code in blocks and blocks.get(code) is not _builtin(code):
        return None
    return text


def summary(code: str, blocks) -> str:
    text = _help_text(code, blocks)
    if text is not None:
        return text["summary"]
    doc = inspect.getdoc(blocks.get(code)) if code in blocks else None
    return doc.strip().splitlines()[0] if doc else ""


def block_list(blocks) -> dict:
    items: list = [("label", "Blocks")]
    items += [("key", code, summary(code, blocks)) for code in sorted(blocks.codes())]
    items.append(("label", "Document keys"))
    items += [
        ("key", code, text["summary"])
        for code, text in sorted(HELP_TEXTS.items())
        if text["kind"] == "key"
    ]
    items.append(("text", "Write _help: _name for one of them, e.g. _help: _img."))
    return {"title": "Blocks and document keys", "items": items}


def block_help(code: str, blocks) -> dict:
    text = _help_text(code, blocks)
    if text is not None:
        title = code if text["kind"] == "block" else f"{code} (document key)"
        items: list = [("text", text["summary"])]
        if text["keys"]:
            items.append(("label", "Keys"))
            items += [("key", name, meaning) for name, meaning in text["keys"]]
        items += [("label", "Example"), ("pre", text["example"])]
        return {"title": title, "items": items}
    doc = inspect.getdoc(blocks.get(code))
    if not doc:
        return {"title": code, "items": [("text", f"{code} has no help: its function has no docstring.")]}
    return {"title": code, "items": [("pre", doc)]}


def unknown_block(code: str, blocks) -> dict:
    known = sorted(set(blocks.codes()) | set(HELP_TEXTS))
    matches = difflib.get_close_matches(code, known, n=3, cutoff=0.6)
    if matches:
        guess = " or ".join(matches)
        message = f"Unknown block {code}: did you mean {guess}?"
    else:
        message = f"Unknown block {code}: no block or document key has that name."
    return {
        "title": f"Unknown block {code}",
        "items": [("text", message), ("text", "Write _help: with no value to list them all.")],
    }


def unknown_variable(name: str, variables: dict) -> dict:
    names = sorted(n for n in variables if isinstance(n, str) and not n.startswith("_"))
    matches = difflib.get_close_matches(name, names, n=3, cutoff=0.6)
    items: list = [("text", f"No variable {name!r} is defined at this point of the document.")]
    if matches:
        items.append(("text", "Did you mean " + " or ".join(f"${m}" for m in matches) + "?"))
    items += [("label", "Variables defined here"), ("pre", ", ".join(names) or "(none)")]
    return {"title": f"${name}", "items": items}


def describe(value) -> str:
    """'dict, 3 items', 'str, 12 characters', 'numpy.ndarray, shape (3, 4)'."""
    kind = type(value)
    if kind.__module__.startswith("ruamel"):
        # YAML mappings and lists: to the author they are a dict and a list.
        kind = dict if isinstance(value, dict) else list if isinstance(value, list) else kind
    name = kind.__qualname__ if kind.__module__ == "builtins" else f"{kind.__module__.split('.')[0]}.{kind.__qualname__}"
    shape = getattr(value, "shape", None)
    if isinstance(shape, tuple):
        return f"{name}, shape {shape}"
    try:
        size = len(value)
    except Exception:
        return name
    unit = "character" if isinstance(value, str) else "item"
    return f"{name}, {size} {unit}{'' if size == 1 else 's'}"


def plain(value):
    """
    Returns 'value' with YAML's mappings and sequences (ruamel's CommentedMap and
    CommentedSeq) turned into plain dicts and lists, all the way down. pprint only
    lays out the plain types; a subclass with its own repr prints on one line.
    """
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [plain(item) for item in value]
    return value


def value_section(title: str, value, metrics: "Metrics") -> dict:
    # Formatted now, so a later block that changes the value doesn't change what is shown.
    if isinstance(value, str):
        text = value
    else:
        text = pprint.pformat(plain(value), width=metrics.chars, sort_dicts=False)
    return {"title": title, "items": [("type", describe(value)), ("pre", text)]}


# --- drawing ----------------------------------------------------------------------


class HelpMarker(Flowable):
    """Takes no space; records its help for the page it is drawn on."""

    # Containers (KeepInFrame, as slides use) skip zero-height flowables without this.
    _ZEROSIZE = True

    def __init__(self, section: dict):
        super().__init__()
        self.section = section

    def wrap(self, available_width, available_height):
        return 0, 0

    def draw(self):
        canvas = self.canv
        pages = canvas.__dict__.setdefault(HELP_PAGES_ATTR, {})
        pages.setdefault(canvas.getPageNumber(), []).append(self.section)


class Metrics:
    """The modal's sizes for a page, scaled from its size."""

    def __init__(self, page_width: float, page_height: float):
        self.page_width, self.page_height = page_width, page_height
        self.size = max(8.0, min(page_width, page_height * 0.8) / 50)
        self.inset = 0.09 * min(page_width, page_height)
        self.stripe = self.size * 0.8
        self.header = self.size * 2.6
        self.footer = self.size * 2.0
        self.padding = self.size * 1.1
        self.shadow = self.size * 0.7
        self.mono = self.size * 0.85
        self.box = (
            self.inset,
            self.inset,
            page_width - 2 * self.inset,
            page_height - 2 * self.inset,
        )
        x, y, width, height = self.box
        self.frame = (
            x + self.padding,
            y + self.footer,
            width - 2 * self.padding,
            height - self.stripe - self.header - self.footer - self.padding * 0.5,
        )
        # Courier is 0.6 em wide.
        self.chars = max(20, int(self.frame[2] / (0.6 * self.mono)))


def _styles(m: Metrics) -> dict:
    size = m.size
    return {
        "title": ParagraphStyle(
            "help-title", fontName="Helvetica-Bold", fontSize=size * 1.3, leading=size * 1.6,
            textColor=DARK_PINK, spaceBefore=size * 0.4, spaceAfter=size * 0.3,
        ),
        "text": ParagraphStyle(
            "help-text", fontName="Helvetica", fontSize=size, leading=size * 1.35,
            textColor=INK, spaceAfter=size * 0.3,
        ),
        "label": ParagraphStyle(
            "help-label", fontName="Helvetica-Bold", fontSize=size * 0.8, leading=size * 1.2,
            textColor=DARK_PINK, spaceBefore=size * 0.5, spaceAfter=size * 0.2,
        ),
        "type": ParagraphStyle(
            "help-type", fontName="Helvetica-Oblique", fontSize=size * 0.9, leading=size * 1.3,
            textColor=DARK_PINK, spaceAfter=size * 0.2,
        ),
        "key": ParagraphStyle(
            "help-key", fontName="Helvetica", fontSize=size, leading=size * 1.3,
            textColor=INK, leftIndent=size * 2, firstLineIndent=-size * 1.2, spaceAfter=size * 0.15,
        ),
        "pre": ParagraphStyle(
            "help-pre", fontName="Courier", fontSize=m.mono, leading=m.mono * 1.25,
            textColor=INK, leftIndent=size * 0.6, spaceBefore=size * 0.15, spaceAfter=size * 0.4,
        ),
    }


def _flowables(sections: list[dict], m: Metrics) -> list:
    styles = _styles(m)
    story = []
    for section in sections:
        story.append(Paragraph(escape(section["title"]), styles["title"]))
        for item in section["items"]:
            kind = item[0]
            if kind == "text":
                story.append(Paragraph(escape(item[1]), styles["text"]))
            elif kind == "type":
                story.append(Paragraph(escape(item[1]), styles["type"]))
            elif kind == "label":
                story.append(Paragraph(escape(item[1]).upper(), styles["label"]))
            elif kind == "key":
                name, meaning = escape(item[1]), escape(item[2])
                story.append(Paragraph(f'<font name="Courier-Bold" color="#7A0A45">{name}</font>&nbsp;&nbsp;&nbsp;{meaning}', styles["key"]))
            elif kind == "pre":
                story.append(Preformatted(item[1], styles["pre"], maxLineLength=m.chars))
    return story


def _draw_modal(canvas, m: Metrics, continued: bool) -> None:
    x, y, width, height = m.box
    canvas.saveState()
    # Dim the page under the modal.
    canvas.setFillColor(colors.Color(0, 0, 0, alpha=0.45))
    canvas.rect(0, 0, m.page_width, m.page_height, stroke=0, fill=1)
    # A hard shadow, then the box.
    canvas.setFillColor(SHADOW)
    canvas.rect(x + m.shadow, y - m.shadow, width, height, stroke=0, fill=1)
    canvas.setFillColor(PAPER)
    canvas.rect(x, y, width, height, stroke=0, fill=1)
    # Hazard stripes along the top.
    top = y + height
    canvas.setFillColor(YELLOW)
    canvas.rect(x, top - m.stripe, width, m.stripe, stroke=0, fill=1)
    path = canvas.beginPath()
    path.rect(x, top - m.stripe, width, m.stripe)
    canvas.clipPath(path, stroke=0, fill=0)
    canvas.setFillColor(INK)
    step = m.stripe * 1.6
    offset = x - m.stripe
    while offset < x + width:
        stripe = canvas.beginPath()
        stripe.moveTo(offset, top - m.stripe)
        stripe.lineTo(offset + step / 2, top - m.stripe)
        stripe.lineTo(offset + step / 2 + m.stripe, top)
        stripe.lineTo(offset + m.stripe, top)
        stripe.close()
        canvas.drawPath(stripe, stroke=0, fill=1)
        offset += step
    canvas.restoreState()

    canvas.saveState()
    # The header bar and its title.
    header_y = top - m.stripe - m.header
    canvas.setFillColor(PINK)
    canvas.rect(x, header_y, width, m.header, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", m.size * 1.5)
    canvas.drawString(x + m.padding, header_y + m.header * 0.32, "HELP" + ("  (continued)" if continued else ""))
    # The footer note.
    canvas.setFillColor(DARK_PINK)
    canvas.setFont("Helvetica-Oblique", m.size * 0.75)
    canvas.drawString(
        x + m.padding, y + m.footer * 0.4,
        "_help is for writing only: ym build refuses documents that still have one.",
    )
    # A thick border over it all.
    canvas.setStrokeColor(PINK)
    canvas.setLineWidth(m.size * 0.35)
    canvas.rect(x, y, width, height, stroke=1, fill=0)
    canvas.restoreState()


def _fill(frame: Frame, story: list, canvas, note_style: ParagraphStyle) -> None:
    """Adds as much of 'story' to 'frame' as fits, splitting where it can."""
    while story:
        if frame.add(story[0], canvas, trySplit=1):
            story.pop(0)
            continue
        parts = frame.split(story[0], canvas)
        if len(parts) > 1:
            story[0:1] = parts
            continue
        if frame._atTop:
            # Too large to show on any page; say so rather than loop.
            story[0] = Paragraph("(too large to show here)", note_style)
            if not frame.add(story[0], canvas):
                story.pop(0)
            continue
        return


def draw_help_pages(canvas) -> None:
    """
    Draws the modal over the page that is ending, if a `_help` is on it, and any
    continuation pages after it. Called by the doc template when a page ends.
    """
    pages = canvas.__dict__.get(HELP_PAGES_ATTR)
    if not pages:
        return
    sections = pages.pop(canvas.getPageNumber(), None)
    if not sections:
        return
    page_width, page_height = canvas._pagesize
    m = Metrics(page_width, page_height)
    story = _flowables(sections, m)
    note_style = _styles(m)["text"]
    continued = False
    while True:
        _draw_modal(canvas, m, continued)
        frame = Frame(*m.frame, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        _fill(frame, story, canvas, note_style)
        if not story:
            return
        # The rest goes on an inserted page; the doc template ends the last one.
        canvas.showPage()
        continued = True
