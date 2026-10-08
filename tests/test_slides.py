import pathlib
import textwrap

from pypdf import PdfReader

from ymprint.report_reader import load_report


def render(tmp_path: pathlib.Path, source: str) -> PdfReader:
    src = tmp_path / "deck.yml"
    src.write_text(textwrap.dedent(source))
    dest = tmp_path / "deck.pdf"
    load_report(src, dest, None)
    return PdfReader(dest)


def page_texts(reader: PdfReader) -> list[str]:
    return [page.extract_text() for page in reader.pages]


DECK = """
    _doc:
      page-size: [960, 540]
      slides: true
    First slide:
      - Alpha
    Second slide:
      - Bravo
      - Sub heading:
        - Nested content stays on its slide
    Third slide: Charlie
"""


def test_each_top_level_heading_is_one_slide(tmp_path):
    reader = render(tmp_path, DECK)
    texts = page_texts(reader)
    assert len(texts) == 3
    assert "First slide" in texts[0] and "Alpha" in texts[0]
    assert "Second slide" in texts[1] and "Nested content" in texts[1]
    assert "Third slide" in texts[2] and "Charlie" in texts[2]


def test_slide_mode_off_does_not_break_pages(tmp_path):
    reader = render(tmp_path, DECK.replace("slides: true", "slides: false"))
    assert len(reader.pages) == 1


def test_slide_mode_from_config_file(tmp_path):
    (tmp_path / "deck.ymprint.yml").write_text("_doc:\n  slides: true\n")
    src = tmp_path / "deck.yml"
    src.write_text("One:\n  - a\nTwo:\n  - b\n")
    dest = tmp_path / "deck.pdf"
    load_report(src, dest, tmp_path)
    assert len(PdfReader(dest).pages) == 2


def test_nested_headings_do_not_start_slides(tmp_path):
    reader = render(tmp_path, """
        _doc:
          slides: true
        Only slide:
          - Part one:
            - a
          - Part two:
            - b
    """)
    assert len(reader.pages) == 1
