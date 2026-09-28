"""Tests for inline markdown → ReportLab markup conversion.

Regression coverage for the rough edge where nested inline formatting and links
were dropped because only the first child of a span was rendered.
"""
from ymprint.markdown.inline import convert_inline_markdown


def test_basic_bold_italic_code():
    out = convert_inline_markdown("This is **bold** and *italic* and `code` text.")
    assert "<b>bold</b>" in out
    assert "<i>italic</i>" in out
    assert 'face="DejaVuSansMono"' in out
    assert ">code</font>" in out


def test_nested_emphasis_inside_strong():
    # The original bug: only 'bold ' survived; the italic + trailing text vanished.
    out = convert_inline_markdown("nested **bold *and italic* words**")
    assert out == "nested <b>bold <i>and italic</i> words</b>"


def test_code_inside_strong():
    out = convert_inline_markdown("**strong with `code` inside**")
    assert out.startswith("<b>strong with <font")
    assert out.endswith(" inside</b>")


def test_link_keeps_label_and_url():
    out = convert_inline_markdown("A [label](http://example.com) here")
    assert 'href="http://example.com"' in out
    assert ">label</font>" in out
    assert out.startswith("A <link")


def test_plain_text_unchanged():
    assert convert_inline_markdown("just plain text") == "just plain text"
