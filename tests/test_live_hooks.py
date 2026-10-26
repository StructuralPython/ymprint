"""Tests for live mode running an app's render hooks, and for app CLIs."""
import os

import pytest
from reportlab.platypus import Paragraph
from rich.console import Console
from typer.testing import CliRunner

from ymprint import Ymprint
from ymprint.app import STARTER_DOCUMENT
from ymprint.cli import live as cli_live
from ymprint.cli.live import run_live


@pytest.fixture
def doc(tmp_path):
    src = tmp_path / "report.yml"
    src.write_text(STARTER_DOCUMENT.format(title="Report"))
    return src


def _bump_mtime(path):
    st = path.stat()
    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))


@pytest.fixture
def headless_live(monkeypatch):
    """Run the live loop without Okular; `ticks` is a list of per-frame actions."""
    monkeypatch.setattr(cli_live, "ensure_okular", lambda console: ["true"])
    monkeypatch.setattr(cli_live.subprocess, "Popen", lambda *a, **k: None)
    ticks = []

    def fake_sleep(_):
        if not ticks:
            raise KeyboardInterrupt
        ticks.pop(0)()

    monkeypatch.setattr(cli_live.time, "sleep", fake_sleep)
    return ticks


def test_run_live_runs_hooks_on_change(doc, tmp_path, headless_live):
    data = tmp_path / "data.json"
    data.write_text("{}")
    events = []
    app = Ymprint()
    app.before_render(lambda e: events.append(("before", e.trigger, e.mode)))
    app.after_render(lambda e: events.append(("after", e.trigger, e.mode)))
    headless_live.extend([lambda: _bump_mtime(data), lambda: None])

    code = run_live(app, doc, watch=[data], console=Console(quiet=True))

    assert code == 0
    assert events == [
        ("before", None, "live"), ("after", None, "live"),
        ("before", data, "live"), ("after", data, "live"),
    ]


def test_hook_writing_watched_file_does_not_loop(doc, headless_live):
    renders = []
    app = Ymprint()

    @app.before_render
    def regenerate_source(event):
        renders.append(event.trigger)
        doc.write_text(doc.read_text())
        _bump_mtime(doc)

    headless_live.extend([lambda: None] * 3)
    run_live(app, doc, console=Console(quiet=True))
    assert renders == [None]


def test_failing_hook_is_shown_not_raised(doc, headless_live):
    app = Ymprint()

    @app.before_render
    def boom(event):
        raise ValueError("boom")

    console = Console(record=True, width=120)
    assert run_live(app, doc, console=console) == 0
    output = console.export_text()
    assert "before_render hook" in output and "boom" in output


def test_live_watches_app_config(doc, tmp_path, headless_live):
    app_cfg = tmp_path / "app" / "app.ymprint.yml"
    app_cfg.parent.mkdir()
    app_cfg.write_text("_style:\n  body:\n    size: 9\n")
    triggers = []
    app = Ymprint(config_path=app_cfg)
    app.before_render(lambda e: triggers.append(e.trigger))
    headless_live.extend([lambda: _bump_mtime(app_cfg), lambda: None])
    run_live(app, doc, console=Console(quiet=True))
    assert triggers == [None, app_cfg]


def test_live_uses_the_apps_starter_document(tmp_path, monkeypatch, headless_live):
    monkeypatch.setattr(cli_live.typer, "confirm", lambda *a, **k: True)
    app = Ymprint(starter_document="{title}:\n  - Custom starter.\n")
    src = tmp_path / "new.yml"
    run_live(app, src, console=Console(quiet=True))
    assert src.read_text() == "new:\n  - Custom starter.\n"


def test_live_rejects_dict_source():
    with pytest.raises(TypeError):
        Ymprint().live({"Heading": ["text"]})


# --- app CLIs ------------------------------------------------------------------

def test_custom_app_cli_convert_uses_its_blocks_and_hooks(tmp_path):
    app = Ymprint(name="shouty")
    calls = []

    @app.block("_shout")
    def shout(block_key, block_value, context):
        return [Paragraph(str(block_value).upper())]

    @app.after_render
    def record(event):
        calls.append((event.mode, event.destination.exists()))

    src = tmp_path / "doc.yml"
    src.write_text("Heading:\n  - _shout: hello\n")
    result = CliRunner().invoke(app.cli(), ["convert", str(src)])
    assert result.exit_code == 0, result.output
    assert calls == [("convert", True)]

    import pymupdf as mu
    assert "HELLO" in mu.open(tmp_path / "doc.pdf")[0].get_text()


def test_cli_convert_reports_hook_failure(tmp_path):
    app = Ymprint(name="failing")

    @app.before_render
    def boom(event):
        raise RuntimeError("database unavailable")

    src = tmp_path / "doc.yml"
    src.write_text(STARTER_DOCUMENT.format(title="Doc"))
    result = CliRunner().invoke(app.cli(), ["convert", str(src)])
    assert result.exit_code == 1
    assert "database unavailable" in result.output
    assert not (tmp_path / "doc.pdf").exists()


def test_cli_is_named_after_the_app():
    assert Ymprint(name="calcsheet").cli().info.name == "calcsheet"
