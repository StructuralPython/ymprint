"""Bullet symbols never render as tofu (ReportLab's black square for a missing glyph)."""
import pathlib

import pymupdf
import pytest

from ymprint.config.config_loaders import load_report_config
from ymprint.config.font_registry import FALLBACK_FONT, font_has_glyph, register_fonts
from ymprint.content_converters import _bullet_symbol_markup, convert_ol
from ymprint.context_builder import build_context
from ymprint.report_reader import load_report

register_fonts()
NESTED = "Bullets:\n  _ul:\n    - one\n      - two\n        - three\n          - four\n"


def marker_fonts(pdf_path) -> dict:
    """{marker: font} for each one-character span (the bullet markers)."""
    with pymupdf.open(pdf_path) as pdf:
        return {
            span["text"].strip(): span["font"]
            for block in pdf[0].get_text("dict")["blocks"]
            for line in block.get("lines", [])
            for span in line["spans"]
            if len(span["text"].strip()) == 1
        }


@pytest.mark.parametrize(
    "font, char, expected",
    [
        ("Helvetica", "•", True),
        ("Helvetica", "‣", False),
        ("Helvetica", "∘", False),
        ("DejaVuSans", "‣", True),
        ("DejaVuSans-Bold", "∘", True),
        ("NotoSans", "∘", False),
        ("NoSuchFont", "a", False),
        ("ZapfDingbats", "•", False),
    ],
)
def test_font_has_glyph(font, char, expected):
    assert font_has_glyph(font, char) is expected


def test_default_bullets_render_every_level(tmp_path):
    source = tmp_path / "b.yml"
    source.write_text(NESTED, encoding="utf-8")
    load_report(source, tmp_path / "b.pdf")
    fonts = marker_fonts(tmp_path / "b.pdf")
    assert {m: fonts[m] for m in "•‣⁃∘"} == dict.fromkeys("•‣⁃∘", "DejaVuSans-Bold")
    # No ReportLab substitution glyphs.
    assert "ZapfDingbats" not in fonts.values()


def test_symbols_the_bullet_font_lacks_fall_back(tmp_path):
    source = tmp_path / "b.yml"
    source.write_text("_style:\n  body:\n    bullets:\n      font: Helvetica\n" + NESTED, encoding="utf-8")
    load_report(source, tmp_path / "b.pdf")
    fonts = marker_fonts(tmp_path / "b.pdf")
    assert fonts["•"] == "Helvetica-Bold"
    assert {m: fonts[m] for m in "‣⁃∘"} == dict.fromkeys("‣⁃∘", "DejaVuSans-Bold")
    assert "ZapfDingbats" not in fonts.values()


def test_bullet_markup():
    assert _bullet_symbol_markup("•", "Helvetica") == "<b>•</b>"
    assert _bullet_symbol_markup("‣", "Helvetica") == f'<font name="{FALLBACK_FONT}"><b>‣</b></font>'
    assert _bullet_symbol_markup("‣", "DejaVuSans") == "<b>‣</b>"
    assert _bullet_symbol_markup("&", "Helvetica") == "<b>&amp;</b>"


def test_ol_numbers_use_the_body_font():
    style = {"body": {"font": "NotoSerif", "bullets": {"font": "Helvetica"}}}
    styles, tbl, doc = load_report_config({"_style": style}, None)
    ctx = build_context({}, styles, doc, tbl, {}, pathlib.Path.cwd(), pathlib.Path.cwd(), None)
    para = convert_ol(["one"], ctx)[0]._flowables[0]
    assert para.style.bulletFontName == "NotoSerif"
