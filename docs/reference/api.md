# Python API reference

The public API is importable from the top-level package:

```python
from ymprint import (
    Ymprint, default_app,
    RenderEvent, RenderCallbackError,
    BlockRegistry, BlockExistsError, parse_block_key,
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
| `@on_context` | Registers `fn(event, context)` to run after the context is built, before content is rendered. |
| `@after_render` | Registers `fn(event)` to run after every render that wrote the PDF. |
| `render(source, destination=None, config_path=None, *, base_dir=None, discover_config=True, trigger=None, mode="api")` | Renders a path or dict to a PDF; returns the `RenderEvent`. |
| `live(source, destination=None, config_path=None, *, watch=())` | Runs live mode; blocks until Ctrl+C and returns an exit code. |
| `config_layers(base_dir, config_path=None, discover_config=True)` | The config layers a render would use, lowest priority first. |
| `cli()` | Returns a new Typer app with `convert` and `live` commands. |

### `render()` arguments

| Argument | Meaning |
| --- | --- |
| `source` | A YAML document path, or the document as a `dict` (not modified). |
| `destination` | Output PDF. Defaults to the source path with `.pdf`; **required** for a dict source. |
| `config_path` | An explicit config file or directory (or a sequence of them, lowest priority first). The highest-priority config layer. |
| `base_dir` | Where relative paths in the document resolve. Defaults to the source's directory, or the current directory for a dict. |
| `discover_config` | Search `base_dir` and its parents for a `*.ymprint.yml`. |
| `trigger`, `mode` | Passed through to the hooks on the `RenderEvent`. |

## `default_app`

The `Ymprint` instance behind the `ym` command. `ymprint.report_reader.load_report(src,
dest, config)` renders with it, using exactly the config given (no discovery).

## `RenderEvent`

A dataclass passed to every hook. Its fields are `app`, `source`, `destination`,
`base_dir`, `config_paths`, `trigger`, `mode` and `vars`, plus the `initial` property.
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
`_frame`, `_vars`, `_style`, `_doc`, `_tablestyle`.

## `parse_block_key(key)`

Splits a document key into `(code, id)`, or returns `None` if it isn't block-shaped:

```python
parse_block_key("_beam_b1")   # ("_beam", "b1")
parse_block_key("_beam")      # ("_beam", None)
parse_block_key("_beamx")     # ("_beamx", None)  — a different code, not `_beam`
parse_block_key("Heading")    # None
```
