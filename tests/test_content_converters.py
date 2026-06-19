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
        pathlib.Path.cwd()
    )
    return context

def test_convert_paragraph(report_ex1, default_context):
    data = report_ex1
    assert con.convert_paragraph(data['title']['first topic'], default_context)
    assert con.convert_paragraph(data['title']['fourth topic']['first sub topic'], default_context)

def test_convert_ul(report_ex1, default_context):
    data = report_ex1
    assert con.convert_ul(data['title']['second topic'], default_context)

def test_convert_ol(report_ex1, default_context):
    data = report_ex1
    assert con.convert_ol(data['title']['third topic'][2]['subheading'], default_context)

def test_convert_table(report_ex1, default_context):
    data = report_ex1
    assert con.convert_table(data['title']['fifth topic'], default_context)
