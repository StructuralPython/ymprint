"""Tests for graceful CLI error handling of authoring mistakes."""
import pathlib
import traceback

import pytest
from typer.testing import CliRunner

from ymprint import yaml_loader
from ymprint.report_reader import load_report
from ymprint.errors import YamlSyntaxError, PythonBlockError, YmprintAuthoringError
from ymprint.blocks.python_block import convert_python_block
from ymprint.cli.error_display import format_authoring_error, _compact_frames
from ymprint.cli.main import app

TEST_DATA = pathlib.Path(__file__).parent / "test-data"
runner = CliRunner()


# ── YAML syntax errors ────────────────────────────────────────────────────────

def test_bad_yaml_raises_authoring_error(tmp_path):
    bad = tmp_path / "broken.yml"
    bad.write_text("title:\n  - item\n  bad_indent: : oops\n")
    with pytest.raises(YamlSyntaxError) as info:
        yaml_loader.load_yaml(bad)
    err = info.value
    assert isinstance(err, YmprintAuthoringError)
    assert err.filepath == bad
    assert err.line is not None  # line/column extracted from ruamel mark


def test_convert_reports_yaml_error_and_exits_nonzero(tmp_path):
    bad = tmp_path / "broken.yml"
    bad.write_text("title: [unclosed\n")
    result = runner.invoke(app, ["convert", str(bad)])
    assert result.exit_code == 1
    assert "error in your document" in result.stdout
    # The friendly panel names the file, not a raw Python traceback.
    assert "Traceback (most recent call last)" not in result.stdout


# ── Python block errors ───────────────────────────────────────────────────────

def _run_py_block(source: str):
    context = {
        "vars": {},
        "frames": {"all_pages": {"width": 400}},
        "styles": {"ymprint": type("S", (), {"body": type("B", (), {"spacing": 1.1, "size": 10})()})()},
    }
    return convert_python_block("_py", {"source": source, "echo": False}, context)


def test_python_block_error_wraps_original(tmp_path):
    with pytest.raises(PythonBlockError) as info:
        _run_py_block("x = 1\nraise ValueError('boom from author')\n")
    err = info.value
    assert isinstance(err, YmprintAuthoringError)
    assert err.block_key == "_py"
    assert isinstance(err.original, ValueError)
    assert "raise ValueError" in err.source


def test_python_block_error_display_points_to_line():
    try:
        _run_py_block("a = 1\nb = a / 0\n")
    except PythonBlockError as err:
        rendered = format_authoring_error(err)
        from rich.console import Console
        console = Console(width=100)
        with console.capture() as cap:
            console.print(rendered)
        text = cap.get()
        assert "ZeroDivisionError" in text
        assert "line 2" in text  # the failing author line
        assert "your Python block" in text
    else:
        pytest.fail("expected PythonBlockError")


# ── Top-and-bottom truncation ─────────────────────────────────────────────────

def test_compact_frames_truncates_deep_stacks():
    # Build a synthetic deep traceback.
    def recurse(n):
        if n == 0:
            raise RuntimeError("deep")
        recurse(n - 1)

    try:
        recurse(20)
    except RuntimeError as e:
        frames = traceback.extract_tb(e.__traceback__)

    rendered = _compact_frames(frames, [])
    from rich.console import Console
    console = Console(width=100)
    with console.capture() as cap:
        for part in rendered:
            console.print(part)
    text = cap.get()
    assert "frame(s) hidden" in text
    # Fewer rendered items than total frames (head + marker + tail).
    assert len(rendered) < len(frames)
