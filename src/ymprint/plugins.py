"""
Plugin discovery. A package extends ymprint (data loaders, export serializers)
by naming a setup function under the `ymprint.plugins` entry-point group:

    [project.entry-points."ymprint.plugins"]
    units = "my_package.ymprint_plugin:setup"

Each setup function is called once, with no arguments, the first time ymprint
needs a loader or serializer, and registers what it provides, e.g. with
ymprint.data_sources.register_loader.
"""
from __future__ import annotations

import warnings
from importlib.metadata import entry_points

ENTRY_POINT_GROUP = "ymprint.plugins"

_loaded = False


def load_plugins() -> None:
    """Runs every installed plugin's setup function, once per process."""
    global _loaded
    if _loaded:
        return
    _loaded = True
    for entry_point in entry_points(group=ENTRY_POINT_GROUP):
        try:
            entry_point.load()()
        except Exception as exc:
            # A broken plugin must not stop documents that don't use it.
            warnings.warn(f"ymprint plugin {entry_point.name!r} failed to load: {exc}")


def plugin_versions() -> dict[str, str]:
    """Returns {distribution name: version} for every installed plugin."""
    versions = {}
    for entry_point in entry_points(group=ENTRY_POINT_GROUP):
        dist = entry_point.dist
        if dist is not None:
            versions[dist.name] = dist.version
    return versions
