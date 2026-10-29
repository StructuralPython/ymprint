# Building a project — `ym build`

A project's documents and scripts depend on each other: the analysis produces forces,
the calcs produce capacities, a script checks utilizations, and the report shows them.
`ym build` runs all of it in a valid order and skips what is up to date. Nobody lists the
order, and nobody lists any step's inputs.

```bash
ym build                               # everything that's stale, in dependency order
ym build --all                         # ignore staleness
ym build 5-validation/beams/calc.yml   # this target and whatever it needs
ym build --dry-run                     # print the plan and why each step is stale
ym graph                               # print the graph (--format dot | mermaid)
```

```text
  ✓ 3-analysis/frame.py                    0.41 s  (2-project/geometry.yml changed)
  ✓ 5-validation/beams/calc.yml            1.30 s  4 documents  (frame changed)
  · 5-validation/joists/calc.yml             up to date
  ✓ 5-validation/utilizations.py           0.05 s  (capacities changed)
  ✓ 6-documentation/report.yml             0.38 s  (utilizations changed)
Built 4 of 5 steps in 2.1 s
```

`ym build` works on the project whose config (`*.ymprint.yml`) is nearest above the current
directory, or the one containing `--project DIR`.

## The steps

The build runs:

- every document matched by `_build.documents` in the project config. A pattern that matches
  no files is an error.
- every producer named in a `_data` entry's `from:`: documents and `.py` scripts.
- every document with a [`_render`](parameterized-documents.md) entry, rendered as that
  entry says (once per parameter set, to its `output`).

```yaml
# project.ymprint.yml
_data:
  geometry: 2-project/geometry.yml
  frame:
    path: build/data/frame.json
    from: 3-analysis/frame.py
  capacities:
    from: 5-validation/beams/calc.yml
  utilizations:
    from: 5-validation/utilizations.py
_build:
  documents:                     # globs, relative to this file
    - 6-documentation/*.yml
```

## Scripts

A script joins the build by being named in `from:`. It reads data by name and publishes
what it produces with `ymprint.project`:

```python
# 3-analysis/frame.py
from ymprint.project import data, publish

geometry, loads, design = data("geometry"), data("loads"), data("design")
model = build_frame(geometry, loads, design, data("sections"), data("materials"))
model.analyze()
publish("frame", extract_results(model))     # writes where `frame` is declared
```

| Function | Meaning |
| --- | --- |
| `data(name)` | A fresh copy of data source `name`. |
| `path(name)` | The file a data source is read from, for code that does its own I/O. |
| `publish(name, value)` | Writes `value` as JSON for data source `name`. The script must be named in the source's `from:`. |

The project is found from the script's own location, so a script also runs on its own
(`python 3-analysis/frame.py`). Under `ym build`, scripts run in the same process,
as `python script.py` would run them, with their folder importable.

## How the order is found: recorded, not declared

What produces each data source is declared once, by `from:`. What each step **reads** isn't
declared at all; it is recorded as the step runs: every data source a document uses (in
text, `_py`, `_hc`, `for_each` or `ym.path()`) and every `data()` call in a script, with a
hash of each file read. The records live in `build/.ym/deps.json`.

When a step reads a data source, `ym build` first brings that source's producers up to date.
So even the first build, with nothing recorded, runs every step after the data it needs.

A step is **stale**, and runs, when:

- it has never been built, or its last build failed;
- its source file changed;
- any file it read last time changed (by content hash), including the project config;
- one of its outputs (its PDFs, its exports) is missing; or
- the YMPrint or plugin version changed.

A producer that runs again but writes the same data doesn't make its readers stale. For
example, editing a calc's wording rebuilds that calc only, while a change that alters its
capacities also rebuilds the utilization check and the report.

A step that reads data it produces itself, or a cycle of steps, is an error. A failed step
fails the steps that need its data; the others still build, and the exit code is 1.

:::{note}
Files a document or script opens by itself (`open("…")` in `_py`) aren't recorded. Declare
them as [`_data`](data-sources.md) and read them by name (or with `ym.path()`), or use
`ym build --all`.
:::

## `ym graph`

Prints each data source with its producers, and each step with the data it read on its last
build. `--format dot` gives a Graphviz graph and `--format mermaid` a Mermaid flowchart.

```text
Data sources:
  geometry = 2-project/geometry.yml
  frame ← 3-analysis/frame.py
  capacities ← 5-validation/beams/calc.yml
  utilizations ← 5-validation/utilizations.py
Steps:
  3-analysis/frame.py  reads: geometry
  5-validation/beams/calc.yml  reads: design, frame, sections
  5-validation/utilizations.py  reads: capacities, frame
  6-documentation/report.yml  reads: utilizations
```
