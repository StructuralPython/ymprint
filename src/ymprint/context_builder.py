from collections import ChainMap
import pathlib
from reportlab.lib import pagesizes
from typing import Optional
from .config import ReportStyles, TableStyle, DocConfig
from .blocks.registry import BlockRegistry

def build_context(
        content_yaml: dict,
        text_styles_yaml: dict, 
        doctemplate_yaml: dict, 
        tablestyles_yaml: dict, 
        document_vars: dict, 
        source_path: str | pathlib.Path, 
        destination_path: str | pathlib.Path,
        config_path: str | pathlib.Path,
        blocks: Optional[BlockRegistry] = None,
        base_dir: Optional[str | pathlib.Path] = None,
    ) -> dict:
    """
    Returns the render context. 'base_dir' is the directory that relative paths in
    the document (images, JSON, `relative-to: source` backgrounds) resolve against;
    it defaults to the source file's directory. 'source_path' is None when the
    document was supplied as data rather than read from a file.
    """
    if base_dir is None:
        base_dir = pathlib.Path(source_path).parent if source_path is not None else pathlib.Path.cwd()
    # inline_styles = {} if "_style" not in content_yaml else content_yaml.pop("_style")
    report_styles = ReportStyles.model_validate(text_styles_yaml['_style'])
    families = report_styles.build_families()
    stylesheet = families['default'][1]
    # inline_doctemplate = {} if "_doc" not in content_yaml else content_yaml.pop("_doc")
    # This is not an appropriate merge. Need the nested chain map.
    combined_doctemplate = doctemplate_yaml# | inline_doctemplate
    doctemplate = DocConfig.model_validate(combined_doctemplate['_doc'])
    rl_basedoctemplate, _ = doctemplate.build(destination_path)
    report_tablestyles = TableStyle.model_validate(tablestyles_yaml['_tablestyle'])
    tablestyles = report_tablestyles.build()
    context = {
        "content": content_yaml,
        "styles": {
            "yaml": text_styles_yaml,
            "ymprint": report_styles,
            "families": {
                name: {"ymprint": family, "rl": sheet}
                for name, (family, sheet) in families.items()
            },
            "rl": {
                "_style": stylesheet
            },
        },
        "doctemplate": {
            "yaml": combined_doctemplate,
            "ymprint": doctemplate,
            "rl": {
                "_doc": rl_basedoctemplate,
            },
        },
        "tablestyles": {
            'yaml': {"_tablestyle": tablestyles_yaml},
            "ymprint": report_tablestyles,
            "rl": {
                "_tablestyle": tablestyles
            },
        },
        "vars": document_vars,
        "page_dims": doctemplate.page_dims,
        "frames": {
            **{
                name: {
                    "anchor": doctemplate.page_anchor(name),
                    "width": doctemplate.available_width(name),
                    "height": doctemplate.available_height(name),
                }
                for name in doctemplate.template_names
            },
            # Conservative frame used by blocks to size flowables that could land
            # on any page: the smallest content box across all templates.
            "all_pages": {
                "anchor": doctemplate.page_anchor(doctemplate.template_names[0]),
                "width": doctemplate.min_available_width(),
                "height": doctemplate.min_available_height(),
            },
        },
        "source_path": source_path,
        "config_path": config_path,
        "destination_path": destination_path,
        "base_dir": pathlib.Path(base_dir),
        "blocks": blocks if blocks is not None else _builtin_blocks(),
    }
    return context


def _builtin_blocks() -> BlockRegistry:
    # Imported lazily: the block modules import from ymprint.blocks, which must
    # finish initializing first.
    from .blocks.builtin import BUILTIN_BLOCKS
    return BUILTIN_BLOCKS
