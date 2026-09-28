"""Blocks must raise author-facing errors, not crash live mode.

Covers the rough edge where empty/None block values and missing keys surfaced as
raw KeyError/TypeError/AttributeError and crashed live mode.
"""
import pathlib

import pytest

# Importing report_reader registers all built-in blocks.
from ymprint import report_reader  # noqa: F401
from ymprint.blocks import convert_blocks
from ymprint.errors import BlockError, YmprintAuthoringError
from ymprint.exceptions import YMPrintSyntaxException
from ymprint.config.config_loaders import load_report_config
from ymprint.context_builder import build_context


@pytest.fixture
def ctx():
    styles, tbl, doc = load_report_config()
    return build_context(
        {}, styles, doc, tbl, {},
        pathlib.Path.cwd(), pathlib.Path.cwd(), pathlib.Path.cwd(),
    )


def test_syntax_exception_is_authoring_error():
    assert issubclass(YMPrintSyntaxException, YmprintAuthoringError)


def test_block_error_is_authoring_error():
    assert issubclass(BlockError, YmprintAuthoringError)


def test_empty_block_value_raises_block_error(ctx):
    with pytest.raises(BlockError):
        convert_blocks("_info", None, ctx)


def test_missing_required_key_raises_block_error(ctx):
    with pytest.raises(BlockError) as exc:
        convert_blocks("_img", {"caption": "no source"}, ctx)
    assert exc.value.block_key == "_img"


def test_unknown_block_raises_block_error(ctx):
    with pytest.raises(BlockError):
        convert_blocks("_nosuchblock", "x", ctx)


def test_python_block_error_not_double_wrapped(ctx):
    # A _py block that raises should surface as its dedicated PythonBlockError,
    # which is an authoring error but *not* a BlockError.
    from ymprint.errors import PythonBlockError
    with pytest.raises(PythonBlockError):
        convert_blocks("_py", {"source": "raise ValueError('boom')"}, ctx)
