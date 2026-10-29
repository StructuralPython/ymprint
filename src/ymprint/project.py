"""
The project API for scripts: read data sources by name and publish the data a
script produces, with no paths in the script.

    # 3-analysis/frame.py
    from ymprint.project import data, publish

    geometry, loads = data("geometry"), data("loads")
    publish("frame", analyze(geometry, loads))

The project is found from the script's location (the nearest *.ymprint.yml
above it). `publish` writes where the project config's `_data` entry for the
name says, and only a script that the entry names in `from:` may publish it.
Under `ym build`, every `data()` call is recorded as an input of the script.
"""
from __future__ import annotations

import pathlib
import sys
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Optional

from .config.config_loaders import locate_config_file
from .data_sources import DataCatalog, DataSourceError
from .exports import write_json_atomic


@dataclass
class Project:
    """A project: its root (the project config's directory) and config layers."""

    root: pathlib.Path
    config_paths: tuple[pathlib.Path, ...] = field(default_factory=tuple)

    @classmethod
    def find(cls, start: pathlib.Path, extra_layers: tuple[pathlib.Path, ...] = ()) -> "Project":
        """
        Returns the project whose config is the nearest *.ymprint.yml at or
        above 'start'. 'extra_layers' (e.g. an application's own config) sit
        below it.
        """
        start = pathlib.Path(start).resolve()
        config = locate_config_file(start)
        if config is None:
            raise DataSourceError(
                f"No project config (*.ymprint.yml) found at or above {start}."
            )
        return cls(root=config.parent, config_paths=(*extra_layers, config))

    def catalog(self) -> DataCatalog:
        return DataCatalog.from_config(self.config_paths, None, self.root, None, self.root)


# Set by `ym build` while it runs a script: (project, script path).
CURRENT_SCRIPT: ContextVar[Optional[tuple[Project, pathlib.Path]]] = ContextVar(
    "ymprint_current_script", default=None
)


def _caller_file(depth: int) -> Optional[pathlib.Path]:
    frame = sys._getframe(depth + 1)
    filename = frame.f_globals.get("__file__")
    return pathlib.Path(filename).resolve() if filename else None


def _context(depth: int = 2) -> tuple[Project, Optional[pathlib.Path]]:
    current = CURRENT_SCRIPT.get()
    if current is not None:
        return current
    script = _caller_file(depth)
    start = script.parent if script is not None else pathlib.Path.cwd()
    return Project.find(start), script


def data(name: str) -> Any:
    """Returns a fresh copy of data source 'name'."""
    project, _ = _context()
    return project.catalog().load(name)


def path(name: str) -> pathlib.Path:
    """Returns the file data source 'name' is read from, for code that does its own I/O."""
    project, _ = _context()
    return project.catalog().path(name)


def publish(name: str, value: Any) -> pathlib.Path:
    """
    Writes 'value' as data source 'name' (as JSON, atomically) and returns the
    file written. The calling script must be one of the source's producers.
    """
    project, script = _context()
    source = project.catalog().get_source(name)
    if script is None or script not in source.producers:
        producers = ", ".join(str(p.relative_to(project.root)) for p in source.producers) or "none"
        raise DataSourceError(
            f"{script.name if script else 'This code'} cannot publish {name!r}: its `_data` entry "
            f"lists its producers in `from:` (currently: {producers})."
        )
    output = source.output_for(script)
    write_json_atomic(output, value, where=script.name)
    return output
