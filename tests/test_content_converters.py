from yamlreports import yaml_loader
from yamlreports import content_converters as con
import pathlib
import pytest

TEST_DATA = pathlib.Path(__file__).parent / "test-data"

@pytest.fixture
def report_ex1():
    return yaml_loader.load_yaml(TEST_DATA / "report_example_1.yml")

def test_convert_paragraph(report_ex1):
    data = report_ex1

def test_convert_subsections(report_ex1):
    data = report_ex1

def test_convert_ul(report_ex1):
    data = report_ex1

def test_convert_ol(report_ex1):
    data = report_ex1

def test_convert_img(report_ex1):
    data = report_ex1

def test_convert_table(report_ex1):
    data = report_ex1