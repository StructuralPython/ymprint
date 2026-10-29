# Parameterized documents

One calculation template often has to produce one PDF per item: `B01.pdf`, `B02.pdf`, and
so on, one for each beam in the design data. In YMPrint, the **document** is the template:
it uses its variables and doesn't say how many times it is rendered. The **project
config** says which renders exist and where they go.

## Passing variables to a render

The building block is passing variables in when you render. They are layered over the
document's `_vars` (they win).

```bash
ym convert beams/calc.yml --var member_name=B01
```

```python
from ymprint.report_reader import load_report

result = load_report("beams/calc.yml", "B01.pdf", vars={"member_name": "B01"})
```

`--var` values are read as YAML scalars: `n=3` is a number, `ok=true` a boolean; quote a
value (`n='3'`) to keep it as text. Repeat `--var` for several variables.

## Declaring the renders — `_render`

```yaml
# project.ymprint.yml
_data:
  design: 4-design/design.yml
_render:
  5-validation/beams/calc.yml:
    for_each: "[m for m in design if m.startswith('B')]"
    as: member_name
    output: build/beams/{{ member_name }}.pdf
```

```yaml
# 5-validation/beams/calc.yml
_vars:
  member_name: B01      # optional default, for previewing in ym live
Beam design – {{ member_name }}:
  - _hc: |
      Z_x = sections[design[member_name]["section"]]["Zx"]
```

`ym convert 5-validation/beams/calc.yml` now renders one PDF per beam in `design.yml`.
Adding `B05` to `design.yml` produces `B05.pdf`, and no other file changes.

| Option | Meaning |
| --- | --- |
| `for_each` | A Python expression that gives the list of parameter sets. It is evaluated with the document's variables (its `_vars` and [`_data`](data-sources.md)) as globals, the same way `_py` code runs. |
| `as` | The variable each item is bound to. A list of names (`as: [member, group]`) unpacks each item. Without `as`, each item must be a mapping of variable names to values. |
| `output` | A Jinja template for the PDF path, using the parameters. It resolves against the config file's directory. Default: `<stem>-<key>.pdf` next to the document. |
| `key` | A Jinja template naming each render, e.g. `"{{ member_name }}"`. Default: the parameter values joined with `-`. |

The keys of `_render` are document paths, relative to the config file. An entry without
`for_each` just sets where that document's PDF goes:

```yaml
_render:
  6-documentation/report.yml:
    output: build/report.pdf
```

Several variables per render: give mappings, or tuples with `as`.

```yaml
for_each: "[{'member_name': k, 'group': v['group']} for k, v in design.items()]"
```

```yaml
for_each: "[(k, v['group']) for k, v in design.items()]"
as: [member_name, group]
```

Inside the document, `ym.params` holds the current parameter set.

## Rendering

| Command | Behaviour |
| --- | --- |
| `ym convert calc.yml` | Renders every parameter set |
| `ym convert calc.yml --only member_name=B02` | Renders the matching set(s) only |
| `ym convert calc.yml --var member_name=B02` | Ignores `_render` and renders once with this value, next to the source |
| `ym live calc.yml` | Watches and re-renders with the `_vars` defaults |
| `ym live calc.yml --only member_name=B02` | Watches and re-renders the B02 set, to its `output` |

All the parameter sets render in one process: the config, fonts and data load once. If
one set fails, the others still render; the failures are listed with their keys
(`B03: KeyError: 'Zx' in _hc`) and the command exits with a non-zero code.

From Python, `Ymprint.render_all()` does the same and returns a `RenderRun`; see the
[API reference](#render-all).
