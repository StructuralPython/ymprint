from yamlreports import context_builder
from yamlreports.config.config_loaders import load_report_config
import pytest
import pathlib

@pytest.fixture
def default_config():
    return load_report_config()

def test_context_builder_executes(default_config):
    styles, tablestyles, doctemplate = default_config
    context = context_builder.build_context(
        {},
        styles, 
        doctemplate, 
        tablestyles, 
        {}, 
        pathlib.Path.cwd(), 
        pathlib.Path.cwd()
    )
    assert context['styles']['rl']['_style']['body']
