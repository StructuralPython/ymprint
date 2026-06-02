import pathlib
from .yaml_loader import load_yaml

def load_report(source_yaml: str | pathlib.Path, destination_pdf: str | pathlib.Path, report_config: str | pathlib.Path) -> None:
    """
    Converts the report at yaml_path into a PDF.
    """
    source_data = load_yaml(source_yaml)
    stylesheet, tablestylesheet, doctemplate = load_report_config(report_config, destination_pdf)
    # assume first page and subsequent templates are all the same page size. set this up in the config.
    available_width
    story = build_story(source_data, stylesheet, tablestylesheet, available_width)
    rl_doc = doctemplate.build()
    rl_doc.build(story)
