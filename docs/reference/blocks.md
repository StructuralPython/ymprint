# Blocks reference

Blocks are YMPrint's special content types for things plain YAML prose can't express —
images, admonitions, code, figures, and more. Some mirror markdown (images, code blocks);
others extend it (admonitions, styled horizontal rules, executable Python).

## Block syntax

A block is a **key that begins with an underscore**, e.g. `_img` or `_spacer`. Its value is
a block-specific data structure, typically either a scalar or a mapping that allows several arguments to be passed.

Blocks appear wherever content is allowed, typically as list items:

```yaml
Report:
  - Photos:
    _img:
      src: photo.png
      caption: "Figure 1"
  - _info: A short informational note.
  - _pagebreak:
```

All block codes accept an optional, user-defined **suffix** after the underscore code, e.g. `_hrule_red` and
`_hrule_blue` are both handled by the `_hrule` block — the suffix simply keeps the YAML keys
unique when you use several in one list and allows you to meaningfully identify them if you are using several in a row.

The suffix does not affect how the block is executed. It is simply an optional identifier.

## Block catalogue

| Block | Purpose |
| --- | --- |
| [`_img`](#block-img) | Embed an image with an optional caption. |
| [`_matplotfig`](#block-matplotfig) | Embed a matplotlib figure object with an optional caption. |
| [`_info` / `_warning` / `_danger` / `_tip` / `_note`](#block-admonitions) | Callout boxes. |
| [`_blockquote`](#block-blockquote) | A quotation with attribution. |
| [`_code`](#block-code) | A non-executable code block. |
| [`_py`](#block-py) | Execute Python and optionally show the syntax-highlighted source. |
| [`_loadjson`](#block-loadjson) | Load variables into the document from a JSON file. |
| [`_pagebreak`](#block-pagebreak) | Force a page break. |
| [`_hrule`](#block-hrule) | A customizable horizontal rule. |
| [`_spacer`](#block-spacer) | Insert vertical whitespace. |

---

(block-img)=
## `_img` — Images

Embed a raster image (PNG, JPEG, …) with a caption. Paths are relative to the report file
(or absolute).

```yaml
_img:
  src: catpuccin.png
  caption: "Figure 1: The catpuccin cat"
  scale_ratio: 0.3
```

| Parameter | Required | Default | Meaning |
| --- | --- | --- | --- |
| `src` | ✅ | — | Path to the image, relative to the `.yml` file or absolute. |
| `caption` | ✅ | — | Caption text shown below the image. |
| `scale_ratio` | | `1` | Scale factor relative to the available content width. The image is automatically shrunk to fit the frame if it would overflow. |

---

(block-matplotfig)=
## `_matplotfig` — Matplotlib figures

Embed a **matplotlib `Figure` object** that you built in a [`_py` block](#block-py).
Pass the figure through the [`$var` syntax](#vars-passing-objects).

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
      scale_ratio: 0.8
```

| Parameter | Required | Default | Meaning |
| --- | --- | --- | --- |
| `fig` | ✅ | — | A matplotlib `Figure`, passed as `$var`. |
| `caption` | | `""` | Caption text shown below the figure. |
| `scale_ratio` | | `0.8` | Scale factor relative to the available content width. The figure image is automatically shrunk to fit the frame if it would overflow.|

:::{note}
`matplotlib` is an optional dependency — install it in the same environment as YMPrint to
use this block.
:::

---

(block-admonitions)=
## Admonitions

Callout boxes for drawing attention. Five variants are available, each taking the callout
text as its value:

```yaml
Report:
  - _info: Here is an "info" admonition.
  - _warning: Here is a "warning" admonition.
  - _danger: Here is a danger admonition.
  - _tip: Here is a helpful tip.
  - _note: This is useful when you want to give a note.
```

| Block | Use for |
| --- | --- |
| `_info` | General information. |
| `_warning` | Something the reader should be careful about. |
| `_danger` | A serious caution. |
| `_tip` | A helpful suggestion. |
| `_note` | An aside worth remembering. |

---

(block-blockquote)=
## `_blockquote` — Block quotes

A quotation with an attribution line.

```yaml
_blockquote:
  quote: “What you do makes a difference, and you have to decide what kind of difference you want to make.”
  attribution: Jane Goodall
```

| Parameter | Required | Meaning |
| --- | --- | --- |
| `quote` | ✅ | The quotation text. |
| `attribution` | | Who said it. |

---

(block-code)=
## `_code` — Preformatted code

A **non-executable**, code block for pre-formatted text. Use this to display code or config
verbatim.

```yaml
_code:
  source: |
    yaml_data: is being shown
    you can put: any yaml data together
    more examples:
      - - cell-padding
        - cell_size
```

| Parameter | Required | Meaning |
| --- | --- | --- |
| `source` | ✅ | The literal text to display. Use a YAML block scalar (`|`) to preserve line breaks. |
| `line_numbers` | | — | Show line numbers alongside the rendered source. |
| `caption` | | — | Caption shown with the rendered code. |
| `width_ratio` | | `0.75` | Width of the rendered code block relative to the content width. |

To **run** code instead of just showing it, use [`_py`](#block-py).

---

(block-py)=
## `_py` — Executable Python

Execute Python with `exec()`. The document's variable dictionary is the global scope, so
any `_vars` you defined are available to the code, and any variables the code creates become
available to the rest of the document (and to blocks via `$var`).

```yaml
_py:
  echo: true
  line_numbers: true
  namespace: py1
  caption: >
    Once this executes, the variables are accessible under the py1 namespace.
  source: |
    import math
    a = 3
    b = 4
    c = math.sin(a / b)
```

:::{note}
The `|` after `source:` tells the YAML parser that this is preformatted text, to respect the line breaks exactly as written, and that text should not be wrapped. 

This is in contrast to the `>` character, often used when writing paragraph content, which allows you to break lines wherever you want in the YAML without breaking lines in the finished document.

Both the `|` and `>` character are part of the YAML spec.
:::

| Parameter | Required | Default | Meaning |
| --- | --- | --- | --- |
| `source` | ✅ | — | Python source to execute. |
| `echo` | | `true` | Whether to render the source as a highlighted code block. Set `false` to run silently. |
| `line_numbers` | | — | Show line numbers alongside the rendered source. |
| `caption` | | — | Caption shown with the rendered code. |
| `namespace` | | — | Nest the created variables under this name (access as `{{namespace.var}}`). Without it, variables land at the top level. |
| `width_ratio` | | `0.75` | Width of the rendered code block relative to the content width. |

:::{warning}
`_py` runs `exec()` in the **same** Python environment as YMPrint. External subprocess
isolation is not currently implemented. Only run documents you trust.

YMPrint is **not** intended to be operated as a public-facing web app.
:::

After execution the variables are usable everywhere:

```yaml
  - - a = {{py1.a}}
    - b = {{py1.b}}
    - c = {{py1.c}}
```

See [Variables → Computing variables in Python](#vars-computing-python).

---

(block-loadjson)=
## `_loadjson` — Load JSON variables

Read a JSON file into your variable context at render time, optionally under a namespace.

```yaml
_loadjson:
  path: extra_vars.json
  namespace: extra_vars
```

| Parameter | Required | Meaning |
| --- | --- | --- |
| `path` | ✅ | Path to the JSON file, relative to the report file. |
| `namespace` | | Nest the loaded values under this name (access as `{{namespace.key}}`). Without it, they load at the top level. |

```yaml
  - - bn = {{extra_vars.bn}}
    - dx = {{extra_vars.dx}}
```

---

(block-pagebreak)=
## `_pagebreak` — Page breaks

Force a page break. Takes `null` as its value (an empty block).

```yaml
Report:
  - >
    This content ends the page.
  - _pagebreak:
  - >
    This content starts a new page.
```

---

(block-hrule)=
## `_hrule` — Horizontal rules

Unlike a markdown rule, `_hrule` is configurable — width, thickness, colour, and line cap.
Use suffixes to keep multiple rules unique in one list.

```yaml
- _hrule_default: null
- _hrule_red:
    width_ratio: 0.8
    thickness: 2
    color: "#bb3322"
- _hrule_blue:
    width_ratio: 0.6
    thickness: 3
    color: "#4422dd"
    cap: round
```

| Parameter | Default | Meaning |
| --- | --- | --- |
| `width_ratio` | `1.0` | Rule width as a fraction of the content width. |
| `thickness` | `1` | Line thickness in points. |
| `color` | `#111111` | Rule colour. |
| `cap` | `square` | Line-cap style: `square` or `round`. |

Passing `null` (as with `_hrule_default: null`) draws a rule with all defaults.

---

(block-spacer)=
## `_spacer` — Vertical space

Insert an arbitrary amount of vertical whitespace, measured in points, to nudge content
positioning by hand.

```yaml
Report:
  - _spacer: 5
  - There is a 5 pt spacer above.
  - _spacer: 20
  - There is a 20 pt spacer above.
```

The value is the height of the space in points. 

:::{tip}
A `_spacer: 0` is a handy trick to stop a
paragraph being misinterpreted as a bullet when it's immediately followed by a list.
:::
