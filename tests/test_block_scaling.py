import pathlib
import textwrap

import pymupdf as mu

from ymprint.report_reader import load_report


def render(tmp_path: pathlib.Path, source: str) -> mu.Document:
    src = tmp_path / "doc.yml"
    src.write_text(textwrap.dedent(source))
    dest = tmp_path / "doc.pdf"
    load_report(src, dest, None)
    return mu.open(dest)


def spans(doc: mu.Document) -> list[dict]:
    """Every text span in the document, with its font name, size and bbox."""
    found = []
    for page in doc:
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                found.extend(line["spans"])
    return found


def span_with(doc: mu.Document, text: str) -> dict:
    return next(s for s in spans(doc) if text in s["text"])


def test_bold_and_italic_markdown_use_bundled_font_faces(tmp_path):
    doc = render(tmp_path, """
        _style:
          body:
            font: Inter
        Fonts:
          - Plain then **heavy** then *slanted*.
    """)
    regular = span_with(doc, "Plain")["font"]
    bold = span_with(doc, "heavy")["font"]
    italic = span_with(doc, "slanted")["font"]
    # The embedded names carry the face (e.g. "Inter18pt-Bold")
    assert "Bold" in bold and bold != regular
    assert "Italic" in italic and italic != regular


def test_oblique_faces_serve_as_italic(tmp_path):
    doc = render(tmp_path, """
        _style:
          body:
            font: DejaVuSans
        Fonts:
          - Some *slanted* text.
    """)
    assert span_with(doc, "slanted")["font"].endswith("DejaVuSans-Oblique")


ADMONITION_DOC = """
    _style:
      body:
        size: {size}
    Callouts:
      - _tip: Tip body text
      - _blockquote:
          quote: Quoted text
          attribution: Someone
"""


def test_admonition_and_quote_text_keep_default_size_at_default_body(tmp_path):
    doc = render(tmp_path, ADMONITION_DOC.format(size=10))
    assert round(span_with(doc, "Tip body text")["size"]) == 10
    assert round(span_with(doc, "Quoted text")["size"]) == 11


def test_admonition_and_quote_text_scale_with_body_size(tmp_path):
    doc = render(tmp_path, ADMONITION_DOC.format(size=40))
    assert round(span_with(doc, "Tip body text")["size"]) == 40
    assert round(span_with(doc, "Quoted text")["size"]) == 44
    assert round(span_with(doc, "Someone")["size"]) == 36


def test_image_caption_scales_with_body_size(tmp_path):
    image = pathlib.Path(__file__).parent / "test-data" / "test_image.png"
    doc = render(tmp_path, f"""
        _style:
          body:
            size: 20
        Figure:
          - _img:
              source: {image}
              caption: The caption
    """)
    assert round(span_with(doc, "The caption")["size"]) == 18


def test_table_body_rows_use_leading_and_colour(tmp_path):
    doc = render(tmp_path, """
        _tablestyle:
          body:
            text:
              size: 30
              color: "#ff0000"
        Table:
          - - Name: first
            - Name: second
    """)
    first, second = span_with(doc, "first"), span_with(doc, "second")
    # Rows are at least one line of 30 pt text apart (they used to overlap)
    assert second["bbox"][1] - first["bbox"][1] >= 30 * 1.4
    assert first["color"] == 0xFF0000


def test_bold_table_headers_keep_font_name_case(tmp_path):
    doc = render(tmp_path, """
        _tablestyle:
          headers:
            text:
              font: NotoSans
              bold: true
        Table:
          - - Header: first
            - Header: second
    """)
    assert span_with(doc, "Header")["font"].endswith("NotoSans-Bold")


def test_two_digit_line_numbers_stay_on_one_line(tmp_path):
    source = "".join(f"            line_{n} = {n}\n" for n in range(1, 13))
    doc = render(tmp_path, (
        "_style:\n"
        "  body:\n"
        "    size: 30\n"
        "Code:\n"
        "  - _code:\n"
        "      line_numbers: true\n"
        "      width_ratio: 1\n"
        "      source: |\n"
    ) + source)
    numbers = [s["text"].strip() for s in spans(doc) if s["text"].strip().isdigit()]
    assert "10" in numbers and "12" in numbers


def test_code_block_shows_markup_literally(tmp_path):
    doc = render(tmp_path, """
        Code:
          - _code:
              source: |
                <font color='red'>literal</font> & more
    """)
    text = "".join(page.get_text() for page in doc)
    assert "<font color='red'>literal</font> & more" in text
