"""Tests for layered config: defaults < config layers (low -> high) < document."""
import pathlib
import textwrap

import pymupdf as mu
import pytest
from reportlab.pdfgen.canvas import Canvas

from ymprint.config.config_loaders import config_base_dir, load_report_config
from ymprint.report_reader import load_report


def write(path: pathlib.Path, text: str) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text))
    return path


def make_background(path: pathlib.Path, mark: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas = Canvas(str(path))
    canvas.drawString(10, 10, mark)
    canvas.showPage()
    canvas.save()


@pytest.fixture
def layers(tmp_path):
    app = write(tmp_path / "app" / "app.ymprint.yml", """
        _style:
          body:
            size: 9
          h1:
            size: 30
        _doc:
          page-size: A5
    """)
    local = write(tmp_path / "job" / "local.ymprint.yml", """
        _style:
          body:
            size: 11
    """)
    explicit = write(tmp_path / "explicit.ymprint.yml", """
        _doc:
          page-size: A3
    """)
    return app, local, explicit


def test_single_path_still_supported(layers):
    app, _, _ = layers
    styles, _, doc = load_report_config({}, app)
    assert styles["_style"]["body"]["size"] == 9
    assert doc["_doc"]["page-size"] == "A5"


def test_higher_layers_override_only_the_keys_they_set(layers):
    styles, _, doc = load_report_config({}, list(layers))
    assert styles["_style"]["body"]["size"] == 11      # local over app
    assert styles["_style"]["h1"]["size"] == 30        # app, untouched by others
    assert doc["_doc"]["page-size"] == "A3"            # explicit over app


def test_document_config_beats_all_layers(layers):
    source = {"_style": {"body": {"size": 14}}}
    styles, _, _ = load_report_config(source, list(layers))
    assert styles["_style"]["body"]["size"] == 14


def test_none_layers_are_skipped(layers):
    app, _, _ = layers
    styles, _, _ = load_report_config({}, [None, app, None])
    assert styles["_style"]["body"]["size"] == 9


def test_missing_layer_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_report_config({}, [tmp_path / "nope.ymprint.yml"])


def test_config_base_dir(tmp_path):
    config_file = write(tmp_path / "cfg" / "a.ymprint.yml", "")
    assert config_base_dir(config_file) == tmp_path / "cfg"
    assert config_base_dir(tmp_path / "cfg") == tmp_path / "cfg"


def test_config_relative_background_resolves_against_its_own_layer(tmp_path):
    # The app layer defines a background relative to *its* directory; a local
    # layer elsewhere must not change where that background is found.
    make_background(tmp_path / "app" / "letterhead.pdf", "APP LETTERHEAD")
    app = write(tmp_path / "app" / "app.ymprint.yml", """
        _doc:
          templates:
            default:
              margins: {top: 72, left: 72, right: 72, bottom: 72}
              background:
                filepath: letterhead.pdf
                relative-to: config
    """)
    local = write(tmp_path / "job" / "local.ymprint.yml", """
        _style:
          body:
            size: 11
    """)
    source = write(tmp_path / "job" / "report.yml", """
        Heading:
          - Some text.
    """)
    dest = tmp_path / "job" / "report.pdf"
    load_report(source, dest, [app, local])
    text = mu.open(dest)[0].get_text()
    assert "APP LETTERHEAD" in text


def test_config_directory_background_resolves_against_the_directory(tmp_path):
    make_background(tmp_path / "cfg" / "bg.pdf", "DIR BACKGROUND")
    write(tmp_path / "cfg" / "house.ymprint.yml", """
        _doc:
          templates:
            default:
              margins: {top: 72, left: 72, right: 72, bottom: 72}
              background:
                filepath: bg.pdf
                relative-to: config
    """)
    source = write(tmp_path / "report.yml", """
        Heading:
          - Some text.
    """)
    dest = tmp_path / "report.pdf"
    load_report(source, dest, tmp_path / "cfg")
    assert "DIR BACKGROUND" in mu.open(dest)[0].get_text()
