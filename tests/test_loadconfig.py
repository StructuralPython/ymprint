import pathlib

import yamlreports.config as config
from yamlreports.yaml_loader import load_yaml
from yamlreports.config.config_loaders import load_report_config

TEST_DATA = pathlib.Path(__file__).parent / "test-data"
EX_DOC_CONFIG_PATH = TEST_DATA / "doctemplate.yml"
EX_STYLE_CONFIG_PATH = TEST_DATA / "textstyles.yml"
EX_TABLE_STYLE_CONFIG_PATH = TEST_DATA / "tablestyles.yml"

def test_load_report_config():
    source_data = {
        "_style": {
            "body": {
                "font": "goofs",
                "color": "blue",
            },
            "headers": {
                "font": "bigs",
                "color": "yellow",
                "size": 12
            }
        }
    }
    styles, tablestyles, doc = load_report_config(
        source_data, TEST_DATA
    )
    assert styles['_style']['body']['font'] == 'goofs'
    assert styles['_style']['body']['size'] == 10 # from config dir
    assert styles['_style']['body']['spacing'] == 14 # from default config

    assert tablestyles['_tablestyle']['cell-padding']['top'] == 0.5 # from config dir
    assert tablestyles['_tablestyle']['headers']['text']['bold'] == True # from default config

    assert doc['_doc']['page-size'] == 'letter'
    assert doc['_doc']['first-page']['background'] is None

    # This key is intentionally not included in the model. See next test.
    assert doc['_doc']['first-page']['cat'] == 'here'


def test_load_doc_config():
    source_data = {
        "_style": {
            "body": {
                "font": "goofs",
                "color": "blue",
            },
            "headers": {
                "font": "bigs",
                "color": "yellow",
                "size": 12
            }
        }
    }
    styles_data, tablestyles_data, doc_data = load_report_config(source_data, TEST_DATA)
    styles = config.ReportStyles.model_validate(styles_data['_style'])
    table_style = config.TableStyle.model_validate(tablestyles_data['_tablestyle'])

    # Keys that do not exist in the model are silently passed over (e.g. ['_doc']['first-page']['cat'])
    document = config.DocConfig.model_validate(doc_data['_doc'])

    # assert document.first_page.cat

