import pathlib
from typing import Optional, Sequence

from .app import default_app
from .render import extract_vars
from .story_builder import build_story

ConfigPath = str | pathlib.Path


def load_report(
    source_yaml: str | pathlib.Path,
    destination_pdf: str | pathlib.Path,
    report_config_path: Optional[ConfigPath | Sequence[ConfigPath]] = None,
) -> None:
    """
    Converts the report at 'source_yaml' into a PDF with the default app.

    Uses exactly the config given by 'report_config_path' (a config file or
    directory, or a sequence of them, lowest priority first); no *.ymprint.yml
    discovery is done. Use Ymprint.render for an app's full config resolution.
    """
    default_app.render(source_yaml, destination_pdf, report_config_path, discover_config=False)
