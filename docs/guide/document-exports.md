# Document exports — `_export`

A calculation document computes values that later stages need. For example, beam
capacities feed a utilization check. Rather than the document writing a file as a side
effect, it **declares** what it produces, and YMPrint writes it.

## Declaring exports

```yaml
# 5-validation/beams/calc.yml
_export:
  Vr: $V_r
  Mr: $M_r
  section: "{{ design[member_name].section }}"

Beam design – {{ member_name }}:
  - _hc: |
      V_r = 0.66 * phi * f_y * A_w
      ...
```

Exports are evaluated **after** the document's content is built, so every `_py` and `_hc`
block has run. A `$var` exports the object itself; any other string is a Jinja template
(its result is text). Mappings and lists can nest. A missing variable is an authoring error
that names the document and its parameter set.

The value a reviewer reads in the PDF and the value the next stage uses are the same
computation.

## Exports as a data source

A `_data` entry names its producers with `from:`. Consumers read it by name like any other
source; they never see a path.

```yaml
# project.ymprint.yml
_data:
  capacities:
    from:
      - 5-validation/beams/calc.yml
      - 5-validation/columns/calc.yml
_render:
  5-validation/beams/calc.yml:
    for_each: "[m for m in design if m.startswith('B')]"
    as: member_name
    output: build/beams/{{ member_name }}.pdf
```

```yaml
# 5-validation/utilizations.yml
Utilizations:
  - _py: |
      dcr = {m: loads[m]["Vf"] / capacities[m]["Vr"] for m in capacities}
```

- A document rendered [once per parameter set](parameterized-documents.md) produces one
  entry per set, under its key: `{"B01": {"Vr": ..., ...}, "B02": {...}}`. A document
  without parameter sets produces its `_export` mapping as is.
- Each producer's output is written **whole** on every full render (`ym convert`,
  `Ymprint.render_all`), so a deleted member disappears and render order doesn't matter.
  Nothing needs to exist beforehand.
- Each producer has its own file, under `build/.ym/exports/`. Consumers see the **union**
  of the producers' mappings. Two producers giving the same key is an error: every value
  has exactly one author.
- Files are written atomically (to a temporary file, then renamed).
- The `from:` declaration is the only place the relationship is stated; a build tool
  uses it to order the build.

Exports are **not** written when only some parameter sets were rendered (`--only`), or by
`ym live` and `--var` renders. If any parameter set fails, the producer's previous output is
removed rather than left stale, so consumers fail loudly instead of reading old values.

### A single producer at a fixed path

A source with one producer can give a `path`, to put the file somewhere visible:

```yaml
_data:
  beam_capacities:
    path: build/data/beam_capacities.json
    from: 5-validation/beams/calc.yml
```

### The build directory

Produced data is stored under `<project root>/build`. Change it in the project config:

```yaml
_build:
  dir: _build
```

## From Python

```python
run = app.render_all("5-validation/beams/calc.yml")
run.exports   # {"B01": {"Vr": ..., "section": "W310x74"}, ...}
run.written   # the export files written

event = load_report("calc.yml", "calc.pdf", vars={"member_name": "B01"})
event.exports  # {"Vr": ..., "Mr": ..., "section": "W310x74"}
event.pdf      # Path
```

## Serialization

JSON-native values are written as they are. Paths become strings, sets become lists, and
anything with `__float__` becomes a float. A plugin can register richer types, for example
a units package turning a quantity into `{"value": 30200.0, "unit": "N"}`:

```python
from ymprint import register_serializer

register_serializer(Quantity, lambda q: {"value": float(q), "unit": q.unit})
```

See [Plugins](../reference/api.md#plugins) to register serializers when a package is installed.
