import pathlib
from .yaml_loader import load_yaml
from .context_builder import build_context

def load_report(source_yaml: str | pathlib.Path, destination_pdf: str | pathlib.Path, report_config: str | pathlib.Path) -> None:
    """
    Converts the report at yaml_path into a PDF.
    """
    source_data = load_yaml(source_yaml)
    # This should not return RL objects as each of these can build their own RL objects
    stylesheet, tablestylesheet, doctemplate = load_report_config(report_config, destination_pdf)

    context = build_context(source_data, doctemplate, styles, tablestyles)
    story = build_story(source_data, context)
    rl_doc = doctemplate.build()
    rl_doc.build(story)
