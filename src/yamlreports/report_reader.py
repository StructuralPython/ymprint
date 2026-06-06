import pathlib
from .yaml_loader import load_yaml
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
from reportlab.platypus import Spacer
from reportlab.lib.units import mm

TYP_SPACER = Spacer(1, 4 * mm)


def load_report(source_yaml: str | pathlib.Path, destination_pdf: str | pathlib.Path, report_config_path: str | pathlib.Path) -> None:
    """
    Converts the report at yaml_path into a PDF.
    """
    source_data = load_yaml(source_yaml)
    # This should not return RL objects as each of these can build their own RL objects
    textstyles, tablestyles, doc_data = load_report_config(source_data, report_config_path)
    doctemplate = DocConfig.model_validate(doc_data)
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
    rl_doc = doctemplate.build(destination_pdf)
    rl_doc.build(story)


def build_story(source_data: dict | list, context: dict, level: int = 1) -> list:
    """
    Returns a list of Flowables generated from 'source_data' and 'context'
    """
    story = []
    if isinstance(source_data, dict):
        source_iter = source_data.items()
    elif isinstance(source_data, list):
        source_iter = iter(source_data)

    for elem in source_iter:
        if isinstance(elem, tuple):
            k, v = elem
        else:
            k = None
            v = elem

        if k is not None:
            heading_style_name = f"h{level}"
            heading = convert_paragraph(k, context, heading_style_name)
            story.extend(heading)

        if check_for_subelements(v, context):
            story.extend(build_story(v, context))
            continue
        elif check_for_paragraph(v, context):
            paragraph = convert_paragraph(v,context)
            story.extend(paragraph)
            story.append(TYP_SPACER)
        elif check_for_ul(v, context):
            ul = convert_ul(v,context)
            story.extend(ul)
            story.append(TYP_SPACER)
        elif check_for_ol(v, context):
            ol = convert_ol(v,context)
            story.extend(ol)
            story.append(TYP_SPACER)
        elif check_for_tables(v, context):
            table = convert_table(v,context)
            story.extend(table)
            story.append(TYP_SPACER)
        elif check_for_image(v, context):
            image = parse_image(v, context)
            story.extend(image)
        else:
            continue

    return story

    return [Paragraph("stub")]


def extract_vars(source_data: dict) -> dict:
    return {}