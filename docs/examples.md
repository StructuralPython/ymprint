# Examples

Each example below is a complete, runnable report from the
[`Examples/`](https://github.com/StructuralPython/yamlreports/tree/main/Examples) directory.
Every preview on this page is the **actual rendered PDF** — produced by running:

```bash
ym convert report.yml
```

Grab any example folder, tweak the YAML, and re-render to see your changes.

---

## Simple example

The essentials: headings from keys, word-wrapped paragraphs, a sub-heading, nested bullets,
an ordered list, and a table. Start here, then read
[Document structure](guide/document-structure.md).

```{literalinclude} ../Examples/Simple example/report.yml
:language: yaml
```

::::{grid} 1 2 2 2
:gutter: 3

:::{grid-item}
```{image} _static/examples/simple-example-1.png
:alt: Simple example, page 1
:class: ym-page-shot
```
+++
<p class="ym-page-caption">Page 1</p>
:::

:::{grid-item}
```{image} _static/examples/simple-example-2.png
:alt: Simple example, page 2
:class: ym-page-shot
```
+++
<p class="ym-page-caption">Page 2</p>
:::

::::

---

## Document configuration

Override the body font, heading font, heading colour, and typographic ratio with a `_style`
block in the document front matter. See [Configuration](guide/configuration.md).

```{literalinclude} ../Examples/Document Configuration/report.yml
:language: yaml
```

::::{grid} 1 2 2 2
:gutter: 3

:::{grid-item}
```{image} _static/examples/document-configuration-1.png
:alt: Document configuration, page 1
:class: ym-page-shot
```
+++
<p class="ym-page-caption">Page 1</p>
:::

:::{grid-item}
```{image} _static/examples/document-configuration-2.png
:alt: Document configuration, page 2
:class: ym-page-shot
```
+++
<p class="ym-page-caption">Page 2</p>
:::

::::

---

## Document variables

Define `_vars`, render them into text with Jinja (`{{ "{{var}}" }}`), and reach into nested
values. See [Variables](guide/variables.md).

```{literalinclude} ../Examples/Document variables/report.yml
:language: yaml
```

::::{grid} 1 2 2 2
:gutter: 3

:::{grid-item}
```{image} _static/examples/document-variables-1.png
:alt: Document variables, page 1
:class: ym-page-shot
```
+++
<p class="ym-page-caption">Page 1</p>
:::

:::{grid-item}
```{image} _static/examples/document-variables-2.png
:alt: Document variables, page 2
:class: ym-page-shot
```
+++
<p class="ym-page-caption">Page 2</p>
:::

::::

---

## PDF backgrounds

Overlay the document onto a designed PDF template and auto-populate its form fields from
`_vars` (here: `field_a`, `field_b`, `field_c`, `field_d`). See
[PDF backgrounds](guide/pdf-backgrounds.md).

```{literalinclude} ../Examples/PDF Backgrounds/report.yml
:language: yaml
```

```{image} _static/examples/pdf-backgrounds.png
:alt: PDF backgrounds — content overlaid on a custom template with populated form fields
:class: ym-page-shot
:width: 70%
:align: center
```

---

## YMPrint blocks

The full block catalogue in one document: images, admonitions, block quotes, page breaks,
horizontal rules, spacers, executable `_py`, a non-executable `_code` block, and `_loadjson`.
See the [Blocks reference](reference/blocks.md).

```{literalinclude} ../Examples/YMPrint blocks/report.yml
:language: yaml
```

::::{grid} 1 2 2 2
:gutter: 3

:::{grid-item}
```{image} _static/examples/ymprint-blocks-1.png
:alt: YMPrint blocks, page 1
:class: ym-page-shot
```
+++
<p class="ym-page-caption">Page 1 — images &amp; admonitions</p>
:::

:::{grid-item}
```{image} _static/examples/ymprint-blocks-2.png
:alt: YMPrint blocks, page 2
:class: ym-page-shot
```
+++
<p class="ym-page-caption">Page 2 — quotes, rules &amp; spacers</p>
:::

:::{grid-item}
```{image} _static/examples/ymprint-blocks-3.png
:alt: YMPrint blocks, page 3
:class: ym-page-shot
```
+++
<p class="ym-page-caption">Page 3 — executable Python</p>
:::

:::{grid-item}
```{image} _static/examples/ymprint-blocks-4.png
:alt: YMPrint blocks, page 4
:class: ym-page-shot
```
+++
<p class="ym-page-caption">Page 4 — code &amp; JSON variables</p>
:::

::::
