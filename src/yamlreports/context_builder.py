from collections import ChainMap
import pathlib
from reportlab.lib import pagesizes

def build_context(document_vars: dict, doctemplate: Doc, source_path: str | pathlib.Path, destination_path: str | pathlib.Path) -> ChainMap:
    context = {
        'vars': document_vars['_vars'],
        'doctemplate': doctemplate['_doc'],
        'source': source_path,
        'dest': destination_path,
        'calculated': doctemplate.calculated_values
    }
    return ChainMap(context)