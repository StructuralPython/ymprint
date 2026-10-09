"""
styles.py
ReportLab styles for markdown-to-PDF report generation.

Covers:
  - Admonition blocks: Info, Warning, Danger, Tip, Note
  - Image blocks (image + caption)

Usage:
    from styles import get_styles, get_table_style
    styles = get_styles()
    ts = get_table_style("info")
"""

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
pt = 1  # ReportLab's internal unit; 1 pt == 1 unit
from reportlab.platypus import TableStyle

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------

# Base font
FONT_NORMAL = "Helvetica"
FONT_BOLD   = "Helvetica-Bold"
FONT_ITALIC = "Helvetica-Oblique"
FONT_MONO   = "Courier"

# Base sizes
BODY_FONT_SIZE   = 10
LABEL_FONT_SIZE  = 8
CAPTION_FONT_SIZE = 9

# Spacing
CELL_PADDING_H = 10   # horizontal padding inside admonition cells (pt)
CELL_PADDING_V = 8    # vertical padding inside admonition cells (pt)
BORDER_RADIUS  = 4    # not directly used by ReportLab, but documents intent

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------

class Palette:
    # Neutrals
    WHITE        = colors.HexColor("#FFFFFF")
    BODY_TEXT    = colors.HexColor("#1A1A2E")
    CAPTION_TEXT = colors.HexColor("#555555")
    TABLE_BORDER = colors.HexColor("#CCCCCC")

    # Info  (blue)
    INFO_BG      = colors.HexColor("#EFF6FF")
    INFO_BORDER  = colors.HexColor("#3B82F6")
    INFO_TITLE   = colors.HexColor("#1D4ED8")
    INFO_TEXT    = colors.HexColor("#1E3A5F")
    INFO_ICON    = "ℹ"

    # Warning  (amber)
    WARNING_BG     = colors.HexColor("#FFFBEB")
    WARNING_BORDER = colors.HexColor("#F59E0B")
    WARNING_TITLE  = colors.HexColor("#B45309")
    WARNING_TEXT   = colors.HexColor("#4D3A00")
    WARNING_ICON   = "⚠"

    # Danger  (red)
    DANGER_BG     = colors.HexColor("#FEF2F2")
    DANGER_BORDER = colors.HexColor("#EF4444")
    DANGER_TITLE  = colors.HexColor("#B91C1C")
    DANGER_TEXT   = colors.HexColor("#4D0000")
    DANGER_ICON   = "✖"

    # Tip  (green)
    TIP_BG     = colors.HexColor("#F0FDF4")
    TIP_BORDER = colors.HexColor("#22C55E")
    TIP_TITLE  = colors.HexColor("#15803D")
    TIP_TEXT   = colors.HexColor("#14532D")
    TIP_ICON   = "✔"

    # Note  (purple)
    NOTE_BG     = colors.HexColor("#FAF5FF")
    NOTE_BORDER = colors.HexColor("#A855F7")
    NOTE_TITLE  = colors.HexColor("#7E22CE")
    NOTE_TEXT   = colors.HexColor("#3B0764")
    NOTE_ICON   = "✎"

 # Blockquote  (neutral slate)
    BLOCKQUOTE_BG          = colors.HexColor("#F8F9FA")
    BLOCKQUOTE_BORDER      = colors.HexColor("#444444")   # slate-400
    BLOCKQUOTE_TEXT        = colors.HexColor("#374151")   # slate-700
    BLOCKQUOTE_ATTRIBUTION = colors.HexColor("#6B7280")   # slate-500

# ---------------------------------------------------------------------------
# Paragraph styles
# ---------------------------------------------------------------------------

def block_scale(context: dict) -> float:
    """
    Returns how much to scale block text and padding so that blocks keep their
    proportions to the document's body text. The design sizes in this module are
    for a 10 pt body, so a 40 pt body (e.g. a 1080p slide) scales blocks by 4.
    """
    return context['styles']['ymprint'].body.size / BODY_FONT_SIZE


def get_text_styles(scale: float = 1.0):
    """
    Return a dict of ParagraphStyle objects keyed by name, with every size
    multiplied by 'scale' (see block_scale).

    Keys
    ----
    admonition_<kind>_title   — bold label line  (kind: info/warning/danger/tip/note)
    admonition_<kind>_body    — body text inside the block
    image_caption             — caption below an image
    """
    base = getSampleStyleSheet()
    body_size = BODY_FONT_SIZE * scale
    label_size = LABEL_FONT_SIZE * scale
    caption_size = CAPTION_FONT_SIZE * scale

    # Shared defaults for admonition body text
    _admonition_body_defaults = dict(
        fontName=FONT_NORMAL,
        fontSize=body_size,
        leading=body_size * 1.4,
        spaceAfter=0,
        spaceBefore=0,
    )

    # Shared defaults for admonition title / label
    _admonition_title_defaults = dict(
        fontName=FONT_BOLD,
        fontSize=label_size,
        leading=label_size * 1.3,
        spaceAfter=3 * scale,
        spaceBefore=0,
        textTransform="uppercase",
    )

    blocks = {
        "info":    (Palette.INFO_TITLE,    Palette.INFO_TEXT),
        "warning": (Palette.WARNING_TITLE, Palette.WARNING_TEXT),
        "danger":  (Palette.DANGER_TITLE,  Palette.DANGER_TEXT),
        "tip":     (Palette.TIP_TITLE,     Palette.TIP_TEXT),
        "note":    (Palette.NOTE_TITLE,    Palette.NOTE_TEXT),
    }

    styles = {}

    for kind, (title_color, body_color) in blocks.items():
        styles[f"admonition_{kind}_title"] = ParagraphStyle(
            name=f"admonition_{kind}_title",
            textColor=title_color,
            **_admonition_title_defaults,
        )
        styles[f"admonition_{kind}_body"] = ParagraphStyle(
            name=f"admonition_{kind}_body",
            textColor=body_color,
            **_admonition_body_defaults,
        )

    # Blockquote — quote body (italic, indented feel via left padding on the table)
    styles["blockquote_body"] = ParagraphStyle(
        name="blockquote_body",
        fontName=FONT_ITALIC,
        fontSize=body_size * 1.1,           # slightly larger feels more editorial
        leading=body_size * 1.1 * 1.5,      # generous leading for readability
        textColor=Palette.BLOCKQUOTE_TEXT,
        spaceAfter=0,
        spaceBefore=0,
    )

    # Blockquote — optional attribution line  ("— Author Name")
    styles["blockquote_attribution"] = ParagraphStyle(
        name="blockquote_attribution",
        fontName=FONT_NORMAL,
        fontSize=body_size * 0.9,
        leading=body_size * 0.9 * 1.4,
        textColor=Palette.BLOCKQUOTE_ATTRIBUTION,
        spaceAfter=0,
        spaceBefore=6 * scale,
        alignment=2,   # right-align attribution
    )


    # Image caption
    styles["image_caption"] = ParagraphStyle(
        name="image_caption",
        fontName=FONT_ITALIC,
        fontSize=caption_size,
        leading=caption_size * 1.4,
        textColor=Palette.CAPTION_TEXT,
        alignment=1,   # centre
        spaceBefore=4 * scale,
        spaceAfter=0,
    )

    return styles


# ---------------------------------------------------------------------------
# Table styles
# ---------------------------------------------------------------------------

# Left-accent border width (pt)
ACCENT_WIDTH = 4

def _admonition_table_style(bg: colors.Color,
                             border: colors.Color,
                             scale: float = 1.0) -> TableStyle:
    """
    Build a TableStyle for a single-column admonition table.

    Layout assumption:
        Table has 1 column and 2 rows:
          row 0 — title  (icon + label)
          row 1 — body text
    """
    return TableStyle([
        # Background
        ("BACKGROUND",    (0, 0), (-1, -1), bg),

        # Left accent bar
        ("LINEBEFORE",    (0, 0), (0, -1), ACCENT_WIDTH * scale, border),

        # Outer border (thin, same hue as accent)
        ("BOX",           (0, 0), (-1, -1), 0.5 * scale, border),

        # No internal grid lines
        ("INNERGRID",     (0, 0), (-1, -1), 0, colors.transparent),

        # Padding
        ("LEFTPADDING",   (0, 0), (-1, -1), CELL_PADDING_H * scale),
        ("RIGHTPADDING",  (0, 0), (-1, -1), CELL_PADDING_H * scale),
        ("TOPPADDING",    (0, 0), (0,  0),  CELL_PADDING_V * scale),   # title row top
        ("BOTTOMPADDING", (0, 0), (0,  0),  3 * scale),                 # title row bottom (tight)
        ("TOPPADDING",    (0, 1), (0, -1),  4 * scale),                 # body row top
        ("BOTTOMPADDING", (0, 1), (0, -1),  CELL_PADDING_V * scale),    # body row bottom

        # Vertical alignment
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("ROUNDEDCORNERS", [4 * scale] * 4)
        # ROUNDEDCORNERS, [tl, tr, bl, br]
    ])


# Blockquote table style
# Layout: 1 column, 1–2 rows
#   row 0 — quote body text (required)
#   row 1 — attribution     (optional; omit the row if no attribution)
BLOCKQUOTE_ACCENT_WIDTH = 5   # slightly thicker than admonition bars
 
def _blockquote_table_style(scale: float = 1.0) -> TableStyle:
    return TableStyle([
        # Subtle background tint
        ("BACKGROUND",    (0, 0), (-1, -1), Palette.BLOCKQUOTE_BG),

        # Thick left accent bar — the defining visual of a blockquote
        ("LINEBEFORE",    (0, 0), (0, -1), BLOCKQUOTE_ACCENT_WIDTH * scale, Palette.BLOCKQUOTE_BORDER),

        # No outer box, no grid — keep it clean and "open"
        ("BOX",           (0, 0), (-1, -1), 0, colors.transparent),
        ("INNERGRID",     (0, 0), (-1, -1), 0, colors.transparent),

        # Generous horizontal padding to offset the accent bar visually
        ("LEFTPADDING",   (0, 0), (-1, -1), 14 * scale),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12 * scale),

        # Vertical padding: roomy on the quote body
        ("TOPPADDING",    (0, 0), (0,  0),  10 * scale),
        ("BOTTOMPADDING", (0, 0), (0,  0),  6 * scale),

        # Attribution row (row 1) sits tight to the quote
        ("TOPPADDING",    (0, 1), (0, -1),  0),
        ("BOTTOMPADDING", (0, 1), (0, -1),  10 * scale),
        ("ROUNDEDCORNERS", [4 * scale] * 4),

        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ])


BLOCKQUOTE_TABLE_STYLE = _blockquote_table_style()


# Background and border colours for each admonition kind
ADMONITION_COLORS: dict[str, tuple[colors.Color, colors.Color]] = {
    "info":    (Palette.INFO_BG,    Palette.INFO_BORDER),
    "warning": (Palette.WARNING_BG, Palette.WARNING_BORDER),
    "danger":  (Palette.DANGER_BG,  Palette.DANGER_BORDER),
    "tip":     (Palette.TIP_BG,     Palette.TIP_BORDER),
    "note":    (Palette.NOTE_BG,    Palette.NOTE_BORDER),
}

# Pre-built table styles for each admonition kind
ADMONITION_TABLE_STYLES: dict[str, TableStyle] = {
    kind: _admonition_table_style(bg, border) for kind, (bg, border) in ADMONITION_COLORS.items()
}

# Image/caption table style
IMAGE_TABLE_STYLE = TableStyle([
    # No background, no border — image block is decoration-free
    ("BACKGROUND",   (0, 0), (-1, -1), colors.transparent),
    ("BOX",          (0, 0), (-1, -1), 0,   colors.transparent),
    ("INNERGRID",    (0, 0), (-1, -1), 0,   colors.transparent),

    # Padding
    ("LEFTPADDING",  (0, 0), (-1, -1), 0),
    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ("TOPPADDING",   (0, 0), (-1, -1), 0),
    ("BOTTOMPADDING",(0, 0), (0,  0),  4),   # gap between image and caption
    ("BOTTOMPADDING",(0, 1), (0, -1),  0),

    # Centre both image and caption horizontally
    ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
    ("VALIGN",       (0, 0), (-1, -1), "TOP"),
])


def get_table_style(block_type: str, scale: float = 1.0) -> TableStyle:
    """
    Return the TableStyle for a given block type.
 
    Parameters
    ----------
    block_type : str
        One of: "info", "warning", "danger", "tip", "note", "blockquote", "image"
    scale : float
        Multiplies padding and rule widths (see block_scale).
 
    Returns
    -------
    TableStyle
    """
    if block_type == "image":
        return IMAGE_TABLE_STYLE
    if block_type == "blockquote":
        return _blockquote_table_style(scale)
    try:
        bg, border = ADMONITION_COLORS[block_type]
    except KeyError:
        valid = list(ADMONITION_TABLE_STYLES) + ["blockquote", "image"]
        raise ValueError(
            f"Unknown block type '{block_type}'. Choose from: {valid}"
        )
    return _admonition_table_style(bg, border, scale)


# ---------------------------------------------------------------------------
# Icon / label helpers
# ---------------------------------------------------------------------------

ADMONITION_META: dict[str, dict] = {
    "info":    {"icon": Palette.INFO_ICON,    "label": "Info"},
    "warning": {"icon": Palette.WARNING_ICON, "label": "Warning"},
    "danger":  {"icon": Palette.DANGER_ICON,  "label": "Danger"},
    "tip":     {"icon": Palette.TIP_ICON,     "label": "Tip"},
    "note":    {"icon": Palette.NOTE_ICON,    "label": "Note"},
}


def admonition_title_text(kind: str, label: str | None = None) -> str:
    """Return  '⚠  WARNING'  style label string for the title row."""
    meta = ADMONITION_META[kind]
    if label is not None:
        return f"{meta['icon']}  {label.upper()}"
    return f"{meta['icon']}  {meta['label'].upper()}"
