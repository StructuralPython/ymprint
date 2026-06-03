import pathlib
from .yaml_loader import load_yaml
from .config 
from .config import ReportStyles, TableStyle, DocConfig
from .context_builder import build_context

def load_report(source_yaml: str | pathlib.Path, destination_pdf: str | pathlib.Path, report_config_path: str | pathlib.Path) -> None:
    """
    Converts the report at yaml_path into a PDF.
    """
    source_data = load_yaml(source_yaml)
    # This should not return RL objects as each of these can build their own RL objects
    textstyles, tablestyles, doc_data = load_report_config(source_data, report_config_path)

    styles = ReportStyles.model_validate(textstyles['_style'])
    table_style = TableStyle.model_validate(tablestyles['_tablestyle'])

    # Keys that do not exist in the model are silently passed over (e.g. ['_doc']['first-page']['cat'])
    document = DocConfig.model_validate(doc_data['_doc'])

    document_vars = extract_vars(source_data)

    context = build_context(document_vars, doctemplate, source_yaml, destination_pdf)
    story = build_story(source_data, context)
    rl_doc = doctemplate.build()
    rl_doc.build(story)
