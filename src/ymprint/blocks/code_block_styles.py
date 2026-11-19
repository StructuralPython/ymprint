"""
code_block_styles.py
====================
ReportLab styles and flowable builders for the `_code` and `_py` blocks.

- Two colour themes: "light" (Paper Light, for white pages) and "dark" (Ink
  Dark, for dark pages and slides). Pygments highlights `_py` source.
- DejaVu Sans Mono, bundled with ymprint (registered by register_fonts()).
- Line numbers, an optional caption bar, and a size in points.

The theme, size and line spacing come from the active text style's `code`
settings (see CodeStyle in config/docstyles.py), and a block can override the
theme and size. resolve_code_look() works out which apply.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pygments.lexers import PythonLexer
from pygments.token import Token

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import Paragraph, Table, TableStyle, XPreformatted

from ..config.docstyles import CODE_THEMES

FONT_MONO = "DejaVuSansMono"
FONT_MONO_BOLD = "DejaVuSansMono-Bold"
FONT_MONO_OBLIQUE = "DejaVuSansMono-Oblique"

# ---------------------------------------------------------------------------
# Layout tokens
# ---------------------------------------------------------------------------

LINE_NUM_WIDTH = 28   # pt: the least width of the line-number column
GUTTER_WIDTH = 8      # pt: gap between line numbers and code
CELL_PAD_H = 12       # pt: left/right padding of the block
CELL_PAD_V = 10       # pt: top/bottom padding of the block


# ---------------------------------------------------------------------------
# Themes
# ---------------------------------------------------------------------------

class _PaperLight:
    """
    Paper Light: a print-optimised light theme for white pages.

    All syntax colours meet WCAG AA contrast against white. Inspired by GitHub
    Light and Xcode's default light theme, with ink colours shifted warmer to
    read naturally on paper.
    """
    # Background / chrome
    BG = colors.HexColor("#FFFFFF")
    GUTTER_BG = colors.HexColor("#F3F4F6")
    BORDER = colors.HexColor("#D1D5DB")
    CAPTION_BG = colors.HexColor("#F3F4F6")

    # Text
    DEFAULT = colors.HexColor("#24292F")
    LINE_NUM = colors.HexColor("#9CA3AF")
    CAPTION_TEXT = colors.HexColor("#6B7280")

    # Syntax
    KEYWORD = colors.HexColor("#8250DF")
    BUILTIN = colors.HexColor("#CF222E")
    DECORATOR = colors.HexColor("#0550AE")
    FUNCTION = colors.HexColor("#6639BA")
    CLASS_NAME = colors.HexColor("#953800")
    STRING = colors.HexColor("#0A3069")   # deep blue: green ink fades on paper
    NUMBER = colors.HexColor("#0550AE")
    COMMENT = colors.HexColor("#57606A")
    OPERATOR = colors.HexColor("#CF222E")
    PUNCTUATION = colors.HexColor("#24292F")
    CONSTANT = colors.HexColor("#0550AE")


class _InkDark:
    """
    Ink Dark: a dark theme for dark pages and slides.

    A blue-black ground a step lighter than near-black pages, so the block
    still reads as a card on them. Syntax colours are soft pastels (in the
    Material Palenight family), each at least WCAG AA against the ground.
    """
    # Background / chrome
    BG = colors.HexColor("#1B1E28")
    GUTTER_BG = colors.HexColor("#222632")
    BORDER = colors.HexColor("#353B4B")
    CAPTION_BG = colors.HexColor("#222632")

    # Text
    DEFAULT = colors.HexColor("#E4E7EF")
    LINE_NUM = colors.HexColor("#6E7790")
    CAPTION_TEXT = colors.HexColor("#A3ABC0")

    # Syntax
    KEYWORD = colors.HexColor("#C792EA")
    BUILTIN = colors.HexColor("#F78C6C")
    DECORATOR = colors.HexColor("#82AAFF")
    FUNCTION = colors.HexColor("#82AAFF")
    CLASS_NAME = colors.HexColor("#FFCB6B")
    STRING = colors.HexColor("#C3E88D")
    NUMBER = colors.HexColor("#F78C6C")
    COMMENT = colors.HexColor("#8A93A8")
    OPERATOR = colors.HexColor("#89DDFF")
    PUNCTUATION = colors.HexColor("#BFC7D5")
    CONSTANT = colors.HexColor("#FF9CAC")


THEMES = {"light": _PaperLight, "dark": _InkDark}
assert set(THEMES) == set(CODE_THEMES)


class CodeLookError(ValueError):
    """A code block's theme or size is not valid."""


@dataclass(frozen=True)
class CodeLook:
    """What a code block looks like: its theme, text size and leading (pt)."""
    theme: type
    size: float
    leading: float
    caption_font: str
    caption_size: float

    @property
    def pad_h(self) -> float:
        return CELL_PAD_H

    @property
    def pad_v(self) -> float:
        return CELL_PAD_V


def resolve_code_look(context: dict, theme: Optional[str] = None, size=None) -> CodeLook:
    """
    The look of a code block built here: the active text style's `code` settings,
    with the block's own 'theme' and 'size' (when given) over them. Raises
    CodeLookError for an unknown theme or a size that isn't a positive number.
    """
    from . import section  # ymprint.blocks; imported here to avoid a cycle

    families = context["styles"].get("families") or {}
    family_entry = families.get(section(context)["text_style"]) or families.get("default")
    family = family_entry["ymprint"] if family_entry else context["styles"]["ymprint"]
    code = family.code
    body = family.body

    theme_name = code.theme if theme is None else theme
    if theme_name not in THEMES:
        raise CodeLookError(
            f"Unknown code theme {theme_name!r}. Use one of: {', '.join(THEMES)}."
        )
    if size is None:
        size = code.size if code.size is not None else body.size * 0.9
    if isinstance(size, bool) or not isinstance(size, (int, float)) or size <= 0:
        raise CodeLookError(f"A code block's size is a positive number of points. Got: {size!r}.")
    return CodeLook(
        theme=THEMES[theme_name],
        size=float(size),
        leading=float(size) * code.spacing,
        caption_font=body.font,
        caption_size=body.size * 0.8,
    )


# ---------------------------------------------------------------------------
# Token → colour and font
# ---------------------------------------------------------------------------

def _token_color(ttype, theme) -> colors.Color:
    """Map a Pygments token type to a colour of 'theme'."""
    if ttype in Token.Keyword or ttype in Token.Keyword.Namespace:
        return theme.KEYWORD
    if ttype in Token.Keyword.Constant:
        return theme.CONSTANT
    if ttype in Token.Name.Builtin or ttype in Token.Name.Exception:
        return theme.BUILTIN
    if ttype in Token.Name.Decorator:
        return theme.DECORATOR
    if ttype in Token.Name.Function or ttype in Token.Name.Function.Magic:
        return theme.FUNCTION
    if ttype in Token.Name.Class:
        return theme.CLASS_NAME
    if ttype in Token.Literal.String or ttype in Token.String:
        return theme.STRING
    if ttype in Token.Literal.Number or ttype in Token.Number:
        return theme.NUMBER
    if ttype in Token.Comment:
        return theme.COMMENT
    if ttype in Token.Operator:
        return theme.OPERATOR
    if ttype in Token.Punctuation:
        return theme.PUNCTUATION
    return theme.DEFAULT


def _token_font(ttype) -> str:
    """Map a Pygments token type to a font name."""
    if ttype in Token.Comment:
        return FONT_MONO_OBLIQUE
    if ttype in Token.Keyword or ttype in Token.Name.Class:
        return FONT_MONO_BOLD
    return FONT_MONO


def _escape(text: str) -> str:
    """XML-escapes text for ReportLab paragraph markup."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _tokenise_to_lines(code: str, theme) -> list[str]:
    """
    Tokenises Python 'code' with Pygments and returns one ReportLab paragraph
    string per source line, with inline colour spans from 'theme'.
    """
    lexer = PythonLexer(stripnl=False, ensurenl=True)
    lines: list[list[str]] = [[]]
    for ttype, value in lexer.get_tokens(code):
        hex_c = _token_color(ttype, theme).hexval()
        font = _token_font(ttype)
        # A single token may span several lines.
        for i, part in enumerate(value.split("\n")):
            if i > 0:
                lines.append([])
            if part:
                lines[-1].append(f'<font name="{font}" color="{hex_c}">{_escape(part)}</font>')
    # Pygments always appends a newline.
    if lines and lines[-1] == []:
        lines.pop()
    return ["".join(spans) if spans else " " for spans in lines]


# ---------------------------------------------------------------------------
# Paragraph styles
# ---------------------------------------------------------------------------

def _code_line_style(look: CodeLook) -> ParagraphStyle:
    return ParagraphStyle(
        name="code_line",
        fontName=FONT_MONO,
        fontSize=look.size,
        leading=look.leading,
        textColor=look.theme.DEFAULT,
        backColor=look.theme.BG,
        spaceBefore=0,
        spaceAfter=0,
        leftIndent=0,
        rightIndent=0,
        splitLongWords=False,   # don't break tokens mid-word
        wordWrap="LTR",
    )


def _line_number_style(look: CodeLook) -> ParagraphStyle:
    return ParagraphStyle(
        name="code_line_number",
        fontName=FONT_MONO,
        fontSize=look.size,
        leading=look.leading,
        textColor=look.theme.LINE_NUM,
        backColor=look.theme.GUTTER_BG,
        alignment=2,   # right-align numbers
        spaceBefore=0,
        spaceAfter=0,
    )


def _gutter_width(last_line_number: int, lnum_style: ParagraphStyle) -> float:
    """
    Width of the line-number column: wide enough for the largest number plus the
    column's right padding (GUTTER_WIDTH), which sits inside the column.
    """
    digits_width = pdfmetrics.stringWidth(str(last_line_number), lnum_style.fontName, lnum_style.fontSize)
    return max(LINE_NUM_WIDTH, digits_width + GUTTER_WIDTH + 2)


def _caption_style(look: CodeLook) -> ParagraphStyle:
    return ParagraphStyle(
        name="code_caption",
        fontName=look.caption_font,
        fontSize=look.caption_size,
        leading=look.caption_size * 1.4,
        textColor=look.theme.CAPTION_TEXT,
        backColor=look.theme.CAPTION_BG,
        alignment=0,
        spaceBefore=0,
        spaceAfter=0,
    )


# ---------------------------------------------------------------------------
# Table styles
# ---------------------------------------------------------------------------

def _code_table_style(look: CodeLook, show_line_numbers: bool) -> TableStyle:
    """TableStyle for the inner grid (line numbers | code)."""
    theme = look.theme
    cmds = [
        ("BACKGROUND", (0, 0), (-1, -1), theme.BG),
        ("BACKGROUND", (0, 0), (0, -1), theme.GUTTER_BG if show_line_numbers else theme.BG),
        ("BOX", (0, 0), (-1, -1), 0, colors.transparent),
        ("INNERGRID", (0, 0), (-1, -1), 0, colors.transparent),
        # Tight cell padding: the leading handles vertical spacing.
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        # The gap after the gutter column.
        ("RIGHTPADDING", (0, 0), (0, -1), GUTTER_WIDTH),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    return TableStyle(cmds)


def _outer_table_style(look: CodeLook, has_caption: bool) -> TableStyle:
    """TableStyle for the outer wrapper (optional caption bar + code grid)."""
    theme = look.theme
    cmds = [
        ("BACKGROUND", (0, 0), (-1, -1), theme.BG),
        ("BOX", (0, 0), (-1, -1), 1, theme.BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0, colors.transparent),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]
    if has_caption:
        cmds += [
            ("BACKGROUND", (0, 0), (0, 0), theme.CAPTION_BG),
            ("LINEBELOW", (0, 0), (0, 0), 0.5, theme.BORDER),
            ("LEFTPADDING", (0, 0), (0, 0), look.pad_h),
            ("RIGHTPADDING", (0, 0), (0, 0), look.pad_h),
            ("TOPPADDING", (0, 0), (0, 0), 6),
            ("BOTTOMPADDING", (0, 0), (0, 0), 6),
        ]
        code_row = 1
    else:
        code_row = 0
    cmds += [
        ("LEFTPADDING", (0, code_row), (0, code_row), look.pad_h),
        ("RIGHTPADDING", (0, code_row), (0, code_row), look.pad_h),
        ("TOPPADDING", (0, code_row), (0, code_row), look.pad_v),
        ("BOTTOMPADDING", (0, code_row), (0, code_row), look.pad_v),
    ]
    return TableStyle(cmds)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _code_table(
    markup_lines: list[str],
    col_width: float,
    look: CodeLook,
    caption: Optional[str],
    show_line_numbers: bool,
    first_line: int,
) -> Table:
    line_style = _code_line_style(look)
    lnum_style = _line_number_style(look)
    n_lines = len(markup_lines)

    if show_line_numbers:
        gutter_w = _gutter_width(first_line + n_lines - 1, lnum_style)
        code_w = col_width - gutter_w - GUTTER_WIDTH - (look.pad_h * 2)
    else:
        gutter_w = 0
        code_w = col_width - (look.pad_h * 2)

    inner_rows = []
    for i, markup in enumerate(markup_lines):
        code_para = XPreformatted(markup, line_style)
        if show_line_numbers:
            inner_rows.append([Paragraph(str(first_line + i), lnum_style), code_para])
        else:
            inner_rows.append([code_para])

    inner_table = Table(
        inner_rows,
        colWidths=[gutter_w, code_w] if show_line_numbers else [code_w],
        style=_code_table_style(look, show_line_numbers),
    )
    if caption:
        caption_para = Paragraph(f"  {_escape(caption)}", _caption_style(look))
        outer_rows = [[caption_para], [inner_table]]
    else:
        outer_rows = [[inner_table]]
    return Table(
        outer_rows,
        colWidths=[col_width],
        style=_outer_table_style(look, has_caption=bool(caption)),
    )


def python_code_block(
    code: str,
    col_width: float,
    context: dict,
    *,
    caption: Optional[str] = None,
    show_line_numbers: bool = True,
    first_line: int = 1,
    theme: Optional[str] = None,
    size: Optional[float] = None,
) -> Table:
    """
    A ReportLab Table showing Python 'code', syntax-highlighted, 'col_width'
    points wide, with an optional 'caption' bar and line numbers. 'theme' and
    'size' override the active text style's code settings.
    """
    look = resolve_code_look(context, theme, size)
    code = code.strip("\n")
    return _code_table(_tokenise_to_lines(code, look.theme), col_width, look, caption,
                       show_line_numbers, first_line)


def generic_code_block(
    code: str,
    col_width: float,
    context: dict,
    *,
    caption: Optional[str] = None,
    show_line_numbers: bool = True,
    first_line: int = 1,
    theme: Optional[str] = None,
    size: Optional[float] = None,
) -> Table:
    """
    A ReportLab Table showing 'code' verbatim (no highlighting), 'col_width'
    points wide, with an optional 'caption' bar and line numbers. 'theme' and
    'size' override the active text style's code settings.
    """
    look = resolve_code_look(context, theme, size)
    code = code.strip("\n")
    lines = [_escape(line) for line in code.split("\n")]
    return _code_table(lines, col_width, look, caption, show_line_numbers, first_line)
