"""The `_help` block: help for blocks and a look at values, as a modal over the page."""
import pathlib
import textwrap
import warnings

import pymupdf as mu
import pytest
from typer.testing import CliRunner

from ymprint import Ymprint
from ymprint.blocks.builtin import BUILTIN_BLOCKS
from ymprint.blocks.help_block import describe, help_section, Metrics
from ymprint.blocks.help_texts import HELP_TEXTS
from ymprint.blocks.registry import RESERVED_CODES
from ymprint.errors import BlockError


def write(path: pathlib.Path, text: str) -> pathlib.Path:
    path.write_text(textwrap.dedent(text), encoding="utf-8")
    return path


def page_texts(path) -> list[str]:
    with mu.open(path) as document:
        return [page.get_text() for page in document]


def render(app, source, tmp_path, mode="live"):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return app.render(source, tmp_path / "out.pdf", mode=mode)


def section(value, variables=None, blocks=None):
    context = {"blocks": blocks or BUILTIN_BLOCKS, "vars": variables or {}}
    return help_section(value, context, Metrics(612, 792))


def texts(section) -> str:
    return "\n".join(" ".join(str(part) for part in item[1:]) for item in section["items"])


# --- what each value shows --------------------------------------------------------


def test_every_builtin_block_and_document_key_has_help():
    assert set(BUILTIN_BLOCKS.codes()) <= set(HELP_TEXTS)
    assert RESERVED_CODES - {"_content"} <= set(HELP_TEXTS)
    for code, text in HELP_TEXTS.items():
        assert text["kind"] in {"block", "key"}, code
        assert text["summary"] and text["example"], code


@pytest.mark.parametrize("value", [None, "", "blocks"])
def test_no_value_lists_every_block_and_key(value):
    listed = section(value)
    names = [item[1] for item in listed["items"] if item[0] == "key"]
    assert set(BUILTIN_BLOCKS.codes()) <= set(names)
    assert {"_vars", "_data", "_ul", "_include"} <= set(names)


def test_a_block_name_shows_its_help():
    shown = section("_img")
    assert shown["title"] == "_img"
    assert ("key", "source", HELP_TEXTS["_img"]["keys"][0][1]) in shown["items"]
    assert ("pre", HELP_TEXTS["_img"]["example"]) in shown["items"]


def test_a_block_key_with_an_id_shows_the_blocks_help():
    assert section("_img_logo")["title"] == "_img"


def test_a_document_key_says_so():
    assert section("_vars")["title"] == "_vars (document key)"


def test_a_typo_suggests_the_block():
    shown = section("_imgg")
    assert shown["title"] == "Unknown block _imgg"
    assert "did you mean _img?" in texts(shown)


def test_a_variable_shows_its_name_type_and_value():
    shown = section("$beam", {"beam": {"span": 6.0, "load": 12.5}})
    assert shown["title"] == "$beam"
    assert shown["items"] == [("type", "dict, 2 items"), ("pre", "{'span': 6.0, 'load': 12.5}")]


def test_an_undefined_variable_lists_the_ones_there_are():
    shown = section("$beem", {"beam": 1, "phi": 0.9})
    assert "No variable 'beem'" in texts(shown)
    assert "Did you mean $beam?" in texts(shown)
    assert ("pre", "beam, phi") in shown["items"]


def test_any_other_value_is_shown_as_data():
    shown = section("Span {{ beam.span }} m", {"beam": {"span": 6.0}})
    assert shown["items"] == [("type", "str, 10 characters"), ("pre", "Span 6.0 m")]
    assert section(42)["items"] == [("type", "int"), ("pre", "42")]


def test_describe_names_the_type_and_size():
    assert describe([1, 2, 3]) == "list, 3 items"
    assert describe("a") == "str, 1 character"
    assert describe(2.5) == "float"

    class Shaped:
        shape = (3, 4)

    assert describe(Shaped()).endswith("Shaped, shape (3, 4)")


def test_an_app_block_shows_its_docstring():
    app = Ymprint()

    @app.block("_beam")
    def beam(block_key, block_value, context):
        """Draws a beam.

        span: the span in metres."""
        return []

    shown = section("_beam", blocks=app.blocks)
    assert shown["items"] == [("pre", "Draws a beam.\n\nspan: the span in metres.")]
    listed = section(None, blocks=app.blocks)
    assert ("key", "_beam", "Draws a beam.") in listed["items"]


def test_an_app_override_of_a_builtin_block_shows_the_apps_docstring():
    app = Ymprint()

    @app.block("_img", override=True)
    def picture(block_key, block_value, context):
        """Our own pictures."""
        return []

    assert section("_img", blocks=app.blocks)["items"] == [("pre", "Our own pictures.")]


# --- the modal in the PDF ---------------------------------------------------------


def test_the_modal_is_drawn_over_the_page_with_the_help(tmp_path):
    source = write(tmp_path / "doc.yml", """\
        _vars:
          beam: {span: 6.0}
        Beam B1:
          - First page.
          - _pagebreak:
          - Second page.
          - _help: _img
          - _help: $beam
        """)
    render(Ymprint(), source, tmp_path)
    first, second = page_texts(tmp_path / "out.pdf")
    assert "HELP" not in first
    assert "HELP" in second and "Second page." in second
    # Several _help blocks on a page share one modal, in order.
    assert second.count("HELP") == 1
    assert second.index("_img") < second.index("$beam") < second.index("'span': 6.0")


def test_long_help_continues_on_inserted_pages(tmp_path):
    source = write(tmp_path / "doc.yml", """\
        Report:
          - _py:
              echo: false
              source: |
                big = {f"key_{i}": list(range(i, i + 12)) for i in range(150)}
          - _help: $big
          - _pagebreak:
          - Next page.
        """)
    render(Ymprint(), source, tmp_path)
    pages = page_texts(tmp_path / "out.pdf")
    assert len(pages) > 2
    assert "key_0'" in pages[0]
    assert all("HELP  (continued)" in page for page in pages[1:-1])
    assert "key_149'" in pages[-2]
    assert "Next page." in pages[-1] and "HELP" not in pages[-1]


def test_help_shows_on_a_slide(tmp_path):
    source = write(tmp_path / "deck.yml", """\
        _doc:
          slides: true
          page-size: [960, 540]
        First slide:
          - Some text.
          - _help: _slide
        Second slide:
          - More text.
        """)
    render(Ymprint(), source, tmp_path)
    first, second = page_texts(tmp_path / "out.pdf")
    assert "HELP" in first and "_slide (document key)" in first
    assert "HELP" not in second


# --- live, convert and build ------------------------------------------------------


@pytest.fixture
def helped(tmp_path):
    return write(tmp_path / "doc.yml", "Report:\n  - _help: _img\n")


def test_live_mode_shows_it_without_a_warning(helped, tmp_path):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        event = Ymprint().render(helped, tmp_path / "out.pdf", mode="live")
    assert event.warnings == []


def test_a_render_from_python_warns(helped, tmp_path):
    with pytest.warns(UserWarning, match="has a `_help` block"):
        event = Ymprint().render(helped, tmp_path / "out.pdf")
    assert len(event.warnings) == 1


def test_convert_warns(helped):
    result = CliRunner().invoke(Ymprint().cli(), ["convert", str(helped)], terminal_width=300)
    assert result.exit_code == 0, result.output
    assert "doc.yml has a `_help` block" in result.output


def test_build_refuses_it(helped, tmp_path):
    with pytest.raises(BlockError, match="ym build"):
        Ymprint().render(helped, tmp_path / "out.pdf", mode="build")
