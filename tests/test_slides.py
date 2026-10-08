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


# --- Layouts and frames --------------------------------------------------------------

import pytest
from reportlab.platypus import Paragraph, Table

from ymprint.config.config_loaders import load_report_config
from ymprint.config.doctemplate import FrameConfig
from ymprint.context_builder import build_context
from ymprint.exceptions import YMPrintSyntaxException
from ymprint.slides import SlideFlowable
from ymprint.story_builder import build_story

TEST_DATA = pathlib.Path(__file__).parent / "test-data"

SLIDE_DOC = {
    "page-size": [960, 540],
    "slides": True,
    "templates": {"default": {"margins": {"top": 20, "left": 40, "right": 40, "bottom": 20}}},
}


def slide_story(content: dict, doc: dict = SLIDE_DOC, config_path=None):
    source = {"_doc": dict(doc), **content}
    styles, tbl, doc_data = load_report_config(source, config_path)
    context = build_context(
        source, styles, doc_data, tbl, {}, TEST_DATA / "deck.yml", TEST_DATA / "deck.pdf", None
    )
    return build_story(source, context)


def frame_texts(slide: SlideFlowable) -> dict[str, list[str]]:
    return {
        frame.name: [f.getPlainText() for f in frame.flowables if isinstance(f, Paragraph)]
        for frame in slide.frames
    }


def test_frame_box_resolves_fractions_and_points():
    frame = FrameConfig.model_validate([0.5, 0.25, 100, 0.5])
    # y is converted from top-left to ReportLab's bottom-left origin
    assert frame.resolve(800, 400) == (400.0, 100.0, 100.0, 200.0)


def test_frame_accepts_mapping_form():
    frame = FrameConfig.model_validate({"box": [0, 0, 1, 1], "valign": "middle", "overflow": "error"})
    assert (frame.valign, frame.overflow) == ("middle", "error")


@pytest.mark.parametrize("bad_box", [[0, 0, 1], [0, 0, 0, 1], [-1, 0, 1, 1]])
def test_frame_rejects_invalid_box(bad_box):
    with pytest.raises(ValueError):
        FrameConfig.model_validate(bad_box)


def test_default_layout_puts_title_and_content_in_body():
    (slide,) = slide_story({"Hello": ["a", "b"]})
    assert isinstance(slide, SlideFlowable)
    assert frame_texts(slide) == {"body": ["Hello", "a", "b"]}


def test_frame_directive_routes_content():
    (slide,) = slide_story({
        "Side by side": [{"_slide": "two-column"}, "left text", {"_frame": "right"}, "right text"],
    })
    assert frame_texts(slide) == {
        "title": ["Side by side"],
        "left": ["left text"],
        "right": ["right text"],
    }


def test_frame_directive_in_mapping_form():
    (slide,) = slide_story({
        "Mapping slide": {"_slide": "two-column", "_frame": "right", "Sub": ["nested"]},
    })
    texts = frame_texts(slide)
    assert texts["left"] == []
    assert texts["right"] == ["Sub", "nested"]


def test_leading_textstyle_applies_to_whole_slide():
    doc_style = {"styles": {"big": {"body": {"size": 30}}}}
    source = {"_style": doc_style, "Styled": [{"_textstyle": "big"}, {"_slide": "two-column"}, "l", {"_frame": "right"}, "r"]}
    (slide,) = slide_story(source)
    sizes = {f.name: [p.style.fontSize for p in f.flowables if isinstance(p, Paragraph)] for f in slide.frames}
    assert sizes["left"] == [30] and sizes["right"] == [30]


def test_image_is_sized_to_its_frame():
    (slide,) = slide_story({
        "Picture": [{"_slide": "two-column"}, {"_frame": "right"}, {"_img": {"source": "test_image.png"}}],
    })
    right = next(f for f in slide.frames if f.name == "right")
    (table,) = right.flowables
    assert isinstance(table, Table)
    assert table._colWidths[0] <= right.width


def test_custom_layouts_merge_across_config_layers(tmp_path):
    (tmp_path / "deck.ymprint.yml").write_text(
        "_doc:\n  layouts:\n    from-config:\n      main: [0, 0, 1, 1]\n"
    )
    doc = {**SLIDE_DOC, "layouts": {"from-content": {"main": [0, 0, 1, 1]}}}
    first, _, second = slide_story(
        {"A": [{"_slide": "from-config"}, "a"], "B": [{"_slide": "from-content"}, "b"]},
        doc=doc, config_path=tmp_path,
    )
    assert [f.name for f in first.frames] == ["main"]
    assert [f.name for f in second.frames] == ["main"]


def test_unknown_layout_is_an_authoring_error():
    with pytest.raises(YMPrintSyntaxException, match="layout 'nope' not found"):
        slide_story({"S": [{"_slide": "nope"}]})


def test_unknown_frame_is_an_authoring_error():
    with pytest.raises(YMPrintSyntaxException, match="Frame 'middle' not found"):
        slide_story({"S": [{"_frame": "middle"}, "x"]})


def test_slide_directive_must_come_first():
    with pytest.raises(YMPrintSyntaxException, match="first item"):
        slide_story({"S": ["x", {"_slide": "two-column"}]})


def test_frame_inside_subsection_is_rejected():
    with pytest.raises(YMPrintSyntaxException, match="_frame"):
        slide_story({"S": [{"Sub": [{"_frame": "right"}, "x"]}]})


def test_directives_outside_slide_mode_are_rejected():
    doc = {**SLIDE_DOC, "slides": False}
    with pytest.raises(YMPrintSyntaxException, match="slide mode"):
        slide_story({"S": [{"_frame": "right"}]}, doc=doc)


LONG_TEXT = "Lots of words in a long paragraph. " * 200


def test_overflow_shrink_keeps_slide_on_one_page(tmp_path):
    reader = render(tmp_path, f"""
        _doc:
          page-size: [960, 540]
          slides: true
        Too much:
          - "{LONG_TEXT}"
    """)
    assert len(reader.pages) == 1


def test_overflow_error_is_an_authoring_error(tmp_path):
    with pytest.raises(YMPrintSyntaxException, match="does not fit"):
        render(tmp_path, f"""
            _doc:
              page-size: [960, 540]
              slides: true
              layouts:
                strict:
                  body:
                    box: [0, 0, 1, 1]
                    overflow: error
            Too much:
              - _slide: strict
              - "{LONG_TEXT}"
        """)
