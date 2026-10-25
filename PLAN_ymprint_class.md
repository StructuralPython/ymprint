# Plan: `Ymprint` application class

Branch: `features/ymprint-class` (off `main` @ `1e2430d`, v0.5.0)

## Status (2026-10-25)

Steps 1–10 are implemented on this branch. Step 11 is partly done:

- Not done yet: dropping `stash@{0}` and the `features/live_callback` branch
  (everything in them has been ported), release notes, and the version bump.
- Breaking for release notes: `ymprint.blocks.register_block` / `list_blocks` /
  `get_block_callable` are removed; `ym convert --config-dir` is now layered
  over a discovered `*.ymprint.yml` instead of replacing it; `_xxx` keys that
  only *start with* a registered code are no longer dispatched as that block.

## Goal

Make ymprint a base you can build document-type-specific applications on
(e.g. a calc-sheet tool, an inspection-report tool). Each application is an
instance of a new `Ymprint` class that owns:

- **its block registry** – built-in blocks plus the app's own, isolated from
  other instances (today there is one module-global registry);
- **render hooks** – `before_render`, `on_context`, `after_render`, registered
  the same way blocks are, run on *every* render (`convert`, `live`,
  programmatic), not just in live mode;
- **input/output handling** – sources as files *or* dicts, a bundled app config
  layered under the user's config, destination resolution, and the render
  pipeline currently in `report_reader.load_report`;
- **its CLI** – `app.cli()` returns a Typer app with `convert` and `live`, so an
  app ships its own command (`calcsheet live report.yml`).

`ym` itself becomes just the default instance.

### Target usage

```python
# calcsheet/__init__.py
from pathlib import Path
from ymprint import Ymprint, RenderEvent

app = Ymprint(name="calcsheet", config_path=Path(__file__).parent / "config")

@app.block("_beam")
def beam_block(block_key, block_value, context):
    ...  # -> list[Flowable]

@app.before_render
def load_design_data(event: RenderEvent) -> None:
    event.vars["project"] = fetch_project(event.source)

@app.on_context
def stamp_revision(event: RenderEvent, context: dict) -> None:
    context["vars"]["revision"] = git_describe(event.base_dir)

@app.after_render
def publish(event: RenderEvent) -> None:
    shutil.copy(event.destination, SHARED_DRIVE)

cli = app.cli()          # pyproject: calcsheet = "calcsheet:cli"

# or programmatically, from a file or from generated data:
app.render("report.yml")
app.render({"Beam B1": {"_beam": {...}}}, destination="b1.pdf", base_dir=job_dir)
```

## Decisions

| # | Question | Decision |
|---|----------|----------|
| 1 | Which hooks | `before_render`, **`on_context`**, `after_render` |
| 2 | Config precedence | **Layered**: ymprint defaults < app config < local `*.ymprint.yml` < explicit `--config` < document `_style`/`_doc`/`_tablestyle` |
| 3 | Module-level `register_block` | **Removed** in this release (no shim) |
| 4 | Source type | **Path or dict**; dict sources resolve relative paths against `base_dir` |
| 5 | Block keys | `_<code>` or `_<code>_<id>`; the code is everything up to the second `_`. `_py_foo` is a `_py` block with id `foo`; `_pyfoo` is a `pyfoo` block. No prefix matching. |

## Relationship to the `features/live_callback` WIP

That work was never committed; it is stashed as `stash@{0}`
("WIP features/live_callback: …"). It is not wasted – its structure carries over:

| WIP piece (stash)                                    | Fate in this refactor |
|------------------------------------------------------|-----------------------|
| `cli/live.py`: `FileWatcher`, `build_live_panel`, `_initialize_document`, `STARTER_DOCUMENT`, `resolve_config`, the loop in `run_live` | **Keep**, move over as-is |
| `FileWatcher.sync()` (ignore files written by callbacks) | **Keep** |
| `RenderEvent` dataclass                              | **Keep, move** to `ymprint/render.py`; extend (see below) |
| `LiveCallbackError` + `format_callback_error`        | **Keep**, rename `RenderCallbackError` (no longer live-specific) |
| `render_document(event, before, after)`              | **Replace** by `Ymprint.render()` |
| `run_live(..., before_render=, after_render=, watch=)` | **Change**: takes `app: Ymprint`; hooks come from the app; `watch` stays |
| `tests/test_live_callbacks.py`, `test_live_init.py` changes | **Port** onto the new API |
| `docs/reference/cli.md` additions                    | **Rewrite** into the new guide page |

Recovering files (untracked files live in the stash's third parent):

```bash
git checkout 'stash@{0}^3' -- src/ymprint/cli/live.py tests/test_live_callbacks.py
git checkout 'stash@{0}' -- tests/test_live_init.py   # tracked-file edits
```

Drop the stash (and the `features/live_callback` branch) once ported.

## Design

### 1. Block keys and `BlockRegistry` (`ymprint/blocks/registry.py`)

**Key grammar** (decision 5), one shared parser used everywhere:

```python
BLOCK_KEY = re.compile(r"^_(?P<code>[a-zA-Z0-9]+)(?:_(?P<id>.+))?$")

def parse_block_key(key) -> tuple[str, str | None] | None:
    """'_py_foo' -> ('_py', 'foo'); '_pyfoo' -> ('_pyfoo', None); 'Heading' -> None"""
```

- `build_story` dispatches a key as a block iff `parse_block_key(k)` succeeds
  **and** its code is registered. This replaces
  `str(k).startswith(tuple(registered_blocks))`, which today sends `_pyfoo`
  into `convert_blocks` because it starts with `_py`.
- `convert_blocks` uses the same parser instead of its own regex (it already
  extracts `_pyfoo` correctly; the bug is only in the dispatch check).
- `_ul`/`_ol` (`LIST_BLOCK_PATTERN`) already follow the `_code_id` rule; switch
  it to `parse_block_key` too so there is one definition.
- Unregistered `_xxx` keys keep today's behaviour (rendered as a heading).
  *Possible follow-up:* raise "Unknown block" for these, to catch typos like
  `_imgg`. Out of scope unless you want it.

**Registry:**

```python
class BlockRegistry:
    def register(self, code: str, convert: BlockConverter, *, override=False) -> None
    def block(self, code: str, *, override=False) -> Callable  # decorator form
    def get(self, code: str) -> BlockConverter | None
    def codes(self) -> list[str]
    def __contains__(self, code: str) -> bool
    def copy(self) -> "BlockRegistry"
```

- Validate at registration: `code` must match `^_[a-zA-Z0-9]+$` (so no `_`
  after the first character, otherwise `_id` parsing is ambiguous) and must not
  be a reserved structural key (`_ul`, `_ol`, `_textstyle`, `_slide`, `_frame`,
  `_vars`, `_style`, `_doc`, `_tablestyle`).
- Raise the existing-but-unused `BlockExistsError` on a duplicate unless
  `override=True` (lets an app deliberately replace a built-in like `_img`).
- Converter signature stays `fn(block_key, block_value, context)`; converters
  that want the id call `parse_block_key(block_key)`.

**Built-in blocks stop self-registering at import.** Each block module keeps
its converter function; a new `blocks/builtin.py` builds
`BUILTIN_BLOCKS: BlockRegistry` by importing them explicitly. That removes the
import-for-side-effect list at the top of `report_reader.py` and puts the list
of built-in blocks in one file.

**Removed** (decision 3): `create_block_registry`, module-level
`register_block`, `list_blocks`, `get_block_callable` in `ymprint.blocks`.
Call out as a breaking change in release notes with the one-line migration
(`ymprint.default_app.register_block(...)` or your own `Ymprint`).

### 2. Registry reaches the story builder through `context`

`build_story` and `convert_blocks` read `context["blocks"]` (a `BlockRegistry`)
instead of globals.

- `build_context(..., blocks: BlockRegistry | None = None)` stores it; `None`
  falls back to `BUILTIN_BLOCKS` so the many tests that build a context by hand
  keep working unchanged.
- Slides already shallow-copy context (`slides._frame_context`), so the
  registry propagates into frames for free.
- Custom converters also see `context["blocks"]` and can render nested blocks,
  which is useful for composite blocks.

### 3. Config layering (decision 2)

Today `load_report_config(source_data, report_config_path)` merges three layers
with `DeepChainMap(content, config, defaults)`, and the CLI picks *one* config
(explicit `--config` or the nearest `*.ymprint.yml`).

Change to an ordered list of layers, lowest priority first:

```python
def load_report_config(source_data=None, config_paths: Sequence[Path | None] = ()) -> ...
# DeepChainMap(content, *reversed(loaded_layers), defaults)
```

`Ymprint` builds the list per render:

1. app `config_path` (bundled house style), if set;
2. local `*.ymprint.yml` found via `locate_config_file(base_dir)`;
3. explicit `config_path` argument / `--config`.

Each is loaded once and missing entries are skipped. The existing
`load_report_config(source, path)` call form keeps working, because a single
path is treated as a one-item list. That keeps the ~15 test call sites untouched.

**Relative backgrounds need care.** `load_pdf_backgrounds` resolves
`relative-to: config` against `context["config_path"]`, a single path. With
several layers, "config" must mean *the layer that defined that background*.
Fix: when each layer is loaded, rewrite its `relative-to: config` background
paths to absolute paths using that layer's directory. Then
`context["config_path"]` is only informational (becomes `config_paths`).
Pre-existing bug to fix at the same time: when `config_path` is a *directory*,
`Path(config_path).parent` resolves one level too high.

Merging is not limited to whole files: a local `*.ymprint.yml` that only sets
`_style.body.size` changes just that key on top of the app's config, because
`build_current_config`'s key-by-key merge already works that way. `templates`
and extension keys keep their current "highest layer wins wholesale" rule. Add
tests for app layer + local layer + explicit layer.

### 4. Sources: path or dict (decision 4)

`render(source: str | Path | dict, ..., base_dir=None)`:

- **Path:** as today; `base_dir = source.parent`; destination defaults to
  `source.with_suffix(".pdf")`.
- **dict:** used directly (deep-copied, since the pipeline `pop`s `_vars`,
  `_style`, etc.); `base_dir` defaults to `Path.cwd()`; `destination` is
  **required** (raise `ValueError` otherwise).

Blocks that currently use `Path(context["source_path"]).parent` (`image_block`,
`json_block`, `pdf_postprocessing` for `relative-to: source`) switch to
`context["base_dir"]`. `context["source_path"]` becomes `None` for dict sources.
Error messages that name the source file (`YamlSyntaxError`, "document is
empty") fall back to `"<dict source>"`.

Live mode stays file-only: `app.live()` rejects a dict.

### 5. Render pipeline + hooks (`ymprint/render.py`)

```python
@dataclass
class RenderEvent:
    app: "Ymprint"
    source: Path | None                 # None for dict sources
    destination: Path
    base_dir: Path
    config_paths: tuple[Path, ...]      # resolved layers, low -> high
    trigger: Path | None = None         # file change that caused it (live); None otherwise
    mode: Literal["convert", "live", "api"] = "api"
    vars: dict = field(default_factory=dict)   # merged over the document's _vars
    @property
    def initial(self) -> bool: ...
```

Not frozen (unlike the WIP) so `before_render` can feed data in via
`event.vars` without writing YAML to disk.

`Ymprint.render(...)` stages:

1. **resolve**: source data, `base_dir`, destination, config layers → `RenderEvent`;
2. **`before_render(event)`** hooks in registration order. Any failure aborts
   the render, since the hook's output may be an input to the document;
3. **load**: YAML (or the dict), merge `event.vars` over `_vars`, load layered
   config, `build_context(..., blocks=self.blocks)`;
4. **`on_context(event, context)`** hooks: they may mutate `context` in place
   (vars, styles, frames) before the story is built. A failure aborts the render;
5. **build**: story, PDF, background post-processing (body of today's
   `load_report`, split into private functions);
6. **`after_render(event)`** hooks, only if the PDF was written;
7. return the `RenderEvent`.

Hook exceptions → `RenderCallbackError(stage, callback, original)`.
`YmprintAuthoringError` raised from a hook passes through unchanged (same rule
as the WIP), so a hook can report a friendly authoring error.

Note for `on_context` docs: `context["styles"]["rl"]` and the families are
already built by then, so changing `context["styles"]["ymprint"]` alone has no
effect. Document which keys are safe to change (`vars`, `frames`, `content`),
and consider rebuilding the style families when a hook changes the style
config, as a later step.

`report_reader.load_report(src, dest, config)` stays as a thin wrapper:
`default_app.render(src, dest, config)`. ~15 tests and external callers use it.

### 6. `Ymprint` class (`ymprint/app.py`)

```python
class Ymprint:
    def __init__(self, name="ym", *, config_path=None, builtin_blocks=True,
                 starter_document=STARTER_DOCUMENT, help=None)

    blocks: BlockRegistry
    def register_block(self, code, convert, *, override=False)
    def block(self, code, *, override=False)            # decorator

    def before_render(self, fn)   # decorator; returns fn
    def on_context(self, fn)      # decorator; returns fn
    def after_render(self, fn)    # decorator; returns fn

    def render(self, source, destination=None, config_path=None, *,
               base_dir=None, trigger=None, mode="api") -> RenderEvent
    def live(self, source, destination=None, config_path=None, *, watch=()) -> int
    def cli(self) -> typer.Typer
```

- `builtin_blocks=True` → `self.blocks = BUILTIN_BLOCKS.copy()`; `False` gives an
  empty registry for tightly-scoped document types.
- `starter_document` lets an app's `live` start a new document from its own
  template instead of ymprint's generic one.
- `cli()` builds a fresh Typer app each call with `convert` and `live` commands
  bound to `self`. `cli/main.py` keeps the command bodies/options but they become
  closures over an app; `ymprint.cli.main:app` becomes `default_app.cli()` so
  the `ym` entry point is unchanged. Apps can add their own commands to the
  returned Typer.

Exports from `ymprint/__init__.py`: `Ymprint`, `RenderEvent`, `BlockRegistry`,
`parse_block_key`, `default_app`.

### 7. Live mode (`ymprint/cli/live.py`)

Port the WIP `run_live` with signature `run_live(app, source, destination=None,
config_path=None, *, watch=(), console=None)`. Watched files: source + every
resolved config layer that exists (app config included) + `watch`. Each refresh
calls `app.render(..., trigger=changed_path, mode="live")`, catches
`YmprintAuthoringError` and `RenderCallbackError` for display, and keeps the
`watcher.sync()` in `finally`. `Ymprint.live()` calls it.

## Implementation steps (one commit each)

1. **Block keys** – `parse_block_key`; use it in `build_story` dispatch,
   `convert_blocks`, `LIST_BLOCK_PATTERN`. Tests: `_py_foo` → `_py`,
   `_pyfoo` not dispatched as `_py`, `_ul_2` still a list.
2. **Registry class** – `BlockRegistry`, validation, reserved codes,
   `BlockExistsError`; `blocks/builtin.py`; remove self-registration from
   block modules and the module-level registry functions; drop side-effect
   imports in `report_reader.py`.
3. **Context-threaded lookup** – `build_context(blocks=...)`; `build_story` /
   `convert_blocks` read `context["blocks"]`. Test: two contexts with
   different registries render different blocks.
4. **Config layering** – `load_report_config(config_paths=[...])`, per-layer
   absolutising of `relative-to: config` backgrounds, directory-parent bug fix.
   Tests for three-layer precedence and backgrounds from the app layer.
5. **`base_dir` + dict sources** – `context["base_dir"]`; update image/json
   blocks and background loader; dict-source error messages.
6. **Render pipeline** – `render.py` (`RenderEvent`, `RenderCallbackError`,
   staged pipeline with all three hooks); `load_report` becomes a wrapper.
   Port the callback tests from the stash; add `on_context` tests.
7. **`Ymprint` class** – `app.py`, `default_app`, exports. Tests: instance
   isolation, decorator forms, `event.vars` reaches `{{VAR}}`/`$VAR`,
   `override=True`, dict source requires destination.
8. **Live mode** – port `cli/live.py` from the stash onto `app.render`; watch
   all config layers; port `test_live_init.py` / live callback tests.
9. **CLI factory** – `Ymprint.cli()`; `cli/main.py` uses `default_app.cli()`.
   `CliRunner` test: a custom app's CLI renders its custom block and runs its
   hooks under `convert`.
10. **Docs** – new `docs/guide/custom-applications.md` (worked example: small
    app with a block, the three hooks, bundled config, packaged entry point);
    `docs/reference/api.md` for `Ymprint`/`RenderEvent`/`BlockRegistry`; block
    key grammar (`_code_id`) in `docs/reference/blocks.md`; config layering in
    `docs/guide/configuration.md`; `cli.md`.
11. **Cleanup** – remove `todo_callback.md`, drop the stash, release notes
    (breaking: `register_block` removal), version bump (0.6.0).

## Testing notes

- Existing tests that hand-build contexts rely on the `build_context` default
  registry and the single-path `load_report_config` form, so they should pass
  untouched after steps 2–4. That is the regression check.
- Instance isolation: register `_foo` on app A, assert app B treats `_foo` as
  an unregistered key.
- `register_fonts()` mutates ReportLab's process-global font table. That's fine
  for now (idempotent), but it means apps can't have conflicting font names;
  note this in the docs.

## Open questions (smaller, can be decided during implementation)

- Should unregistered `_xxx` keys become an "Unknown block" error instead of a
  heading (catches typos)? It's a behaviour change, so it's not in the plan by default.
- ~~`on_context` changing styles~~ → decided: changes to the style models take
  effect (styles are rebuilt after the hooks).
