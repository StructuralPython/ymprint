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
| `from` | The document(s) or script(s) that produce this data, instead of a person writing it. See [Produced data](#produced-data). |

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

Live mode watches the data files a document reads (as well as its images and PDF
backgrounds), so editing `design.yml` re-renders the document that uses it.

(produced-data)=
## Produced data — `from:`

Some data isn't written by a person: an analysis computes forces, a calc computes
capacities. Its `_data` entry says so with `from:`, which names the file that produces it.

`from:` is **always written on a `_data` entry**, never in the producer. It can name a
document (`.yml`) or a Python script (`.py`), and the entry looks the same either way. What
differs is how the producer hands its values over:

- A **document** declares an [`_export`](document-exports.md) mapping. YMPrint evaluates it
  after the document renders and writes the file.
- A **script** calls `publish(name, value)` from `ymprint.project`. The script writes the
  file itself, when that line runs.

```yaml
# project.ymprint.yml
_data:
  loads: loads.yml                  # written by a person
  forces:
    from: analysis/frame.py         # produced by a script
  capacities:
    from: calcs/beams.yml           # produced by a document
```

Readers can't tell the difference. A document uses `{{ forces.B01.Mf }}` or
`capacities["B01"]` and a script calls `data("forces")`, whatever produced them.

### A script as producer

```python
# analysis/frame.py
from ymprint.project import data, publish

loads = data("loads")
forces = {m: {"Mf": v["w"] * v["L"] ** 2 / 8} for m, v in loads.items()}
publish("forces", forces)           # the name of the _data entry, not a path
```

`publish` takes the name of the data source. It writes `value` as JSON to wherever that
source's output is stored (see [Where produced data is stored](#where-produced-data-is-stored)),
so the script never contains a path. The script must be named in that entry's `from:`.
Otherwise `publish` refuses:

```text
DataSourceError: frame.py cannot publish 'loads': its `_data` entry lists its producers
in `from:` (currently: none).
```

The script writes its data every time it runs, whether under `ym build` or on its own with
`python analysis/frame.py`. If a script is named in `from:` but never calls `publish` for
that name, nothing is written, and documents that read the source fail with
*has not been produced yet*.

One script can produce several sources. Name it in each entry's `from:` and call `publish`
once for each:

```yaml
_data:
  forces:    {from: analysis/frame.py}
  reactions: {from: analysis/frame.py}
```

```python
publish("forces", forces)
publish("reactions", {m: v["w"] * v["L"] / 2 for m, v in loads.items()})
```

### A document as producer

```yaml
# calcs/beams.yml
_export:
  B01: {Mr: $Mr_B01}
  B02: {Mr: $Mr_B02}

Beam capacities:
  - _hc: |
      Mr_B01 = phi * Z_x * f_y
      ...
```

The document never names `capacities`. It declares what it produces, and every `_data`
entry whose `from:` names `calcs/beams.yml` receives that whole `_export` mapping. A
document rendered [once per parameter set](parameterized-documents.md) produces one entry
per set, keyed by the set.

Exports are written on full renders (`ym build`, `ym convert`, `Ymprint.render_all`), but
not by `ym live`, `--var` or `--only` renders. A document named in `from:` without an
`_export` is an error. See [Document exports](document-exports.md) for the details.

### Side by side

| | Document (`.yml`) | Script (`.py`) |
| --- | --- | --- |
| Hands over its values with | an `_export` mapping | `publish(name, value)` |
| Who writes the file | YMPrint, after the document renders | the script, when `publish` runs |
| Producing several sources | every source naming it gets the same `_export` mapping | one `publish` call per source, each with its own value |
| Written when | full renders: `ym build`, `ym convert`, `render_all` | every run: `ym build` or `python script.py` |
| Rendered per parameter set | one entry per set, keyed by the set | — |
| Named in `from:` but produces nothing | error: the document has no `_export` | readers fail: *has not been produced yet* |

### Several producers

`from:` can list several producers, documents and scripts mixed. Each producer's output is
stored separately, and readers see the **union** of their mappings:

```yaml
_data:
  capacities:
    from:
      - calcs/beams.yml             # _export: {B01: ..., B02: ...}
      - analysis/joists.py          # publish("capacities", {"J01": ...})
```

```yaml
- "Joist J01: Mr = {{ capacities.J01.Mr }}, beam B01: Mr = {{ capacities.B01.Mr }}"
```

Each producer must produce a mapping, and no two producers may give the same key: every
value has exactly one author. A source with several producers can't have a `path`, and
`ym.path()` doesn't work for it, because it is read from several files.

### Where produced data is stored

| The `_data` entry has | Each producer writes to |
| --- | --- |
| no `path` | `build/.ym/exports/<source name>/<producer>.json` |
| a `path` (one producer only) | that path, e.g. to keep the file somewhere visible |

```yaml
_data:
  forces:
    path: build/data/forces.json
    from: analysis/frame.py
```

```text
build/
├── data/forces.json                                  # forces (has a path)
└── .ym/exports/
    ├── capacities/calcs__beams.yml.json              # capacities, from the document
    ├── capacities/analysis__joists.py.json           # capacities, from the script
    └── reactions/analysis__frame.py.json             # reactions
```

The build directory can be changed with [`_build: {dir: ...}`](document-exports.md#the-build-directory).
These files belong to YMPrint: read them by name with `_data`, not by path.

### `from:` and `ym build`

`from:` is the only place the producer relationship is stated, and it is all
[`ym build`](building-projects.md) needs. Every producer it names becomes a build step. When
a step reads a source, the build runs that source's producers first:

```text
  ✓ analysis/frame.py                          0.01 s  (never built)
  ✓ calcs/beams.yml                            0.31 s  (never built)
  ✓ analysis/joists.py                         0.00 s  (never built)
  ✓ analysis/check.py                          0.02 s  (never built)
  ✓ report/report.yml                          0.03 s  (never built)
Built 5 of 5 steps in 0.4 s
```

Outside `ym build`, reading a produced source before its producer has run is an error that
names the producer:

```text
Data source 'forces' has not been produced yet: frame.py has not written it
(…/build/data/forces.json). Render …/analysis/frame.py first, or run `ym build`.
```

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
