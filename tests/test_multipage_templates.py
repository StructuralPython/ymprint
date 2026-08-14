import pathlib

import pytest
from reportlab.platypus import PageBreak, NextPageTemplate

import ymprint.config as config
from ymprint.config.config_loaders import load_report_config
from ymprint.blocks.page_break_block import convert_page_break
from ymprint.blocks.nextpagetemplate_block import convert_next_page_template
from ymprint.exceptions import YMPrintSyntaxException

TEST_DATA = pathlib.Path(__file__).parent / "test-data"


def make_doc_config():
    return config.DocConfig.model_validate(
        {
            "page-size": "a4",
            "landscape": False,
            "templates": {
                "cover": {"margins": {"top": 200, "left": 72, "right": 72, "bottom": 72}},
                "body": {"margins": {"top": 72, "left": 72, "right": 72, "bottom": 72}},
            },
        }
    )


# --- DocConfig template resolution -------------------------------------------------

def test_template_names_preserve_order():
    doc = make_doc_config()
    assert doc.template_names == ["cover", "body"]


def test_resolve_template_id_by_name_and_index():
    doc = make_doc_config()
    assert doc.resolve_template_id("body") == "body"
    assert doc.resolve_template_id(0) == "cover"
    assert doc.resolve_template_id(1) == "body"


def test_resolve_template_id_rejects_unknown_name():
    doc = make_doc_config()
    with pytest.raises(ValueError):
        doc.resolve_template_id("nope")


def test_resolve_template_id_rejects_out_of_range_index():
    doc = make_doc_config()
    with pytest.raises(ValueError):
        doc.resolve_template_id(5)


def test_min_available_dims_use_smallest_template():
    doc = make_doc_config()
    # cover has the larger top margin, so the smallest height comes from cover
    assert doc.min_available_height() == doc.available_height("cover")
    assert doc.min_available_width() == doc.available_width("body")


def test_build_records_page_template_map():
    from io import BytesIO
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph

    doc_cfg = make_doc_config()
    styles = getSampleStyleSheet()
    story = [
        Paragraph("p1", styles["Normal"]),
        NextPageTemplate("body"),
        PageBreak(),
        Paragraph("p2", styles["Normal"]),
    ]
    doc, page_map = doc_cfg.build("/dev/null")
    doc.build(story, filename=BytesIO())
    assert page_map == {0: "cover", 1: "body"}


# --- Block converters --------------------------------------------------------------

def make_context():
    return {"doctemplate": {"ymprint": make_doc_config()}}


def test_pagebreak_without_value_is_plain_break():
    result = convert_page_break("_pagebreak", None, make_context())
    assert len(result) == 1
    assert isinstance(result[0], PageBreak)


def test_pagebreak_with_name_switches_template():
    result = convert_page_break("_pagebreak", "body", make_context())
    assert isinstance(result[0], NextPageTemplate)
    assert result[0].action == ("nextPageTemplate", "body")
    assert isinstance(result[1], PageBreak)


def test_pagebreak_with_index_switches_template():
    result = convert_page_break("_pagebreak", 1, make_context())
    assert isinstance(result[0], NextPageTemplate)
    assert result[0].action == ("nextPageTemplate", "body")


def test_pagebreak_unknown_template_raises_syntax_exception():
    with pytest.raises(YMPrintSyntaxException):
        convert_page_break("_pagebreak", "missing", make_context())


def test_nextpagetemplate_sets_template_without_break():
    result = convert_next_page_template("_nextpagetemplate", "body", make_context())
    assert len(result) == 1
    assert isinstance(result[0], NextPageTemplate)
    assert result[0].action == ("nextPageTemplate", "body")


def test_nextpagetemplate_unknown_template_raises_syntax_exception():
    with pytest.raises(YMPrintSyntaxException):
        convert_next_page_template("_nextpagetemplate", 9, make_context())


# --- Config merge with named templates --------------------------------------------

def test_config_named_templates_override_default_template():
    # example_2_config defines 'first' and 'body' templates
    _styles, _tablestyles, doc = load_report_config({}, TEST_DATA / "example_2_config")
    templates = doc["_doc"]["templates"]
    assert list(templates.keys()) == ["first", "body"]
    # the default 'default' template must not leak in
    assert "default" not in templates


def test_config_without_templates_falls_back_to_default():
    # example_1_config defines a single 'default' template
    _styles, _tablestyles, doc = load_report_config({}, TEST_DATA / "example_1_config")
    templates = doc["_doc"]["templates"]
    assert list(templates.keys()) == ["default"]
    assert templates["default"]["margins"]["top"] == 84
