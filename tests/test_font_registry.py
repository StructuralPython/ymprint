"""Tests for registering the bundled fonts."""
import reportlab.rl_config as rl_config
from reportlab.pdfbase import pdfmetrics

from ymprint.config import font_registry
from ymprint.config.font_registry import register_fonts


def test_registering_again_adds_nothing(monkeypatch):
    register_fonts()
    search_path = list(rl_config.TTFSearchPath)
    fonts = set(pdfmetrics.getRegisteredFontNames())

    # A second call (one per render) must not grow the search path or parse fonts again.
    parsed = []
    monkeypatch.setattr(font_registry, "TTFont", lambda *args: parsed.append(args))
    register_fonts()
    register_fonts()
    assert rl_config.TTFSearchPath == search_path
    assert set(pdfmetrics.getRegisteredFontNames()) == fonts
    assert parsed == []


def test_bundled_families_are_registered():
    register_fonts()
    fonts = set(pdfmetrics.getRegisteredFontNames())
    assert {"DejaVuSansMono", "DejaVuSansMono-Bold", "Inter"} <= fonts
