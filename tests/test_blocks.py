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
