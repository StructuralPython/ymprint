# Installation

YMPrint requires **Python 3.14 or newer**.

## With pip

```bash
pip install ymprint
``` 

## With `uv` (recommended)

[`uv`](https://docs.astral.sh/uv/) is the fastest way to install and run YMPrint as a tool:

```bash
uv tool install ymprint
```

This puts the `ym` command on your `PATH`. Verify it:

```bash
ym --help
```

To run it once without a persistent install:

```bash
uvx ymprint --help
```

## With `pip`

```bash
pip install ymprint
```

## From source

```bash
git clone https://github.com/StructuralPython/yamlreports.git
cd yamlreports
uv sync
uv run ym --help
```

## What gets installed

Installing YMPrint pulls in everything needed to render PDFs:

| Dependency | Role |
| --- | --- |
| `reportlab` | The PDF layout engine that typesets your document. |
| `pymupdf` | Read PDF backgrounds, fill form fields, overlay content. |
| `jinja2` | Interpolate `_vars` into your content. |
| `wenmode` | Parses inline markdown (the latest library from lepture!) |
| `pydantic` | Validate the document, style, and table configuration. |
| `pygments` | Syntax highlighting for `_code` and `_py` blocks. |
| `ruamel-yaml` | Parse your report YAML. |
| `typer` | The `ym` command-line interface. |

A set of fonts is bundled with YMPrint, so documents render consistently on any machine
without needing to rely on system fonts (which may or may not load easily into ReportLab). See the [Fonts reference](reference/fonts.md).

:::{tip}
`matplotlib` is **not** a hard dependency. Install it in the same environment only if you
plan to use the [`_matplotfig`](#block-matplotfig) block.
:::

## Live preview (optional)

The [`ym live`](reference/cli.md#ym-live) command opens the rendered PDF in the
[Okular](https://okular.kde.org/) document viewer which hot-reloads your PDF on every save. 

The Okular PDF viewer is available for _every_ desktop platform (Windows, Mac, and many flavours of Linux).

If you
want to use live mode, install Okular through your system package manager, for example:

```bash
sudo apt install okular      # Debian / Ubuntu
```

If you are on Windows, you can install Okular with Winget or with the Windows store.
