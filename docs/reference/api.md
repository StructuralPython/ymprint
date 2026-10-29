# Python API reference

The public API is importable from the top-level package:

```python
from ymprint import (
    Ymprint, default_app,
    RenderEvent, RenderCallbackError,
    BlockRegistry, BlockExistsError, parse_block_key,
    register_loader, register_serializer, RenderRun,
)
```

For a walkthrough, see [Custom applications](../guide/custom-applications.md).

## `Ymprint`

```python
Ymprint(
    name: str = "ym",
    *,
    config_path: str | Path | None = None,
    builtin_blocks: bool = True,
    starter_document: str = STARTER_DOCUMENT,
)
```

| Parameter | Meaning |
| --- | --- |
| `name` | The application's name, used as its CLI name. |
| `config_path` | The application's config file or directory (house style). Layered above YMPrint's defaults and below the user's config. |
| `builtin_blocks` | Start from a copy of the built-in blocks (`True`) or an empty registry (`False`). |
| `starter_document` | The document `live` offers to create when the source doesn't exist. `{title}` is replaced with the file name. |

| Member | Description |
| --- | --- |
| `blocks` | This application's `BlockRegistry`. |
| `register_block(code, convert, *, override=False)` | Adds a block. |
| `@block(code, *, override=False)` | Decorator form of `register_block`. |
| `@before_render` | Registers `fn(event)` to run before every render. |
| `@on_context` | Registers `fn(event, context)` to run after the context is built, before content is rendered. Changes to the style models in `context` take effect. |
| `@after_render` | Registers `fn(event)` to run after every render that wrote the PDF. |
| `render(source, destination=None, config_path=None, *, base_dir=None, discover_config=True, trigger=None, mode="api", project_root=None, vars=None, params=None)` | Renders a path or dict to a PDF, once; returns the `RenderEvent`. |
| `render_all(source, config_path=None, *, destination=None, only=None, discover_config=True, mode="api")` | Renders a document as its `_render` entry says (once per parameter set); returns a [`RenderRun`](#render-all). |
| `instances(source, config_path=None, *, only=None, discover_config=True)` | The renders `render_all` would make, as `Instance(params, destination, key)`s. |
| `live(source, destination=None, config_path=None, *, watch=(), vars=None, only=None)` | Runs live mode; blocks until Ctrl+C and returns an exit code. |
| `config_layers(base_dir, config_path=None, discover_config=True)` | The config layers a render would use, lowest priority first. |
| `project_root(base_dir, discover_config=True)` | The project root for a document in `base_dir`. |
| `cli()` | Returns a new Typer app with `convert`, `live`, `build` and `graph` commands. |

### `render()` arguments

| Argument | Meaning |
| --- | --- |
| `source` | A YAML document path, or the document as a `dict` (not modified). |
| `destination` | Output PDF. Defaults to the source path with `.pdf`; **required** for a dict source. |
| `config_path` | An explicit config file or directory (or a sequence of them, lowest priority first). The highest-priority config layer. |
| `base_dir` | Where relative paths in the document resolve. Defaults to the source's directory, or the current directory for a dict. |
| `discover_config` | Search `base_dir` and its parents for a `*.ymprint.yml`. |
| `trigger`, `mode` | Passed through to the hooks on the `RenderEvent`. |
| `project_root` | `ym.project_root` in the document. Defaults to the directory of the discovered `*.ymprint.yml`, else `base_dir`. |
| `vars` | Variables layered over the document's `_vars` (they win). |
| `params` | The parameter set this render is for: `ym.params` and `RenderEvent.params`. |

(render-all)=
### `render_all()` and `RenderRun`

`render_all` renders a document as its [`_render`](../guide/parameterized-documents.md)
entry in the project config says. With a `for_each`, the document is read once and
rendered once per parameter set; a failing set doesn't stop the others. Without one, it
renders once (to the entry's `output`, `destination`, or next to the source) and errors
propagate as from `render()`.

| `RenderRun` field | Meaning |
| --- | --- |
| `source` | The document. |
| `spec` | Its `_render` entry, or `None`. |
| `instances` | The renders attempted: `Instance(params, destination, key)`. |
| `results` | The `RenderEvent` of each render that succeeded. |
| `failures` | `RenderFailure(instance, error)` for each that failed; `describe()` gives a one-line summary. |
| `inputs` | Every data file read, by `for_each` and by the renders. |
| `keys` | The key of each result, in order. |
| `exports` | The document's [exports](../guide/document-exports.md): its `_export` values, or `{key: values}` per parameter set. `None` without `_export`. |
| `written` | The export files written to the `_data` entries that name the document in `from:`. |
| `notes` | Why exports were not written, when they weren't. |
| `ok` | `True` when nothing failed. |

## `default_app`

The `Ymprint` instance behind the `ym` command. `ymprint.report_reader.load_report(src,
dest, config, vars=None)` renders with it, using exactly the config given (no discovery),
and returns the `RenderEvent`.

## `RenderEvent`

A dataclass passed to every hook. Its fields are `app`, `source`, `destination`,
`base_dir`, `config_paths`, `trigger`, `mode`, `vars`, `params` and `project_root`, plus the
`initial` property. After the content is rendered, `inputs` holds the data files the
document read (its [`_data`](../guide/data-sources.md) sources and `_loadjson` files), and
`exports` holds its [`_export`](../guide/document-exports.md) values (or `None`). `pdf` is
the PDF written.
See [The RenderEvent](../guide/custom-applications.md#the-renderevent).

## `RenderCallbackError`

Raised by `render()` when a hook raises anything other than a `YmprintAuthoringError`.

| Attribute | Meaning |
| --- | --- |
| `stage` | `"before_render"`, `"on_context"` or `"after_render"`. |
| `callback` | The hook that raised. |
| `original` | The original exception. |

## `BlockRegistry`

A mapping of block codes to converter functions.

| Member | Description |
| --- | --- |
| `register(code, convert, *, override=False)` | Adds a block. Raises `ValueError` for an invalid or reserved code, and `BlockExistsError` for a duplicate unless `override=True`. |
| `@block(code, *, override=False)` | Decorator form of `register`. |
| `get(code)` | The converter for `code`, or `None`. |
| `codes()` | The registered codes. |
| `copy()` | An independent copy. |
| `code in registry`, `len(registry)` | Membership and size. |

A converter has the signature `convert(block_key, block_value, context) -> list[Flowable]`.

Reserved codes, which are handled by YMPrint itself: `_ul`, `_ol`, `_textstyle`, `_slide`,
`_frame`, `_vars`, `_style`, `_doc`, `_tablestyle`, `_data`, `_export`.

## `parse_block_key(key)`

Splits a document key into `(code, id)`, or returns `None` if it isn't block-shaped:

```python
parse_block_key("_beam_b1")   # ("_beam", "b1")
parse_block_key("_beam")      # ("_beam", None)
parse_block_key("_beamx")     # ("_beamx", None)  — a different code, not `_beam`
parse_block_key("Heading")    # None
```

## Plugins

### `register_loader(name, loader, *, extensions=(), override=False)`

Registers `loader(path) -> data` for [`_data`](../guide/data-sources.md) entries that give
`loader: <name>`. `extensions` (for example `[".toml"]`) makes it the default for files with
those suffixes. The built-in loaders are `yaml` and `json`.

### `register_serializer(type, serializer)`

Registers `serializer(value) -> JSON-native data` for exported values of `type` (and its
subclasses). Later registrations take precedence. Built in: JSON-native types, paths, sets,
and anything with `__float__`.

### Installed plugins

A package extends YMPrint when it is installed by naming a setup function in the
`ymprint.plugins` entry-point group. YMPrint calls each setup function once, with no
arguments, before it first needs a loader or serializer; the function registers what the
package provides.

```toml
# the plugin's pyproject.toml
[project.entry-points."ymprint.plugins"]
units = "my_package.ymprint_plugin:setup"
```

```python
# my_package/ymprint_plugin.py
from ymprint import register_loader

def setup():
    register_loader("yaml+units", load_yaml_with_quantities)
```

## `ymprint.project`

For scripts that are steps of a [project build](../guide/building-projects.md).

| Function | Meaning |
| --- | --- |
| `data(name)` | A fresh copy of data source `name` of the project containing the calling script. |
| `path(name)` | The file data source `name` is read from. |
| `publish(name, value)` | Writes `value` (as JSON, atomically) for data source `name`; the calling script must be named in its `from:`. Returns the file written. |

## `ymprint.build.Build`

`Build(app, start=None, *, force=False, dry_run=False, report=None)` is the engine behind
`ym build`. `run(targets=())` returns a `BuildSummary` whose `results` are `StepResult`s
(`step`, `status`, `reasons`, `seconds`, `detail`, `error`, `failures`) in the order the
steps finished; `report(result)` is called as each finishes.
