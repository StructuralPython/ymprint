import pathlib

import pytest

from ymprint.config.docstyles import ReportStyles, _deep_merge
from ymprint.config.config_loaders import load_report_config
from ymprint.context_builder import build_context
from ymprint.story_builder import build_story, _extract_textstyle, _resolve_style
from ymprint.exceptions import YMPrintSyntaxException

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


def make_context(style=BASE_STYLE):
    styles, tbl, doc = load_report_config({"_style": style}, None)
    return build_context(
        {}, styles, doc, tbl, {},
        pathlib.Path.cwd(), pathlib.Path.cwd(), None,
    )


def para_sizes(story):
    """(text, fontSize) for every rendered Paragraph in a story."""
    return [
        (f.getPlainText(), f.style.fontSize)
        for f in story
        if hasattr(f, "getPlainText")
    ]


# --- family building / inheritance -------------------------------------------------

def test_deep_merge_nested():
    base = {"body": {"size": 10, "color": "black"}, "headings": {"ratio": 1.2}}
    override = {"body": {"size": 6}}
    assert _deep_merge(base, override) == {
        "body": {"size": 6, "color": "black"},
        "headings": {"ratio": 1.2},
    }


def test_build_families_includes_default_and_named():
    families = ReportStyles.model_validate(BASE_STYLE).build_families()
    assert set(families.keys()) == {"default", "fine-print"}


def test_named_style_inherits_unspecified_fields():
    families = ReportStyles.model_validate(BASE_STYLE).build_families()
    fine_family, fine_sheet = families["fine-print"]
    # size + color overridden
    assert fine_sheet["body"].fontSize == 6
    # font inherited from default body
    assert fine_sheet["body"].fontName == "Helvetica"
    # bullet symbols inherited
    assert fine_family.body.bullets.symbols == "•‣"


def test_whole_family_headings_rescale_with_body_size():
    families = ReportStyles.model_validate(BASE_STYLE).build_families()
    default_h1 = families["default"][1]["h1"].fontSize
    fine_h1 = families["fine-print"][1]["h1"].fontSize
    # fine-print body is smaller, so its derived headings are smaller too
    assert fine_h1 < default_h1
    assert fine_h1 == pytest.approx(6 * (1.25 ** 5))


# --- config merge ------------------------------------------------------------------

def test_named_styles_survive_config_merge():
    src = {"_style": {"styles": {"legal": {"body": {"size": 7}}}}}
    styles, _tbl, _doc = load_report_config(src, None)
    assert styles["_style"]["styles"] == {"legal": {"body": {"size": 7}}}


# --- block detection ---------------------------------------------------------------

def test_extract_textstyle_mapping_key_form():
    assert _extract_textstyle("_textstyle", "fine-print") == "fine-print"


def test_extract_textstyle_list_item_form():
    assert _extract_textstyle(None, {"_textstyle": "fine-print"}) == "fine-print"


def test_extract_textstyle_ignores_other_elements():
    assert _extract_textstyle("Heading", "text") is None
    assert _extract_textstyle(None, {"other": 1}) is None


def test_resolve_style_unknown_raises():
    ctx = make_context()
    with pytest.raises(YMPrintSyntaxException):
        _resolve_style("does-not-exist", ctx)


# --- end-to-end scoping ------------------------------------------------------------

def test_scope_applies_and_reverts():
    ctx = make_context()
    source = {
        "Intro": [
            "para A",
            {"_textstyle": "fine-print"},
            "para B",
            {"_textstyle": "default"},
            "para C",
        ],
        "Outer": ["outer heading child"],  # a heading frame that must be default
    }
    sizes = dict(para_sizes(build_story(source, ctx)))
    assert sizes["para A"] == 10       # default
    assert sizes["para B"] == 6        # fine-print
    assert sizes["para C"] == 10       # switched back
    # Outer heading reverted to default family (h1 = 10 * 1.25**5)
    assert sizes["Outer"] == pytest.approx(10 * (1.25 ** 5))


def test_scope_inherited_into_child_frame():
    ctx = make_context()
    source = {
        "Intro": [
            {"_textstyle": "fine-print"},
            {"Nested": ["child para"]},
        ],
    }
    sizes = dict(para_sizes(build_story(source, ctx)))
    # the nested heading is rendered with the fine-print family (h-level)
    assert sizes["Nested"] == pytest.approx(6 * (1.25 ** 4))


def test_unknown_textstyle_in_source_raises():
    ctx = make_context()
    source = {"Intro": [{"_textstyle": "nope"}, "para"]}
    with pytest.raises(YMPrintSyntaxException):
        build_story(source, ctx)


# --- alignment / underline ---------------------------------------------------------

from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from ymprint.config.helpers import convert_alignment, YMPrintValueError
from ymprint.content_converters import convert_paragraph

ALIGN_STYLE = {
    "headings": {"font": "Helvetica", "color": "#222", "ratio": "major third",
                 "align": "center", "underline": True},
    "body": {"font": "Helvetica", "color": "black", "size": 10, "spacing": 1.7,
             "align": "justify",
             "bullets": {"font": "Helvetica", "size": 10, "color": "black",
                         "symbols": "•", "spacing": 10, "indent-bullet": 20, "indent-text": 40}},
    "styles": {"rightaligned": {"body": {"align": "right", "underline": True}}},
}


def test_convert_alignment_names():
    assert convert_alignment(None) == TA_LEFT
    assert convert_alignment("center") == TA_CENTER
    assert convert_alignment("Centre") == TA_CENTER
    assert convert_alignment("right") == TA_RIGHT
    assert convert_alignment("justify") == TA_JUSTIFY
    assert convert_alignment("justified") == TA_JUSTIFY


def test_convert_alignment_unknown_raises():
    with pytest.raises(YMPrintValueError):
        convert_alignment("diagonal")


def test_alignment_applied_to_body_and_headings():
    families = ReportStyles.model_validate(ALIGN_STYLE).build_families()
    assert families["default"][1]["body"].alignment == TA_JUSTIFY
    assert families["default"][1]["h1"].alignment == TA_CENTER
    assert families["rightaligned"][1]["body"].alignment == TA_RIGHT


def test_alignment_defaults_to_left_when_unset():
    families = ReportStyles.model_validate(BASE_STYLE).build_families()
    assert families["default"][1]["body"].alignment == TA_LEFT


def test_heading_underline_wraps_text():
    ctx = make_context(ALIGN_STYLE)
    para = convert_paragraph("My Heading", ctx, "h1", "default")
    assert para[0].text == "<u>My Heading</u>"


def test_body_without_underline_is_not_wrapped():
    ctx = make_context(ALIGN_STYLE)
    para = convert_paragraph("Body text", ctx, "body", "default")
    assert para[0].text == "Body text"


def test_underline_follows_active_named_style():
    ctx = make_context(ALIGN_STYLE)
    # 'rightaligned' switches on body underline
    para = convert_paragraph("Small print", ctx, "body", "rightaligned")
    assert para[0].text == "<u>Small print</u>"
