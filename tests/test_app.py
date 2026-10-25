"""Tests for the Ymprint application class and its render hooks."""
import pathlib
import textwrap

import pymupdf as mu
import pytest
from reportlab.platypus import Paragraph

from ymprint import (
    BlockExistsError, RenderCallbackError, RenderEvent, Ymprint, default_app,
)
from ymprint.blocks.builtin import BUILTIN_BLOCKS
from ymprint.errors import YmprintAuthoringError


def write(path: pathlib.Path, text: str) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text))
    return path


def pdf_text(path) -> str:
    return "".join(page.get_text() for page in mu.open(path))


@pytest.fixture
def doc(tmp_path):
    return write(tmp_path / "report.yml", """
        Report:
          - Hello {{who}}.
    """)


def shout_block(block_key, block_value, context):
    return [Paragraph(str(block_value).upper())]


# --- blocks --------------------------------------------------------------------

def test_app_starts_with_a_copy_of_the_builtin_blocks():
    app = Ymprint()
    assert set(app.blocks.codes()) == set(BUILTIN_BLOCKS.codes())
    assert app.blocks is not BUILTIN_BLOCKS


def test_empty_registry_option():
    assert len(Ymprint(builtin_blocks=False).blocks) == 0


def test_blocks_are_isolated_between_apps(tmp_path):
    a, b = Ymprint(), Ymprint()
    a.register_block("_shout", shout_block)
    source = {"Heading": [{"_shout_1": "hi there"}]}

    a.render(source, tmp_path / "a.pdf")
    assert "HI THERE" in pdf_text(tmp_path / "a.pdf")

    # On app b `_shout_1` is not a block, so the mapping renders as a heading.
    b.render(source, tmp_path / "b.pdf")
    assert "HI THERE" not in pdf_text(tmp_path / "b.pdf")
    assert "_shout" not in default_app.blocks


def test_block_decorator_and_override():
    app = Ymprint()

    @app.block("_shout")
    def shout(block_key, block_value, context):
        return []

    assert app.blocks.get("_shout") is shout
    with pytest.raises(BlockExistsError):
        app.register_block("_img", shout)
    app.register_block("_img", shout, override=True)
    assert app.blocks.get("_img") is shout
    assert BUILTIN_BLOCKS.get("_img") is not shout


# --- hooks ---------------------------------------------------------------------

def test_hooks_run_in_order_around_the_render(doc):
    app = Ymprint()
    calls = []

    @app.before_render
    def before(event):
        calls.append(("before", event.destination.exists()))

    @app.on_context
    def on_context(event, context):
        calls.append(("context", event.destination.exists()))

    @app.after_render
    def after(event):
        calls.append(("after", event.destination.exists()))

    event = app.render(doc)
    assert calls == [("before", False), ("context", False), ("after", True)]
    assert isinstance(event, RenderEvent)
    assert event.destination == doc.with_suffix(".pdf")
    assert event.mode == "api" and event.initial and event.app is app


def test_multiple_hooks_run_in_registration_order(doc):
    app = Ymprint()
    calls = []
    app.before_render(lambda e: calls.append(1))
    app.before_render(lambda e: calls.append(2))
    app.render(doc)
    assert calls == [1, 2]


def test_before_render_vars_reach_the_document(doc):
    app = Ymprint()

    @app.before_render
    def supply(event):
        event.vars["who"] = "from the hook"

    app.render(doc)
    assert "Hello from the hook." in pdf_text(doc.with_suffix(".pdf"))


def test_event_vars_override_document_vars(tmp_path):
    src = write(tmp_path / "r.yml", """
        _vars:
          who: document
          other: kept
        Report:
          - "{{who}} {{other}}"
    """)
    app = Ymprint()
    app.before_render(lambda e: e.vars.update(who="hook"))
    app.render(src)
    assert "hook kept" in pdf_text(src.with_suffix(".pdf"))


def test_on_context_can_change_vars(doc):
    app = Ymprint()

    @app.on_context
    def stamp(event, context):
        context["vars"]["who"] = "context hook"

    app.render(doc)
    assert "Hello context hook." in pdf_text(doc.with_suffix(".pdf"))


@pytest.mark.parametrize("stage", ["before_render", "on_context"])
def test_failing_hook_aborts_the_render(doc, stage):
    app = Ymprint()
    after_calls = []

    def boom(*args):
        raise ValueError("boom")

    getattr(app, stage)(boom)
    app.after_render(after_calls.append)
    with pytest.raises(RenderCallbackError) as info:
        app.render(doc)
    assert info.value.stage == stage
    assert info.value.callback is boom
    assert isinstance(info.value.original, ValueError)
    assert not doc.with_suffix(".pdf").exists()
    assert after_calls == []


def test_after_render_skipped_on_authoring_error(tmp_path):
    src = write(tmp_path / "empty.yml", "")
    app = Ymprint()
    after_calls = []
    app.after_render(after_calls.append)
    with pytest.raises(YmprintAuthoringError):
        app.render(src)
    assert after_calls == []


def test_authoring_error_from_hook_passes_through(doc):
    app = Ymprint()

    @app.before_render
    def bad(event):
        raise YmprintAuthoringError("bad input data")

    with pytest.raises(YmprintAuthoringError):
        app.render(doc)


# --- sources -------------------------------------------------------------------

def test_dict_source_requires_destination():
    with pytest.raises(ValueError, match="destination"):
        Ymprint().render({"Heading": ["text"]})


def test_dict_source_is_not_mutated(tmp_path):
    source = {"_vars": {"who": "data"}, "Report": ["Hello {{who}}."]}
    event = Ymprint().render(source, tmp_path / "out.pdf", base_dir=tmp_path)
    assert source == {"_vars": {"who": "data"}, "Report": ["Hello {{who}}."]}
    assert event.source is None and event.base_dir == tmp_path
    assert "Hello data." in pdf_text(tmp_path / "out.pdf")


def test_dict_source_relative_paths_use_base_dir(tmp_path):
    import json
    (tmp_path / "data.json").write_text(json.dumps({"span": "6 m"}))
    source = {"_loadjson": {"path": "data.json"}, "Beam": ["Span {{span}}"]}
    Ymprint().render(source, tmp_path / "out.pdf", base_dir=tmp_path)
    assert "Span 6 m" in pdf_text(tmp_path / "out.pdf")


def test_empty_dict_source_is_an_authoring_error(tmp_path):
    with pytest.raises(YmprintAuthoringError):
        Ymprint().render({}, tmp_path / "out.pdf")


# --- config layers -------------------------------------------------------------

def test_config_layer_order(tmp_path):
    app_cfg = write(tmp_path / "app" / "app.ymprint.yml", "")
    local = write(tmp_path / "job" / "local.ymprint.yml", "")
    explicit = write(tmp_path / "explicit.ymprint.yml", "")
    app = Ymprint(config_path=app_cfg)
    layers = app.config_layers(tmp_path / "job", explicit)
    assert layers == (app_cfg, local, explicit)
    assert app.config_layers(tmp_path / "job", discover_config=False) == (app_cfg,)


def test_config_layer_found_twice_is_kept_once(tmp_path):
    app_cfg = write(tmp_path / "app.ymprint.yml", "")
    app = Ymprint(config_path=app_cfg)
    assert app.config_layers(tmp_path) == (app_cfg,)


def test_app_config_is_layered_under_local_config(tmp_path):
    app_cfg = write(tmp_path / "app" / "app.ymprint.yml", """
        _doc:
          page-size: A5
        _style:
          body:
            size: 9
    """)
    write(tmp_path / "job" / "local.ymprint.yml", """
        _style:
          body:
            size: 14
    """)
    src = write(tmp_path / "job" / "r.yml", """
        Report:
          - text
    """)
    seen = {}
    app = Ymprint(config_path=app_cfg)
    app.on_context(lambda e, ctx: seen.update(
        size=ctx["styles"]["ymprint"].body.size,
        page=ctx["page_dims"],
    ))
    event = app.render(src)
    assert seen["size"] == 14                     # local over app
    assert len(event.config_paths) == 2
    width, height = mu.open(src.with_suffix(".pdf"))[0].rect[2:]
    assert round(width) == 420 and round(height) == 595   # A5 from the app layer


# --- on_context style changes ----------------------------------------------------

def span_sizes(path) -> dict[str, float]:
    sizes = {}
    for block in mu.open(path)[0].get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                sizes[span["text"].strip()] = round(span["size"], 1)
    return sizes


def test_on_context_style_changes_take_effect(doc):
    app = Ymprint()

    @app.on_context
    def bigger_text(event, context):
        context["styles"]["ymprint"].body.size = 16
        context["vars"]["who"] = "world"

    app.render(doc)
    sizes = span_sizes(doc.with_suffix(".pdf"))
    assert sizes["Hello world."] == 16
    # Headings derive from the body size, so they scale too.
    assert sizes["Report"] > 16


def test_on_context_can_replace_the_style_model(doc):
    from ymprint.config import ReportStyles
    app = Ymprint()

    @app.on_context
    def swap(event, context):
        current = context["styles"]["ymprint"].model_dump(by_alias=True)
        current["body"]["size"] = 7
        context["styles"]["ymprint"] = ReportStyles.model_validate(current)
        context["vars"]["who"] = "small"

    app.render(doc)
    assert span_sizes(doc.with_suffix(".pdf"))["Hello small."] == 7


def test_on_context_named_style_changes_take_effect(tmp_path):
    src = write(tmp_path / "r.yml", """
        _style:
          styles:
            note:
              body:
                size: 8
        Report:
          - _textstyle: note
          - A note.
    """)
    app = Ymprint()
    app.on_context(lambda e, ctx: ctx["styles"]["ymprint"].styles["note"]["body"].update(size=12))
    app.render(src)
    assert span_sizes(src.with_suffix(".pdf"))["A note."] == 12


def test_on_context_table_style_changes_take_effect(tmp_path):
    src = write(tmp_path / "r.yml", """
        Report:
          - Item: one
            Qty: 1
          - Item: two
            Qty: 2
    """)
    app = Ymprint()

    @app.on_context
    def red_headers(event, context):
        context["tablestyles"]["ymprint"].headers.text.color = "#ff0000"

    app.render(src)
    page = mu.open(src.with_suffix(".pdf"))[0]
    colors = {
        span["text"]: span["color"]
        for block in page.get_text("dict")["blocks"]
        for line in block.get("lines", [])
        for span in line["spans"]
    }
    assert colors["Item"] == 0xFF0000
