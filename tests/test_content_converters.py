from ymprint import yaml_loader
from ymprint import content_converters as con
from ymprint.context_builder import build_context
from ymprint.config.config_loaders import load_report_config
import pathlib
import pytest

TEST_DATA = pathlib.Path(__file__).parent / "test-data"

@pytest.fixture
def report_ex1():
    return yaml_loader.load_yaml(TEST_DATA / "report_example_1.yml")

@pytest.fixture
def default_config():
    return load_report_config()

@pytest.fixture
def default_context(default_config):
    styles, tablestyles, doctemplate = default_config
    context = build_context(
        {},
        styles, 
        doctemplate, 
        tablestyles, 
        {}, 
        pathlib.Path.cwd(), 
        pathlib.Path.cwd(),
        pathlib.Path.cwd()
    )
    return context

def test_convert_paragraph(report_ex1, default_context):
    data = report_ex1
    assert con.convert_paragraph(data['title']['first topic'], default_context)
    assert con.convert_paragraph(data['title']['An actual topic']['first sub topic'], default_context)

def test_convert_ul(default_context):
    items = ["first bullet", "second bullet", ["nested a", "nested b"]]
    assert con.convert_ul(items, default_context)

def test_convert_ol_list(default_context):
    items = ["first", "second", ["nested one", "nested two"]]
    assert con.convert_ol(items, default_context)

def test_convert_ol_mapping_backcompat(default_context):
    items = {1: "first", 2: "second", 3: "third"}
    assert con.convert_ol(items, default_context)

def test_convert_table(report_ex1, default_context):
    data = report_ex1
    assert con.convert_table(data['title']['fifth topic'], default_context)
