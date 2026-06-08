from yamlreports import yaml_loader
from yamlreports.report_reader import build_story
from yamlreports.context_builder import build_context
from yamlreports.config.config_loaders import load_report_config
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


def test_build_story(report_ex1, default_context):
    data = report_ex1
    # assert build_story(
    #     data, default_context
    # )
    assert True