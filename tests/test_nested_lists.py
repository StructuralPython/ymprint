"""Nested lists under _ul / _ol must render as nested ListFlowables.

Regression for the rough edge: '_ul does not recognize nested lists under it'
(the recursive call's result was appended as a raw python list, so the nested
list never rendered and could break the build).
"""
import pathlib

import pytest
from reportlab.platypus import ListFlowable

from ymprint.config.config_loaders import load_report_config
from ymprint.context_builder import build_context
from ymprint.content_converters import convert_ul, convert_ol


@pytest.fixture
def ctx():
    styles, tbl, doc = load_report_config()
    return build_context({}, styles, doc, tbl, {},
                         pathlib.Path.cwd(), pathlib.Path.cwd(), None)


def _no_raw_lists(listflowable):
    """Every item is a Flowable (Paragraph or nested ListFlowable), never a raw list."""
    for item in listflowable._flowables:
        assert not isinstance(item, list), "nested list was appended as a raw python list"
        if isinstance(item, ListFlowable):
            _no_raw_lists(item)


def test_ul_nested_list_becomes_nested_listflowable(ctx):
    top = convert_ul(["a", ["n1", "n2"], "b"], ctx)[0]
    _no_raw_lists(top)
    nested = [f for f in top._flowables if isinstance(f, ListFlowable)]
    assert len(nested) == 1
    assert [p.getPlainText() for p in nested[0]._flowables] == ["n1", "n2"]


def test_ul_deeply_nested(ctx):
    top = convert_ul(["a", ["n1", ["deep"]]], ctx)[0]
    _no_raw_lists(top)


def test_ol_nested_list_becomes_nested_listflowable(ctx):
    top = convert_ol(["one", ["n1", "n2"], "two"], ctx)[0]
    _no_raw_lists(top)
    nested = [f for f in top._flowables if isinstance(f, ListFlowable)]
    assert len(nested) == 1


# --- Nested items written by indentation under a bullet -----------------------
# YAML folds a more-indented `- item` line into the parent bullet's text
# ('one - nested a - nested b'); the loader splits it back into a nested list.

from ymprint.story_builder import build_story
from ymprint.yaml_loader import load_yaml


def _load(tmp_path, text):
    path = tmp_path / "report.yml"
    path.write_text(text, encoding="utf-8")
    return load_yaml(path)


def test_indented_nested_ul_items_are_not_folded_into_parent(tmp_path):
    data = _load(tmp_path, (
        "H:\n"
        "  _ul:\n"
        "    - one\n"
        "      - nested a\n"
        "      - nested b\n"
        "    - two\n"
    ))
    assert data["H"]["_ul"] == ["one", ["nested a", "nested b"], "two"]


def test_indented_nested_items_deeper_levels_and_continuations(tmp_path):
    data = _load(tmp_path, (
        "H:\n"
        "  _ol_steps:\n"
        "    - one\n"
        "      - nested a\n"
        "        continues here\n"
        "      - nested b\n"
        "        - deep\n"
        "    - two\n"
    ))
    assert data["H"]["_ol_steps"] == [
        "one", ["nested a continues here", "nested b", ["deep"]], "two"
    ]


def test_folded_text_outside_lists_is_left_alone(tmp_path):
    # Only `_ul` / `_ol` values are unfolded; a paragraph keeps YAML's folding.
    data = _load(tmp_path, "H:\n  - a paragraph\n    - with a dash\n")
    assert data["H"] == ["a paragraph - with a dash"]


def test_indented_nested_ul_renders_nested_listflowable(tmp_path, ctx):
    data = _load(tmp_path, "H:\n  _ul:\n    - one\n      - n1\n      - n2\n")
    lists = [f for f in build_story(data, ctx) if isinstance(f, ListFlowable)]
    nested = [f for f in lists[0]._flowables if isinstance(f, ListFlowable)]
    assert [p.getPlainText() for p in nested[0]._flowables] == ["n1", "n2"]


# --- Nested items written as a mapping: `- one:` followed by a sub-list --------

def test_mapping_item_becomes_item_plus_nested_list(ctx):
    top = convert_ul([{"one": ["n1", "n2"]}, "two"], ctx)[0]
    _no_raw_lists(top)
    texts = [f.getPlainText() for f in top._flowables if not isinstance(f, ListFlowable)]
    assert texts == ["one", "two"]
    nested = [f for f in top._flowables if isinstance(f, ListFlowable)]
    assert [p.getPlainText() for p in nested[0]._flowables] == ["n1", "n2"]


# --- Empty bullets ---------------------------------------------------------------
# A bare `-` loads as None, which used to crash with a TypeError.

def test_empty_ul_item_renders_blank_bullet(ctx):
    top = convert_ul(["a", None, "b"], ctx)[0]
    assert len(top._flowables) == 3
    assert top._flowables[1].getPlainText().strip() == ""


def test_empty_ol_item_keeps_numbering(ctx):
    top = convert_ol(["a", None, "c"], ctx)[0]
    assert len(top._flowables) == 3
    assert "3." in top._flowables[2].text


def test_empty_bullet_from_yaml_builds(tmp_path, ctx):
    data = _load(tmp_path, "H:\n  _ul:\n    - one\n    -\n    - two\n")
    assert data["H"]["_ul"] == ["one", None, "two"]
    lists = [f for f in build_story(data, ctx) if isinstance(f, ListFlowable)]
    assert len(lists[0]._flowables) == 3
