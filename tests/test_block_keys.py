"""Tests for the block key grammar: `_<code>` or `_<code>_<id>`."""
import pathlib

import pytest
from reportlab.platypus import Paragraph

from ymprint.blocks.registry import parse_block_key
from ymprint.config.config_loaders import load_report_config
from ymprint.context_builder import build_context
from ymprint.story_builder import build_story


@pytest.fixture
def ctx():
    styles, tablestyles, doctemplate = load_report_config()
    return build_context(
        {}, styles, doctemplate, tablestyles, {},
        pathlib.Path.cwd(), pathlib.Path.cwd(), pathlib.Path.cwd(),
    )


@pytest.mark.parametrize("key, expected", [
    ("_py", ("_py", None)),
    ("_py_setup", ("_py", "setup")),
    ("_py_setup_2", ("_py", "setup_2")),
    ("_pyfoo", ("_pyfoo", None)),
    ("_img2", ("_img2", None)),
])
def test_parse_block_key(key, expected):
    assert parse_block_key(key) == expected


@pytest.mark.parametrize("key", ["Heading", "py_setup", "_", "__py", "_py-x", None, 3])
def test_parse_block_key_rejects_non_block_keys(key):
    assert parse_block_key(key) is None


def test_block_with_id_dispatches_to_its_code(ctx):
    story = build_story({"_spacer_gap": None}, ctx)
    assert story and not any(isinstance(f, Paragraph) for f in story)


def test_longer_code_is_not_dispatched_by_prefix(ctx):
    # `_pyfoo` is not a `_py` block; it is not registered, so it stays a heading.
    story = build_story({"_pyfoo": "text"}, ctx)
    texts = [f.getPlainText() for f in story if isinstance(f, Paragraph)]
    assert texts == ["_pyfoo", "text"]
