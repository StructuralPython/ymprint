from io import BytesIO
import pathlib
from .yaml_loader import load_yaml
from .blocks import image_block
from .blocks import admonition_block
from .blocks import quote_block
from .blocks import page_break_block
from .blocks import spacer_block
from .blocks import hrule_block
from .blocks import get_block_callable, list_blocks, convert_blocks
from .config.config_loaders import load_report_config
from .config import ReportStyles, TableStyle, DocConfig
from .context_builder import build_context
from .content_checks import (
    check_for_paragraph,
    check_for_ol,
    check_for_subelements,
    check_for_tables,
    check_for_ul
)
from .content_converters import (
    convert_paragraph,
    convert_table,
    convert_ul,
    convert_ol,
)
from .config.pdf_backgrounds import overlay_pdf_background
from reportlab.platypus import Spacer, NextPageTemplate
from reportlab.lib.units import mm

from rich import print


TYP_SPACER = Spacer(1, 4 * mm)


def load_report(source_yaml: str | pathlib.Path, destination_pdf: str | pathlib.Path, report_config_path: str | pathlib.Path) -> None:
    """
    Converts the report at yaml_path into a PDF.
    """
    source_path = pathlib.Path(source_yaml).resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"The source YAML file at {str(source_path)} does not exist")
    source_data = load_yaml(source_path)
    # source_config = extract_source_config(source_data)
    source_config = {}
    # This should not return RL objects as each of these can build their own RL objects
    textstyles, tablestyles, doc_data = load_report_config(source_config, report_config_path)
    doctemplate = DocConfig.model_validate(doc_data['_doc'])
    document_vars = extract_vars(source_data)

    context = build_context(
        source_data, 
        textstyles, 
        doc_data, 
        tablestyles, 
        document_vars, 
        source_yaml, 
        destination_pdf
    )

    story = build_story(source_data, context)
    if context['doctemplate']['yaml']['_doc'].get('first-page') is not None:
        story = [NextPageTemplate(1)] + story
    rl_doc = doctemplate.build(destination_pdf)
    rl_report_buffer = BytesIO()
    rl_doc.build(story, filename=rl_report_buffer)
    rl_report_buffer.seek(0)
    source_parent = source_path.parent
    first_page_background = context['doctemplate']['yaml']['_doc']['first-page'].get('background', None)
    if first_page_background is not None:
        first_page_background = source_parent / first_page_background
    overlay_pdf_background(
        rl_report_buffer, 
        source_parent / context['doctemplate']['yaml']['_doc']['background'], 
        pathlib.Path(destination_pdf),
        context
        first_page_background,
    )


def build_story(source_data: dict | list, context: dict, level: int = 1) -> list:
    """
    Returns a list of Flowables generated from 'source_data' and 'context'
    """
    story = []
    if isinstance(source_data, dict):
        source_iter = source_data.items()
    elif isinstance(source_data, list):
        source_iter = iter(source_data)
    registered_blocks = list_blocks()

    for elem in source_iter:
        if isinstance(elem, tuple):
            k, v = elem
        else:
            k = None
            v = elem

        if k is not None:
            if str(k).startswith(tuple(registered_blocks)):
                story.extend(convert_blocks(k, v, context))
                continue
            else:
                heading_style_name = f"h{level}"
                heading = convert_paragraph(k, context, heading_style_name)
                story.extend(heading)

        if check_for_paragraph(v, context):
            paragraph = convert_paragraph(v,context)
            story.extend(paragraph)
            # story.append(TYP_SPACER)
        elif check_for_ul(v, context):
            ul = convert_ul(v,context)
            story.extend(ul)
            # story.append(TYP_SPACER)
        elif check_for_ol(v, context):
            ol = convert_ol(v,context)
            story.extend(ol)
            # story.append(TYP_SPACER)
        elif check_for_tables(v, context):
            table = convert_table(v,context)
            story.extend(table)
            # story.append(TYP_SPACER)
        elif check_for_subelements(v, context):
            story.extend(build_story(v, context, level = level + 1))
            # story.append(TYP_SPACER)
            continue
        else:
            continue
    return story



def extract_vars(source_data: dict) -> dict:
    return {}