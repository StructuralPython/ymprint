import pathlib
from typing import Mapping, Optional, Sequence

from .app import default_app
from .render import RenderEvent, extract_vars
from .story_builder import build_story

ConfigPath = str | pathlib.Path


def load_report(
    source_yaml: str | pathlib.Path,
    destination_pdf: str | pathlib.Path,
    report_config_path: Optional[ConfigPath | Sequence[ConfigPath]] = None,
    vars: Optional[Mapping] = None,
) -> RenderEvent:
    """
    Converts the report at 'source_yaml' into a PDF with the default app, and
    returns the RenderEvent describing the render.

    Uses exactly the config given by 'report_config_path' (a config file or
    directory, or a sequence of them, lowest priority first); no *.ymprint.yml
    discovery is done. Use Ymprint.render for an app's full config resolution.
    'vars' are layered over the document's `_vars` (they win).
    """
    return default_app.render(
        source_yaml, destination_pdf, report_config_path, discover_config=False, vars=vars
    )
