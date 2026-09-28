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
