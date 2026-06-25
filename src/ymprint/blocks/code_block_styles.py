"""
code_block_styles.py
====================
ReportLab styles and flowable builder for Python code blocks.

Features
--------
- Syntax highlighting via Pygments (One Dark-inspired palette)
- DejaVu Sans Mono — bundled in the ``fonts/`` subdirectory alongside this
  module, so no system fonts are required on any platform
- Line numbers, optional caption, horizontal rule separator

Dependencies
------------
    pip install reportlab pygments

Package layout
--------------
    your_package/
        code_block_styles.py
        fonts/
            DejaVuSansMono.ttf
            DejaVuSansMono-Bold.ttf
            DejaVuSansMono-Oblique.ttf

Usage
-----
    from code_block_styles import python_code_block, register_fonts

    register_fonts()   # call once at program start

    block = python_code_block(
        code=\"\"\"
    def greet(name: str) -> str:
        return f"Hello, {name}!"
    \"\"\",
        col_width=440,
        caption="example.py",
    )
    story.append(block)
"""
import pathlib
from typing import Optional

from pygments import highlight as _hl
from pygments.lexers import PythonLexer
from pygments.formatters import RawTokenFormatter   # gives us (ttype, value) pairs
from pygments.token import (
    Token, Comment, Keyword, Name, Number, Operator,
    Punctuation, String, Literal,
)
from pygments.lexers import PythonLexer

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Table, TableStyle, Spacer

# ---------------------------------------------------------------------------
# Font registration
# ---------------------------------------------------------------------------

# Bundled fonts directory — sits alongside this module file.
# Ship the fonts/ subdirectory with your package; no system fonts required.
_FONTS_DIR = pathlib.Path(__file__).parents[1] / "config" / "fonts" 
FONT_MONO         = "DejaVuSansMono"
FONT_MONO_BOLD    = "DejaVuSansMono-Bold"
FONT_MONO_OBLIQUE = "DejaVuSansMono-Oblique"

_FONT_FILES = {
    FONT_MONO: f"{FONT_MONO}.ttf",
    FONT_MONO_BOLD: f"{FONT_MONO_BOLD}.ttf",
    FONT_MONO_OBLIQUE: f"{FONT_MONO_OBLIQUE}.ttf",
}


def register_fonts() -> None:
    """
    Register the bundled DejaVu Sans Mono TTF faces with ReportLab.

    Prepends the package-local ``fonts/`` directory to ReportLab's
    ``TTFSearchPath`` so that ``TTFont('DejaVuSansMono', 'DejaVuSansMono.ttf')``
    resolves to the bundled copy on any platform, regardless of what system
    fonts are installed.

    Call once at program start before building any flowables.

    Raises
    ------
    FileNotFoundError
        If the bundled ``fonts/`` directory or any expected TTF file is missing.
        This indicates a broken package installation rather than a missing system
        font, so we raise rather than silently fall back.
    """
    if not _FONTS_DIR.exists():
        raise FileNotFoundError(
            f"Bundled fonts directory not found: {_FONTS_DIR}\n"
            "Ensure the 'fonts/' directory is distributed alongside this module."
        )

    # Prepend so our bundled copies take priority over any system-installed
    # versions of the same filename.
    import reportlab.rl_config as rl_config
    if _FONTS_DIR not in rl_config.TTFSearchPath:
        rl_config.TTFSearchPath.insert(0, str(_FONTS_DIR.resolve()))

    for name, filename in _FONT_FILES.items():
        font_path = _FONTS_DIR / filename
        if not font_path.exists():
            raise FileNotFoundError(
                f"Bundled font file missing: {font_path.resolve()}\n"
                "Ensure all DejaVu Sans Mono TTF files are present in fonts/."
            )
        pdfmetrics.registerFont(TTFont(name, filename))


# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------

# CODE_FONT_SIZE   = 9
# CODE_LEADING     = CODE_FONT_SIZE * 1.55
LINE_NUM_WIDTH   = 28          # pt — column reserved for line numbers
GUTTER_WIDTH     = 8           # pt — gap between line numbers and code
CELL_PAD_H       = 12          # pt — left/right padding of the outer block
CELL_PAD_V       = 10          # pt — top/bottom padding of the outer block
# CAPTION_FONT     = "Helvetica"
# CAPTION_FONT_SIZE = 8


class _PaperLight:
    """
    Paper Light — a print-optimised light theme for code blocks.

    Designed for white/transparent backgrounds. All syntax colours are
    tested for WCAG AA contrast against white (#FFFFFF).

    Inspired by GitHub Light and Xcode's default light theme, with ink
    colours shifted warmer to read naturally on paper.
    """
    # Background / chrome
    BG           = colors.HexColor("#FFFFFF")   # transparent / white page
    GUTTER_BG    = colors.HexColor("#F3F4F6")   # grey-100 — subtle gutter tint
    BORDER       = colors.HexColor("#D1D5DB")   # grey-300 — light but visible
    CAPTION_BG   = colors.HexColor("#F3F4F6")   # matches gutter

    # Text
    DEFAULT      = colors.HexColor("#24292F")   # near-black — GitHub's body ink
    LINE_NUM     = colors.HexColor("#9CA3AF")   # grey-400 — recedes from code
    CAPTION_TEXT = colors.HexColor("#6B7280")   # grey-500

    # Syntax
    KEYWORD      = colors.HexColor("#8250DF")   # purple   — GitHub Light keyword
    BUILTIN      = colors.HexColor("#CF222E")   # red      — built-ins & exceptions
    DECORATOR    = colors.HexColor("#0550AE")   # blue     — decorators
    FUNCTION     = colors.HexColor("#6639BA")   # violet   — function names
    CLASS_NAME   = colors.HexColor("#953800")   # burnt orange — class names
    STRING       = colors.HexColor("#0A3069")   # deep blue — strings (not green;
                                                #   green ink fades on paper)
    NUMBER       = colors.HexColor("#0550AE")   # blue     — numeric literals
    COMMENT      = colors.HexColor("#57606A")   # grey-600 — muted but readable
    OPERATOR     = colors.HexColor("#CF222E")   # red      — operators
    PUNCTUATION  = colors.HexColor("#24292F")   # same as default
    CONSTANT     = colors.HexColor("#0550AE")   # blue     — True/False/None

# ---------------------------------------------------------------------------
# Token → colour mapping
# ---------------------------------------------------------------------------

def _token_color(ttype) -> colors.Color:
    """Map a Pygments token type to a ReportLab colour."""
    if ttype in Token.Keyword or ttype in Token.Keyword.Namespace:
        return _PaperLight.KEYWORD
    if ttype in Token.Keyword.Constant:
        return _PaperLight.CONSTANT
    if ttype in Token.Name.Builtin or ttype in Token.Name.Exception:
        return _PaperLight.BUILTIN
    if ttype in Token.Name.Decorator:
        return _PaperLight.DECORATOR
    if ttype in Token.Name.Function or ttype in Token.Name.Function.Magic:
        return _PaperLight.FUNCTION
    if ttype in Token.Name.Class:
        return _PaperLight.CLASS_NAME
    if ttype in Token.Literal.String or ttype in Token.String:
        return _PaperLight.STRING
    if ttype in Token.Literal.Number or ttype in Token.Number:
        return _PaperLight.NUMBER
    if ttype in Token.Comment:
        return _PaperLight.COMMENT
    if ttype in Token.Operator:
        return _PaperLight.OPERATOR
    if ttype in Token.Punctuation:
        return _PaperLight.PUNCTUATION
    return _PaperLight.DEFAULT


def _token_font(ttype) -> str:
    """Map a Pygments token type to a font name."""
    if ttype in Token.Comment:
        return FONT_MONO_OBLIQUE
    if ttype in Token.Keyword or ttype in Token.Name.Class:
        return FONT_MONO_BOLD
    return FONT_MONO


# ---------------------------------------------------------------------------
# XML escaping for ReportLab Paragraph markup
# ---------------------------------------------------------------------------

def _escape(text: str) -> str:
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


# ---------------------------------------------------------------------------
# Core: tokenise + build per-line Paragraph markup
# ---------------------------------------------------------------------------

def _tokenise_to_lines(code: str) -> list[str]:
    """
    Tokenise ``code`` with Pygments and return a list of ReportLab
    Paragraph XML strings — one per source line, with inline colour spans.
    """
    lexer = PythonLexer(stripnl=False, ensurenl=True)
    tokens = list(lexer.get_tokens(code))

    # Walk tokens, building up line buffers
    lines: list[list[str]] = [[]]   # list of lines; each line is a list of spans

    for ttype, value in tokens:
        col   = _token_color(ttype)
        font  = _token_font(ttype)
        hex_c = col.hexval()# if hasattr(col, 'hexval') else col.hexColor()

        # Split on newlines — a single token may span multiple lines
        parts = value.split("\n")
        for i, part in enumerate(parts):
            if i > 0:
                lines.append([])   # start a new line
            if part:
                span = (
                    f'<font name="{font}" color="{hex_c}">'
                    f'{_escape(part)}</font>'
                )
                lines[-1].append(span)

    # Remove a trailing empty line that Pygments always appends
    if lines and lines[-1] == []:
        lines.pop()

    return ["".join(spans) if spans else " " for spans in lines]


# ---------------------------------------------------------------------------
# Paragraph styles
# ---------------------------------------------------------------------------

def _code_line_style(context: dict) -> ParagraphStyle:
    body_size = context['styles']['yaml']['_style']['body']['size']
    return ParagraphStyle(
        name="code_line",
        fontName=FONT_MONO,
        fontSize=body_size * 0.9,
        leading=body_size * 0.9 * 1.55,
        textColor=_PaperLight.DEFAULT,
        backColor=_PaperLight.BG,
        spaceBefore=0,
        spaceAfter=0,
        leftIndent=0,
        rightIndent=0,
        splitLongWords=False,   # don't break tokens mid-word
        wordWrap="LTR",
    )


def _line_number_style(context: dict) -> ParagraphStyle:
    body_size = context['styles']['yaml']['_style']['body']['size']
    return ParagraphStyle(
        name="code_line_number",
        fontName=FONT_MONO,
        fontSize=body_size * 0.9,
        leading=body_size * 0.9 * 1.55,
        textColor=_PaperLight.LINE_NUM,
        backColor=_PaperLight.GUTTER_BG,
        alignment=2,   # right-align numbers
        spaceBefore=0,
        spaceAfter=0,
    )


def _caption_style(context: dict) -> ParagraphStyle:
    body_size = context['styles']['yaml']['_style']['body']['size']
    body_font = context['styles']['yaml']['_style']['body']['font']
    return ParagraphStyle(
        name="code_caption",
        fontName=body_font,
        fontSize=body_size * 0.8,
        leading=body_size * 0.8 * 1.4,
        textColor=_PaperLight.CAPTION_TEXT,
        backColor=_PaperLight.CAPTION_BG,
        alignment=0,
        spaceBefore=0,
        spaceAfter=0,
    )


# ---------------------------------------------------------------------------
# Table styles
# ---------------------------------------------------------------------------

def _code_table_style(n_rows: int, show_line_numbers: bool) -> TableStyle:
    """TableStyle for the inner grid (line numbers | code)."""
    cmds = [
        # Backgrounds
        ("BACKGROUND",    (0, 0), (-1, -1), _PaperLight.BG),
        ("BACKGROUND",    (0, 0), (0, -1),  _PaperLight.GUTTER_BG),

        # No borders between cells
        ("BOX",           (0, 0), (-1, -1), 0, colors.transparent),
        ("INNERGRID",     (0, 0), (-1, -1), 0, colors.transparent),

        # Tight cell padding — leading handles vertical spacing
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),

        # Right-pad the gutter column to create the gap
        ("RIGHTPADDING",  (0, 0), (0,  -1), GUTTER_WIDTH),

        # Align everything to the top of each cell
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]

    if not show_line_numbers:
        # Hide gutter background when line numbers are off
        cmds.append(("BACKGROUND", (0, 0), (0, -1), _PaperLight.BG))

    return TableStyle(cmds)


def _outer_table_style(has_caption: bool) -> TableStyle:
    """TableStyle for the outer wrapper (optional caption bar + code grid)."""
    cmds = [
        ("BACKGROUND",    (0, 0), (-1, -1), _PaperLight.BG),
        ("BOX",           (0, 0), (-1, -1), 1,   _PaperLight.BORDER),
        ("INNERGRID",     (0, 0), (-1, -1), 0,   colors.transparent),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]

    if has_caption:
        # Caption row: background + bottom separator line
        cmds += [
            ("BACKGROUND",    (0, 0), (0, 0),  _PaperLight.CAPTION_BG),
            ("LINEBELOW",     (0, 0), (0, 0),  0.5, _PaperLight.BORDER),
            ("LEFTPADDING",   (0, 0), (0, 0),  CELL_PAD_H),
            ("RIGHTPADDING",  (0, 0), (0, 0),  CELL_PAD_H),
            ("TOPPADDING",    (0, 0), (0, 0),  6),
            ("BOTTOMPADDING", (0, 0), (0, 0),  6),
        ]
        code_row = 1
    else:
        code_row = 0

    # Code grid row: add breathing-room padding inside the dark background
    cmds += [
        ("LEFTPADDING",   (0, code_row), (0, code_row), CELL_PAD_H),
        ("RIGHTPADDING",  (0, code_row), (0, code_row), CELL_PAD_H),
        ("TOPPADDING",    (0, code_row), (0, code_row), CELL_PAD_V),
        ("BOTTOMPADDING", (0, code_row), (0, code_row), CELL_PAD_V),
    ]

    return TableStyle(cmds)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def python_code_block(
    code: str,
    col_width: float,
    context: dict,
    *,
    caption: Optional[str] = None,
    show_line_numbers: bool = True,
    first_line: int = 1,
) -> Table:
    """
    Build and return a ReportLab ``Table`` flowable for a Python code block.

    Parameters
    ----------
    code : str
        Raw Python source code (may include leading/trailing newlines).
    col_width : float
        Total available width in points (e.g. page width minus margins).
    caption : str, optional
        Filename or short description shown in a header bar above the code.
        Pass ``None`` to omit the caption bar entirely.
    show_line_numbers : bool
        Whether to render a gutter column with line numbers. Default: True.
    first_line : int
        Number to assign to the first line. Default: 1.

    Returns
    -------
    Table
        A ReportLab Platypus flowable ready to append to a story.

    Notes
    -----
    Call ``register_fonts()`` once before using this function so that
    DejaVu Sans Mono is available. If the TTF files are not found,
    the function falls back to Courier automatically.
    """
    register_fonts()

    code = code.strip("\n")   # remove leading/trailing blank lines
    markup_lines = _tokenise_to_lines(code)
    n_lines      = len(markup_lines)

    line_style   = _code_line_style(context)
    lnum_style   = _line_number_style(context)

    # --- Build inner grid rows ---
    if show_line_numbers:
        gutter_w = LINE_NUM_WIDTH
        code_w   = col_width - gutter_w - GUTTER_WIDTH - (CELL_PAD_H * 2)
    else:
        gutter_w = 0
        code_w   = col_width - (CELL_PAD_H * 2)

    inner_rows = []
    for i, markup in enumerate(markup_lines):
        line_num_para = Paragraph(str(first_line + i), lnum_style)
        code_para     = Paragraph(markup, line_style)
        if show_line_numbers:
            inner_rows.append([line_num_para, code_para])
        else:
            inner_rows.append([code_para])

    col_widths = [gutter_w, code_w] if show_line_numbers else [code_w]

    inner_table = Table(
        inner_rows,
        colWidths=col_widths,
        style=_code_table_style(n_lines, show_line_numbers),
    )

    # --- Wrap in outer table (adds padding, border, optional caption) ---
    if caption:
        caption_para = Paragraph(f"  {_escape(caption)}", _caption_style(context))
        outer_rows   = [[caption_para], [inner_table]]
    else:
        outer_rows = [[inner_table]]

    outer_table = Table(
        outer_rows,
        colWidths=[col_width],
        style=_outer_table_style(has_caption=bool(caption)),
    )

    return outer_table
