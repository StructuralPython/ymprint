"""Tests for the _img block: width_ratio (with scale_ratio alias), source/src, optional caption."""
import pathlib

import pytest

from ymprint import report_reader  # noqa: F401  (registers blocks)
from ymprint.blocks import convert_blocks
from ymprint.config.config_loaders import load_report_config
from ymprint.context_builder import build_context

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
IMAGE = REPO_ROOT / "ymprintlogosmall.png"


@pytest.fixture
def ctx():
    styles, tbl, doc = load_report_config()
    # source_path drives relative image resolution; point it at the repo root.
    return build_context(
        {}, styles, doc, tbl, {},
        REPO_ROOT / "report.yml", REPO_ROOT / "report.pdf", None,
    )


def _table_width(flowables):
    table = flowables[0]
    return table._colWidths[0]


def test_scale_ratio_alias_matches_width_ratio(ctx):
    a = convert_blocks("_img", {"src": str(IMAGE), "caption": "c", "scale_ratio": 0.3}, ctx)
    b = convert_blocks("_img", {"src": str(IMAGE), "caption": "c", "width_ratio": 0.3}, ctx)
    assert _table_width(a) == _table_width(b)


def test_width_ratio_scales_smaller_than_default(ctx):
    small = convert_blocks("_img", {"src": str(IMAGE), "caption": "c", "width_ratio": 0.2}, ctx)
    big = convert_blocks("_img", {"src": str(IMAGE), "caption": "c", "width_ratio": 0.8}, ctx)
    assert _table_width(small) < _table_width(big)


def _rows(flowables):
    return flowables[0]._cellvalues


def test_source_and_src_are_equivalent(ctx):
    a = convert_blocks("_img", {"source": str(IMAGE)}, ctx)
    b = convert_blocks("_img", {"src": str(IMAGE)}, ctx)
    assert _table_width(a) == _table_width(b)


def test_caption_is_optional(ctx):
    with_caption = convert_blocks("_img", {"source": str(IMAGE), "caption": "hi"}, ctx)
    without_caption = convert_blocks("_img", {"source": str(IMAGE)}, ctx)
    # caption present -> image row + caption row; absent -> image row only
    assert len(_rows(with_caption)) == 2
    assert len(_rows(without_caption)) == 1


def test_missing_source_raises_block_error(ctx):
    from ymprint.errors import BlockError
    with pytest.raises(BlockError):
        convert_blocks("_img", {"caption": "no image"}, ctx)
