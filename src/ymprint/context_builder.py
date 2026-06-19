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
    # inline_styles = {} if "_style" not in content_yaml else content_yaml.pop("_style")
    report_styles = ReportStyles.model_validate(text_styles_yaml['_style'])
    stylesheet = report_styles.build()
    # inline_doctemplate = {} if "_doc" not in content_yaml else content_yaml.pop("_doc")
    # This is not an appropriate merge. Need the nested chain map.
    combined_doctemplate = doctemplate_yaml['_doc']# | inline_doctemplate
    doctemplate = DocConfig.model_validate(combined_doctemplate)
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
            "yaml": {"_doc": combined_doctemplate},
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
            "all_pages": {
                "anchor": doctemplate.page_anchor('all'),
                "width": doctemplate.available_width('all'),
                "height": doctemplate.available_height('all'),
            }
        },
        "source_path": source_path,
        "destination_path": destination_path,
    }
    return context