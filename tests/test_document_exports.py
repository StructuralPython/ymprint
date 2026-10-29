"""Tests for document exports (`_export`) and produced data sources (`from:`)."""
import json
import pathlib
import textwrap

import pymupdf as mu
import pytest
from typer.testing import CliRunner

from ymprint import Ymprint
from ymprint.data_sources import DataSourceError
from ymprint.exports import ExportError, dumps, register_serializer
from ymprint.report_reader import load_report


def write(path: pathlib.Path, text: str) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text))
    return path


def pdf_text(path) -> str:
    return "".join(page.get_text() for page in mu.open(path))


@pytest.fixture
def project(tmp_path):
    write(tmp_path / "project.ymprint.yml", """
        _data:
          design: design.yml
          sections: sections.yml
          beam_capacities:
            from: beams/calc.yml
          capacities:
            from: [beams/calc.yml, columns/calc.yml]
        _render:
          beams/calc.yml:
            for_each: "[m for m in design if m.startswith('B')]"
            as: member_name
            output: build/beams/{{ member_name }}.pdf
    """)
    write(tmp_path / "design.yml", """
        B01: {section: W310x74}
        B02: {section: W250x58}
        B03: {section: W310x74}
        C01: {section: W250x67}
    """)
    write(tmp_path / "sections.yml", """
        W310x74: {Aw: 2.94}
        W250x58: {Aw: 2.11}
        W250x67: {Aw: 2.29}
    """)
    write(tmp_path / "beams" / "calc.yml", """
        _vars:
          member_name: B01
        _export:
          Vr: $V_r
          section: "{{ design[member_name].section }}"
        Beam {{ member_name }}:
          - _py:
              echo: false
              source: |
                V_r = round(0.66 * 350 * sections[design[member_name]["section"]]["Aw"], 3)
          - "Vr = {{ V_r }} kN"
    """)
    write(tmp_path / "columns" / "calc.yml", """
        _export:
          C01: {Pr: 1200}
        Columns:
          - text
    """)
    return tmp_path


def beam_export(root) -> pathlib.Path:
    return root / "build" / ".ym" / "exports" / "beam_capacities" / "beams__calc.yml.json"


def test_render_all_writes_one_key_per_member_with_no_existing_file(project):
    run = Ymprint().render_all(project / "beams" / "calc.yml")
    assert run.ok
    exported = json.loads(beam_export(project).read_text())
    assert sorted(exported) == ["B01", "B02", "B03"]
    assert exported["B02"] == {"Vr": 487.41, "section": "W250x58"}
    assert beam_export(project) in run.written
    assert sorted(run.exports) == ["B01", "B02", "B03"]


def test_deleting_a_member_removes_it_from_the_export(project):
    app = Ymprint()
    app.render_all(project / "beams" / "calc.yml")
    design = project / "design.yml"
    design.write_text(design.read_text().replace("B03: {section: W310x74}\n", ""))
    app.render_all(project / "beams" / "calc.yml")
    assert sorted(json.loads(beam_export(project).read_text())) == ["B01", "B02"]


def test_exported_value_is_the_value_shown_in_the_pdf(project):
    Ymprint().render_all(project / "beams" / "calc.yml")
    exported = json.loads(beam_export(project).read_text())
    for member, values in exported.items():
        assert f"Vr = {values['Vr']} kN" in pdf_text(project / "build" / "beams" / f"{member}.pdf")


def test_consumers_read_the_union_of_the_producers(project):
    app = Ymprint()
    app.render_all(project / "beams" / "calc.yml")
    app.render_all(project / "columns" / "calc.yml")
    report = write(project / "report.yml", """
        Report:
          - "{{ capacities | length }} members; B01 Vr = {{ capacities.B01.Vr }}; C01 Pr = {{ capacities.C01.Pr }}"
    """)
    app.render(report)
    assert "4 members; B01 Vr = 679.14; C01 Pr = 1200" in pdf_text(project / "report.pdf")


def test_a_key_from_two_producers_is_an_error(project):
    write(project / "columns" / "calc.yml", "_export:\n  B01: {Pr: 1}\nColumns:\n  - text\n")
    app = Ymprint()
    app.render_all(project / "beams" / "calc.yml")
    app.render_all(project / "columns" / "calc.yml")
    report = write(project / "report.yml", "Report:\n  - '{{ capacities }}'\n")
    with pytest.raises(DataSourceError, match="'B01' is produced by both calc.yml and calc.yml"):
        app.render(report)


def test_reading_data_that_has_not_been_produced_is_an_error(project):
    report = write(project / "report.yml", "Report:\n  - '{{ beam_capacities }}'\n")
    with pytest.raises(DataSourceError, match="has not been produced yet"):
        Ymprint().render(report)


def test_a_missing_export_variable_names_the_document_and_parameters(project):
    calc = project / "beams" / "calc.yml"
    calc.write_text(calc.read_text().replace("Vr: $V_r", "Vr: $V_rr"))
    run = Ymprint().render_all(calc)
    assert len(run.failures) == 3
    message = str(run.failures[0].error)
    assert "calc.yml (member_name=B01)" in message and "'V_rr'" in message


def test_a_failed_set_removes_the_stale_export(project):
    calc = project / "beams" / "calc.yml"
    app = Ymprint()
    app.render_all(calc)
    assert beam_export(project).exists()
    with open(project / "design.yml", "a") as file:
        file.write("B04: {section: missing}\n")
    run = app.render_all(calc)
    assert [f.instance.key for f in run.failures] == ["B04"]
    assert not beam_export(project).exists()
    assert "previous ones removed" in run.notes[0]


def test_rendering_some_sets_does_not_write_exports(project):
    run = Ymprint().render_all(project / "beams" / "calc.yml", only={"member_name": "B02"})
    assert not beam_export(project).exists()
    assert "only some parameter sets" in run.notes[0]


def test_a_document_without_parameter_sets_exports_a_flat_mapping(project):
    run = Ymprint().render_all(project / "columns" / "calc.yml")
    output = project / "build" / ".ym" / "exports" / "capacities" / "columns__calc.yml.json"
    assert json.loads(output.read_text()) == {"C01": {"Pr": 1200}}
    assert run.written == [output]


def test_a_producer_with_a_path_writes_there(tmp_path):
    write(tmp_path / "p.ymprint.yml", "_data:\n  limits:\n    path: out/limits.json\n    from: calc.yml\n")
    calc = write(tmp_path / "calc.yml", "_export:\n  L: 360\nDoc:\n  - text\n")
    Ymprint().render_all(calc)
    assert json.loads((tmp_path / "out" / "limits.json").read_text()) == {"L": 360}


def test_a_producer_without_export_is_an_error(tmp_path):
    write(tmp_path / "p.ymprint.yml", "_data:\n  limits:\n    from: calc.yml\n")
    calc = write(tmp_path / "calc.yml", "Doc:\n  - text\n")
    with pytest.raises(ExportError, match="has no `_export`"):
        Ymprint().render_all(calc)


def test_path_with_several_producers_is_an_error(tmp_path):
    write(tmp_path / "p.ymprint.yml", "_data:\n  x:\n    path: x.json\n    from: [a.yml, b.yml]\n")
    doc = write(tmp_path / "doc.yml", "Doc:\n  - text\n")
    with pytest.raises(DataSourceError, match="cannot have a `path`"):
        Ymprint().render(doc)


def test_ym_path_of_a_multi_producer_source_is_an_error(project):
    report = write(project / "report.yml", """
        Report:
          - _py:
              echo: false
              source: ym.path("capacities")
    """)
    with pytest.raises(Exception, match="no single path"):
        Ymprint().render(report)


def test_exports_are_on_the_render_event(tmp_path):
    doc = write(tmp_path / "doc.yml", """
        _vars:
          name: beam
        _export:
          n: $n
          label: "{{ name }}-{{ n }}"
          nested: {items: [$n, 2], text: plain}
        Doc:
          - _py:
              echo: false
              source: n = 7
    """)
    event = load_report(doc, tmp_path / "doc.pdf")
    assert event.exports == {"n": 7, "label": "beam-7", "nested": {"items": [7, 2], "text": "plain"}}
    assert event.pdf == tmp_path / "doc.pdf"
    assert load_report(write(tmp_path / "plain.yml", "Doc:\n  - x\n"), tmp_path / "p.pdf").exports is None


def test_cli_convert_reports_written_exports(project):
    result = CliRunner().invoke(Ymprint().cli(), ["convert", str(project / "beams" / "calc.yml")], terminal_width=300)
    assert result.exit_code == 0, result.output
    assert "Exports written" in result.output


class Quantity:
    def __init__(self, value, unit):
        self.value, self.unit = value, unit


class Ratio:
    def __float__(self):
        return 0.5


def test_serialization():
    register_serializer(Quantity, lambda q: {"value": q.value, "unit": q.unit})
    data = {"q": Quantity(30.2, "kN"), "p": pathlib.PurePosixPath("a/b"), "r": Ratio(), "s": {2, 1}}
    assert json.loads(dumps(data)) == {"q": {"value": 30.2, "unit": "kN"}, "p": "a/b", "r": 0.5, "s": [1, 2]}
    with pytest.raises(TypeError, match="cannot export a object"):
        dumps({"x": object()})
