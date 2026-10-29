"""Tests for `ym build`, `ym graph` and the script project API."""
import json
import pathlib
import textwrap

import pytest
from typer.testing import CliRunner

from ymprint import Ymprint
from ymprint.build import Build, BuildError, format_graph
from ymprint.data_sources import DataSourceError


def write(path: pathlib.Path, text: str) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text))
    return path


@pytest.fixture
def project(tmp_path):
    """A small ASET-like project: analysis script → beam calcs → utilizations → report."""
    write(tmp_path / "project.ymprint.yml", """
        _data:
          design: 4-design/design.yml
          sections: 1-reference/sections.yml
          geometry: 2-project/geometry.yml
          frame:
            path: build/data/frame.json
            from: 3-analysis/frame.py
          capacities:
            from: 5-validation/beams/calc.yml
          utilizations:
            from: 5-validation/utilizations.py
        _render:
          5-validation/beams/calc.yml:
            for_each: "list(design)"
            as: member_name
            output: build/beams/{{ member_name }}.pdf
        _build:
          documents:
            - 6-documentation/*.yml
    """)
    write(tmp_path / "4-design" / "design.yml", "B01: {section: W310}\nB02: {section: W250}\n")
    write(tmp_path / "1-reference" / "sections.yml", "W310: {Vr: 600}\nW250: {Vr: 450}\n")
    write(tmp_path / "2-project" / "geometry.yml", "B01: {span: 6}\nB02: {span: 8}\n")
    write(tmp_path / "3-analysis" / "frame.py", """
        from ymprint.project import data, publish

        geometry = data("geometry")
        publish("frame", {m: {"Vf": 10 * g["span"]} for m, g in geometry.items()})
    """)
    write(tmp_path / "5-validation" / "beams" / "calc.yml", """
        _vars:
          member_name: B01
        _export:
          Vr: $V_r
        Beam {{ member_name }}:
          - _py:
              echo: false
              source: |
                V_r = sections[design[member_name]["section"]]["Vr"]
          - "Vf = {{ frame[member_name].Vf }}, Vr = {{ V_r }}"
    """)
    write(tmp_path / "5-validation" / "utilizations.py", """
        from ymprint.project import data, publish

        frame, capacities = data("frame"), data("capacities")
        publish("utilizations", [
            {"Member": m, "DCR": round(frame[m]["Vf"] / capacities[m]["Vr"], 3)} for m in sorted(capacities)
        ])
    """)
    write(tmp_path / "6-documentation" / "report.yml", """
        Report:
          - $utilizations
    """)
    return tmp_path


def build(root, *targets, **options):
    lines = []
    summary = Build(Ymprint(), root, report=lines.append, **options).run(list(targets))
    return summary, {r.step.id: r for r in summary.results}


CALC = "5-validation/beams/calc.yml"
FRAME = "3-analysis/frame.py"
UTILS = "5-validation/utilizations.py"
REPORT = "6-documentation/report.yml"


def built(results):
    return sorted(step for step, r in results.items() if r.status == "built")


def test_clean_build_produces_everything_in_a_valid_order(project):
    summary, results = build(project)
    assert summary.ok, [(r.step.id, r.error, r.failures) for r in summary.results]
    order = [r.step.id for r in summary.results]
    assert order.index(FRAME) < order.index(CALC) < order.index(UTILS) < order.index(REPORT)
    assert built(results) == sorted([FRAME, CALC, UTILS, REPORT])
    assert results[CALC].detail == "2 documents"
    assert (project / "build" / "beams" / "B02.pdf").exists()
    assert (project / "6-documentation" / "report.pdf").exists()
    utilizations = json.loads((project / "build" / ".ym" / "exports" / "utilizations" / "5-validation__utilizations.py.json").read_text())
    assert utilizations == [{"Member": "B01", "DCR": 0.1}, {"Member": "B02", "DCR": 0.178}]


def test_a_second_build_does_nothing_and_says_so(project):
    build(project)
    summary, results = build(project)
    assert {r.status for r in results.values()} == {"up-to-date"}
    result = CliRunner().invoke(Ymprint().cli(), ["build", "--project", str(project)])
    assert result.exit_code == 0, result.output
    assert "up to date" in result.output


def test_editing_input_data_rebuilds_what_reads_it(project):
    build(project)
    write(project / "2-project" / "geometry.yml", "B01: {span: 6}\nB02: {span: 9}\n")
    summary, results = build(project)
    assert built(results) == sorted([FRAME, CALC, UTILS, REPORT])
    assert "2-project/geometry.yml changed" in results[FRAME].reasons
    assert results[UTILS].reasons == ["frame changed"]


def test_editing_a_template_without_changing_its_exports_rebuilds_only_it(project):
    build(project)
    calc = project / CALC
    calc.write_text(calc.read_text().replace("Vf = ", "Shear Vf = "))
    _, results = build(project)
    assert built(results) == [CALC]
    assert results[CALC].reasons == ["source changed"]


def test_editing_a_template_that_changes_its_exports_rebuilds_downstream(project):
    build(project)
    calc = project / CALC
    calc.write_text(calc.read_text().replace('["Vr"]', '["Vr"] * 0.9'))
    _, results = build(project)
    assert built(results) == sorted([CALC, UTILS, REPORT])


def test_unrelated_data_does_not_rebuild_anything(project):
    build(project)
    write(project / "1-reference" / "unused.yml", "x: 1\n")
    _, results = build(project)
    assert built(results) == []


def test_a_missing_output_is_rebuilt(project):
    build(project)
    (project / "build" / "beams" / "B01.pdf").unlink()
    _, results = build(project)
    assert built(results) == [CALC]
    assert "build/beams/B01.pdf missing" in results[CALC].reasons


def test_all_rebuilds_everything(project):
    build(project)
    _, results = build(project, force=True)
    assert built(results) == sorted([FRAME, CALC, UTILS, REPORT])


def test_a_target_builds_only_what_it_needs(project):
    _, results = build(project, project / UTILS)
    assert built(results) == sorted([FRAME, CALC, UTILS])
    assert not (project / "6-documentation" / "report.pdf").exists()


def test_dry_run_plans_without_building(project):
    _, results = build(project, dry_run=True)
    assert {r.status for r in results.values()} == {"planned"}
    assert not (project / "build").exists()

    build(project)
    write(project / "2-project" / "geometry.yml", "B01: {span: 7}\nB02: {span: 8}\n")
    _, results = build(project, dry_run=True)
    assert results[FRAME].reasons == ["2-project/geometry.yml changed"]
    assert "frame may change (3-analysis/frame.py is stale)" in results[UTILS].reasons
    # A dry run can't know whether a producer's output will change, so it says so.
    assert results[REPORT].reasons == ["utilizations may change (5-validation/utilizations.py is stale)"]


def test_a_failing_step_fails_the_steps_that_need_it(project):
    write(project / FRAME, "raise ValueError('model did not converge')\n")
    summary, results = build(project)
    assert not summary.ok
    assert results[FRAME].status == "failed"
    assert "did not converge" in str(results[FRAME].error)
    assert results[CALC].status == "failed"
    assert any("frame.py failed" in line for line in results[CALC].failures)

    result = CliRunner().invoke(Ymprint().cli(), ["build", "--project", str(project)], terminal_width=300)
    assert result.exit_code == 1
    assert "did not converge" in result.output


def test_a_glob_matching_nothing_fails_loudly(project):
    config = project / "project.ymprint.yml"
    config.write_text(config.read_text().replace("6-documentation/*.yml", "7-missing/*.yml"))
    with pytest.raises(BuildError, match="'7-missing/\\*.yml' .* matches no files"):
        Build(Ymprint(), project)


def test_a_missing_producer_fails_loudly(project):
    (project / FRAME).unlink()
    with pytest.raises(BuildError, match="names producer 3-analysis/frame.py, which does not exist"):
        Build(Ymprint(), project)


def test_a_cycle_is_reported(tmp_path):
    write(tmp_path / "p.ymprint.yml", """
        _data:
          x: {from: a.py}
          y: {from: b.py}
    """)
    write(tmp_path / "a.py", "from ymprint.project import data, publish\npublish('x', data('y'))\n")
    write(tmp_path / "b.py", "from ymprint.project import data, publish\npublish('y', data('x'))\n")
    summary, results = build(tmp_path)
    assert not summary.ok
    assert "Dependency cycle: a.py → b.py → a.py" in str(results["a.py"].error) + str(results["b.py"].error)


def test_graph(project):
    build(project)
    app_build = Build(Ymprint(), project)
    text = format_graph(app_build)
    assert "capacities ← 5-validation/beams/calc.yml" in text
    assert f"{UTILS}  reads: capacities, frame" in text
    dot = format_graph(app_build, "dot")
    assert f'"{CALC}" -> "capacities";' in dot and f'"capacities" -> "{UTILS}";' in dot
    assert format_graph(app_build, "mermaid").startswith("flowchart LR")
    result = CliRunner().invoke(Ymprint().cli(), ["graph", "--project", str(project), "--format", "dot"])
    assert result.exit_code == 0 and "digraph" in result.output


def test_cli_build_prints_each_step(project):
    result = CliRunner().invoke(Ymprint().cli(), ["build", "--project", str(project)], terminal_width=300)
    assert result.exit_code == 0, result.output
    assert f"✓ {CALC}" in result.output and "2 documents" in result.output
    assert "Built 4 of 4 steps" in result.output
    result = CliRunner().invoke(Ymprint().cli(), ["build", "--project", str(project), "--dry-run"], terminal_width=300)
    assert "Nothing to do" in result.output


def test_publish_requires_the_caller_to_be_a_producer(project):
    import runpy

    rogue = write(project / "3-analysis" / "rogue.py", "from ymprint.project import publish\npublish('frame', {})\n")
    with pytest.raises(DataSourceError, match="rogue.py cannot publish 'frame'.*3-analysis/frame.py"):
        runpy.run_path(str(rogue), run_name="__main__")


def test_scripts_can_run_standalone(project):
    import runpy

    runpy.run_path(str(project / FRAME), run_name="__main__")
    assert json.loads((project / "build" / "data" / "frame.json").read_text()) == {
        "B01": {"Vf": 60}, "B02": {"Vf": 80},
    }


def test_a_first_build_finds_the_order_by_running(project):
    # Building only the report: it reads utilizations, whose script reads frame
    # and capacities, so their producers run first though nothing is recorded.
    summary, _ = build(project, project / REPORT)
    assert [r.step.id for r in summary.results] == [FRAME, CALC, UTILS, REPORT]
    assert summary.ok
