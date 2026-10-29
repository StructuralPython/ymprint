# CLI reference

YMPrint installs a single command, `ym`, with two subcommands.

```bash
ym --help
```

| Command | What it does |
| --- | --- |
| [`ym convert`](#ym-convert) | Render a YAML file to PDF (once per parameter set, if it has them). |
| [`ym live`](#ym-live) | Render, open the PDF in Okular, which will hot-reload on every save. |

## `ym convert`

Render a YAML file to a PDF. A document with a `_render` entry in the project config is
rendered as it says: once per parameter set, to its `output`. See
[Parameterized documents](../guide/parameterized-documents.md).

```bash
ym convert SRC [--dest DEST] [--config-dir DIR] [--var NAME=VALUE ...] [--only NAME=VALUE ...]
```

| Argument | Required | Meaning |
| --- | --- | --- |
| `SRC` | ✅ | Path to the source YAML report. |
| `--dest` | | Output PDF path. Defaults to the source path with a `.pdf` extension, written next to the source file. |
| `--config-dir` | | Directory holding a config file. It is layered over any project config found by searching the source file's parent directories, which in turn is layered over the internal defaults. |
| `--var` | | Set a variable, `NAME=VALUE` (repeatable), over the document's `_vars`. Renders once, ignoring the document's parameter sets. Values are read as YAML scalars. |
| `--only` | | Render only the parameter sets with `NAME=VALUE` (repeatable). |

If any parameter set fails, the others still render, the failures are listed, and the
exit code is 1. `--dest` cannot be used with a document that has parameter sets.

**Examples**

```bash
# Write report.pdf next to report.yml
ym convert report.yml

# Choose an explicit output path
ym convert report.yml --dest output/inspection.pdf

# Use a shared project config directory
ym convert report.yml --config-dir ../shared-config
```

On success it prints the resolved output path:

```text
✍️ .... 📝 ... PDF created: /path/to/report.pdf
```

## `ym live`

Render the PDF, open it in the [Okular](https://okular.kde.org/) viewer, and rebuild
automatically whenever the source (or the non-default config file) changes.

Ideal for live authoring.

```bash
ym live SRC [--dest DEST] [--config-file FILE] [--var NAME=VALUE ...] [--only NAME=VALUE ...]
```

| Argument | Required | Meaning |
| --- | --- | --- |
| `SRC` | ✅ | YAML file to render and watch. |
| `--dest` | | Output PDF path. Defaults to the source path with a `.pdf` extension. |
| `--config-file` | | A config file layered over any discovered project config. |
| `--var` | | Set a variable, `NAME=VALUE` (repeatable). |
| `--only` | | For a document with parameter sets: preview the one set with `NAME=VALUE`, written to its `output`. Without it, live mode previews the `_vars` defaults. |

**What it watches.** Live mode watches the source file and every config file in play
(the discovered project config, the `--config-file`, and a custom application's own
config), plus the [data files](../guide/data-sources.md) the document read. When any of
them changes, the PDF is re-rendered and Okular refreshes.

**Starting from scratch.** If `SRC` does not exist yet, live mode offers to create a
minimal starter document at that path (after a confirming prompt) so you can begin
authoring immediately. Decline the prompt to exit without creating anything.

**Locked PDFs.** Some viewers (such as Okular on Windows) keep the PDF open and stop it
being replaced; live mode then overwrites the PDF in place instead. A sync client (such
as the Egnyte Drive client) can hold the PDF open for a moment after it is written. Live
mode retries briefly; if the PDF is still locked, it switches to rendering a local
preview copy, opens it in a new Okular window, and saves it over `--dest` when you press
`Ctrl+C` (or if live mode crashes). If the PDF is still locked at that point, live mode prints where the preview
is so you can copy it by hand.

```bash
ym live report.yml
```

```text
YMPrint live mode  watching report.yml — Ctrl+C to quit
```

Edit and save your report in another window; the preview updates. Press `Ctrl+C` to stop.

:::{note}
Live mode uses **Okular** as the viewer. Install it via your system package manager (for
example `sudo apt install okular` on Debian/Ubuntu). See
[Installation → Live preview](../installation.md#live-preview-optional).
:::

## Config discovery

YMPrint walks **up** from the source file's directory looking for a config file (a
`*.ymprint.yml` project config). The nearest match is used. A `--config-dir` (or
`--config-file`) is layered on top of it.

This enables a whole tree of documents to share one project style. See
[Configuration](../guide/configuration.md).

## Your own CLI

The `convert` and `live` commands can be served by your own application, with its own
blocks, render hooks and house style. For example, `calcsheet convert beam.yml`. See
[Custom applications](../guide/custom-applications.md).
