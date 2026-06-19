from ymprint import yaml_loader
from ymprint.report_reader import build_story, load_report
from ymprint.context_builder import build_context
from ymprint.config.config_loaders import load_report_config
import pathlib
import pytest

TEST_DATA = pathlib.Path(__file__).parent / "test-data"

@pytest.fixture
def report_ex1():
    return yaml_loader.load_yaml(TEST_DATA / "report_example_1.yml")

@pytest.fixture
def report_ex2():
    return yaml_loader.load_yaml(TEST_DATA / "report_example_2.yml")

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

def test_load_yaml(report_ex1, report_ex2):
    load_report(TEST_DATA / "report_example_1.yml", TEST_DATA / "example_output1.pdf", TEST_DATA / "example_1_config")
    load_report(TEST_DATA / "report_example_2.yml", TEST_DATA / "example_output2.pdf", TEST_DATA / "example_2_config")
    assert False
