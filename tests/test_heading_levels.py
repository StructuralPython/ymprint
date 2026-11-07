"""Heading levels count headings, not YAML containers; headings are bookmarked."""
import pathlib

import fitz
import pytest
from reportlab.platypus import Paragraph

from ymprint.blocks import section
from ymprint.blocks.registry import BlockRegistry
from ymprint.config.config_loaders import load_report_config
from ymprint.context_builder import build_context
from ymprint.outline import OUTLINE_ATTR, heading_style_name, mark_outline
from ymprint.report_reader import load_report
from ymprint.story_builder import build_story


def make_context(source=None, blocks=None):
    source = source or {}
    styles, tbl, doc = load_report_config(source, None)
    return build_context(
        source, styles, doc, tbl, {}, pathlib.Path.cwd(), pathlib.Path.cwd(), None, blocks=blocks,
    )


def headings(story):
    """(text, style name) for each heading paragraph in 'story'."""
    return [
        (f.getPlainText(), f.style.name)
        for f in story
        if isinstance(f, Paragraph) and f.style.name.startswith("h")
    ]


@pytest.mark.parametrize(
    "source",
    [
        # Mapping nesting.
        {"A": {"B": {"C": {"D": "text"}}}},
        # List nesting: each `- Heading:` is one level, not two.
        {"A": [{"B": [{"C": [{"D": "text"}]}]}]},
        # Paragraphs between the headings.
        {"A": ["p", {"B": ["p", {"C": ["p", {"D": "text"}]}]}]},
        # A list, then mappings.
        {"A": [{"B": {"C": {"D": "text"}}}]},
    ],
    ids=["mapping", "list", "list-with-paragraphs", "list-then-mapping"],
)
def test_each_nested_heading_is_one_level_down(source):
    story = build_story(source, make_context())
    assert headings(story) == [("A", "h1"), ("B", "h2"), ("C", "h3"), ("D", "h4")]


def test_siblings_share_a_level():
    story = build_story({"A": [{"B": "x"}, "para", {"C": "y"}], "D": "z"}, make_context())
    assert headings(story) == [("A", "h1"), ("B", "h2"), ("C", "h2"), ("D", "h1")]


def test_headings_deeper_than_six_render_as_h6():
    source = "text"
    for name in reversed("ABCDEFGH"):
        source = [{name: source}]
    story = build_story({"Top": source}, make_context())
    levels = [style for _, style in headings(story)]
    assert levels == ["h1", "h2", "h3", "h4", "h5", "h6", "h6", "h6", "h6"]
    # The outline keeps the true depth.
    assert [getattr(f, OUTLINE_ATTR)[1] for f in story if hasattr(f, OUTLINE_ATTR)] == list(range(1, 10))


def test_heading_style_name_clamps():
    assert heading_style_name(0) == "h1"
    assert heading_style_name(3) == "h3"
    assert heading_style_name(9) == "h6"


def test_headings_are_marked_for_the_outline():
    story = build_story({"Report **title**": [{"Sub": "text"}]}, make_context())
    marks = [getattr(f, OUTLINE_ATTR) for f in story if hasattr(f, OUTLINE_ATTR)]
    assert marks == [("Report title", 1), ("Sub", 2)]


def test_mark_outline_skips_empty_titles():
    para = Paragraph("   ")
    mark_outline(para, 2)
    assert not hasattr(para, OUTLINE_ATTR)


def test_blocks_see_their_section():
    seen = []
    blocks = BlockRegistry()

    @blocks.block("_probe")
    def probe(block_key, block_value, context):
        seen.append(dict(section(context)))
        return []

    styles = {"styles": {"fine-print": {"body": {"size": 6}}}}
    source = {
        "_probe_top": None,
        "A": [
            {"_probe": None},
            {"B": [{"_textstyle": "fine-print"}, {"_probe": None}]},
        ],
    }
    context = make_context({"_style": styles}, blocks=blocks)
    build_story(source, context)
    assert seen == [
        {"level": 1, "text_style": "default"},
        {"level": 2, "text_style": "default"},
        {"level": 3, "text_style": "fine-print"},
    ]
    # Restored once the blocks are built.
    assert "section" not in context


def test_section_defaults_outside_a_render():
    assert section({}) == {"level": 1, "text_style": "default"}


def test_pdf_has_bookmarks(tmp_path):
    source = tmp_path / "doc.yml"
    source.write_text(
        "Report:\n"
        "  - intro\n"
        "  - Scope:\n"
        "    - Details: text\n"
        "Results: text\n",
        encoding="utf-8",
    )
    load_report(source, tmp_path / "doc.pdf")
    toc = fitz.open(tmp_path / "doc.pdf").get_toc()
    assert toc == [[1, "Report", 1], [2, "Scope", 1], [3, "Details", 1], [1, "Results", 1]]


def test_bookmarks_survive_a_pdf_background(tmp_path):
    background = tmp_path / "bg.pdf"
    bg = fitz.open()
    bg.new_page(width=595.2756, height=841.8898)
    bg.save(background)
    source = tmp_path / "doc.yml"
    source.write_text(
        "_doc:\n"
        "  templates:\n"
        "    default:\n"
        "      margins: {top: 72, left: 72, right: 72, bottom: 72}\n"
        "      background:\n"
        "        filepath: bg.pdf\n"
        "        relative-to: source\n"
        "Report:\n"
        "  - Scope: text\n",
        encoding="utf-8",
    )
    load_report(source, tmp_path / "doc.pdf")
    assert fitz.open(tmp_path / "doc.pdf").get_toc() == [[1, "Report", 1], [2, "Scope", 1]]


def test_outline_cannot_skip_levels(tmp_path):
    from reportlab.platypus import Paragraph as P
    from reportlab.lib.styles import getSampleStyleSheet
    from ymprint.outline import YmprintDocTemplate
    from reportlab.platypus import Frame, PageTemplate

    styles = getSampleStyleSheet()
    path = tmp_path / "skip.pdf"
    doc = YmprintDocTemplate(str(path))
    doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(72, 72, 400, 600)])])
    doc.build([mark_outline(P("One", styles["h1"]), 1), mark_outline(P("Deep", styles["h3"]), 3)])
    assert fitz.open(path).get_toc() == [[1, "One", 1], [2, "Deep", 1]]
    assert [(t, lvl) for t, lvl, _ in doc.outline_entries] == [("One", 1), ("Deep", 2)]


SLIDE_DOC = {
    "page-size": [960, 540],
    "slides": True,
    "templates": {"default": {"margins": {"top": 20, "left": 40, "right": 40, "bottom": 20}}},
}


@pytest.mark.parametrize(
    "content",
    [{"Point": "text"}, [{"Point": "text"}]],
    ids=["mapping", "list"],
)
def test_slide_sub_heading_is_h2(content):
    from ymprint.slides import SlideFlowable

    source = {"_doc": dict(SLIDE_DOC), "Slide title": content}
    story = build_story(source, make_context(source))
    slides = [f for f in story if isinstance(f, SlideFlowable)]
    assert len(slides) == 1
    flowables = [f for frame in slides[0].frames for f in frame.flowables]
    assert headings(flowables) == [("Slide title", "h1"), ("Point", "h2")]
    assert getattr(slides[0], OUTLINE_ATTR) == ("Slide title", 1)
