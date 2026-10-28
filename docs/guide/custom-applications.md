# Custom applications

YMPrint can be the engine for your own document tool: a calc-sheet generator, an
inspection-report app, a letter writer. You define the tool as an instance of the
`Ymprint` class. The instance holds:

- **blocks**: YMPrint's built-in blocks plus your own;
- **render hooks**: your code that runs before, during and after every render;
- **a house style**: a config file bundled with your application;
- **a CLI**: its own `convert` and `live` commands.

`ym` itself is just the default `Ymprint` instance.

## A minimal application

```python
# calcsheet/__init__.py
from pathlib import Path

from reportlab.platypus import Paragraph
from ymprint import RenderEvent, Ymprint

HERE = Path(__file__).parent

app = Ymprint(name="calcsheet", config_path=HERE / "config")


@app.block("_beam")
def beam_block(block_key, block_value, context):
    """Renders `_beam: {span: 6.0, load: 12.5}` as a one-line summary."""
    style = context["styles"]["rl"]["_style"]["body"]
    span, load = block_value["span"], block_value["load"]
    moment = load * span**2 / 8
    return [Paragraph(f"Span {span} m, w = {load} kN/m: M = {moment:.1f} kNm", style)]


@app.before_render
def load_project(event: RenderEvent) -> None:
    event.vars["project"] = {"name": "Riverside Footbridge", "number": "P-1042"}


@app.after_render
def announce(event: RenderEvent) -> None:
    print(f"Wrote {event.destination}")


cli = app.cli()
```

Expose the CLI as a console script in your package's `pyproject.toml`:

```toml
[project.scripts]
calcsheet = "calcsheet:cli"
```

Your users then get the same commands as `ym`, with your blocks, hooks and house style:

```bash
calcsheet convert beam-B1.yml
calcsheet live beam-B1.yml
```

```yaml
# beam-B1.yml
"{{project.name}} ({{project.number}})":
  - Beam B1:
      _beam:
        span: 6.0
        load: 12.5
```

## Blocks

Register a block with the `@app.block(code)` decorator or with
`app.register_block(code, convert)`. A block code is an underscore followed by
letters and digits, such as `_beam`. A second underscore can't be part of the code,
because in documents it separates the code from an optional id: `_beam_b1` and
`_beam_b2` are both `_beam` blocks (see [Block syntax](../reference/blocks.md#block-syntax)).

The converter is called as `convert(block_key, block_value, context)` and returns a
list of ReportLab flowables:

| Argument | Contents |
| --- | --- |
| `block_key` | The key as written, e.g. `_beam_b1`. `ymprint.parse_block_key(block_key)` returns `("_beam", "b1")`. |
| `block_value` | The data under the key, with any `$VAR` values already replaced by the variable's Python object. |
| `context` | The render state: `styles`, `frames`, `vars`, `base_dir`, `blocks` and more. Use `ymprint.blocks.content_box(context)` for the width and height available to your block. |

Each application starts from its own **copy** of the built-in blocks, so blocks you
register never leak into `ym` or into another application. To replace a built-in
block, pass `override=True`. Registering a code that already exists otherwise raises
`BlockExistsError`. To start with no blocks at all, use `Ymprint(builtin_blocks=False)`.

## Render hooks

Hooks run on **every** render: `convert`, `live` (each refresh) and `app.render()`.
Register them with decorators. Several hooks at the same stage run in registration
order.

| Hook | Signature | Runs | If it raises |
| --- | --- | --- | --- |
| `@app.before_render` | `fn(event)` | Before the document is read | The render is skipped |
| `@app.on_context` | `fn(event, context)` | After config is loaded and the context built, before content is rendered. Style changes made here take effect | The render is skipped |
| `@app.after_render` | `fn(event)` | After the PDF is written | — (the PDF already exists) |

`after_render` only runs when the PDF was written. If the document has an error, it
does not run.

### The `RenderEvent`

| Attribute | Meaning |
| --- | --- |
| `app` | The `Ymprint` application doing the render. |
| `source` | The document file, or `None` when the document was passed as a dict. |
| `destination` | The document's target PDF. |
| `output` | Where the PDF is actually written when not `destination` (live mode's local preview when the destination is locked); otherwise `None`. `output_path` gives whichever applies. |
| `base_dir` | Where relative paths in the document resolve (images, `_loadjson`, backgrounds). |
| `config_paths` | The config layers in effect, lowest priority first. |
| `trigger` | In live mode, the watched file whose change caused this render; otherwise `None`. |
| `initial` | `True` when `trigger` is `None`. |
| `mode` | `"convert"`, `"live"` or `"api"`. |
| `vars` | Variables merged **over** the document's `_vars`. Fill it in `before_render` to feed data in. |

### Feeding data into a document

`event.vars` is how an application supplies data without writing files. Everything in it
is available to `{{var}}` templating, `$var` block arguments and `_py` blocks, and it takes
precedence over the document's own `_vars`:

```python
@app.before_render
def load_design_data(event):
    event.vars["loads"] = read_load_table(event.base_dir / "loads.xlsx")
```

A `before_render` hook can also regenerate the document or its inputs on disk. In live
mode, changes that hooks make to watched files don't trigger another refresh.

### Working with the context

`on_context` receives the full render context. You can change it in place:

- `context["vars"]`: the merged variables (the document's `_vars` plus `event.vars`). `_py` and `_loadjson` blocks add to them as the content renders;
- `context["content"]`: the document content that is about to be rendered;
- `context["frames"]`: the content boxes that blocks size themselves against;
- `context["styles"]["ymprint"]` and `context["tablestyles"]["ymprint"]`: the text and
  table style models, after all config layers have been merged.

```python
@app.on_context
def stamp_revision(event, context):
    context["vars"]["revision"] = git_describe(event.base_dir)
```

#### Changing styles

Change the style **models**, either by setting attributes or by replacing a model.
YMPrint rebuilds the ReportLab styles from them after your `on_context` hooks run, so the
changes apply to the whole document. Headings scale with the body size, as they do in
config:

```python
@app.on_context
def draft_styles(event, context):
    styles = context["styles"]["ymprint"]
    styles.body.size = 11
    styles.headings.color = "#888888"
    styles.styles["note"] = {"body": {"size": 8}}        # named style, sparse like in config
    context["tablestyles"]["ymprint"].headers.text.color = "#ff0000"
```

To replace a model, validate a new one:
`context["styles"]["ymprint"] = ReportStyles.model_validate(data)`, where `ReportStyles`
is imported from `ymprint.config`. Attribute assignments are not validated, so a wrong
type only fails later, when the styles are rebuilt.

`context["styles"]["yaml"]` and `context["tablestyles"]["yaml"]` hold the config as it was
loaded. They are not read back, so editing them has no effect.

For a fixed house style, prefer the [application config](#house-style-the-application-config).
`on_context` is for styling that depends on the render, such as a "DRAFT" look from a
flag in `event.vars`.

### Errors in hooks

If a hook raises, the error is wrapped in `RenderCallbackError` (with `.stage`, `.callback`
and `.original`). `convert` shows it in an error panel and exits with code 1. `live` shows
it in the live panel and keeps watching. If your hook detects a problem in the user's
input, raise `ymprint.errors.YmprintAuthoringError` instead: it passes through unwrapped
and is reported like any other error in the document.

Hooks are called with the event (and context) only. To pass extra arguments, bind them
with `functools.partial` or a closure. For state that persists between live refreshes,
register an instance of a class with `__call__`.

## House style: the application config

`Ymprint(config_path=...)` takes a config file or a directory containing one. It is layered
between YMPrint's defaults and the user's config, and each layer only overrides the keys
it sets:

```text
ymprint defaults  ─►  app config  ─►  *.ymprint.yml near the document  ─►  --config-dir  ─►  document front matter
   (lowest)                                                                                      (highest)
```

A background with `relative-to: config` resolves against the directory of **the config
file that defines it**. So letterhead PDFs shipped next to your application's config keep
working when a user adds their own `*.ymprint.yml`.

## Rendering from Python

```python
app.render("beam-B1.yml")                          # -> beam-B1.pdf
app.render("beam-B1.yml", "out/B1.pdf", "site-config/")

# A document you build in code:
doc = {"Beam B1": [{"_beam": {"span": 6.0, "load": 12.5}}]}
app.render(doc, "B1.pdf", base_dir=job_dir)

app.live("beam-B1.yml", watch=["loads.xlsx"])      # blocks until Ctrl+C
```

`render()` returns the `RenderEvent`. When the source is a dict, `destination` is
required, and relative paths resolve against `base_dir` (by default, the current
directory). The dict you pass is not modified. Live mode needs a file to watch.

`Ymprint(starter_document=...)` sets the document that `live` offers to create when the
source file doesn't exist. `{title}` in it is replaced with the file name.

## Adding commands

`app.cli()` returns a regular [Typer](https://typer.tiangolo.com/) app, so you can add your
own commands next to `convert` and `live`:

```python
cli = app.cli()

@cli.command()
def batch(folder: str):
    """Render every calc sheet in FOLDER."""
    for path in sorted(Path(folder).glob("*.yml")):
        app.render(path, mode="convert")
```
