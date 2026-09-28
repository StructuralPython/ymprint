import pathlib

import pytest

from ymprint.config.config_loaders import load_report_config
from ymprint.context_builder import build_context
from ymprint.blocks.p_block import convert_p_block
from ymprint.story_builder import build_story
from ymprint.exceptions import YMPrintSyntaxException

# A style config with the default family plus a smaller named "fine-print" family,
# so tests can tell the two apart by rendered font size.
BASE_STYLE = {
    "headings": {"font": "Helvetica", "color": "#222222", "ratio": "major third"},
    "body": {
        "font": "Helvetica",
        "color": "black",
        "size": 10,
        "spacing": 1.7,
        "bullets": {
            "font": "Helvetica",
            "size": 10,
            "color": "black",
            "symbols": "•‣",
            "spacing": 10,
            "indent-bullet": 20,
            "indent-text": 40,
        },
    },
    "styles": {"fine-print": {"body": {"size": 6, "color": "#888888"}}},
}


def make_context(document_vars=None, style=BASE_STYLE):
    styles, tbl, doc = load_report_config({"_style": style}, None)
    return build_context(
        {}, styles, doc, tbl, document_vars or {},
        pathlib.Path.cwd(), pathlib.Path.cwd(), None,
    )


def paras(story):
    """(text, fontSize) for every rendered Paragraph in a story."""
    return [
        (f.getPlainText(), f.style.fontSize)
        for f in story
        if hasattr(f, "getPlainText")
    ]


# --- value forms -------------------------------------------------------------------

def test_bare_string_renders_default_body_paragraph():
    ctx = make_context()
    story = convert_p_block("_p", "A quick paragraph.", ctx)
    rendered = paras(story)
    assert rendered == [("A quick paragraph.", 10)]


def test_mapping_content_attribute():
    ctx = make_context()
    story = convert_p_block("_p", {"content": "Mapping form."}, ctx)
    assert paras(story) == [("Mapping form.", 10)]


def test_text_alias_for_content():
    ctx = make_context()
    story = convert_p_block("_p", {"text": "Aliased."}, ctx)
    assert paras(story) == [("Aliased.", 10)]


def test_style_selects_named_family():
    ctx = make_context()
    story = convert_p_block(
        "_p", {"content": "Small print.", "style": "fine-print"}, ctx
    )
    # fine-print body renders at size 6, not the default 10
    assert paras(story) == [("Small print.", 6)]


# --- errors ------------------------------------------------------------------------

def test_unknown_style_raises():
    ctx = make_context()
    with pytest.raises(YMPrintSyntaxException):
        convert_p_block("_p", {"content": "x", "style": "does-not-exist"}, ctx)


def test_missing_content_raises():
    ctx = make_context()
    with pytest.raises(YMPrintSyntaxException):
        convert_p_block("_p", {"style": "default"}, ctx)


def test_invalid_value_type_raises():
    ctx = make_context()
    with pytest.raises(YMPrintSyntaxException):
        convert_p_block("_p", ["not", "a", "paragraph"], ctx)


# --- content rendering -------------------------------------------------------------

def test_inline_markdown_is_converted():
    ctx = make_context()
    story = convert_p_block("_p", "Some **bold** text.", ctx)
    # convert_inline_markdown turns **bold** into reportlab <b> markup
    assert "<b>bold</b>" in story[0].text


def test_jinja_variable_is_interpolated():
    ctx = make_context(document_vars={"name": "Ada"})
    story = convert_p_block("_p", "Hello {{name}}.", ctx)
    assert paras(story) == [("Hello Ada.", 10)]


# --- end to end via build_story ----------------------------------------------------

def test_paragraph_after_a_block_without_heading():
    ctx = make_context()
    source = {
        "Section": [
            {"_info": "An admonition."},
            {"_p": {"content": "Follow-up paragraph, no heading needed.", "style": "fine-print"}},
        ]
    }
    rendered = dict(paras(build_story(source, ctx)))
    assert rendered["Follow-up paragraph, no heading needed."] == 6
