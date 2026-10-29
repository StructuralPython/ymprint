"""Tests for the project root and named data sources (`_data`)."""
import json
import pathlib
import shutil
import textwrap

import pymupdf as mu
import pytest

from ymprint import Ymprint
from ymprint.data_sources import (
    DataCatalog, DataSourceError, DocumentVars, load_file, register_loader,
)
from ymprint.errors import YmprintAuthoringError

TEST_DATA = pathlib.Path(__file__).parent / "test-data"


def write(path: pathlib.Path, text: str) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text))
    return path


def pdf_text(path) -> str:
    return "".join(page.get_text() for page in mu.open(path))


@pytest.fixture
def project(tmp_path):
    """A project config at the root, data in one folder, a document two folders deep."""
    write(tmp_path / "project.ymprint.yml", """
        _data:
          design: 4-design/design.yml
          sections: 1-reference/sections.json
    """)
    write(tmp_path / "4-design" / "design.yml", """
        B01: {section: W310x74}
        B02: {section: W250x58}
    """)
    write(tmp_path / "1-reference" / "sections.json", json.dumps({"W310x74": {"Zx": 1160}}))
    doc = write(tmp_path / "5-validation" / "beams" / "calc.yml", """
        Beam B01:
          - "Section: {{ design.B01.section }}"
    """)
    return tmp_path, doc


def test_document_reads_data_by_name_from_any_cwd(project, monkeypatch, tmp_path_factory):
    root, doc = project
    for cwd in (root, doc.parent, tmp_path_factory.mktemp("elsewhere")):
        monkeypatch.chdir(cwd)
        event = Ymprint().render(doc, cwd / "out.pdf")
        assert "Section: W310x74" in pdf_text(cwd / "out.pdf")
        assert event.project_root == root.resolve()


def test_data_is_a_python_global_in_py_blocks(project):
    root, doc = project
    write(doc, """
        Beam:
          - _py:
              echo: false
              source: |
                Z_x = sections[design["B01"]["section"]]["Zx"]
                root = ym.project_root.name
                where = ym.path("design").relative_to(ym.project_root).as_posix()
          - "Zx = {{ Z_x }} in {{ root }} from {{ where }}"
    """)
    Ymprint().render(doc, root / "out.pdf")
    assert f"Zx = 1160 in {root.name} from 4-design/design.yml" in pdf_text(root / "out.pdf")


def test_sources_load_lazily_and_reads_are_recorded(project):
    root, doc = project
    # A source that is declared but never used is never read, even if its file
    # is missing.
    write(root / "project.ymprint.yml", """
        _data:
          design: 4-design/design.yml
          sections: 1-reference/sections.json
          missing: nowhere.yml
    """)
    event = Ymprint().render(doc, root / "out.pdf")
    assert event.inputs == {(root / "4-design" / "design.yml").resolve()}


def test_using_a_missing_data_file_is_an_authoring_error(project):
    root, doc = project
    (root / "4-design" / "design.yml").unlink()
    with pytest.raises(DataSourceError, match="Data file not found"):
        Ymprint().render(doc, root / "out.pdf")


def test_document_data_resolves_against_the_document_and_overrides_config(project):
    root, doc = project
    write(doc.parent / "local-design.yml", "B01: {section: HSS}\n")
    write(doc, """
        _data:
          design: local-design.yml
        Beam:
          - "Section: {{ design.B01.section }}"
    """)
    Ymprint().render(doc, root / "out.pdf")
    assert "Section: HSS" in pdf_text(root / "out.pdf")


def test_var_with_a_data_source_name_is_an_error(project):
    root, doc = project
    write(doc, """
        _vars:
          design: 1
        Beam:
          - text
    """)
    with pytest.raises(YmprintAuthoringError, match="'design'.*also a `_data` source"):
        Ymprint().render(doc, root / "out.pdf")


def test_runtime_vars_take_precedence_over_data(project):
    root, doc = project
    app = Ymprint()

    @app.before_render
    def inject(event):
        event.vars["design"] = {"B01": {"section": "injected"}}

    app.render(doc, root / "out.pdf")
    assert "Section: injected" in pdf_text(root / "out.pdf")


def test_one_render_cannot_change_the_data_the_next_one_sees(project):
    root, doc = project
    write(doc, """
        Beam:
          - _py:
              echo: false
              source: |
                design["B01"]["section"] = "mutated"
          - "Section: {{ design.B01.section }}"
    """)
    other = write(doc.parent / "other.yml", """
        Other:
          - "Section: {{ design.B01.section }}"
    """)
    Ymprint().render(doc, root / "a.pdf")
    Ymprint().render(other, root / "b.pdf")
    assert "Section: mutated" in pdf_text(root / "a.pdf")
    assert "Section: W310x74" in pdf_text(root / "b.pdf")


def test_without_a_project_config_the_root_is_the_document_folder(tmp_path):
    doc = write(tmp_path / "sub" / "doc.yml", """
        _data:
          values: values.yml
        Doc:
          - _py:
              echo: false
              source: |
                root = str(ym.project_root)
          - "{{ values.a }} {{ root }}"
    """)
    write(tmp_path / "sub" / "values.yml", "a: 42\n")
    event = Ymprint().render(doc, tmp_path / "out.pdf", discover_config=False)
    assert event.project_root == doc.parent.resolve()
    assert "42" in pdf_text(tmp_path / "out.pdf")


def test_data_entries_can_be_used_as_block_variables(project):
    root, doc = project
    seen = {}
    app = Ymprint()

    @app.block("_show")
    def show(block_key, block_value, context):
        seen["value"] = block_value
        return []

    write(doc, """
        Beam:
          - _show: $design
    """)
    app.render(doc, root / "out.pdf")
    assert seen["value"]["B01"]["section"] == "W310x74"


@pytest.mark.parametrize("declaration, message", [
    ("[a, b]", "must be a mapping"),
    ("{1bad: x.yml}", "not a valid variable name"),
    ("{ym: x.yml}", "reserved"),
    ("{d: {loader: json}}", "needs a `path`"),
    ("{d: {path: x.yml, glob: true}}", "unknown option"),
])
def test_invalid_declarations(tmp_path, declaration, message):
    doc = write(tmp_path / "doc.yml", f"_data: {declaration}\nDoc:\n  - text\n")
    with pytest.raises(DataSourceError, match=message):
        Ymprint().render(doc, tmp_path / "out.pdf", discover_config=False)


def test_custom_loader(tmp_path):
    register_loader("lines", lambda path: path.read_text().split(), override=True)
    write(tmp_path / "members.txt", "B01 B02 B03\n")
    doc = write(tmp_path / "doc.yml", """
        _data:
          members: {path: members.txt, loader: lines}
        Doc:
          - "{{ members | length }} members"
    """)
    Ymprint().render(doc, tmp_path / "out.pdf", discover_config=False)
    assert "3 members" in pdf_text(tmp_path / "out.pdf")


def test_unknown_extension_needs_a_loader(tmp_path):
    write(tmp_path / "x.toml", "a = 1\n")
    doc = write(tmp_path / "doc.yml", "_data: {x: x.toml}\nDoc:\n  - '{{ x }}'\n")
    with pytest.raises(DataSourceError, match="No loader"):
        Ymprint().render(doc, tmp_path / "out.pdf", discover_config=False)


def test_load_file_returns_fresh_copies_and_rereads_changed_files(tmp_path):
    path = write(tmp_path / "d.yml", "a: [1]\n")
    first = load_file(path)
    first["a"].append(2)
    assert load_file(path) == {"a": [1]}
    write(path, "a: [1, 2, 3]\n")
    assert load_file(path) == {"a": [1, 2, 3]}


def test_document_vars_resolve_lazily(tmp_path):
    write(tmp_path / "d.yml", "a: 1\n")
    catalog = DataCatalog.from_config([], {"d": "d.yml"}, tmp_path)
    variables = DocumentVars({"x": 1}, catalog=catalog)
    assert "d" in variables and "d" not in list(variables)
    assert catalog.reads == {}
    assert variables.get("d") == {"a": 1}
    assert variables.get("nope", "default") == "default"
    assert list(catalog.reads) == ["d"]


def test_loadjson_reads_through_the_cache_and_is_recorded(tmp_path):
    write(tmp_path / "data.json", json.dumps({"x": 5}))
    doc = write(tmp_path / "doc.yml", """
        Doc:
          - _loadjson:
              path: data.json
          - "x = {{ x }}"
    """)
    event = Ymprint().render(doc, tmp_path / "out.pdf", discover_config=False)
    assert "x = 5" in pdf_text(tmp_path / "out.pdf")
    assert event.inputs == {(tmp_path / "data.json").resolve()}


# --- one path rule: backgrounds -------------------------------------------------

def background_config(background: str) -> str:
    return f"""
        _doc:
          templates:
            default:
              margins: {{top: 72, left: 72, right: 72, bottom: 72}}
              background: {background}
    """


def test_config_background_without_relative_to_resolves_against_the_config(tmp_path, monkeypatch):
    shutil.copy(TEST_DATA / "background_first_page.pdf", tmp_path / "bg.pdf")
    write(tmp_path / "project.ymprint.yml", background_config("{filepath: bg.pdf}"))
    doc = write(tmp_path / "docs" / "deep" / "doc.yml", "Doc:\n  - text\n")
    monkeypatch.chdir(doc.parent)
    Ymprint().render(doc, tmp_path / "out.pdf")
    assert (tmp_path / "out.pdf").exists()


def test_document_background_without_relative_to_resolves_against_the_document(tmp_path, monkeypatch):
    (tmp_path / "docs").mkdir()
    shutil.copy(TEST_DATA / "background_first_page.pdf", tmp_path / "docs" / "bg.pdf")
    doc = write(tmp_path / "docs" / "doc.yml", textwrap.dedent(background_config("{filepath: bg.pdf}")) + "Doc:\n  - text\n")
    monkeypatch.chdir(tmp_path)
    Ymprint().render(doc, tmp_path / "out.pdf", discover_config=False)
    assert (tmp_path / "out.pdf").exists()
