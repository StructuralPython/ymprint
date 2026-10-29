# Project data — `_data`

A project usually has data that many documents use: section properties, the design
schedule, analysis results. Declare each file **once**, by name, and every document in the
project can use it by that name. Documents never contain paths to project data.

## The project root

The directory of the project config (the nearest `*.ymprint.yml` above the document; see
[Configuration](configuration.md#project-configuration)) is the **project root**. A
document with no project config above it is its own root: its directory is used.

## Declaring data sources

```yaml
# project.ymprint.yml  (at the project root)
_data:
  sections:  1-reference/sections.yml
  materials: 1-reference/materials.yml
  design:    4-design/design.yml
  frame:     3-analysis/results/frame.json
```

Every document under the project root can now use `sections`, `design` and so on:

- as Jinja variables in text: `{{ design.B01.section }}`;
- as Python globals in `_py` and `_hc` blocks: `sections[design["B01"]["section"]]["Zx"]`;
- as block values with `$design`.

```yaml
# 5-validation/beams/calc.yml — no paths
Beam B01:
  - "Section: {{ design.B01.section }}"
  - _hc: |
      Z_x = sections[design["B01"]["section"]]["Zx"]
```

Renaming the `4-design/` folder means editing one line in the project config.

### Long form

```yaml
_data:
  frame:
    path: 3-analysis/results/frame.json
    loader: json        # default: chosen from the file extension
```

| Option | Meaning |
| --- | --- |
| `path` | The file, relative to the file that declares the entry. |
| `loader` | The loader to read it with. Built in: `yaml` (`.yml`, `.yaml`) and `json` (`.json`). |
| `from` | The document(s) or script(s) that produce this data, instead of a person writing it. See [Document exports](document-exports.md). |

### In a document

A document can declare its own `_data` in its front matter. Its entries are added to the
project's, and replace a project entry of the same name.

```yaml
_data:
  local_loads: loads.yml      # relative to this document
```

A `_vars` name that is also a data source name is an error: rename one of them.
Variables passed in at render time (for example by a `before_render` hook) take
precedence over data sources.

## How data is loaded

- **Lazily.** A source is read the first time the document uses it. A source that a
  document never uses is never read, so a missing file only matters to the documents
  that use it.
- **Once per process.** A file is parsed once and reused until it changes on disk.
- **A fresh copy per render.** Changing data in a `_py` block only changes this render's
  copy; the next document sees the file as it is.

Live mode watches the data files a document reads, so editing `design.yml` re-renders
the document that uses it.

## One path rule

Every relative path resolves against **the directory of the file that declares it**:

| Declared in | Resolves against |
| --- | --- |
| `_data` in a config file | that config file's directory |
| `_data`, `_img`, `_loadjson` in a document | the document's directory |
| A page background in a config file | that config file's directory |
| A page background in a document | the document's directory |

So a document renders the same whether `ym` is launched from the project root, from the
document's folder, or from anywhere else. (A background can still say `relative-to: cwd`
to resolve against the current directory.)

## The `ym` variable

`_py` and `_hc` code runs in the directory `ym` was launched from, like any Python. Code
that needs project paths uses the reserved variable `ym`:

| Name | Value |
| --- | --- |
| `ym.project_root` | `pathlib.Path` of the project root |
| `ym.source` | `pathlib.Path` of the document being rendered |
| `ym.path(name)` | The resolved path of data source `name`, for code that does its own I/O (not for a source with several producers) |
| `ym.params` | The current parameter set, for documents rendered once per parameter set |

```yaml
- _py: |
    import pandas as pd
    loads = pd.read_csv(ym.path("load_schedule"))
```

## Custom loaders

Register a loader for other file types. A plugin package can do this when it is
installed; see [Plugins](../reference/api.md#plugins).

```python
from ymprint import register_loader

register_loader("toml", lambda path: tomllib.loads(path.read_text()), extensions=[".toml"])
```

A loader is a function `loader(path) -> data`. A units-aware loader, for example, could turn
`fy: 350 MPa` into a quantity when the file is read.
