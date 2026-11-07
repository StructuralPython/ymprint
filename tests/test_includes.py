"""`_include`: partial documents built in place (ymprint.includes)."""
import json
import pathlib
import textwrap
from importlib.util import find_spec

import pymupdf
import pytest

from ymprint import Ymprint
from ymprint.blocks.registry import BlockRegistry
from ymprint.build import Build
from ymprint.errors import IncludeError, PythonBlockError
from ymprint.includes import extract_include

needs_hc = pytest.mark.skipif(find_spec("ym_handcalcs") is None, reason="ym-handcalcs is not installed")


def write(path: pathlib.Path, text: str) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")
    return path


@pytest.fixture
def project(tmp_path):
    """A project whose partials live in a library folder outside it."""
    root = tmp_path / "project"
    write(root / "project.ymprint.yml", """
        _data:
          beam_check: ../library/beam_check.yml
          headingless: ../library/headingless.yml
    """)
    write(tmp_path / "library" / "beam_check.yml", """
        _vars:
          caption: Default caption
          span: 1.0
        Moment check:
          - _py:
              echo: false
              source: |
                M = w * span ** 2 / 8
          - "{{ caption }}: M = {{ M }}"
          - Sub step: detail
    """)
    write(tmp_path / "library" / "headingless.yml", """
        - Plain partial paragraph.
    """)
    return root


def render(root, document: str, name="doc.yml", **options):
    source = write(root / name, document)
    event = Ymprint().render(source, root / "doc.pdf", **options)
    return event, root / "doc.pdf"


def pdf_text(path) -> str:
    with pymupdf.open(path) as pdf:
        return " ".join("".join(page.get_text() for page in pdf).split())


def toc(path) -> list:
    with pymupdf.open(path) as pdf:
        return pdf.get_toc()


def span_sizes(path) -> dict:
    with pymupdf.open(path) as pdf:
        return {
            span["text"].strip(): round(span["size"], 1)
            for page in pdf
            for block in page.get_text("dict")["blocks"]
            for line in block.get("lines", [])
            for span in line["spans"]
            if span["text"].strip()
        }


# --- syntax ------------------------------------------------------------------------

def test_extract_include_forms():
    assert extract_include("_include", "x") == ("_include", "x")
    assert extract_include("_include_b1", "x") == ("_include_b1", "x")
    assert extract_include(None, {"_include": "x"}) == ("_include", "x")
    assert extract_include("_includes", "x") is None
    assert extract_include("Heading", "x") is None


def test_include_is_reserved():
    with pytest.raises(ValueError, match="reserved"):
        BlockRegistry().register("_include", lambda k, v, c: [])


# --- placement ---------------------------------------------------------------------

def test_partial_headings_continue_the_include_sites_level(project):
    _, pdf = render(project, """
        _vars: {w: 2.0}
        Calculations:
          - Beam B01:
            - _include: beam_check
    """)
    assert toc(pdf) == [
        [1, "Calculations", 1],
        [2, "Beam B01", 1],
        [3, "Moment check", 1],
        [4, "Sub step", 1],
    ]


def test_partial_at_the_top_level_starts_at_h1(project):
    _, pdf = render(project, """
        _vars: {w: 2.0}
        _include: beam_check
        After: text
    """)
    assert [entry[:2] for entry in toc(pdf)] == [[1, "Moment check"], [2, "Sub step"], [1, "After"]]


def test_text_style_is_inherited_and_does_not_leak(project, tmp_path):
    write(tmp_path / "library" / "styled.yml", """
        - Inherited paragraph.
        - _textstyle: tiny
        - Tiny paragraph.
    """)
    write(project / "project.ymprint.yml", """
        _data:
          styled: ../library/styled.yml
    """)
    _, pdf = render(project, """
        _style:
          styles:
            fine: {body: {size: 7}}
            tiny: {body: {size: 5}}
        Section:
          - _textstyle: fine
          - _include: styled
          - Back in the document.
    """)
    sizes = span_sizes(pdf)
    assert sizes["Inherited paragraph."] == 7
    assert sizes["Tiny paragraph."] == 5
    assert sizes["Back in the document."] == 7


def test_headingless_partial(project):
    _, pdf = render(project, "Section:\n  - _include: headingless\n")
    assert "Plain partial paragraph." in pdf_text(pdf)
    assert toc(pdf) == [[1, "Section", 1]]


# --- parameters and scope ------------------------------------------------------------

def test_with_overrides_defaults_and_shared_results_stay(project):
    event, pdf = render(project, """
        _vars: {w: 2.0}
        _export:
          M: $M
        Beam:
          - _include:
              path: beam_check
              with: {span: 4.0, caption: Given}
          - "After: {{ M }}"
    """)
    text = pdf_text(pdf)
    assert "Given: M = 4.0" in text
    assert "After: 4.0" in text
    assert event.exports == {"M": 4.0}


def test_shared_defaults_do_not_override_document_values(project):
    _, pdf = render(project, """
        _vars: {w: 2.0, caption: From the document}
        Beam:
          - _include: beam_check
    """)
    assert "From the document: M = 0.25" in pdf_text(pdf)


def test_scoped_includes_are_independent(project):
    event, pdf = render(project, """
        _vars: {w: 2.0, span: 99}
        _export:
          b1: $b1
          b2: $b2
          span: $span
        Beam B01:
          - _include:
              path: beam_check
              namespace: b1
              with: {span: 2.0, caption: B01}
        Beam B02:
          - _include:
              path: beam_check
              namespace: b2
              with: {span: 4.0, caption: B02}
        Summary: "{{ b1.M }} and {{ b2.M }}"
    """)
    text = pdf_text(pdf)
    assert "B01: M = 1.0" in text and "B02: M = 4.0" in text
    assert "1.0 and 4.0" in text
    assert event.exports["b2"]["M"] == 4.0
    # The document's own `span` is untouched; b1 holds what the partial set.
    assert event.exports["span"] == 99
    assert event.exports["b1"] == {"caption": "B01", "span": 2.0, "M": 1.0}


def test_dollar_var_parameter_passes_the_object(project, tmp_path):
    write(tmp_path / "library" / "obj.yml", """
        - _py:
            echo: false
            source: |
              total = sum(values)
        - "Total {{ total }}"
    """)
    write(project / "project.ymprint.yml", "_data:\n  obj: ../library/obj.yml\n")
    _, pdf = render(project, """
        _vars:
          numbers: [1, 2, 3]
        S:
          - _include: {path: obj, with: {values: $numbers}}
    """)
    assert "Total 6" in pdf_text(pdf)


# --- the partial's own files -----------------------------------------------------------

def test_paths_and_data_resolve_relative_to_the_partial(project, tmp_path):
    lib = tmp_path / "library"
    write(lib / "values.json", json.dumps({"from_json": "J"}))
    write(lib / "table.yml", "rating: 42\n")
    write(lib / "files.yml", """
        _data:
          table: table.yml
        Partial:
          - _loadjson:
              path: values.json
          - "json={{ from_json }} data={{ table.rating }}"
    """)
    write(project / "values.json", json.dumps({"doc_value": "D"}))
    write(project / "project.ymprint.yml", "_data:\n  files: ../library/files.yml\n")
    event, pdf = render(project, """
        Doc:
          - _include: files
          - _loadjson:
              path: values.json
          - "doc={{ doc_value }}"
    """)
    text = pdf_text(pdf)
    assert "json=J data=42" in text
    # base_dir is restored after the partial.
    assert "doc=D" in text
    inputs = {p.resolve() for p in event.inputs}
    assert (lib / "files.yml").resolve() in inputs
    assert (lib / "table.yml").resolve() in inputs
    assert (lib / "values.json").resolve() in inputs


def test_scoped_partial_sees_its_own_data(project, tmp_path):
    lib = tmp_path / "library"
    write(lib / "table.yml", "rating: 7\n")
    write(lib / "scoped.yml", """
        _data:
          table: table.yml
        Partial: "rating {{ table.rating }}"
    """)
    write(project / "project.ymprint.yml", "_data:\n  scoped: ../library/scoped.yml\n")
    _, pdf = render(project, "Doc:\n  - _include: {path: scoped, namespace: s}\n")
    assert "rating 7" in pdf_text(pdf)


@needs_hc
def test_hc_path_finds_the_partials_own_py(project, tmp_path):
    lib = tmp_path / "library"
    write(lib / "calc.py", "M_f = w * L**2 / 8\n")
    write(lib / "hc_partial.yml", """
        _data:
          calc: calc.py
        _vars:
          L: 2.0
        Calc:
          - _hc:
              path: calc
          - "M_f is {{ M_f }}"
    """)
    write(project / "project.ymprint.yml", "_data:\n  hcp: ../library/hc_partial.yml\n")
    event, pdf = render(project, "_vars: {w: 3.0}\nBeam:\n  - _include: hcp\n")
    assert "M_f is 1.5" in pdf_text(pdf)
    assert (lib / "calc.py").resolve() in {p.resolve() for p in event.inputs}


def test_absolute_path(project, tmp_path):
    partial = tmp_path / "library" / "headingless.yml"
    _, pdf = render(project, f"S:\n  - _include: {partial}\n")
    assert "Plain partial paragraph." in pdf_text(pdf)


def test_nested_partials(project, tmp_path):
    lib = tmp_path / "library"
    write(lib / "outer.yml", "_data:\n  inner: inner.yml\nOuter:\n  - _include: inner\n")
    write(lib / "inner.yml", "Inner: deepest\n")
    write(project / "project.ymprint.yml", "_data:\n  outer: ../library/outer.yml\n")
    _, pdf = render(project, "Doc:\n  - _include: outer\n")
    assert toc(pdf) == [[1, "Doc", 1], [2, "Outer", 1], [3, "Inner", 1]]


# --- errors ----------------------------------------------------------------------------

def test_self_inclusion_is_an_error(project, tmp_path):
    lib = tmp_path / "library"
    write(lib / "a.yml", "_data:\n  b: b.yml\nA:\n  - _include: b\n")
    write(lib / "b.yml", "_data:\n  a: a.yml\nB:\n  - _include: a\n")
    write(project / "project.ymprint.yml", "_data:\n  a: ../library/a.yml\n")
    with pytest.raises(IncludeError, match=r"a\.yml → b\.yml → a\.yml") as info:
        render(project, "Doc:\n  - _include: a\n")
    assert [p.name for p in info.value.include_chain] == ["doc.yml", "a.yml", "b.yml"]


@pytest.mark.parametrize(
    "value, message",
    [
        ("relative/path.yml", "must be a `_data` name or an absolute path"),
        ("nope", "no data source named 'nope'"),
        ({"path": "beam_check", "colour": 1}, "unknown option"),
        ({"path": "beam_check", "namespace": "not valid"}, "valid variable name"),
        ({"path": "beam_check", "with": [1]}, "`with` must be a mapping"),
        ({"with": {}}, "expected the partial"),
    ],
)
def test_bad_include_options(project, value, message):
    with pytest.raises(IncludeError, match=message):
        Ymprint().render({"S": [{"_include": value}]}, project / "doc.pdf", base_dir=project)


@pytest.mark.parametrize("key", ["_doc", "_export", "_style"])
def test_document_only_keys_are_rejected(project, tmp_path, key):
    write(tmp_path / "library" / "bad.yml", f"{key}: {{}}\nContent: text\n")
    write(project / "project.ymprint.yml", "_data:\n  bad: ../library/bad.yml\n")
    with pytest.raises(IncludeError, match=f"uses {key}"):
        render(project, "S:\n  - _include: bad\n")


def test_empty_partial_is_an_error(project, tmp_path):
    write(tmp_path / "library" / "empty.yml", "# nothing\n")
    write(project / "project.ymprint.yml", "_data:\n  empty: ../library/empty.yml\n")
    with pytest.raises(IncludeError, match="is empty"):
        render(project, "S:\n  - _include: empty\n")


def test_produced_data_in_a_partial_is_rejected(project, tmp_path):
    write(tmp_path / "library" / "prod.yml", "_data:\n  x:\n    from: make.py\nC: text\n")
    write(project / "project.ymprint.yml", "_data:\n  prod: ../library/prod.yml\n")
    with pytest.raises(IncludeError, match="has a `from`"):
        render(project, "S:\n  - _include: prod\n")


def test_errors_inside_a_partial_name_the_chain(project, tmp_path):
    write(tmp_path / "library" / "boom.yml", "- _py:\n    source: 1 / 0\n")
    write(project / "project.ymprint.yml", "_data:\n  boom: ../library/boom.yml\n")
    with pytest.raises(PythonBlockError) as info:
        render(project, "S:\n  - _include: boom\n")
    assert [p.name for p in info.value.include_chain] == ["doc.yml", "boom.yml"]


def test_context_is_restored_after_an_error(project, tmp_path):
    from ymprint.config.config_loaders import load_report_config
    from ymprint.context_builder import build_context
    from ymprint.data_sources import DataCatalog, parse_data_declarations
    from ymprint.story_builder import build_story

    write(tmp_path / "library" / "boom.yml", "- _py:\n    source: 1 / 0\n")
    styles, tbl, doc = load_report_config({}, None)
    catalog = DataCatalog(
        sources=parse_data_declarations({"boom": str(tmp_path / "library" / "boom.yml")}, project, None),
        project_root=project,
    )
    vars_ = {}
    context = build_context({}, styles, doc, tbl, vars_, project / "d.yml", project / "d.pdf", None, data=catalog)
    with pytest.raises(PythonBlockError):
        build_story({"S": [{"_include": "boom"}]}, context)
    assert context["base_dir"] == project
    assert context["data"] is catalog
    assert context["vars"] is vars_
    assert context["include_stack"] == []


# --- slides ----------------------------------------------------------------------------

def test_slides_from_a_top_level_include_continue_the_deck(project, tmp_path):
    write(tmp_path / "library" / "slides.yml", "Slide two: a\nSlide three: b\n")
    write(project / "project.ymprint.yml", "_data:\n  more: ../library/slides.yml\n")
    _, pdf = render(project, """
        _doc:
          page-size: [960, 540]
          slides: true
          templates:
            default:
              margins: {top: 20, left: 40, right: 40, bottom: 20}
        Slide one: x
        _include: more
        Slide four: y
    """)
    with pymupdf.open(pdf) as doc:
        assert doc.page_count == 4
    assert [e[1] for e in toc(pdf)] == ["Slide one", "Slide two", "Slide three", "Slide four"]


# --- ym build ---------------------------------------------------------------------------

def test_build_tracks_partials_and_their_local_data(project, tmp_path):
    lib = tmp_path / "library"
    write(lib / "table.yml", "rating: 1\n")
    write(lib / "local.yml", "_data:\n  table: table.yml\nPart: \"rating {{ table.rating }}\"\n")
    write(project / "project.ymprint.yml", """
        _data:
          local: ../library/local.yml
        _build:
          documents:
            - report.yml
    """)
    write(project / "report.yml", "Report:\n  - _include: local\n")

    def build():
        summary = Build(Ymprint(), project, report=lambda line: None).run([])
        assert summary.ok, [(r.step.id, r.error) for r in summary.results]
        return {r.step.id: r for r in summary.results}

    assert build()["report.yml"].status == "built"
    # Up to date: the partial-local `table` is recorded as a file, not a name.
    assert build()["report.yml"].status == "up-to-date"
    write(lib / "table.yml", "rating: 2\n")
    assert build()["report.yml"].status == "built"
    write(lib / "local.yml", "_data:\n  table: table.yml\nPart: \"changed {{ table.rating }}\"\n")
    assert build()["report.yml"].status == "built"
    assert "changed 2" in pdf_text(project / "report.pdf")


# --- front matter with headingless content (`_content`) -----------------------------------

def test_headingless_partial_with_front_matter_uses_content(project, tmp_path):
    lib = tmp_path / "library"
    write(lib / "with_front_matter.yml", """
        _vars:
          caption: Default
        _content:
          - "Caption: {{ caption }}"
          - Second paragraph.
    """)
    write(project / "project.ymprint.yml", "_data:\n  fm: ../library/with_front_matter.yml\n")
    _, pdf = render(project, "Section:\n  - _include: {path: fm, with: {caption: Given}}\n")
    text = pdf_text(pdf)
    assert "Caption: Given" in text and "Second paragraph." in text
    assert toc(pdf) == [[1, "Section", 1]]


@needs_hc
def test_headingless_hc_partial(project, tmp_path):
    lib = tmp_path / "library"
    write(lib / "beam_check.py", "## Moment check\nM_f = w * L**2 / 8\n")
    write(lib / "hc_content.yml", """
        _data:
          calc: beam_check.py
        _content:
          - _hc:
              path: calc
          - "M_f = {{ M_f }}"
    """)
    write(project / "project.ymprint.yml", "_data:\n  beam_check: ../library/hc_content.yml\n")
    _, pdf = render(project, """
        Calculations:
          - Beam B01:
            - _include: {path: beam_check, namespace: b1, with: {w: 12.5, L: 6.0}}
          - Beam B02:
            - _include: {path: beam_check, namespace: b2, with: {w: 10.0, L: 4.0}}
          - "Summary: {{ b1.M_f }} and {{ b2.M_f }}"
    """)
    assert "Summary: 56.25 and 20.0" in pdf_text(pdf)
    # With ym-handcalcs 0.4+, the calc's `##` heading continues the document's levels.
    levels = [entry[:2] for entry in toc(pdf)]
    assert levels[:3] == [[1, "Calculations"], [2, "Beam B01"], [3, "Moment check"]]


def test_content_with_other_keys_is_an_error(project, tmp_path):
    write(tmp_path / "library" / "mixed.yml", "_content:\n  - a\nHeading: b\n")
    write(project / "project.ymprint.yml", "_data:\n  mixed: ../library/mixed.yml\n")
    with pytest.raises(IncludeError, match="Put all of its content under `_content`"):
        render(project, "S:\n  - _include: mixed\n")
