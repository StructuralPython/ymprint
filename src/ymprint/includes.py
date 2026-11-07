"""
`_include`: build a partial document in place.

A partial is a YAML content file, stored anywhere, that may begin with `_data`
(files it uses, relative to the partial) and `_vars` (defaults for its
parameters). Content without a heading of its own goes under `_content` when
there is front matter (YAML can't follow a mapping with a bare list). A
document includes it by name:

    Beam B01:
      - _include:
          path: beam_check        # a `_data` name, or an absolute path
          namespace: b1           # optional: run in its own scope
          with: {span: 6.0}       # parameters, over the partial's `_vars`

The partial's content is built where the `_include` is, at the current heading
level and text style, so it renders as if it had been written there. While it
is built, relative paths resolve against the partial's folder, and the
partial's `_data` names are visible (to `_hc` `path:`, `ym.path()`, Jinja and
`_py`).

Without `namespace`, the partial runs in the document's variables, as inline
content would. With `namespace`, it runs in a copy of them, and the names it
creates or rebinds are put in `_vars[namespace]` afterwards.

See design/scoped_includes.yml.
"""
from __future__ import annotations

import copy
import dataclasses
import pathlib
from contextlib import contextmanager
from typing import Any, Optional

from .blocks import retrieve_block_variables
from .blocks.registry import parse_block_key
from .data_sources import YM_VAR, DataCatalog, DocumentVars, parse_data_declarations
from .errors import IncludeError, YmprintAuthoringError
from .yaml_loader import load_yaml

INCLUDE_CODE = "_include"
OPTIONS = {"path", "with", "namespace"}
# Keys only a whole document may use.
DOCUMENT_ONLY_KEYS = ("_doc", "_style", "_tablestyle", "_export", "_render")
PARTIAL_SUFFIXES = (".yml", ".yaml")
# A partial's content, when it has front matter and no heading of its own.
CONTENT_KEY = "_content"
# context keys: the stack of partials being built, and parsed partials by path.
STACK_KEY = "include_stack"
CACHE_KEY = "include_cache"


def extract_include(k, v) -> Optional[tuple[str, Any]]:
    """
    Returns (key, value) when this element is an `_include`, else None. Handles
    both the mapping-key form (`_include: ...`) and the single-key list-item form
    (`- _include: ...`). `_include_<id>` keeps keys unique within a mapping.
    """
    if _is_include_key(k):
        return k, v
    if k is None and isinstance(v, dict) and len(v) == 1:
        (only_key, only_value), = v.items()
        if _is_include_key(only_key):
            return only_key, only_value
    return None


def _is_include_key(key) -> bool:
    parsed = parse_block_key(key)
    return parsed is not None and parsed[0] == INCLUDE_CODE


def build_include(key: str, value: Any, context: dict, level: int, current_style: str, top: bool) -> list:
    """Returns the flowables of the partial that `_include` 'value' names."""
    from .story_builder import build_story

    options = include_options(key, value)
    path = resolve_partial(key, options["path"], context)
    stack: list[pathlib.Path] = context.setdefault(STACK_KEY, [])
    if path in stack:
        chain = " → ".join(p.name for p in [*stack, path])
        raise IncludeError(f"{key}: {path.name} includes itself ({chain}).")
    content, local_data, defaults = load_partial(key, path, context)

    parent_vars = context["vars"]
    catalog = child_catalog(context["data"], local_data, path, context)
    namespace = options.get("namespace")
    # `$var` values become the variable's object, as in a block's value.
    parameters = retrieve_block_variables(options.get("with") or {}, context)
    local_names = set(catalog.sources) - set(context["data"].sources)
    clashes = sorted(set(defaults) & local_names)
    if clashes:
        raise IncludeError(
            f"{path.name} defines {', '.join(repr(c) for c in clashes)} in `_vars`, "
            "which is also one of its `_data` names. Rename one of them."
        )

    stack.append(path)
    try:
        if namespace is None:
            with _shared_scope(parent_vars, catalog, defaults, parameters):
                with _swapped(context, base_dir=path.parent, data=catalog):
                    return build_story(content, context, level=level, current_style=current_style, top=top)
        scope = DocumentVars(dict(parent_vars), catalog=catalog)
        before = dict(scope)
        scope.update(defaults)
        scope.update(parameters)
        scope[YM_VAR] = _ym_with(parent_vars, catalog)
        with _swapped(context, base_dir=path.parent, data=catalog, vars=scope):
            story = build_story(content, context, level=level, current_style=current_style, top=top)
        parent_vars[namespace] = scope_results(scope, before)
        return story
    except YmprintAuthoringError as exc:
        # Keep the innermost chain: it is set first, as the error unwinds.
        if getattr(exc, "include_chain", None) is None:
            exc.include_chain = [context.get("source_path"), *stack]
        raise
    finally:
        stack.pop()


def include_options(key: str, value: Any) -> dict:
    """The `_include` options as a dict; a bare string is the path."""
    if isinstance(value, str):
        value = {"path": value}
    if not isinstance(value, dict) or "path" not in value:
        raise IncludeError(
            f"{key}: expected the partial's `_data` name (or an absolute path), or a mapping "
            "with a `path` (and optionally `with` and `namespace`)."
        )
    unknown = set(value) - OPTIONS
    if unknown:
        raise IncludeError(
            f"{key}: unknown option(s) {', '.join(sorted(map(str, unknown)))}. "
            f"Choose from: {', '.join(sorted(OPTIONS))}."
        )
    parameters = value.get("with")
    if parameters is not None and not isinstance(parameters, dict):
        raise IncludeError(f"{key}: `with` must be a mapping of parameter names to values.")
    for name in parameters or {}:
        if not (isinstance(name, str) and name.isidentifier()):
            raise IncludeError(f"{key}: parameter name {name!r} in `with` is not a valid variable name.")
    namespace = value.get("namespace")
    if namespace is not None and not (isinstance(namespace, str) and namespace.isidentifier()):
        raise IncludeError(f"{key}: `namespace` must be a valid variable name, got {namespace!r}.")
    return value


def resolve_partial(key: str, path: Any, context: dict) -> pathlib.Path:
    """
    The partial file named by 'path': the name of a `_data` source, or an absolute
    path. Records the read, so `ym live` and `ym build` see it as an input.
    """
    catalog: DataCatalog = context["data"]
    if not (isinstance(path, str) and path.strip()):
        raise IncludeError(f"{key}: `path` must be a `_data` name or an absolute path, got {path!r}.")
    if pathlib.Path(path).is_absolute():
        file = pathlib.Path(path).resolve()
        catalog.record_file(file)
    elif path.isidentifier():
        if path not in catalog:
            declared = ", ".join(sorted(catalog.names())) or "none"
            raise IncludeError(
                f"{key}: no data source named {path!r} (declared: {declared}). Declare the "
                "partial in `_data` (in the project config) and include it by name."
            )
        file = catalog.path(path)
    else:
        raise IncludeError(
            f"{key}: `path` must be a `_data` name or an absolute path, got {path!r}. Declare the "
            "partial in `_data` (in the project config) and include it by name."
        )
    if file.suffix.lower() not in PARTIAL_SUFFIXES:
        raise IncludeError(f"{key}: a partial must be a .yml or .yaml file, got {file}.")
    if not file.is_file():
        raise IncludeError(f"{key}: the partial for `path: {path}` does not exist: {file}")
    return file


def load_partial(key: str, path: pathlib.Path, context: dict) -> tuple[Any, Any, dict]:
    """
    Returns (content, `_data`, `_vars`) of the partial at 'path', as fresh copies.
    Each partial is parsed once per render.
    """
    cache: dict = context.setdefault(CACHE_KEY, {})
    if path not in cache:
        cache[path] = _parse_partial(key, path)
    content, local_data, defaults = copy.deepcopy(cache[path])
    return content, local_data, defaults


def _parse_partial(key: str, path: pathlib.Path) -> tuple[Any, Any, dict]:
    data = load_yaml(path)
    if not data:
        raise IncludeError(f"{key}: the partial {path.name} is empty.")
    if not isinstance(data, (dict, list)):
        raise IncludeError(f"{key}: the partial {path.name} must be a mapping or a list of content.")
    local_data, defaults = None, {}
    if isinstance(data, dict):
        used = [k for k in DOCUMENT_ONLY_KEYS if k in data]
        if used:
            raise IncludeError(
                f"{key}: the partial {path.name} uses {', '.join(used)}, which only a document "
                "may use. A partial has content, and optionally `_data` and `_vars`."
            )
        local_data = data.pop("_data", None)
        defaults = data.pop("_vars", None) or {}
        if not isinstance(defaults, dict):
            raise IncludeError(f"{key}: `_vars` in the partial {path.name} must be a mapping.")
        if CONTENT_KEY in data:
            # YAML can't follow front matter (a mapping) with a bare list, so content
            # without a heading of its own goes under `_content`.
            others = [k for k in data if k != CONTENT_KEY]
            if others:
                raise IncludeError(
                    f"{key}: the partial {path.name} has `_content` and also "
                    f"{', '.join(repr(k) for k in others)}. Put all of its content under `_content`."
                )
            data = data[CONTENT_KEY]
            if not isinstance(data, (dict, list, str)):
                raise IncludeError(f"{key}: `_content` in the partial {path.name} must be content (a list, mapping or text).")
        if not data:
            raise IncludeError(f"{key}: the partial {path.name} has no content.")
    return data, local_data, dict(defaults)


def child_catalog(parent: DataCatalog, local_data: Any, path: pathlib.Path, context: dict) -> DataCatalog:
    """
    A catalog with the partial's own `_data` (relative to the partial) over
    'parent''s sources. It shares 'parent''s records, so what the partial reads
    is recorded on the render.
    """
    local = parse_data_declarations(local_data, path.parent, path, project_root=parent.project_root)
    for name, source in local.items():
        if source.producers:
            raise IncludeError(
                f"`_data` entry {name!r} in the partial {path.name} has a `from`. Partials can't "
                "declare produced data; declare it in the project config."
            )
    local = {name: dataclasses.replace(source, local=True) for name, source in local.items()}
    return DataCatalog(
        sources={**parent.sources, **local},
        project_root=parent.project_root,
        reads=parent.reads,
        files=parent.files,
    )


def scope_results(scope: dict, before: dict) -> dict:
    """
    The variables a scoped partial left: the names it created or rebound (its
    `_vars` and parameters included), compared by identity with 'before'.
    """
    missing = object()
    return {
        name: value
        for name, value in scope.items()
        if name != YM_VAR
        and not (name.startswith("__") and name.endswith("__"))
        and before.get(name, missing) is not value
    }


def _ym_with(variables: dict, catalog: DataCatalog):
    ym = dict.get(variables, YM_VAR)
    return dataclasses.replace(ym, catalog=catalog) if ym is not None else None


@contextmanager
def _shared_scope(variables: DocumentVars, catalog: DataCatalog, defaults: dict, parameters: dict):
    """
    Runs a partial in the document's own variables: its `_vars` fill names not
    already set, then its parameters are set. The partial's `_data` names are
    visible while it runs; the values it computes stay afterwards.
    """
    for name, value in defaults.items():
        if not dict.__contains__(variables, name):
            variables[name] = value
    variables.update(parameters)
    saved_catalog = getattr(variables, "catalog", None)
    saved_ym = dict.get(variables, YM_VAR)
    if saved_catalog is not None:
        variables.catalog = catalog
    if saved_ym is not None:
        variables[YM_VAR] = dataclasses.replace(saved_ym, catalog=catalog)
    try:
        yield
    finally:
        if saved_catalog is not None:
            variables.catalog = saved_catalog
        if saved_ym is not None:
            variables[YM_VAR] = saved_ym


@contextmanager
def _swapped(context: dict, **values):
    """Sets context keys for the duration, restoring them even when the partial fails."""
    saved = {key: context[key] for key in values}
    context.update(values)
    try:
        yield
    finally:
        context.update(saved)
