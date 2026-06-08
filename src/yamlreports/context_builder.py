from collections import ChainMap
import pathlib
from reportlab.lib import pagesizes
from .config import ReportStyles, TableStyle, DocConfig

def build_context(
        content_yaml: dict,
        text_styles_yaml: dict, 
        doctemplate_yaml: dict, 
        tablestyles_yaml: dict, 
        document_vars: dict, 
        source_path: str | pathlib.Path, 
        destination_path: str | pathlib.Path
    ) -> dict:
    report_styles = ReportStyles.model_validate(text_styles_yaml['_style'])
    stylesheet = report_styles.build()
    doctemplate = DocConfig.model_validate(doctemplate_yaml['_doc'])
    rl_basedoctemplate = doctemplate.build(destination_path)
    report_tablestyles = TableStyle.model_validate(tablestyles_yaml['_tablestyle'])
    tablestyles = report_tablestyles.build()
    context = {
        "content": content_yaml,
        "styles": {
            "yaml": text_styles_yaml,
            "ymprint": report_styles,
            "rl": {
                "_style": stylesheet
            },
        },
        "doctemplate": {
            "yaml": doctemplate_yaml,
            "ymprint": doctemplate,
            "rl": {
                "_doc": rl_basedoctemplate,
            },
        },
        "tablestyles": {
            'yaml': tablestyles_yaml,
            "ymprint": report_tablestyles,
            "rl": {
                "_tablestyle": tablestyles
            },
        },
        "vars": document_vars,
        "page_dims": doctemplate.page_dims,
        "frames": {
            "first_page": {
                "anchor": doctemplate.page_anchor('first'),
                "width": doctemplate.available_width('first'),
                "height": doctemplate.available_height('first'),
            },
            "other_pages": {
                "anchor": doctemplate.page_anchor('others'),
                "width": doctemplate.available_width('others'),
                "height": doctemplate.available_height('others'),
            }
        },
        "source_path": source_path,
        "destination_path": destination_path,
    }
    return context