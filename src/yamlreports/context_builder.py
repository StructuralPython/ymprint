from collections import ChainMap
import pathlib
from reportlab.lib import pagesizes

def build_context(
        text_styles_yaml: dict, 
        doctemplate_yaml: dict, 
        tablestyles_yaml: dict, 
        document_vars: dict, 
        source_path: str | pathlib.Path, 
        destination_path: str | pathlib.Path
    ) -> dict:
    context = {
        "styles": {
            "yaml": text_styles_yaml,
            "rl": {
                "_style": ...
            },
        },
        "doctemplate": {
            "yaml": doctemplate_yaml,
            "rl": {
                "_doc": ...
            },
        },
        "tablestyles": {
            'yaml': tablestyles_yaml,
            "rl": {
                "_tablestyle": ...
            },
        },
        "vars": document_vars,
        "page_dims": [..., ...],
        "frames": {
            "first_page": {
                "anchor": [..., ...],
                "width": ...,
                "height": ...,
            },
            "other_pages": {
                "anchor": [..., ...],
                "width": ...,
                "height": ...,
            }
        },
        "source_path": source_path,
        "destination_path": destination_path,
    }
    return context