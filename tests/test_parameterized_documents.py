"""Tests for vars= / --var and rendering a document once per parameter set (`_render`)."""
import pathlib
import textwrap

import pymupdf as mu
import pytest
from rich.console import Console
from typer.testing import CliRunner

from ymprint import Ymprint
from ymprint.cli import live as cli_live
from ymprint.cli.live import run_live
from ymprint.fanout import RenderSpecError, RenderUsageError, parse_assignments
from ymprint.report_reader import load_report


def write(path: pathlib.Path, text: str) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text))
    return path


def pdf_text(path) -> str:
    return "".join(page.get_text() for page in mu.open(path))


CONFIG = """
    _data:
      design: design.yml
    _render:
      beams/calc.yml:
        for_each: "[m for m in design if m.startswith('B')]"
        as: member_name
        output: build/beams/{{ member_name }}.pdf
"""


@pytest.fixture
def project(tmp_path):
    write(tmp_path / "project.ymprint.yml", CONFIG)
    write(tmp_path / "design.yml", """
        B01: {section: W310x74}
        B02: {section: W250x58}
        C01: {section: W250x67}
    """)
    doc = write(tmp_path / "beams" / "calc.yml", """
        _vars:
          member_name: B01
        Beam design – {{ member_name }}:
          - "Section: {{ design[member_name].section }}"
    """)
    return tmp_path, doc


def beam_pdfs(root):
    return sorted(p.name for p in (root / "build" / "beams").glob("*.pdf"))


def test_render_all_renders_one_pdf_per_parameter_set(project):
    root, doc = project
    run = Ymprint().render_all(doc)
    assert run.ok
    assert beam_pdfs(root) == ["B01.pdf", "B02.pdf"]
    assert [i.key for i in run.instances] == ["B01", "B02"]
    text = pdf_text(root / "build" / "beams" / "B02.pdf")
    assert "Beam design – B02" in text and "Section: W250x58" in text
    assert (root / "design.yml").resolve() in run.inputs


def test_adding_a_member_to_the_data_adds_a_pdf(project):
    root, doc = project
    with open(root / "design.yml", "a") as file:
        file.write("B05: {section: W200x46}\n")
    Ymprint().render_all(doc)
    assert beam_pdfs(root) == ["B01.pdf", "B02.pdf", "B05.pdf"]


def test_var_on_the_cli_matches_the_fan_out(project):
    root, doc = project
    Ymprint().render_all(doc)
    result = CliRunner().invoke(Ymprint().cli(), ["convert", str(doc), "--var", "member_name=B02"])
    assert result.exit_code == 0, result.output
    assert pdf_text(doc.with_suffix(".pdf")) == pdf_text(root / "build" / "beams" / "B02.pdf")


def test_only_on_the_cli_renders_the_matching_set(project):
    root, doc = project
    result = CliRunner().invoke(Ymprint().cli(), ["convert", str(doc), "--only", "member_name=B02"])
    assert result.exit_code == 0, result.output
    assert beam_pdfs(root) == ["B02.pdf"]


def test_only_matching_nothing_fails(project):
    root, doc = project
    result = CliRunner().invoke(Ymprint().cli(), ["convert", str(doc), "--only", "member_name=Z9"])
    assert result.exit_code == 1
    assert "No parameter set" in result.output


def test_a_failing_set_is_reported_and_the_others_still_render(project):
    root, doc = project
    with open(root / "design.yml", "a") as file:
        file.write("B03: {depth: 310}\n")
    write(doc, """
        Beam {{ member_name }}:
          - _py:
              echo: false
              source: |
                section = design[member_name]["section"]
          - "{{ section }}"
    """)
    run = Ymprint().render_all(doc)
    assert [f.instance.key for f in run.failures] == ["B03"]
    assert run.failures[0].describe().startswith("B03: KeyError")
    assert beam_pdfs(root) == ["B01.pdf", "B02.pdf"]

    result = CliRunner().invoke(Ymprint().cli(), ["convert", str(doc)], terminal_width=200)
    assert result.exit_code == 1
    assert "Rendered 2 of 3" in result.output and "B03: KeyError" in result.output


def test_params_are_available_as_ym_params(project):
    root, doc = project
    write(doc, """
        Beam:
          - _py:
              echo: false
              source: |
                shown = ", ".join(f"{k}={v}" for k, v in ym.params.items())
          - "params: {{ shown }}"
    """)
    Ymprint().render_all(doc, only={"member_name": "B01"})
    assert "params: member_name=B01" in pdf_text(root / "build" / "beams" / "B01.pdf")


def test_items_can_be_mappings_and_outputs_default_next_to_the_source(tmp_path):
    write(tmp_path / "p.ymprint.yml", """
        _render:
          calc.yml:
            for_each: "[{'a': 1, 'b': 'x'}, {'a': 2, 'b': 'y'}]"
    """)
    doc = write(tmp_path / "calc.yml", "Doc:\n  - '{{ a }}{{ b }}'\n")
    run = Ymprint().render_all(doc)
    assert run.ok
    assert [i.destination.name for i in run.instances] == ["calc-1-x.pdf", "calc-2-y.pdf"]
    assert "2y" in pdf_text(tmp_path / "calc-2-y.pdf")


def test_as_can_unpack_tuples_and_key_can_be_set(tmp_path):
    write(tmp_path / "p.ymprint.yml", """
        _render:
          calc.yml:
            for_each: "[(1, 'x'), (2, 'y')]"
            as: [a, b]
            key: "{{ b }}"
            output: "out/{{ b }}.pdf"
    """)
    doc = write(tmp_path / "calc.yml", "Doc:\n  - '{{ a }}{{ b }}'\n")
    instances = Ymprint().instances(doc)
    assert [(i.params, i.key, i.destination.name) for i in instances] == [
        ({"a": 1, "b": "x"}, "x", "x.pdf"), ({"a": 2, "b": "y"}, "y", "y.pdf"),
    ]


def test_a_render_entry_without_for_each_sets_the_output(tmp_path):
    write(tmp_path / "p.ymprint.yml", "_render:\n  report.yml:\n    output: build/report.pdf\n")
    doc = write(tmp_path / "report.yml", "Doc:\n  - text\n")
    run = Ymprint().render_all(doc)
    assert run.results[0].destination == (tmp_path / "build" / "report.pdf").resolve()
    assert (tmp_path / "build" / "report.pdf").exists()


@pytest.mark.parametrize("entry, message", [
    ("{for_each: '[1, 1]', as: n}", "same destination"),
    ("{for_each: '5', as: n}", "must give a list"),
    ("{for_each: 'nope', as: n}", "NameError"),
    ("{for_each: '[1]'}", "not a mapping of variable names"),
    ("{for_each: '[1]', as: n, output: '{{ m }}.pdf'}", "'m' is undefined"),
    ("{as: n}", "has `as` but no `for_each`"),
    ("{for_each: '[1]', every: 2}", "unknown option"),
])
def test_invalid_render_entries(tmp_path, entry, message):
    write(tmp_path / "p.ymprint.yml", f"_render:\n  calc.yml: {entry}\n")
    doc = write(tmp_path / "calc.yml", "Doc:\n  - text\n")
    with pytest.raises(RenderSpecError, match=message):
        Ymprint().render_all(doc)


def test_render_in_a_document_is_an_error(tmp_path):
    doc = write(tmp_path / "calc.yml", "_render: {}\nDoc:\n  - text\n")
    with pytest.raises(Exception, match="belongs in the project config"):
        Ymprint().render(doc, discover_config=False)


def test_usage_errors(project, tmp_path):
    root, doc = project
    with pytest.raises(RenderUsageError, match="destination cannot be given"):
        Ymprint().render_all(doc, destination=tmp_path / "x.pdf")
    plain = write(root / "plain.yml", "Doc:\n  - text\n")
    with pytest.raises(RenderUsageError, match="not rendered per parameter set"):
        Ymprint().render_all(plain, only={"a": 1})
    result = CliRunner().invoke(Ymprint().cli(), ["convert", str(doc), "--dest", str(tmp_path / "x.pdf")])
    assert result.exit_code == 2


def test_load_report_takes_vars_and_returns_the_event(tmp_path):
    doc = write(tmp_path / "doc.yml", "_vars:\n  who: nobody\nDoc:\n  - 'Hello {{ who }}'\n")
    event = load_report(doc, tmp_path / "doc.pdf", vars={"who": "world"})
    assert event.destination == tmp_path / "doc.pdf"
    assert "Hello world" in pdf_text(tmp_path / "doc.pdf")


def test_parse_assignments():
    assert parse_assignments(["a=B01", "n=3", "x=1.5", "ok=true", "s='3'", "e="]) == {
        "a": "B01", "n": 3, "x": 1.5, "ok": True, "s": "3", "e": "",
    }
    with pytest.raises(ValueError, match="NAME=VALUE"):
        parse_assignments(["novalue"])


def test_live_only_previews_the_selected_set(project, monkeypatch):
    root, doc = project
    monkeypatch.setattr(cli_live, "ensure_okular", lambda console: ["true"])
    monkeypatch.setattr(cli_live.subprocess, "Popen", lambda *a, **k: None)
    monkeypatch.setattr(cli_live.time, "sleep", lambda _: (_ for _ in ()).throw(KeyboardInterrupt))
    seen = []
    app = Ymprint()
    app.after_render(lambda e: seen.append((e.destination.name, e.params)))
    assert run_live(app, doc, only={"member_name": "B02"}, console=Console(quiet=True)) == 0
    assert seen == [("B02.pdf", {"member_name": "B02"})]
    assert "Beam design – B02" in pdf_text(root / "build" / "beams" / "B02.pdf")
