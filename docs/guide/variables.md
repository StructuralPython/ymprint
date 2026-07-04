# Variables

Document variables let you define values once and reuse them — as text interpolated into
your content, or as data passed into blocks.

## Defining variables — `_vars`

Add a `_vars` mapping to the **root** of your report. Values can be any native YAML type:
string, integer, float, `null`, boolean, list, or mapping.

```yaml
_vars:
  a: "hello"
  b: true
  c: 23
  d: -0.013
  e: {'key': 'value', 'key2': 'val2'}
  f: ['val1', 'val2']
```

There are two distinct ways to use a variable: **Jinja interpolation** for display text,
and the **`$var` syntax** for passing objects into blocks.

## Interpolating into text with Jinja

Inside any displayed string, reference a variable with double braces. Values are rendered
with Jinja and **stringified** — you see `str(value)`.

```yaml
Document Variables:
  - >
    This document defines a, b, c, d, e, and f.
  - - a = {{a}}
    - b = {{b}}
    - c = {{c}}
    - d = {{d}}
    - e = {{e.key2}}      # index into a mapping
    - f = {{f}}
```

Use dotted access (`{{e.key2}}`) to reach into nested mappings.

:::{tip}
A paragraph immediately followed by a list can sometimes be misread as a bullet. A common
fix is a zero-height spacer between them:

```yaml
  - _spacer: 0    # prevents the paragraph above being read as a bullet
```
:::

(vars-passing-objects)=
## Passing Python objects into blocks — `$var`

Some blocks need **real objects**, not stringified text — for example a matplotlib figure.
For those, reference a variable with the bash-style `$name` syntax. This passes the actual
Python object through to the block's parameter.

```yaml
_vars:
  small_space: 5

Report:
  - Some text.
  - _spacer: $small_space    # reuse a consistent spacer everywhere
  - More text.
```

:::{important}
`$var` is only for **block parameters**. You cannot use the `$name` syntax inside content
that is meant to be displayed — attempting to do so raises an error. For display text, use
Jinja (`{{name}}`) instead.
:::

(vars-computing-python)=
## Computing variables in Python — `_py`

The [`_py` block](#block-py) executes Python with the
`_vars` dictionary as its scope. Variables you create in Python become available to the
rest of the document, and vice versa.

```yaml
Report:
  - _py:
      namespace: py1
      source: |
        import math
        a = 3
        b = 4
        c = math.sin(a / b)
  - - a = {{py1.a}}
    - b = {{py1.b}}
    - c = {{py1.c}}
```

This is how you construct objects that don't exist in YAML — such as a matplotlib figure —
and hand them to a block via `$var`:

```yaml
Report:
  - _py:
      echo: false
      source: |
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        ax.plot([0, 1, 2], [0, 1, 4])
  - _matplotfig:
      fig: $fig
      caption: "Figure 1: A computed plot"
```

See [Namespaces](#namespaces) for what `namespace: py1` does.

(vars-loadjson)=
## Loading variables from JSON — `_loadjson`

The [`_loadjson` block](#block-loadjson) reads a JSON
file into your variables at render time, optionally under a namespace.

```yaml
Report:
  - _loadjson:
      path: extra_vars.json
      namespace: extra_vars
  - - bn = {{extra_vars.bn}}
    - dx = {{extra_vars.dx}}
```

## Namespaces

Both `_py` and `_loadjson` accept an optional `namespace`. When you provide one, the
variables they create are nested under that name in the variable dictionary, so you access
them as `{{namespace.variable}}`. Without a namespace, the variables land at the top level
and are accessed directly as `{{variable}}`.

This keeps computed or loaded values from colliding with the variables you defined in
`_vars`.

## Auto-filling PDF form fields

When you overlay your document onto a [PDF background](pdf-backgrounds.md), any variable
whose name **exactly matches** a form-field name in the background PDF automatically fills
that field. See [PDF backgrounds](pdf-backgrounds.md#auto-populated-form-fields) for details
and how to avoid accidental clashes.
