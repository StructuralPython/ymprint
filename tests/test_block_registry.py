"""Tests for BlockRegistry and per-context block lookup."""
import pathlib

import pytest
from reportlab.platypus import Paragraph, Spacer

from ymprint.blocks import convert_blocks
from ymprint.blocks.builtin import BUILTIN_BLOCKS
from ymprint.blocks.registry import BlockExistsError, BlockRegistry
from ymprint.config.config_loaders import load_report_config
from ymprint.context_builder import build_context
from ymprint.errors import BlockError
from ymprint.story_builder import build_story


def make_ctx(blocks=None):
    styles, tablestyles, doctemplate = load_report_config()
    return build_context(
        {}, styles, doctemplate, tablestyles, {},
        pathlib.Path.cwd(), pathlib.Path.cwd(), pathlib.Path.cwd(),
        blocks=blocks,
    )


def spacer_block(block_key, block_value, context):
    return [Spacer(1, block_value)]


def test_register_and_get():
    registry = BlockRegistry()
    registry.register("_gap", spacer_block)
    assert "_gap" in registry
    assert registry.get("_gap") is spacer_block
    assert registry.codes() == ["_gap"]


def test_decorator_registers_and_returns_function():
    registry = BlockRegistry()

    @registry.block("_gap")
    def gap(block_key, block_value, context):
        return []

    assert registry.get("_gap") is gap


@pytest.mark.parametrize("code", ["gap", "_", "_my_gap", "_my-gap", "", None])
def test_invalid_codes_rejected(code):
    with pytest.raises(ValueError):
        BlockRegistry().register(code, spacer_block)


@pytest.mark.parametrize("code", ["_ul", "_ol", "_textstyle", "_slide", "_frame", "_vars", "_doc"])
def test_reserved_codes_rejected(code):
    with pytest.raises(ValueError, match="reserved"):
        BlockRegistry().register(code, spacer_block)


def test_duplicate_requires_override():
    registry = BlockRegistry({"_gap": spacer_block})
    with pytest.raises(BlockExistsError):
        registry.register("_gap", lambda k, v, c: [])
    replacement = lambda k, v, c: []
    registry.register("_gap", replacement, override=True)
    assert registry.get("_gap") is replacement


def test_copy_is_independent():
    copied = BUILTIN_BLOCKS.copy()
    copied.register("_gap", spacer_block)
    assert "_gap" in copied
    assert "_gap" not in BUILTIN_BLOCKS
    assert set(BUILTIN_BLOCKS.codes()) < set(copied.codes())


def test_builtin_blocks_present():
    for code in ["_img", "_py", "_code", "_p", "_info", "_spacer", "_pagebreak"]:
        assert code in BUILTIN_BLOCKS


def test_context_defaults_to_builtin_blocks():
    assert make_ctx()["blocks"] is BUILTIN_BLOCKS


def test_blocks_are_looked_up_in_the_context_registry():
    custom = BUILTIN_BLOCKS.copy()
    custom.register("_gap", spacer_block)

    story = build_story({"_gap_one": 12}, make_ctx(custom))
    assert [type(f) for f in story] == [Spacer]

    # Without the block registered, `_gap_one` is an ordinary heading.
    story = build_story({"_gap_one": 12}, make_ctx())
    assert any(isinstance(f, Paragraph) for f in story)


def test_unknown_block_error_lists_context_registry():
    custom = BlockRegistry({"_gap": spacer_block})
    with pytest.raises(BlockError, match="_gap"):
        convert_blocks("_img", {}, make_ctx(custom))
