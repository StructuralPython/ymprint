"""Tests for tables from `$var` data and the `_table` block."""
import pathlib
import textwrap

import pymupdf as mu
import pytest

from ymprint import Ymprint
from ymprint.errors import YmprintAuthoringError

ROWS = """
  - _py:
      echo: false
      source: |
        rows = [
            {"Member": "B01", "DCR": 0.52},
            {"Member": "B02", "DCR": 1.07},
            {"Member": "B03", "DCR": 0.93},
        ]
"""


def render(tmp_path: pathlib.Path, source: str) -> mu.Document:
    src = tmp_path / "doc.yml"
    src.write_text(textwrap.dedent(source))
    dest = tmp_path / "doc.pdf"
    Ymprint().render(src, dest, discover_config=False)
    return mu.open(dest)


def lines(doc: mu.Document) -> list[str]:
    return [line for page in doc for line in page.get_text().splitlines() if line.strip()]


def fills(doc: mu.Document) -> list[tuple]:
    """The fill colours of the rectangles drawn on the first page, as (r, g, b) 0-255."""
    return [
        tuple(round(c * 255) for c in d["fill"])
        for d in doc[0].get_drawings()
        if d.get("fill") is not None
    ]


def test_var_with_rows_renders_like_the_literal_table(tmp_path):
    computed = lines(render(tmp_path, "Summary:\n" + ROWS + "  - $rows\n"))
    literal = lines(render(tmp_path, """
        Summary:
          - - Member: B01
              DCR: 0.52
            - Member: B02
              DCR: 1.07
            - Member: B03
              DCR: 0.93
    """))
    assert computed == literal
    assert computed[-6:] == ["B01", "0.52", "B02", "1.07", "B03", "0.93"]


def test_var_table_cells_are_not_templates(tmp_path):
    doc = render(tmp_path, """
        _vars:
          secret: leaked
        Summary:
          - _py:
              echo: false
              source: |
                rows = [{"Note": "{{ secret }}"}]
          - $rows
    """)
    assert "{{ secret }}" in lines(doc)


def test_var_that_is_not_a_table_is_an_error_naming_its_type(tmp_path):
    with pytest.raises(YmprintAuthoringError, match=r"\$n is a int"):
        render(tmp_path, "_vars:\n  n: 3\nSummary:\n  - $n\n")


def test_undefined_var_is_an_error(tmp_path):
    with pytest.raises(YmprintAuthoringError, match="no variable 'nope'"):
        render(tmp_path, "Summary:\n  - $nope\n")


def test_var_table_from_a_data_source(tmp_path):
    (tmp_path / "loads.yml").write_text("- {Case: D, w: 2.5}\n- {Case: L, w: 4.0}\n")
    doc = render(tmp_path, "_data:\n  loads: loads.yml\nLoads:\n  - $loads\n")
    assert lines(doc)[-6:] == ["Case", "w", "D", "2.5", "L", "4.0"]


def test_table_block_columns_headers_format_and_sort(tmp_path):
    doc = render(tmp_path, "Summary:\n" + ROWS + """
          - _table:
              data: $rows
              columns: [Member, DCR]
              headers: {DCR: "D/C"}
              format: {DCR: "{:.1f}"}
              sort: [-DCR]
              caption: "Table 1: utilizations"
    """.replace("\n          ", "\n  "))
    assert lines(doc)[-9:] == [
        "Member", "D/C", "B02", "1.1", "B03", "0.9", "B01", "0.5", "Table 1: utilizations",
    ]


def test_table_block_data_by_name(tmp_path):
    (tmp_path / "loads.yml").write_text("- {Case: D, w: 2.5}\n- {Case: L, w: 4.0}\n")
    doc = render(tmp_path, """
        _data:
          loads: loads.yml
        Loads:
          - _table:
              data: loads
              columns: [w]
    """)
    assert lines(doc)[-3:] == ["w", "2.5", "4.0"]


def test_table_block_row_style_shades_rows(tmp_path):
    doc = render(tmp_path, "Summary:\n" + ROWS + """
          - _table:
              data: $rows
              row_style: "{{ 'danger' if row.DCR > 1.0 else ('warning' if row.DCR > 0.9 else '') }}"
    """.replace("\n          ", "\n  "))
    colours = fills(doc)
    assert (0xF8, 0xD7, 0xDA) in colours   # danger: B02
    assert (0xFF, 0xF3, 0xCD) in colours   # warning: B03


def test_row_styles_from_config_add_to_the_defaults(tmp_path):
    doc = render(tmp_path, """
        _tablestyle:
          body:
            rows:
              styles:
                ok: "#00ff00"
        Summary:
          - _table:
              data: [{a: 1}, {a: 2}]
              row_style: "{{ 'ok' if row.a == 1 else 'danger' }}"
    """)
    colours = fills(doc)
    assert (0, 255, 0) in colours and (0xF8, 0xD7, 0xDA) in colours


@pytest.mark.parametrize("table, message", [
    ("{columns: [a]}", "needs a 'data:'"),
    ("{data: $nope}", "no variable or data source named 'nope'"),
    ("{data: 5}", "must be a list of mappings"),
    ("{data: [{a: 1}], colour: red}", "unknown option"),
    ("{data: [{a: 1}], format: {b: '{:.1f}'}}", "unknown column"),
    ("{data: [{a: 1}, {b: 2}], sort: [a]}", "cannot sort by 'a'"),
    ("{data: [{a: 1}], row_style: purple}", "row style 'purple' is not defined"),
])
def test_table_block_errors(tmp_path, table, message):
    with pytest.raises(YmprintAuthoringError, match=message):
        render(tmp_path, f"T:\n  - _table: {table}\n")
