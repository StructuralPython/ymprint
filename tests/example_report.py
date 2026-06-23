"""
example_report.py
Demonstrates all block styles from styles.py in a generated PDF.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, Paragraph, Spacer, Image
)
from reportlab.lib import colors
from io import BytesIO

from styles import get_styles, get_table_style, admonition_title_text, ADMONITION_META

# ---------------------------------------------------------------------------
# Helper: build an admonition flowable
# ---------------------------------------------------------------------------

def admonition(kind: str, body_text: str, col_width: float) -> Table:
    """
    Build a two-row, single-column Table for an admonition block.

    Row 0: title (icon + label)
    Row 1: body text
    """
    styles = get_styles()
    title_para = Paragraph(
        admonition_title_text(kind),
        styles[f"admonition_{kind}_title"],
    )
    body_para = Paragraph(body_text, styles[f"admonition_{kind}_body"])

    tbl = Table(
        [[title_para], [body_para]],
        colWidths=[col_width],
        style=get_table_style(kind),
    )
    return tbl


# ---------------------------------------------------------------------------
# Helper: build an image+caption flowable
# ---------------------------------------------------------------------------

def image_block(image_path_or_buffer, caption: str,
                max_width: float, max_height: float) -> Table:
    """
    Build a two-row, single-column Table:
      Row 0: Image (auto-scaled to fit max_width × max_height)
      Row 1: Caption paragraph
    """
    styles = get_styles()
    img = Image(image_path_or_buffer, width=max_width, height=max_height,
                kind="proportional")
    caption_para = Paragraph(caption, styles["image_caption"])

    tbl = Table(
        [[img], [caption_para]],
        colWidths=[max_width],
        style=get_table_style("image"),
    )
    return tbl


# ---------------------------------------------------------------------------
# Create a tiny placeholder PNG (grey rectangle) so the example is self-contained
# ---------------------------------------------------------------------------

def _make_placeholder_image(width_px=400, height_px=200):
    """Return a BytesIO PNG to use as a placeholder image."""
    try:
        from PIL import Image as PILImage
        img = PILImage.new("RGB", (width_px, height_px), color=(200, 200, 200))
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf
    except ImportError:
        # Pillow not available — return None and skip image block
        return None


# ---------------------------------------------------------------------------
# Build the PDF
# ---------------------------------------------------------------------------

def build_demo_pdf(output_path="demo_blocks.pdf"):
    PAGE_W, PAGE_H = A4
    MARGIN = 2 * cm
    CONTENT_WIDTH = PAGE_W - 2 * MARGIN

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN,  bottomMargin=MARGIN,
    )

    story = []
    SEP = Spacer(1, 0.4 * cm)

    # --- Admonition blocks ---
    admonition_samples = {
        "info":    "This is an informational message. Use it to provide "
                   "helpful context or background detail to the reader.",
        "warning": "Something unexpected might happen here. Double-check "
                   "your configuration before proceeding.",
        "danger":  "This action is <b>irreversible</b>. All data will be "
                   "permanently deleted. Proceed only if you are certain.",
        "tip":     "You can speed up this workflow by using the <i>--fast</i> "
                   "flag, which skips optional validation steps.",
        "note":    "At time of writing this feature is in beta. The API "
                   "surface may change in a future release.",
    }

    for kind, text in admonition_samples.items():
        story.append(admonition(kind, text, col_width=CONTENT_WIDTH))
        story.append(SEP)

    # --- Image block ---
    placeholder = _make_placeholder_image()
    if placeholder:
        story.append(Spacer(1, 0.4 * cm))
        story.append(
            image_block(
                placeholder,
                caption="Figure 1 — A placeholder image demonstrating the image block style.",
                max_width=CONTENT_WIDTH * 0.7,
                max_height=6 * cm,
            )
        )

    doc.build(story)
    print(f"PDF written to: {output_path}")


if __name__ == "__main__":
    build_demo_pdf()
