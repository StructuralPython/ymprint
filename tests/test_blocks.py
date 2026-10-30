from ymprint.blocks import retrieve_block_variables
from ymprint.exceptions import YMPrintSyntaxException
import pytest

def test_retrieve_block_variables():

    var_bank = {"var_data": 1, "var_data_2": 3.24, "var_data_3": ("Python", "Tuple")}

    good_data = {
        "title": [
            "Paragraph text",
            {
                "_block": "$var_data"
            },
            {
                "_otherblock": {
                    "param": "$var_data_2"
                }
            },
            {
                "_thirdblock": [
                    "some text", "$var_data_3"
                ]
            }
        ]
    }

    assert retrieve_block_variables(good_data, {"vars": var_bank}) == {
        "title": [
            "Paragraph text",
            {
                "_block": 1
            },
            {
                "_otherblock": {
                    "param": 3.24
                }
            },
            {
                "_thirdblock": [
                    "some text", ("Python", "Tuple")
                ]
            }
        ]
    }

def test_loadjson_without_namespace_merges_into_vars(tmp_path):
    import json
    import pathlib
    from ymprint.blocks import convert_blocks
    from ymprint.config.config_loaders import load_report_config
    from ymprint.context_builder import build_context

    (tmp_path / "data.json").write_text(json.dumps({"span": 6.0}))
    styles, tbl, doc = load_report_config()
    ctx = build_context(
        {}, styles, doc, tbl, {"existing": 1},
        tmp_path / "report.yml", tmp_path / "report.pdf", None,
    )
    convert_blocks("_loadjson", {"path": "data.json"}, ctx)
    assert ctx["vars"] == {"existing": 1, "span": 6.0}


def _dump_context(tmp_path, document_vars):
    from ymprint.config.config_loaders import load_report_config
    from ymprint.context_builder import build_context

    styles, tbl, doc = load_report_config()
    return build_context(
        {}, styles, doc, tbl, document_vars,
        tmp_path / "report.yml", tmp_path / "report.pdf", None,
    )


def test_dumpjson_writes_named_and_dotted_vars(tmp_path):
    import json
    from ymprint.blocks import convert_blocks

    beam = {"span": 6.0, "load": 12}
    ctx = _dump_context(tmp_path, {"beam": beam, "phi": 0.9, "other": 1})
    convert_blocks("_dumpjson", {"path": "out/vals.json", "vars": ["beam.span", "phi"]}, ctx)
    assert json.loads((tmp_path / "out" / "vals.json").read_text()) == {"beam": {"span": 6.0}, "phi": 0.9}
    assert beam == {"span": 6.0, "load": 12}


def test_dumpjson_namespace_round_trips_with_loadjson(tmp_path):
    from ymprint.blocks import convert_blocks

    ctx = _dump_context(tmp_path, {"beam": {"span": 6.0, "load": 12}, "name": "B01"})
    convert_blocks("_dumpjson", {"path": "{{ name }}.json", "namespace": "beam", "vars": ["span", "load"]}, ctx)
    convert_blocks("_loadjson", {"path": "B01.json", "namespace": "copy"}, ctx)
    assert ctx["vars"]["copy"] == {"span": 6.0, "load": 12}


def test_dumpjson_leaves_an_unchanged_file_alone(tmp_path):
    import os
    from ymprint.blocks import convert_blocks

    ctx = _dump_context(tmp_path, {"a": 1})
    convert_blocks("_dumpjson", {"path": "a.json", "vars": ["a"]}, ctx)
    out = tmp_path / "a.json"
    os.utime(out, (0, 0))
    convert_blocks("_dumpjson", {"path": "a.json", "vars": ["a"]}, ctx)
    assert out.stat().st_mtime == 0
    ctx["vars"]["a"] = 2
    convert_blocks("_dumpjson", {"path": "a.json", "vars": ["a"]}, ctx)
    assert out.stat().st_mtime != 0


@pytest.mark.parametrize("value, message", [
    ({"path": "x.json", "vars": ["missing"]}, "no variable 'missing'"),
    ({"path": "x.json", "vars": ["beam.depth"]}, "no variable 'beam.depth'"),
    ({"path": "x.json", "vars": ["beam", "beam.span"]}, "overlaps"),
    ({"path": "x.json", "vars": ["beam.span", "beam"]}, "overlaps"),
    ({"path": "x.json", "vars": ["obj"]}, "could not write"),
    ({"path": "x.json"}, "needs a `path`"),
])
def test_dumpjson_errors(tmp_path, value, message):
    from ymprint.blocks import convert_blocks

    ctx = _dump_context(tmp_path, {"beam": {"span": 6.0}, "obj": object()})
    with pytest.raises(Exception, match=message):
        convert_blocks("_dumpjson", value, ctx)
    assert not (tmp_path / "x.json").exists()
