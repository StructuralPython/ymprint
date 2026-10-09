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

## Scoped text styles

Define named text styles under `_style.styles`, then switch the active family part-way through
the document with the `_textstyle` block. Here a `fine-print` style (smaller, grey) and a
`callout` style (larger, blue, centred) are switched in and out — each swap restyles the body,
headings, and lists that follow it, and reverts when the section ends. See
[Configuration → Named text styles](#style-named).

```{literalinclude} ../Examples/Text Styles/report.yml
:language: yaml
```

::::{container} ym-single-shot
```{image} _static/examples/text-styles.png
:alt: Scoped text styles — default, fine-print, and callout families switched within one document
:class: ym-page-shot
```
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

::::{container} ym-single-shot
```{image} _static/examples/pdf-backgrounds.png
:alt: PDF backgrounds — content overlaid on a custom template with populated form fields
:class: ym-page-shot
```
::::

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

---

## Slides

A 1080p deck (`page-size: [1920, 1080]`) in slide mode: custom layouts and frames, a
different PDF background for title, section, content and closing slides, and most of the
block catalogue (code, executed Python, matplotlib, admonitions, tables) sized for a
screen. The four backgrounds are vector PDFs drawn with ReportLab by
`make_backgrounds.py`, which sits next to the deck. See
[Slide presentations](guide/slides.md).

```{literalinclude} ../Examples/Slides/slides.yml
:language: yaml
```

::::{grid} 1 2 2 2
:gutter: 3

:::{grid-item}
```{image} _static/examples/slides-1.png
:alt: Slides example, title slide
:class: ym-page-shot
```
+++
<p class="ym-page-caption">Slide — Title slide — custom hero background</p>
:::

:::{grid-item}
```{image} _static/examples/slides-2.png
:alt: Slides example, a slide that shows its own source
:class: ym-page-shot
```
+++
<p class="ym-page-caption">Slide — A slide that shows its own source</p>
:::

:::{grid-item}
```{image} _static/examples/slides-3.png
:alt: Slides example, images in a frame
:class: ym-page-shot
```
+++
<p class="ym-page-caption">Slide — Images in a frame</p>
:::

:::{grid-item}
```{image} _static/examples/slides-4.png
:alt: Slides example, executed python feeding a table
:class: ym-page-shot
```
+++
<p class="ym-page-caption">Slide — Executed Python feeding a table</p>
:::

:::{grid-item}
```{image} _static/examples/slides-5.png
:alt: Slides example, a live matplotlib figure
:class: ym-page-shot
```
+++
<p class="ym-page-caption">Slide — A live matplotlib figure</p>
:::

:::{grid-item}
```{image} _static/examples/slides-6.png
:alt: Slides example, admonitions and quotes, scaled for slides
:class: ym-page-shot
```
+++
<p class="ym-page-caption">Slide — Admonitions and quotes, scaled for slides</p>
:::

:::{grid-item}
```{image} _static/examples/slides-7.png
:alt: Slides example, tables from lists of mappings
:class: ym-page-shot
```
+++
<p class="ym-page-caption">Slide — Tables from lists of mappings</p>
:::

:::{grid-item}
```{image} _static/examples/slides-8.png
:alt: Slides example, closing slide
:class: ym-page-shot
```
+++
<p class="ym-page-caption">Slide — Closing slide</p>
:::

::::
