"""
Tests for the files a render records as read (data, images, JSON and background
PDFs), and for live mode and `ym build` acting on them.
"""
import os
import pathlib
import shutil
import textwrap

import pymupdf as mu
import pytest
from reportlab.pdfgen.canvas import Canvas
from rich.console import Console

from ymprint import Ymprint
from ymprint.build import Build
from ymprint.cli import live as cli_live
from ymprint.cli.live import FileWatcher, run_live
from ymprint.errors import BackgroundNotFoundError

TEST_DATA = pathlib.Path(__file__).parent / "test-data"


def write(path: pathlib.Path, text: str) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text))
    return path


def make_background(path: pathlib.Path, mark: str) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas = Canvas(str(path))
    canvas.drawString(10, 10, mark)
    canvas.showPage()
    canvas.save()
    return path


def bump_mtime(path: pathlib.Path) -> None:
    st = path.stat()
    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))


def background_config(filepath: str, relative_to: str | None = None, **more: str) -> str:
    """A `_doc` with a `default` template on 'filepath', plus one template per 'more' item."""
    lines = ["_doc:", "  templates:"]
    for name, path in {"default": filepath, **more}.items():
        lines += [
            f"    {name}:",
            "      margins: {top: 72, left: 72, right: 72, bottom: 72}",
            "      background:",
            f"        filepath: {path}",
        ]
        if relative_to and name == "default":
            lines.append(f"        relative-to: {relative_to}")
    return "\n".join(lines) + "\n"


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


def settle():
    """A poll with no change, so the last save settles and is reloaded."""


# --- FileWatcher ----------------------------------------------------------------

def test_a_change_is_reported_once_the_file_settles(tmp_path):
    path = tmp_path / "bg.pdf"
    path.write_bytes(b"1")
    watcher = FileWatcher(path)
    bump_mtime(path)
    assert not watcher.changed()      # still changing, as far as it knows
    assert watcher.changed()          # unchanged since: report it
    assert not watcher.changed()


def test_a_file_still_being_written_is_not_reported(tmp_path):
    path = tmp_path / "bg.pdf"
    path.write_bytes(b"1")
    watcher = FileWatcher(path)
    path.write_bytes(b"")
    bump_mtime(path)
    assert not watcher.changed()
    path.write_bytes(b"12345")
    bump_mtime(path)
    assert not watcher.changed()
    assert watcher.changed()


def test_a_created_file_is_reported(tmp_path):
    path = tmp_path / "bg.pdf"
    watcher = FileWatcher(path)
    path.write_bytes(b"1")
    assert not watcher.changed()
    assert watcher.changed()


# --- what a render records -------------------------------------------------------

def test_render_records_a_config_background(tmp_path):
    bg = make_background(tmp_path / "letterhead.pdf", "LETTERHEAD")
    write(tmp_path / "project.ymprint.yml", background_config("letterhead.pdf"))
    doc = write(tmp_path / "docs" / "doc.yml", "Doc:\n  - text\n")
    event = Ymprint().render(doc, tmp_path / "out.pdf")
    assert bg.resolve() in event.inputs


@pytest.mark.parametrize("relative_to, folder", [(None, "docs"), ("source", "docs"), ("config", "cfg"), ("cwd", "cwd")])
def test_render_records_a_document_background(tmp_path, monkeypatch, relative_to, folder):
    bg = make_background(tmp_path / folder / "bg.pdf", "BG")
    write(tmp_path / "cfg" / "house.ymprint.yml", "_style:\n  body:\n    size: 10\n")
    (tmp_path / "cwd").mkdir(exist_ok=True)
    monkeypatch.chdir(tmp_path / "cwd")
    doc = write(tmp_path / "docs" / "doc.yml", background_config("bg.pdf", relative_to) + "Doc:\n  - text\n")
    event = Ymprint().render(doc, tmp_path / "out.pdf", tmp_path / "cfg" / "house.ymprint.yml")
    assert bg.resolve() in event.inputs


def test_render_records_every_declared_background_once(tmp_path):
    shared = make_background(tmp_path / "shared.pdf", "SHARED")
    spare = make_background(tmp_path / "spare.pdf", "SPARE")
    config = background_config("shared.pdf", other="shared.pdf", unused="spare.pdf")
    doc = write(tmp_path / "doc.yml", config + "Doc:\n  - text\n")
    event = Ymprint().render(doc, tmp_path / "out.pdf", discover_config=False)
    assert {shared.resolve(), spare.resolve()} <= event.inputs
    assert "SHARED" in mu.open(tmp_path / "out.pdf")[0].get_text()


def test_render_records_images_and_json(tmp_path):
    image = tmp_path / "photo.png"
    shutil.copy(TEST_DATA / "test_image.png", image)
    write(tmp_path / "values.json", '{"a": 1}')
    doc = write(tmp_path / "doc.yml", """
        Doc:
          - _loadjson: {path: values.json}
          - _img: {source: photo.png}
    """)
    event = Ymprint().render(doc, tmp_path / "out.pdf", discover_config=False)
    assert {image.resolve(), (tmp_path / "values.json").resolve()} <= event.inputs


def test_a_missing_background_is_an_authoring_error_that_records_it(tmp_path):
    doc = write(tmp_path / "doc.yml", background_config("missing.pdf") + "Doc:\n  - text\n")
    with pytest.raises(BackgroundNotFoundError) as info:
        Ymprint().render(doc, tmp_path / "out.pdf", discover_config=False)
    assert "'default'" in str(info.value) and "missing.pdf" in str(info.value)
    assert (tmp_path / "missing.pdf").resolve() in info.value.render_event.inputs


def test_a_failed_render_records_the_data_it_read(tmp_path):
    write(tmp_path / "values.yml", "a: 1\n")
    doc = write(tmp_path / "doc.yml", """
        _data:
          values: values.yml
        Doc:
          - _py:
              source: |
                x = values["a"] / 0
    """)
    with pytest.raises(Exception) as info:
        Ymprint().render(doc, tmp_path / "out.pdf", discover_config=False)
    assert (tmp_path / "values.yml").resolve() in info.value.render_event.inputs


# --- live mode -------------------------------------------------------------------

def live_document(tmp_path, background="letterhead.pdf"):
    write(tmp_path / "project.ymprint.yml", background_config(background))
    return write(tmp_path / "doc.yml", "Doc:\n  - text\n")


def test_live_rerenders_when_the_background_changes(tmp_path, headless_live):
    bg = make_background(tmp_path / "letterhead.pdf", "OLD LETTERHEAD")
    doc = live_document(tmp_path)
    triggers = []
    app = Ymprint()
    app.after_render(lambda e: triggers.append(e.trigger))
    headless_live.extend([lambda: make_background(bg, "NEW LETTERHEAD"), settle])

    assert run_live(app, doc, console=Console(quiet=True)) == 0
    assert triggers == [None, bg.resolve()]
    assert "NEW LETTERHEAD" in mu.open(tmp_path / "doc.pdf")[0].get_text()


def test_live_rerenders_once_a_missing_background_is_created(tmp_path, headless_live):
    doc = live_document(tmp_path)
    started, finished = [], []
    app = Ymprint()
    app.before_render(lambda e: started.append(e.trigger))
    app.after_render(lambda e: finished.append(e.trigger))
    headless_live.extend([lambda: make_background(tmp_path / "letterhead.pdf", "LETTERHEAD"), settle])

    assert run_live(app, doc, console=Console(quiet=True)) == 0
    # The first render failed on the missing background; creating it re-rendered.
    assert started == [None, (tmp_path / "letterhead.pdf").resolve()]
    assert finished == [(tmp_path / "letterhead.pdf").resolve()]
    assert "LETTERHEAD" in mu.open(tmp_path / "doc.pdf")[0].get_text()


def test_live_stops_watching_a_background_no_longer_used(tmp_path, headless_live):
    a = make_background(tmp_path / "a.pdf", "A")
    b = make_background(tmp_path / "b.pdf", "B")
    doc = live_document(tmp_path, "a.pdf")
    config = tmp_path / "project.ymprint.yml"
    triggers = []
    app = Ymprint()
    app.after_render(lambda e: triggers.append(e.trigger))

    def switch_to_b():
        config.write_text(background_config("b.pdf"))
        bump_mtime(config)

    headless_live.extend([
        switch_to_b, settle,
        lambda: make_background(a, "A2"), settle,
        lambda: make_background(b, "B2"), settle,
    ])
    assert run_live(app, doc, console=Console(quiet=True)) == 0
    assert triggers == [None, config, b.resolve()]


def test_live_waits_for_a_background_written_in_chunks(tmp_path, headless_live):
    bg = make_background(tmp_path / "letterhead.pdf", "OLD")
    doc = live_document(tmp_path)
    renders = []
    app = Ymprint()
    app.before_render(lambda e: renders.append(e.trigger))

    def truncate():
        bg.write_bytes(b"")
        bump_mtime(bg)

    def finish():
        make_background(bg, "NEW")
        bump_mtime(bg)

    console = Console(record=True, width=200)
    headless_live.extend([truncate, finish, settle])
    assert run_live(app, doc, console=console) == 0
    assert renders == [None, bg.resolve()]
    assert "Render failed" not in console.export_text()
    assert "NEW" in mu.open(tmp_path / "doc.pdf")[0].get_text()


# --- ym build --------------------------------------------------------------------

def run_build(root, **options):
    summary = Build(Ymprint(), root, report=lambda line: None, **options).run([])
    return {r.step.id: r for r in summary.results}


def test_build_rebuilds_a_document_when_its_background_changes(tmp_path):
    bg = make_background(tmp_path / "letterhead.pdf", "OLD")
    write(tmp_path / "project.ymprint.yml", background_config("letterhead.pdf") + "_build:\n  documents:\n    - docs/*.yml\n")
    write(tmp_path / "docs" / "report.yml", "Doc:\n  - text\n")
    assert run_build(tmp_path)["docs/report.yml"].status == "built"

    # Identical bytes: still up to date.
    bg.write_bytes(bg.read_bytes())
    bump_mtime(bg)
    assert run_build(tmp_path)["docs/report.yml"].status == "up-to-date"

    make_background(bg, "NEW")
    planned = run_build(tmp_path, dry_run=True)["docs/report.yml"]
    assert planned.reasons == ["letterhead.pdf changed"]
    assert run_build(tmp_path)["docs/report.yml"].status == "built"
