from collections import ChainMap
import pathlib
from reportlab.lib import pagesizes
from .config import ReportStyles, TableStyle, DocConfig
from .config.helpers import Bundle

def build_context(
        content_yaml: dict,
        text_styles_yaml: Bundle, 
        doctemplate_yaml: Bundle, 
        tablestyles_yaml: Bundle, 
        document_vars: dict, 
        source_path: str | pathlib.Path, 
        destination_path: str | pathlib.Path
    ) -> dict:
    # inline_styles = {} if "_style" not in content_yaml else content_yaml.pop("_style")
    ym_styles = Bundle()
    rl_styles = Bundle()
    for style_name, style in text_styles_yaml.items():
        ym_style = ReportStyles.model_validate(style)
        ym_styles.update({style_name: ym_style})
        rl_styles.update({style_name: ym_style.build()})

    # inline_doctemplate = {} if "_doc" not in content_yaml else content_yaml.pop("_doc")
    # This is not an appropriate merge. Need the nested chain map.
    ym_doctemplates = Bundle()
    rl_doctemplates = Bundle()
    combined_doctemplate = doctemplate_yaml.default# | inline_doctemplate
    doctemplate = DocConfig.model_validate(combined_doctemplate)
    rl_basedoctemplate = doctemplate.build(destination_path)


    report_tablestyles = TableStyle.model_validate(tablestyles_yaml.default)
    tablestyles = report_tablestyles.build()
    context = {
        "content": content_yaml,
        "styles": {
            "yaml": text_styles_yaml,
            "ymprint": ym_styles,
            "rl": rl_styles,
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
            "remaining_pages": {
                "anchor": doctemplate.page_anchor('all'),
                "width": doctemplate.available_width('all'),
                "height": doctemplate.available_height('all'),
            },
            "all_pages": {
                "anchor": doctemplate.page_anchor('all'),
                "width": min(doctemplate.available_width('all'), doctemplate.available_width('first')),
                "height": min(doctemplate.available_height('all'), doctemplate.available_height('first')),
            }
        },
        "source_path": source_path,
        "destination_path": destination_path,
    }
    return context