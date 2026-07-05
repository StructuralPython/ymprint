# CLI reference

YMPrint installs a single command, `ym`, with two subcommands.

```bash
ym --help
```

| Command | What it does |
| --- | --- |
| [`ym convert`](#ym-convert) | Render a YAML file to a PDF once. |
| [`ym live`](#ym-live) | Render, open the PDF in Okular, which will hot-reload on every save. |

## `ym convert`

Render a single YAML file to a PDF.

```bash
ym convert SRC [DEST] [--config-dir DIR]
```

| Argument | Required | Meaning |
| --- | --- | --- |
| `SRC` | ✅ | Path to the source YAML report. |
| `DEST` | | Output PDF path. Defaults to the source path with a `.pdf` extension, written next to the source file. |
| `--config-dir` | | Directory holding a project config file. If omitted, YMPrint searches parent directories for one. If a config file is not found in the parent directories, the internal default configuration will take priority. |

**Examples**

```bash
# Write report.pdf next to report.yml
ym convert report.yml

# Choose an explicit output path
ym convert report.yml output/inspection.pdf

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
ym live SRC [DEST] [--config-dir DIR]
```

| Argument | Required | Meaning |
| --- | --- | --- |
| `SRC` | ✅ | YAML file to render and watch. |
| `DEST` | | Output PDF path. Defaults to the source path with a `.pdf` extension. |
| `--config-dir` | | Directory of config files to also watch for changes. |

**What it watches.** Live mode watches the source file and, if a config directory is in
play, the config files within it (`config.ymprint.yml`.
When any of them changes, the PDF is re-rendered and Okular refreshes.

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

When you don't pass `--config-dir`, YMPrint walks **up** from the current working directory
looking for a config file (a `*.ymprint.yml` project config). The nearest match is used.

This enables a whole tree of documents to share one project style. See
[Configuration](../guide/configuration.md).
