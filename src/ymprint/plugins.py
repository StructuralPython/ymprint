"""
Plugin discovery. A package extends ymprint in two ways.

Data loaders and export serializers: name a setup function under the
`ymprint.plugins` entry-point group:

    [project.entry-points."ymprint.plugins"]
    units = "my_package.ymprint_plugin:setup"

Each setup function is called once, with no arguments, the first time ymprint
needs a loader or serializer, and registers what it provides, e.g. with
ymprint.data_sources.register_loader.

Blocks: name each block's converter under the `ymprint.blocks` entry-point
group, with the block code as the entry's name:

    [project.entry-points."ymprint.blocks"]
    _beam = "my_package.blocks:beam_block"

Every application with `plugin_blocks=True` (the default, `ym` included) can
then render `_beam` blocks. A plugin block never replaces a block the
application already has. Its module is imported the first time a document uses
the block, so installed plugins cost nothing for documents that don't.
"""
from __future__ import annotations

import warnings
from importlib.metadata import EntryPoint, entry_points
from typing import Any, Optional

from .blocks.registry import BLOCK_CODE_PATTERN, RESERVED_CODES, BlockConverter

ENTRY_POINT_GROUP = "ymprint.plugins"
BLOCKS_ENTRY_POINT_GROUP = "ymprint.blocks"

_loaded = False
_plugin_blocks: Optional[dict[str, BlockConverter]] = None


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
    """Returns {distribution name: version} for every installed plugin, blocks included."""
    versions = {}
    for group in (ENTRY_POINT_GROUP, BLOCKS_ENTRY_POINT_GROUP):
        for entry_point in entry_points(group=group):
            dist = entry_point.dist
            if dist is not None:
                versions[dist.name] = dist.version
    return versions


def plugin_blocks() -> dict[str, BlockConverter]:
    """
    Returns {block code: converter} for every block installed under the
    `ymprint.blocks` entry-point group, read once per process.

    An entry's name is its block code; the leading underscore may be left out
    (`beam` is `_beam`). Entries with invalid or reserved codes are skipped
    with a warning. When two packages provide the same code, the first by
    distribution name is used, with a warning.
    """
    global _plugin_blocks
    if _plugin_blocks is None:
        _plugin_blocks = _discover_blocks(entry_points(group=BLOCKS_ENTRY_POINT_GROUP))
    return dict(_plugin_blocks)


def _discover_blocks(found) -> dict[str, BlockConverter]:
    blocks: dict[str, BlockConverter] = {}
    owners: dict[str, str] = {}
    for entry_point in sorted(found, key=lambda ep: (_dist_name(ep), ep.name)):
        code = entry_point.name if entry_point.name.startswith("_") else f"_{entry_point.name}"
        owner = _dist_name(entry_point) or entry_point.value
        if not BLOCK_CODE_PATTERN.match(code) or code in RESERVED_CODES:
            warnings.warn(
                f"ymprint block plugin {owner!r} names an invalid block code {code!r}; skipped. "
                "A block code is an underscore followed by letters and digits, and not one of "
                "ymprint's reserved codes."
            )
            continue
        if code in blocks:
            warnings.warn(
                f"ymprint block {code!r} is provided by both {owners[code]!r} and {owner!r}; "
                f"using {owners[code]!r}."
            )
            continue
        blocks[code] = LazyBlock(code, entry_point, owner)
        owners[code] = owner
    return blocks


def _dist_name(entry_point: EntryPoint) -> str:
    dist = getattr(entry_point, "dist", None)
    return dist.name if dist is not None else ""


class LazyBlock:
    """
    A block converter from an installed plugin, imported on its first call. If
    the import fails, every use of the block reports why as a BlockError, and
    other blocks are unaffected.
    """

    def __init__(self, code: str, entry_point: EntryPoint, owner: str):
        self.code = code
        self.entry_point = entry_point
        self.owner = owner
        self._convert: Optional[BlockConverter] = None
        self._error: Optional[str] = None

    def __call__(self, block_key: str, block_value: Any, context: dict) -> list:
        return self.load(block_key)(block_key, block_value, context)

    def load(self, block_key: Optional[str] = None) -> BlockConverter:
        """Returns the plugin's converter, importing it the first time."""
        if self._convert is None and self._error is None:
            try:
                convert = self.entry_point.load()
                if not callable(convert):
                    raise TypeError(f"{self.entry_point.value} is not callable")
                self._convert = convert
            except Exception as exc:
                self._error = f"{type(exc).__name__}: {exc}"
        if self._error is not None:
            from .errors import BlockError

            raise BlockError(
                block_key or self.code,
                f"The {self.code!r} block comes from the plugin {self.owner!r}, which failed "
                f"to load ({self._error}). Reinstall or update {self.owner!r}.",
            )
        return self._convert

    def __repr__(self) -> str:
        return f"LazyBlock({self.code!r}, {self.entry_point.value!r})"
