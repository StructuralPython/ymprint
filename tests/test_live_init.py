"""Tests for live mode's ability to initialize a new (empty) document.

Covers the rough edge: 'Cannot launch live on an empty document (add the ability
to initialize an empty document with a confirming prompt if it does not exist)'.
"""
import pathlib

import typer
from rich.console import Console

from ymprint.app import STARTER_DOCUMENT
from ymprint.cli import live as cli_live
from ymprint.report_reader import load_report


def test_starter_document_renders(tmp_path):
    src = tmp_path / "My Report.yml"
    src.write_text(STARTER_DOCUMENT.format(title=src.stem))
    dest = tmp_path / "My Report.pdf"
    load_report(src, dest, None)
    assert dest.exists() and dest.stat().st_size > 0


def test_initialize_document_creates_file_on_yes(tmp_path, monkeypatch):
    src = tmp_path / "new.yml"
    monkeypatch.setattr(typer, "confirm", lambda *a, **k: True)
    created = cli_live._initialize_document(src, STARTER_DOCUMENT, Console())
    assert created is True
    assert src.exists()
    # The created file is a valid, renderable ymprint document.
    load_report(src, tmp_path / "new.pdf", None)


def test_initialize_document_declined_leaves_no_file(tmp_path, monkeypatch):
    src = tmp_path / "new.yml"
    monkeypatch.setattr(typer, "confirm", lambda *a, **k: False)
    created = cli_live._initialize_document(src, STARTER_DOCUMENT, Console())
    assert created is False
    assert not src.exists()


def test_initialize_document_creates_parent_dirs(tmp_path, monkeypatch):
    src = tmp_path / "nested" / "dir" / "report.yml"
    monkeypatch.setattr(typer, "confirm", lambda *a, **k: True)
    assert cli_live._initialize_document(src, STARTER_DOCUMENT, Console()) is True
    assert src.exists()
