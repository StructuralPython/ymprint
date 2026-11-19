"""The `_code` and `_py` blocks' theme and text size."""
import pathlib
import textwrap

import pytest
from reportlab.platypus import KeepTogether

from ymprint.blocks.code_block_styles import THEMES, resolve_code_look
from ymprint.config.config_loaders import load_report_config
from ymprint.config.font_registry import register_fonts
from ymprint.context_builder import build_context
from ymprint.errors import BlockError
from ymprint.report_reader import load_report
from ymprint.story_builder import build_story

TEST_DATA = pathlib.Path(__file__).parent / "test-data"

register_fonts()


def story_and_context(source: dict):
    styles, tbl, doc_data = load_report_config(source, None)
    context = build_context(
        source, styles, doc_data, tbl, {}, TEST_DATA / "doc.yml", TEST_DATA / "doc.pdf", None
    )
    return build_story(source, context), context


def code_tables(story):
    """The outer Table of each code block in 'story'."""
    return [f._content[0] for f in story if isinstance(f, KeepTogether)]


def background(table):
    """The colour of the table's first BACKGROUND command."""
    for cmd in table._bkgrndcmds:
        if cmd[0] == "BACKGROUND":
            return cmd[3]
    raise AssertionError("no background")


def code_font_size(table):
    inner = table._cellvalues[-1][0]
    return inner._cellvalues[0][-1].style.fontSize


STYLE = {
    "body": {"size": 10},
    "styles": {"dark-page": {"code": {"theme": "dark", "size": 14, "spacing": 1.3}}},
}


def test_default_look_is_light_at_nine_tenths_of_the_body_size():
    story, _ = story_and_context({"_style": STYLE, "Code": [{"_code": {"source": "x = 1"}}]})
    (table,) = code_tables(story)
    assert background(table) == THEMES["light"].BG
    assert code_font_size(table) == pytest.approx(9.0)


def test_text_style_sets_theme_and_size():
    story, _ = story_and_context({
        "_style": STYLE,
        "Code": [{"_textstyle": "dark-page"}, {"_code": {"source": "x = 1"}}, {"_py": {"source": "y = 2"}}],
    })
    code, py = code_tables(story)
    for table in (code, py):
        assert background(table) == THEMES["dark"].BG
        assert code_font_size(table) == 14
    line_style = code._cellvalues[-1][0]._cellvalues[0][-1].style
    assert line_style.leading == pytest.approx(14 * 1.3)


def test_block_theme_and_size_override_the_text_style():
    story, _ = story_and_context({
        "_style": STYLE,
        "Code": [
            {"_textstyle": "dark-page"},
            {"_code": {"source": "x = 1", "theme": "light", "size": 20}},
        ],
    })
    (table,) = code_tables(story)
    assert background(table) == THEMES["light"].BG
    assert code_font_size(table) == 20


def test_padding_does_not_change_with_the_text_size():
    # Existing documents keep their code block widths: a larger size makes the
    # text larger, not the padding (which would clip lines that used to fit).
    _, context = story_and_context({"_style": STYLE, "Code": "x"})
    small = resolve_code_look(context, size=9)
    large = resolve_code_look(context, size=27)
    assert (large.pad_h, large.pad_v) == (small.pad_h, small.pad_v) == (12, 10)


@pytest.mark.parametrize("block", ["_code", "_py"])
@pytest.mark.parametrize("value, message", [
    ({"theme": "neon"}, "Unknown code theme 'neon'"),
    ({"size": 0}, "positive number"),
    ({"size": "big"}, "positive number"),
])
def test_bad_theme_or_size_is_an_authoring_error(block, value, message):
    with pytest.raises(BlockError, match=message):
        story_and_context({"Code": [{block: {"source": "x = 1", **value}}]})


def test_dark_code_renders(tmp_path):
    src = tmp_path / "doc.yml"
    src.write_text(textwrap.dedent("""
        Code:
          - _code:
              theme: dark
              size: 12
              source: print("hi")
    """))
    load_report(src, tmp_path / "doc.pdf", None)
    assert (tmp_path / "doc.pdf").stat().st_size > 0
