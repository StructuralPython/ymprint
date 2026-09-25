"""List markers (ol numbers, ul bullets) must track the active body text size.

Regression for the rough edge: '_ol block: bullet sizes should match text style size'.
"""
import pathlib

import pytest

from ymprint.config.config_loaders import load_report_config
from ymprint.context_builder import build_context
from ymprint.content_converters import convert_ol, convert_ul

# body size deliberately differs from bullets.size to expose the mismatch.
STYLE = {
    "headings": {"font": "Helvetica", "color": "#222", "ratio": "major third"},
    "body": {
        "font": "Helvetica", "color": "black", "size": 20, "spacing": 1.7,
        "bullets": {"font": "Helvetica", "size": 8, "color": "black",
                    "symbols": "•", "spacing": 10, "indent-bullet": 20, "indent-text": 40},
    },
}


@pytest.fixture
def ctx():
    styles, tbl, doc = load_report_config({"_style": STYLE}, None)
    return build_context({}, styles, doc, tbl, {},
                         pathlib.Path.cwd(), pathlib.Path.cwd(), None)


def test_ol_number_matches_body_text_size(ctx):
    para = convert_ol(["one", "two"], ctx)[0]._flowables[0]
    assert para.style.bulletFontSize == 20
    assert para.style.bulletFontSize == para.style.fontSize


def test_ul_bullet_matches_body_text_size(ctx):
    para = convert_ul(["a", "b"], ctx)[0]._flowables[0]
    assert para.style.bulletFontSize == 20
    assert para.style.bulletFontSize == para.style.fontSize
