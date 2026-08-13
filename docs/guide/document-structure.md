# Document structure

A YMPrint document is an ordinary YAML file. The **shape of the YAML is the shape of the
document**: nesting becomes hierarchy, list order becomes reading order. This page explains
how each YAML construct is rendered.

## The core idea: keys are headings

A mapping key whose value is document content becomes a **heading**, and the value is laid
out underneath it.

```yaml
Report title:
  - First paragraph under the heading.
  - Second paragraph under the heading.
```

Because a YAML key can only have **one** value, anything with more than a single piece of
content underneath a heading must be written as a **list**. A list is a **sequence of
content items rendered in order**: a string becomes a paragraph, a mapping becomes a
sub-heading with its own content. A list is *not* a bulleted list — bullets and numbers are
opt-in via the [`_ul` and `_ol`](#bullet-lists) blocks.

### Heading → paragraph → sub-heading

To build a `Heading → Paragraph → Sub-heading` structure you need a list, because the
paragraph *and* the sub-heading are effectively two values under the top-level heading:

```yaml
Report title:
  - >
    A paragraph that sits directly under the top-level heading.
  - Sub-heading:
      >
      Turning a list item into a key/value pair makes the key a sub-heading and
      its value the content beneath it.
```

### Heading → paragraph (repeated)

If you only ever have one paragraph per heading, you can skip the list and use a plain
`key: value` structure:

```yaml
Introduction: >
  A single paragraph under the "Introduction" heading.
Scope: >
  A single paragraph under the "Scope" heading.
```

## Paragraphs and line wrapping

Use YAML's block scalar `>` to write a word-wrapped paragraph. Single newlines in the
source are folded into spaces; a **blank line** starts a new paragraph.

```yaml
Notes:
  - >
    You can insert linebreaks wherever you want within the YAML source, but new
    paragraphs won't be created unless you use two newlines (a blank line).

    This is a second paragraph.
```

:::{tip}
Inline markdown is supported inside text — see [Inline formatting](#inline-formatting)
below.
:::

(bullet-lists)=
## Bullet lists — `_ul`

A bare list is a sequence of paragraphs/sub-sections (see above), **not** a bulleted list.
To render bullets, wrap the items in a `_ul` block:

```yaml
Standard content types:
  _ul:
    - Bullet 1
    - Bullet 2
    - Bullet 3
```

:::{note}
This is a change from earlier versions, where a plain list of strings was auto-bulleted.
A list on its own now means "these items in order" (paragraphs and sub-sections); bullets
are explicit. This removes the ambiguity where a single wrapped paragraph under a heading
would come out as a one-item bullet.
:::

### Nested bullets

Nest a list inside a `_ul` item to indent bullets. The bullet symbol changes with depth
(the default hierarchy is `•‣⁃∘`):

```yaml
_ul:
  - Bullet 1
  - Bullet 2
  - - Sub-bullet A
    - Sub-bullet B
    - Sub-bullet C
```

## Ordered lists — `_ol`

Wrap the items in an `_ol` block. Numbering is automatic by position, and nesting a list
inside an item creates a nested numbered list:

```yaml
Ordered list:
  _ol:
    - First item
    - Second item
    - - Nested first
      - Nested second
```

## Tables

A list of mappings becomes a **table**. The keys of the first mapping are the column
headers, and each mapping is a row:

```yaml
Tables:
  - Item Number: 12.01
    Description: There is a problem here. This report documents it.
    Location: Under the stairs
  - Item Number: 12.02
    Description: There are five ladybugs on the table cloth.
    Location: Kitchen
  - Item Number: 45
    Description: The item numbers are arbitrary values you structure.
    Location: This table
```

Table appearance (padding, header style, row banding, rule lines) is controlled by
`_tablestyle`. See [Configuration → Table styles](#cfg-tablestyle).

## Inline formatting

Text values support a small amount of inline markdown, converted to styled runs in the PDF:

| Markdown | Renders as |
| --- | --- |
| `` `code` `` | inline code on a light grey background in a monospace face |
| `*emphasis*` | *italic* |
| `**strong**` | **bold** |
| `[label](url)` | a link |

```yaml
Notes:
  - >
    There are `three` categories of configuration, and the **document config**
    always wins over *project* config.
```

## Configuration and blocks

Two kinds of underscore-prefixed keys change the default behaviour:

- **Front-matter configuration** at the document root — `_doc`, `_style`, `_tablestyle`,
  and `_vars`. These set page layout, styling, and variables. See
  [Configuration](configuration.md) and [Variables](variables.md).
- **Blocks** anywhere in the content — `_img`, `_info`, `_code`, `_py`, `_spacer`, and
  friends. These expand into custom content. See the [Blocks reference](../reference/blocks.md).

```yaml
_style:            # front-matter configuration
  body:
    font: NotoSans

Report:
  - Photo:
    _img:          # a block
      src: photo.png
      caption: "Figure 1"
```

## A complete example

```yaml
Report title:
  - >
    Here is the first paragraph. You will notice the `-` character creates a YAML list.
  - Sub-heading: >
      A paragraph and a sub-heading under one top-level heading require a list.
  - Standard content types:
    - Bullets:
        _ul:
          - Bullet 1
          - Bullet 2
    - Ordered list:
        _ol:
          - First item
          - Second item
    - Tables:
      - Item Number: 12.01
        Location: Under the stairs
      - Item Number: 12.02
        Location: Kitchen
```
