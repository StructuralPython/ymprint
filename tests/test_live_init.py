"""Tests for live mode's ability to initialize a new (empty) document.

Covers the rough edge: 'Cannot launch live on an empty document (add the ability
to initialize an empty document with a confirming prompt if it does not exist)'.
"""
import pathlib

import typer
from rich.console import Console

from ymprint.cli import main as cli_main
from ymprint.report_reader import load_report


def test_starter_document_renders(tmp_path):
    src = tmp_path / "My Report.yml"
    src.write_text(cli_main.STARTER_DOCUMENT.format(title=src.stem))
    dest = tmp_path / "My Report.pdf"
    load_report(src, dest, None)
    assert dest.exists() and dest.stat().st_size > 0


def test_initialize_document_creates_file_on_yes(tmp_path, monkeypatch):
    src = tmp_path / "new.yml"
    monkeypatch.setattr(typer, "confirm", lambda *a, **k: True)
    created = cli_main._initialize_document(src, Console())
    assert created is True
    assert src.exists()
    # The created file is a valid, renderable ymprint document.
    load_report(src, tmp_path / "new.pdf", None)


def test_initialize_document_declined_leaves_no_file(tmp_path, monkeypatch):
    src = tmp_path / "new.yml"
    monkeypatch.setattr(typer, "confirm", lambda *a, **k: False)
    created = cli_main._initialize_document(src, Console())
    assert created is False
    assert not src.exists()


def test_initialize_document_creates_parent_dirs(tmp_path, monkeypatch):
    src = tmp_path / "nested" / "dir" / "report.yml"
    monkeypatch.setattr(typer, "confirm", lambda *a, **k: True)
    assert cli_main._initialize_document(src, Console()) is True
    assert src.exists()
