"""
Named data sources (`_data`).

A project declares its data once, by name, in the project config or in a
document's front matter:

    _data:
      design: 4-design/design.yml
      frame:
        path: 3-analysis/results/frame.json
        loader: json

Documents then use `design` and `frame` as variables (in Jinja, `_py`, `_hc`
and `$var`) without knowing where the files are. A relative path resolves
against the directory of the file that declares it.

Sources load lazily, on first use, and every read is recorded on the render's
DataCatalog, so a build tool can tell which data a document actually used.
Loaded files are cached for the life of the process by (path, mtime, size);
each render gets its own deep copy, so one document cannot change what the
next one sees.
"""
from __future__ import annotations

import copy
import json
import pathlib
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Optional

from .errors import YmprintAuthoringError
from .plugins import load_plugins
from .yaml_loader import load_yaml

# The variable that gives `_py` and `_hc` code the project paths; see YmContext.
YM_VAR = "ym"


class DataSourceError(YmprintAuthoringError):
    """A `_data` declaration is invalid, or a data source could not be loaded."""


# --- loaders -------------------------------------------------------------------

Loader = Callable[[pathlib.Path], Any]

_LOADERS: dict[str, Loader] = {}
_EXTENSIONS: dict[str, str] = {}


def register_loader(
    name: str,
    loader: Loader,
    *,
    extensions: Iterable[str] = (),
    override: bool = False,
) -> None:
    """
    Registers loader(path) -> data under 'name', for `_data` entries that give
    `loader: <name>`. 'extensions' (e.g. ['.toml']) makes it the default loader
    for files with those suffixes.
    """
    if name in _LOADERS and not override:
        raise ValueError(f"A data loader named {name!r} is already registered.")
    _LOADERS[name] = loader
    for suffix in extensions:
        _EXTENSIONS[suffix.lower()] = name


def _load_json(path: pathlib.Path) -> Any:
    with open(path, encoding="utf-8") as file:
        return json.load(file)


register_loader("yaml", load_yaml, extensions=[".yml", ".yaml"])
register_loader("json", _load_json, extensions=[".json"])


def get_loader(name: str) -> Loader:
    load_plugins()
    try:
        return _LOADERS[name]
    except KeyError:
        raise DataSourceError(
            f"Unknown data loader {name!r}. Available loaders: {sorted(_LOADERS)}"
        ) from None


def loader_for(path: pathlib.Path) -> str:
    """Returns the name of the default loader for 'path', from its extension."""
    load_plugins()
    try:
        return _EXTENSIONS[path.suffix.lower()]
    except KeyError:
        raise DataSourceError(
            f"No loader for {path.name!r}: give the data source a `loader:` "
            f"(one of {sorted(_LOADERS)})."
        ) from None


# (resolved path) -> (mtime_ns, size, loader name, data)
_CACHE: dict[pathlib.Path, tuple[int, int, str, Any]] = {}


def load_file(path: pathlib.Path, loader: Optional[str] = None) -> Any:
    """
    Returns a fresh copy of the data in 'path', read with 'loader' (default: by
    extension). Files are parsed once per process until they change on disk.
    """
    path = pathlib.Path(path).resolve()
    loader = loader or loader_for(path)
    try:
        stat = path.stat()
    except FileNotFoundError:
        raise DataSourceError(f"Data file not found: {path}") from None
    cached = _CACHE.get(path)
    if cached is not None and cached[:3] == (stat.st_mtime_ns, stat.st_size, loader):
        data = cached[3]
    else:
        data = get_loader(loader)(path)
        _CACHE[path] = (stat.st_mtime_ns, stat.st_size, loader, data)
    return copy.deepcopy(data)


def clear_cache() -> None:
    _CACHE.clear()


# --- declarations --------------------------------------------------------------

SOURCE_KEYS = {"path", "loader"}


@dataclass(frozen=True)
class DataSource:
    """One `_data` entry, with its path made absolute."""

    name: str
    # The file whose `_data` declares this source.
    declared_in: Optional[pathlib.Path]
    path: pathlib.Path
    loader: Optional[str] = None

    def files(self) -> tuple[pathlib.Path, ...]:
        """The files this source is read from."""
        return (self.path,)

    def load(self) -> Any:
        return load_file(self.path, self.loader)


def parse_data_declarations(
    declarations: Any,
    base_dir: pathlib.Path,
    declared_in: Optional[pathlib.Path],
) -> dict[str, DataSource]:
    """
    Returns {name: DataSource} for a `_data` mapping, resolving relative paths
    against 'base_dir' (the directory of 'declared_in').
    """
    where = str(declared_in) if declared_in is not None else "the document"
    if declarations is None:
        return {}
    if not isinstance(declarations, Mapping):
        raise DataSourceError(
            f"`_data` in {where} must be a mapping of names to data files, "
            f"not {type(declarations).__name__}."
        )
    sources = {}
    for name, spec in declarations.items():
        if not isinstance(name, str) or not name.isidentifier():
            raise DataSourceError(
                f"`_data` name {name!r} in {where} is not a valid variable name."
            )
        if name == YM_VAR:
            raise DataSourceError(f"`_data` name {YM_VAR!r} in {where} is reserved by ymprint.")
        if isinstance(spec, str):
            spec = {"path": spec}
        if not isinstance(spec, Mapping):
            raise DataSourceError(
                f"`_data` entry {name!r} in {where} must be a path or a mapping "
                f"with a `path`, not {type(spec).__name__}."
            )
        unknown = set(spec) - SOURCE_KEYS
        if unknown:
            raise DataSourceError(
                f"`_data` entry {name!r} in {where} has unknown option(s) "
                f"{sorted(unknown)}. Choose from: {sorted(SOURCE_KEYS)}."
            )
        if not spec.get("path"):
            raise DataSourceError(f"`_data` entry {name!r} in {where} needs a `path`.")
        sources[name] = DataSource(
            name=name,
            declared_in=declared_in,
            path=(base_dir / str(spec["path"])).resolve(),
            loader=spec.get("loader"),
        )
    return sources


def config_file(layer: pathlib.Path) -> Optional[pathlib.Path]:
    """The config file of a config layer (a file, or a directory holding one)."""
    if layer.is_file():
        return layer
    matches = sorted(layer.glob("*.ymprint.yml"))
    return matches[0] if matches else None


def config_declarations(config_paths: Iterable[pathlib.Path], key: str) -> list[tuple[Any, pathlib.Path]]:
    """
    Returns (value, config file) for each config layer that sets 'key', lowest
    priority first.
    """
    found = []
    for layer in config_paths:
        path = config_file(pathlib.Path(layer))
        if path is None:
            continue
        data = load_yaml(path) or {}
        if isinstance(data, Mapping) and data.get(key) is not None:
            found.append((data[key], path.resolve()))
    return found


# --- the catalog a render reads from -------------------------------------------

@dataclass
class DataCatalog:
    """
    The data sources visible to one render, and a record of what it read.

    'reads' maps each source name the render used to the files it was read
    from; 'files' holds files read directly (e.g. by `_loadjson`).
    """

    sources: dict[str, DataSource] = field(default_factory=dict)
    project_root: Optional[pathlib.Path] = None
    reads: dict[str, tuple[pathlib.Path, ...]] = field(default_factory=dict)
    files: set[pathlib.Path] = field(default_factory=set)

    @classmethod
    def from_config(
        cls,
        config_paths: Iterable[pathlib.Path],
        document_data: Any,
        base_dir: pathlib.Path,
        source: Optional[pathlib.Path] = None,
        project_root: Optional[pathlib.Path] = None,
    ) -> "DataCatalog":
        """
        Returns the catalog for a document: the `_data` of each config layer
        (lowest priority first), then the document's own `_data`, each entry
        replacing an earlier one with the same name.
        """
        sources: dict[str, DataSource] = {}
        for declarations, path in config_declarations(config_paths, "_data"):
            sources.update(parse_data_declarations(declarations, path.parent, path))
        sources.update(parse_data_declarations(document_data, base_dir, source))
        return cls(sources=sources, project_root=project_root)

    def __contains__(self, name: object) -> bool:
        return name in self.sources

    def names(self) -> list[str]:
        return list(self.sources)

    def get_source(self, name: str) -> DataSource:
        try:
            return self.sources[name]
        except KeyError:
            raise DataSourceError(
                f"No data source named {name!r}. Declared sources: {sorted(self.sources)}"
            ) from None

    def load(self, name: str) -> Any:
        """Returns a fresh copy of data source 'name', recording the read."""
        source = self.get_source(name)
        data = source.load()
        self.reads[name] = source.files()
        return data

    def path(self, name: str) -> pathlib.Path:
        """Returns the file data source 'name' is read from, recording the read."""
        source = self.get_source(name)
        self.reads[name] = source.files()
        return source.path

    def record_file(self, path: pathlib.Path) -> None:
        self.files.add(pathlib.Path(path).resolve())

    def inputs(self) -> set[pathlib.Path]:
        """Every file this render read data from."""
        found = set(self.files)
        for paths in self.reads.values():
            found.update(paths)
        return found


class DocumentVars(dict):
    """
    The document's variables: a dict that also resolves the names of its data
    sources, loading each one the first time it is looked up.

    It is used as the globals of `_py` and `_hc` code and as the Jinja context,
    so `design["B01"]` and `{{ design.B01 }}` both load `design` on first use.
    Names that are not loaded yet do not appear when the dict is iterated.
    """

    def __init__(self, *args, catalog: Optional[DataCatalog] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.catalog = catalog if catalog is not None else DataCatalog()

    def __missing__(self, key):
        if key in self.catalog:
            value = self.catalog.load(key)
            self[key] = value
            return value
        raise KeyError(key)

    def __contains__(self, key) -> bool:
        return dict.__contains__(self, key) or key in self.catalog

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default


@dataclass(frozen=True)
class YmContext:
    """
    The `ym` variable in `_py` and `_hc` code.

    'project_root': the directory of the project config (the discovered
        *.ymprint.yml), or the document's directory when there is none.
    'source': the document being rendered (None for a document given as data).
    'params': the parameter set of this render (empty unless the document is
        rendered once per parameter set).
    """

    project_root: pathlib.Path
    source: Optional[pathlib.Path]
    params: Mapping = field(default_factory=dict)
    catalog: DataCatalog = field(default_factory=DataCatalog, repr=False)

    def path(self, name: str) -> pathlib.Path:
        """The resolved path of data source 'name', for code that does its own I/O."""
        return self.catalog.path(name)


def build_document_vars(
    document_vars: Mapping,
    runtime_vars: Mapping,
    catalog: DataCatalog,
    ym: YmContext,
    where: str = "the document",
) -> DocumentVars:
    """
    Returns the variables of one render: the document's `_vars`, its data
    sources (loaded on use), `ym`, and 'runtime_vars' (from the API or the
    command line), which take precedence over all of them.

    A `_vars` name that is also a data source name is an error, rather than one
    silently hiding the other.
    """
    clashes = sorted(set(document_vars) & set(catalog.sources))
    if clashes:
        raise DataSourceError(
            f"{where} defines {', '.join(repr(c) for c in clashes)} in `_vars`, "
            f"which is also a `_data` source name. Rename one of them."
        )
    if YM_VAR in document_vars:
        raise DataSourceError(f"`_vars` in {where} uses the reserved name {YM_VAR!r}.")
    variables = DocumentVars(document_vars, catalog=catalog)
    variables[YM_VAR] = ym
    variables.update(runtime_vars)
    return variables
