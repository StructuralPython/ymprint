(slides)=
# Slide presentations

YMPrint can render a PDF slide deck. Turn on **slide mode** and every top-level heading
becomes one slide on its own page: no `_pagebreak` needed. Slides can also be split into
**frames**, so you can put text on the left and an image on the right.

## A minimal deck

```yaml
_doc:
  page-size: [960, 540]    # 16:9, in points
  slides: true

_style:
  body:
    size: 24

How long have computers been in structural engineering?:
  - 1990s?
  - 1980s?
  - 1970s?

What you just saw:
  - "We have not created the software yet..."
  - The ideas are over 60 years old
```

Each top-level heading is the slide's title and its content fills the slide. Nested
headings stay on their slide.

```{tip}
Page sizes are in points (72 pt = 1 inch). `[960, 540]` is the PowerPoint widescreen size
(13.33 × 7.5 in), where a 24–32 pt body reads well on a projector. A larger page such as
`[1920, 1080]` works too, but scale your text sizes up to match. See
[Custom page sizes](configuration.md#custom-page-sizes).
```

## Layouts and frames

A **layout** is a named set of **frames**, which are rectangles on the slide. Pick a slide's layout
with `_slide` as its **first** item, then send content to a frame with `_frame`:

```yaml
Here is what people were doing in 1966:
  - _slide: two-column
  - We have not created the software yet...     # → the first content frame ("left")
  - The ideas are over 60 years old
  - _frame: right                               # everything after this → "right"
  - _img:
      source: bbc_1966.png
      caption: BBC, 1966
```

- Content before any `_frame` goes to the layout's first frame other than `title`.
- If the layout has a frame named `title`, the slide's heading is drawn there. Otherwise
  the heading is drawn at the top of the first content frame. A title too long for its
  frame is shrunk to fit, like any other frame content. Heading sizes come from
  [`_style`](#cfg-style).
- Blocks size themselves to the frame they are in, so an `_img` with `width_ratio: 1`
  fills its frame's width.
- A slide without `_slide` uses the `default` layout.

### Built-in layouts

| Layout | Frames |
| --- | --- |
| `default` | `body`: the whole slide. |
| `title` | `title` (top 55 %, text aligned to its bottom) and `body` below it. For cover slides. |
| `two-column` | `title` across the top 22 %, then `left` and `right` columns below it. |

### Defining layouts

Define your own layouts under `_doc.layouts`. A layout with the same name as a built-in
one replaces it.

```yaml
_doc:
  page-size: [960, 540]
  slides: true
  layouts:
    image-right:
      title: [0, 0, 1, 0.22]
      text:  [0, 0.25, 0.55, 0.75]
      image:
        box: [0.6, 0.25, 0.4, 0.75]
        valign: middle
        overflow: shrink
```

Each frame is `[x, y, width, height]`, measured from the **top-left** corner of the page
template's content box (the page inside its margins):

- Values **≤ 1** are fractions of the content box (`0.5` is half its width or height).
- Values **> 1** are points.

A frame written as a mapping can also set:

| Key | Meaning |
| --- | --- |
| `box` | `[x, y, width, height]`, as above. |
| `valign` | `top` (default), `middle` or `bottom`: where the content sits within the frame. |
| `overflow` | What happens when the content doesn't fit: `shrink` (default) scales it down to fit, `error` stops with a message naming the slide and frame, `truncate` clips it. |

Layouts can also go in a [project config file](configuration.md), so a whole set of decks
can share them. Layouts defined in the document are added to those from config files.

## Slide settings: `_slide`

`_slide` must be the first item of a slide. Give it a layout name, or a mapping:

```yaml
Thank you:
  - _slide:
      layout: title
      template: closing     # a page template from _doc.templates
  - Questions?
```

| Setting | Meaning |
| --- | --- |
| `layout` | The layout to use. Default `default`. |
| `template` | The [page template](#cfg-doc) (name or 0-based index) for this slide's margins and [PDF background](pdf-backgrounds.md). |

Settings apply to **that slide only**. A slide that doesn't name a template uses the
deck's first template, so the first template listed under `_doc.templates` is the deck's
normal template and the first slide always uses it.

A `_textstyle` among a slide's leading items restyles the whole slide, title included:

```yaml
Fine print:
  - _textstyle: fine-print
  - _slide: two-column
  - ...
```

## Things to know

- `_slide` and `_frame` only work in slide mode, and `_frame` only directly under a
  slide's heading, not inside a sub-section.
- You no longer need `_pagebreak` between slides. One inside a slide's content is
  ignored, but a leftover top-level `_pagebreak` adds a blank page. To change a slide's
  page template, use `_slide: {template: ...}`, not `_pagebreak: <template>`.
- In a mapping-style slide, give repeated `_frame` keys a suffix to keep them unique:
  `_frame_a: left`, `_frame_b: right`.
