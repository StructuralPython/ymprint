import pathlib

import pytest
from reportlab.platypus import Paragraph, ListFlowable

from ymprint.story_builder import build_story, _extract_list_block
from ymprint.context_builder import build_context
from ymprint.config.config_loaders import load_report_config

TEST_DATA = pathlib.Path(__file__).parent / "test-data"


@pytest.fixture
def ctx():
    styles, tablestyles, doctemplate = load_report_config()
    return build_context(
        {}, styles, doctemplate, tablestyles, {},
        pathlib.Path.cwd(), pathlib.Path.cwd(), pathlib.Path.cwd(),
    )


def kinds(story):
    return [type(f).__name__ for f in story]


# --- _extract_list_block -----------------------------------------------------------

def test_extract_list_block_heading_value_form():
    assert _extract_list_block("_ul", ["a", "b"]) == ("ul", ["a", "b"])
    assert _extract_list_block("_ol", ["a"]) == ("ol", ["a"])


def test_extract_list_block_list_item_form():
    assert _extract_list_block(None, {"_ul": ["a"]}) == ("ul", ["a"])
    assert _extract_list_block(None, {"_ol": ["a"]}) == ("ol", ["a"])


def test_extract_list_block_allows_suffix():
    assert _extract_list_block("_ul_left", ["a"]) == ("ul", ["a"])
    assert _extract_list_block(None, {"_ol_steps": ["a"]}) == ("ol", ["a"])


def test_extract_list_block_ignores_non_list_blocks():
    assert _extract_list_block("heading", ["a"]) is None
    assert _extract_list_block("_ultra", ["a"]) is None      # not _ul / _ul_*
    assert _extract_list_block(None, {"_img": {}}) is None
    assert _extract_list_block(None, {"a": 1, "b": 2}) is None


# --- bare list is now paragraphs, not bullets --------------------------------------

def test_bare_string_list_renders_as_paragraphs():
    story = build_story({"Heading": ["first line", "second line"]}, ctx_value())
    assert "ListFlowable" not in kinds(story)
    assert kinds(story).count("Paragraph") >= 3  # heading + 2 paragraphs


def test_single_item_list_is_a_paragraph_not_a_bullet():
    # the original bug: one wrapped paragraph under a heading came out as a bullet
    story = build_story({"Heading": ["just one paragraph"]}, ctx_value())
    assert "ListFlowable" not in kinds(story)


# --- explicit lists produce ListFlowables ------------------------------------------

def test_ul_block_produces_list_flowable():
    story = build_story({"Heading": {"_ul": ["a", "b", "c"]}}, ctx_value())
    assert "ListFlowable" in kinds(story)


def test_ol_block_produces_numbered_list_flowable():
    story = build_story({"_ol": ["a", "b"]}, ctx_value())
    lists = [f for f in story if isinstance(f, ListFlowable)]
    assert len(lists) == 1


def test_ul_as_list_item_form():
    story = build_story({"Section": ["intro paragraph", {"_ul": ["x", "y"]}]}, ctx_value())
    assert "ListFlowable" in kinds(story)
    assert "Paragraph" in kinds(story)


# helper (module-level context without a fixture, for direct calls above)
_CTX = None
def ctx_value():
    global _CTX
    if _CTX is None:
        styles, tablestyles, doctemplate = load_report_config()
        _CTX = build_context(
            {}, styles, doctemplate, tablestyles, {},
            pathlib.Path.cwd(), pathlib.Path.cwd(), pathlib.Path.cwd(),
        )
    return _CTX
