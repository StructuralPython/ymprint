# Design: Slide presentations

Status: in progress
Branch: `features/slides` (off `main`), one PR per step

## Motivation

A presentation can already be written with existing YMPrint features (see
`Examples/presentation.yml`): one top-level heading per slide, a landscape page, and a
`_pagebreak` at the end of every slide. That works but is noisy, and there is no way to
place content side by side (text on the left, an image on the right). Adding general
multi-column layout to every YMPrint document would complicate its simple
top-to-bottom model, so frames are scoped to slides.

## Decisions (locked)

1. **Slides come from headings.** With slide mode on, every top-level heading is one
   slide: its title and content are rendered and a page break follows automatically.
   A repeated `_slide:` key per slide is not possible because the YAML loader (ruamel,
   round-trip) rejects duplicate keys.
2. **Settings live in `_doc`.** `slides: true` turns slide mode on and `layouts:`
   defines named frame layouts. Both layer through project config files like
   `templates` does; no fourth config scope is added.
3. **Overflow defaults to `shrink`.** A frame's content is scaled down to fit
   (ReportLab `KeepInFrame`). Each frame may set `overflow: error | truncate` instead.
4. **Explicit page sizes ignore `landscape`.** `page-size: [width, height]` (points)
   is used exactly as written; `landscape` only rotates named sizes.

## Source syntax

```yaml
_doc:
  page-size: [960, 540]
  slides: true
  layouts:
    two-column:
      title: [0, 0, 1, 0.15]
      left:  [0, 0.2, 0.48, 0.8]
      right: [0.52, 0.2, 0.48, 0.8]

How long have computers been in structural engineering?:
  - 1990s?
  - 1980s?

What people were doing in 1966:
  - _slide: two-column
  - Some text on the left
  - _frame: right
  - _img:
      source: bbc_1966.png
```

- **Frames** are `[x, y, w, h]` within the template's content box (inside the
  margins), origin top-left. Values ≤ 1 are fractions of the box; values > 1 are
  points (the `parse_width` convention). A frame may instead be a mapping with `box:`,
  `valign: top | middle | bottom` and `overflow: shrink | error | truncate`.
- **Layouts.** The built-in `default` layout has a single `body` frame. If a layout
  has a `title` frame the heading is drawn there; otherwise it flows at the top of the
  first frame.
- **`_slide`** must be the first item of a slide. It takes a layout name, or a mapping
  `{layout:, template:}`. Settings apply to that slide only; a slide that names no
  template uses the deck's first template.
- **`_frame: name`** routes the content that follows into that frame. Content before
  any `_frame` goes to the layout's first non-title frame.
- `_slide` / `_frame` are structural directives (like `_textstyle`), not registered
  blocks. Unknown layouts/frames, or use outside slide mode, are authoring errors.

## Rendering

1. The slide converter splits a slide's items by `_frame` and runs `build_story` on
   each group with a context whose current content box is that frame. Blocks size
   themselves via a `content_box(context)` helper (current frame, else `all_pages`).
2. Each frame's flowables are wrapped in `KeepInFrame` with the frame's overflow mode.
3. A `SlideFlowable` fills the page's content box and draws each frame at its
   position with `Frame.addFromList`.
4. Every slide after the first emits `[NextPageTemplate(t), PageBreak]` before its
   content, so per-slide templates (and their PDF backgrounds) work.

ReportLab's native multi-frame page templates were rejected: content silently flows
from frame to frame and page to page, and there is no "go to named frame".

## Steps

1. `page-size` as `[width, height]`.
2. Slide mode: automatic page break per top-level heading, `default` layout.
3. Layouts, `_frame`, `_slide`, `SlideFlowable`; blocks size from `content_box`.
4. Per-slide `template`, docs (`docs/guide/slides.md`) and an example deck.
