# Configuration

YMPrint has **three categories** of configuration, applied across **three priority levels**.
A minimal amount of configuration goes a long way because every level inherits from the one
above it.

## The three categories

| Key | Category | Controls |
| --- | --- | --- |
| `_doc` | Document template | Page size, orientation, margins, PDF background, first-page overrides. |
| `_style` | Text styles | Body and heading fonts, colours, size, line spacing, bullet styling. |
| `_tablestyle` | Table styles | Cell padding, header text, row colours and rule lines. |

## The three priority levels

Configuration is resolved from three sources, each overriding the previous:

1. **Internal defaults** (lowest priority) — bundled with YMPrint.
2. **Project config** — a shared config file discovered in a parent directory.
3. **Document config** (highest priority) — front matter written directly in the report.

Each level **inherits** from the level above it, so you only need to specify what you want
to change. Setting just the body font in your document leaves every other default intact.

```text
internal defaults  ─►  project config  ─►  document front matter
   (lowest)                                    (highest, wins)
```

:::{note}
Currently the document template uses a **single content frame**. This only matters if you
want something like a two-column layout where text flows into a second column on the same
page. Everything else — margins, backgrounds, first-page overrides — is fully configurable.
:::

## Inline (document) configuration

Put configuration keys at the **root** of your report file, above your content. This is the
highest-priority level and is the simplest way to style a one-off document.

```yaml
_style:
  body:
    font: NotoSans
  headings:
    font: AppleGaramond
    ratio: minor third
    color: "#dd9922"

Customizing your document:
  - >
    Everything below inherits the styles above.
```

## Project configuration

To make several documents share a look, place a config file named `*.ymprint.yml` in a
parent directory. YMPrint walks up from the current working directory and uses the nearest
one it finds. You can also point at a specific directory with `--config-dir`.

```bash
ym convert report.yml --config-dir ../shared-config
```

A project config file holds the same `_doc`, `_style`, and `_tablestyle` keys. Any document
that doesn't override a given setting inherits it from the project config, which in turn
inherits from the internal defaults.

(cfg-doc)=
## Document template — `_doc`

Controls the page itself.

```yaml
_doc:
  page-size: a4          # a4, letter, etc.
  landscape: false
  margins:
    top: 72.0            # points (72 pt = 1 inch)
    left: 72.0
    right: 72.0
    bottom: 72.0
  background: null       # path to a PDF to overlay onto — see PDF backgrounds
  first-page:            # optional: different margins / background for page 1
    margins:
      top: 72.0
      left: 72.0
      right: 72.0
      bottom: 72.0
    background: null
```

| Key | Meaning |
| --- | --- |
| `page-size` | Named page size, e.g. `a4`, `letter`. |
| `landscape` | `true` to rotate to landscape. |
| `margins` | Page margins in points (`top`, `left`, `right`, `bottom`). |
| `background` | Path to a PDF whose pages are used as a background. See [PDF backgrounds](pdf-backgrounds.md). |
| `first-page` | Optional block giving the first page its own `margins` and `background`. |

(cfg-style)=
## Text styles — `_style`

Controls body and heading typography.

```yaml
_style:
  headings:
    font: Helvetica
    color: "#222222"
    ratio: Major Third      # typographic scale as a musical interval
  body:
    font: Helvetica
    color: black
    size: 10                # points
    spacing: 1.7            # line spacing ratio
    bullets:
      font: Helvetica
      size: 10
      color: black
      symbols: "•‣⁃∘"        # bullet glyphs by nesting depth
      spacing: 10
      indent-bullet: 20
      indent-text: 40
```

### Headings

| Key | Meaning |
| --- | --- |
| `font` | Heading font family (see [Fonts](../reference/fonts.md)). |
| `color` | Heading colour, hex or name. |
| `ratio` | Typographic scale expressed as a **musical interval** — e.g. `minor third`, `major second`, `Major Third`. Larger intervals produce a bigger jump between heading levels. |

### Body

| Key | Meaning |
| --- | --- |
| `font` | Body font family. |
| `color` | Body text colour. |
| `size` | Body font size in points. |
| `spacing` | Line-spacing ratio. |
| `bullets` | Bullet styling — glyph hierarchy (`symbols`), colour, size, and indentation of the bullet (`indent-bullet`) and its text (`indent-text`). |

(cfg-tablestyle)=
## Table styles — `_tablestyle`

Controls how tables (lists of mappings) are drawn.

```yaml
_tablestyle:
  cell-padding:
    top: 7.5
    left: 15
    right: 15
    bottom: 7.5
  headers:
    text:
      font: Helvetica
      size: 12
      color: "#000000"
      bold: true
    row:
      color: "#ffffff"
      lines:
        - above
        - below
  body:
    text:
      font: Helvetica
      size: 11
      color: black
    rows:
      color:
        even: "#ffffff"
        odd: "#ffffff"
      lines:
        - above
```

| Section | Meaning |
| --- | --- |
| `cell-padding` | Inner padding of every cell, in points. |
| `headers.text` | Font, size, colour, and weight of header cells. |
| `headers.row` | Header background colour and which rule `lines` to draw (`above`, `below`). |
| `body.text` | Font, size, and colour of body cells. |
| `body.rows.color` | Row banding — separate colours for `even` and `odd` rows. |
| `body.rows.lines` | Which rule lines to draw around body rows. |

## Putting it together

A document that changes only what it needs, inheriting everything else:

```yaml
_doc:
  background: background.pdf
_vars:
  field_a: 1645
_style:
  body:
    size: 9
  headings:
    ratio: major second

Custom styling with PDF backgrounds:
  - >
    Only the background, body size, and heading ratio are overridden. Margins,
    colours, bullet styles, and table styling all come from the defaults.
```
