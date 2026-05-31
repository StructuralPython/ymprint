import pathlib

import yamlreports.config as config
from yamlreports.yaml_loader import load_yaml

TEST_DATA = pathlib.Path(__file__).parent / "test-data"
EX_DOC_CONFIG_PATH = TEST_DATA / "example_doc.yml"
EX_STYLE_CONFIG_PATH = TEST_DATA / "example_style.yml"
EX_TABLE_STYLE_CONFIG_PATH = TEST_DATA / "tablestyle.yml"

def test_load_doc_config():
    data = load_yaml(EX_DOC_CONFIG_PATH)
    config.DocConfig.model_validate(data['_doc'])


def test_load_style_config():
    data = load_yaml(EX_STYLE_CONFIG_PATH)
    config.ReportStyles.model_validate(data['_style'])

def test_load_tablestyle():
    data = load_yaml(EX_TABLE_STYLE_CONFIG_PATH)
    config.TableStyle.model_validate(data['_tablestyle'])

