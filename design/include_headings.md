# Design: Heading levels and `_include`

Status: accepted (option D for `_hc` headings). Heading-count levels, the h6 cap,
`section(context)` and PDF bookmarks are implemented in YMPrint 0.11.0.
Follow-up to `scoped_includes.yml`.

## The question

When a partial is included, should its headings nest under the heading where the
`_include` sits, or could authors just agree that top-level headings belong only in the
main document?

Short answer:

- **A partial with no headings doesn't care about levels at all.** This covers the
  motivating case (an `_hc` block plus a `_matplotfig` block). The include site owns the
  heading, so nesting never comes up.
- **A partial with headings needs relative levels.** No convention keeps those headings
  correct without them. Relative levels cost one argument in the implementation.
- **The depth problem from the last round isn't caused by nesting.** It comes from how
  `build_story` counts levels today: it counts YAML containers, not headings. That is a
  separate bug, and fixing it removes the problem whichever include rule is chosen.

## How levels are computed today

`build_story(data, context, level)` gives a heading key the level `max(level, 1)`
(`src/ymprint/story_builder.py:153` and `:160`). `build_content` then builds that
heading's content with `level + 1` for **any** list or mapping
(`src/ymprint/story_builder.py:192`). A list item that is a mapping goes through
`build_content` again, which adds another level.

So a heading's level is the **number of YAML containers around it**, with depths 0 and
1 both clamped to h1. The documentation describes something else:
`docs/guide/document-structure.md` says a mapping in a list "becomes a sub-heading",
meaning one level down.

### Measured

Rendered with the default styles (h1 = 30.5 pt down to h6 = 10 pt, Major Third ratio):

| Source shape | A | B | C | D |
| --- | --- | --- | --- | --- |
| Mapping: `A:` / `B:` / `C:` / `D:` | h1 | **h1** | h2 | h3 |
| List: `A:` / `- B:` / `- C:` / `- D:` | h1 | h2 | **h4** | **h6** |
| List, then mapping: `A:` / `- B:` / `C:` / `D:` | h1 | h2 | h3 | h4 |
| Siblings in a list: `A:` / `- B:` / `- C:` (B and C at the same depth) | h1 | h2 | h2 | |

This shows two separate bugs:

1. **The mapping form doesn't step down at first.** `A: {B: …}` renders B at the same
   size as A, because depth 0 and depth 1 both become h1.
2. **The list form steps down two levels at a time** after the first. The list style is
   the one the docs teach for "heading, then paragraph, then sub-heading". A 5th nested
   heading crashes with `KeyError: "Style 'h8' not found in stylesheet"`, as a raw
   traceback rather than an authoring error. Mapping nesting crashes at the 7th
   heading (`h7`).

Rendering a heading at h6 or below also makes it the same size as body text (10 pt),
so even before the crash, deep headings stop looking like headings.

## The options for partials

Assume the partial is built where `_include` appears, as `scoped_includes.yml` proposes.

### A. Relative: start one level below the include site

`build_story(partial, context, level=level, ...)`. A partial's top-level heading
becomes a sub-heading of whatever holds the `_include`. The result looks as if the
partial had been written in place.

- Correct at any include depth, and the same partial works under h1 or under h3.
- In the output, "top-level headings only in the main document" holds automatically. A
  partial's top-level keys never become h1 unless the `_include` is itself at the top
  level of the document, and there h1 is right.
- With today's counting, depth grows quickly: an include in list form under
  `Calculations:` / `- Beam B01:` starts at h3, its first list-style sub-heading is h5,
  and the next one crashes. **With heading-count levels (below)** the same partial gives
  h3, h4, h5.

### B. Absolute: build the partial as its own document

`build_story(partial, context, level=0, ...)`. The partial's headings get whatever
level they would have in a standalone file.

- Easy to picture when looking at the partial file alone.
- Wrong in context. A partial heading such as `Moment check:` comes out as h1, larger
  than the `Beam B01` heading it sits under.
- The convention "no top-level headings in partials" doesn't save it. Every heading in
  a partial file sits at that file's top level or below, so the author can't write "a
  sub-heading" without wrapping it in a parent heading, and then that parent becomes h1.
  Under today's counting, the level would also depend on whether the partial's content
  is a list or a mapping (see the table), which isn't something an author expects to
  control heading size.

### C. Headingless partials (a convention, not a rule)

The partial contains content only (paragraphs, blocks, tables, bullet lists), and the
include site writes the heading:

```yaml
Beam B01:
  - _include:
      path: beam_check
      namespace: b1
```

- Level-independent: the partial renders the same at any depth, under either A or B.
- This is all the motivating case needs. The `beam_check` example in
  `scoped_includes.yml` should drop its `Beam check:` heading and look like this.
- It can't be the only rule. Partials with internal structure ("Inputs", "Results",
  "Checks") are a reasonable use, and an error that forbids headings would rule them
  out.

### D. Explicit control: `heading_offset` / `heading_level` on `_include`

Lets the author shift the partial's headings by a fixed amount, or pin the level of its
top heading.

- Covers unusual layouts, for example a partial used both as a section of its own and
  as a sub-section.
- It's one more thing to learn, and A plus heading-count levels already gives the right
  answer by default. Hold this back until someone has a real need.

A per-heading syntax (`_h3: Moment check`) was considered and rejected. It puts levels
back into the source by hand, which is what using YAML structure is meant to avoid.

## Recommendation

1. **Use relative levels (A).** Building the partial at the current `level` is what
   already happens to content written inline, so a partial behaves like pasted text.
2. **Document headingless partials (C) as the preferred style:** the include site owns
   the title, and the partial owns the content. Partials with internal headings are
   still allowed.
3. **Fix level counting separately from includes**, so a heading's level is the number
   of headings above it, plus one. This fixes both bugs above, makes A safe at realistic
   depths, and matches the documented model.
4. **Clamp at h6** instead of raising `KeyError`. (Implemented without a warning, which
   would be noisy in `ym live`. The bookmark keeps the true depth.) If clamping turns
   out to hide mistakes, raise an authoring error that names the heading (and the
   include chain, if any).
5. **Leave out D** until it's needed.

## Fixing the level count

Treat `level` as "the level the next heading in this frame gets", starting at 1. Only
an emitted heading adds a level. Lists and mappings without headings pass the level
through unchanged.

```python
def build_story(source_data, context, level=1, current_style="default"):
    ...
    if k is not None and not a block:
        heading = convert_paragraph(k, context, f"h{min(level, 6)}", ...)
        story.extend(heading)
        story.extend(build_content(v, context, level + 1, current_style))  # heading adds a level
        continue
    story.extend(build_content(v, context, level, current_style))          # list item: same level

def build_content(value, context, level=1, current_style="default"):
    ...
    if isinstance(value, (list, dict)):
        return build_story(value, context, level=level, current_style=current_style)  # no +1
```

Points to watch:

- **Slide mode** checks `level == 0` to find the top-level headings that become slides.
  That check becomes `level == 1` (or an explicit `top_level` flag).
  `build_slide` builds slide content with `build_content(..., 0, ...)`
  (`src/ymprint/slides.py:265`). Passing 2 makes a sub-heading on a slide h2 under the
  slide title. Today that sub-heading is h1 in mapping form and h2 in list form.
- **`_leading_textstyle`** and block dispatch don't use `level` and are unaffected.
- **`_ul` / `_ol`** have their own `level` for bullet nesting. It's unrelated and stays
  as it is.
- **`_include`** passes the frame's `level` to `build_story` for the partial, with no
  extra handling.

### Impact on existing documents

A static comparison of the two rules over `Examples/` (55 headings in 8 documents):

| Document | Headings | Changed | Change |
| --- | --- | --- | --- |
| Document Configuration | 5 | 1 | h4 → h3 |
| Simple example | 6 | 3 | h4 → h3 (Bullets, Ordered list, Tables) |
| Text Styles | 5 | 1 | h4 → h3 |
| Document variables, PDF Backgrounds, YMPrint blocks | 16 | 0 | |
| Presentation, Slides (slide mode) | 23 | 0 | |

Every change is a third-level list-style heading moving up from h4 to h3, which is what
the docs describe. None of the examples use the mapping form under a top-level heading,
so bug 1 doesn't show there. Documents that do use it will see B shrink from h1 to h2.

This is a visible change to rendered output, so it needs a changelog entry. Since
YMPrint is pre-1.0 (0.10.x), I'd ship it in the next minor version rather than add a
compatibility switch. If a switch turns out to be needed, a `_doc` setting such as
`heading_depth: containers` could keep the old rule for one release.

### Why correct levels will matter more later

YMPrint doesn't generate PDF bookmarks or a table of contents yet (nothing in `src/`
uses outlines). If those are added, heading levels become the outline structure, and
outline levels can't skip (h2 → h4) or repeat a parent's level (h1 under h1). Both
happen today.

## Tests to add with the fix

- Each shape in the measured table renders h1, h2, h3, h4 in order.
- A heading nested 7 deep renders at h6 with a warning, not a `KeyError`.
- In slide mode, the slide title is h1 and a sub-heading on the slide is h2, in both list
  and mapping form.
- A partial included under an h2 heading has its top-level heading at h3, and a
  headingless partial renders identically at the top level and under h3.

---

## Complication: headings inside `_hc` calculations

An `_hc` block can contain its own headings, written as comments in the Python source.
They form a second heading hierarchy, parallel to the document's and independent of it.
A reusable partial is exactly where a calculation like this ends up, so the two
hierarchies will meet often.

### How ym-handcalcs renders them today

- **Syntax** (`handcalcs/parsing/line_nodes.py`, `Heading.from_raw_comment`): the first
  `#` is the Python comment marker, so `## Moment check` is calc heading level 1,
  `### …` is level 2, and `#### …` (or more) is level 3. ym-handcalcs caps levels at 3
  (`renderer.py`, `heading_flowables`).
- **Styles** (`ym_handcalcs/styles.py`): `hcH1`–`hcH3` are fixed multiples of the block's
  `base_size` (2.0×, 1.45×, 1.2×), in the renderer's own sans font (DejaVuSans-Bold).
  Levels 1–2 use the theme accent colour with a rule underneath, and level 3 uses the
  ink colour.
- **What the block takes from the document:** only `base_size`, which defaults to
  `body.size` of the document's **default** style family
  (`ym_handcalcs/block.py`, `convert_hc_block`). It doesn't use the heading font,
  heading colour, heading ratio, the active `_textstyle` family, or the heading level
  it sits under. Blocks don't receive the last two at all: `build_story` doesn't put
  `level` or `current_style` in the context it passes to `convert_blocks`.
- **Bookmarks:** each calc heading carries `hc_outline = (key, text, level)`. Only
  ym-handcalcs's own `build_pdf` reads it. YMPrint ignores it.

### Measured

A document with `Calculations:` / `- Beam B01:` / `- _hc:` containing `##`, `###` and
`####` headings (body size 10 pt, default style):

| Text | Size | Font | Colour |
| --- | --- | --- | --- |
| Calculations (YMPrint h1) | 30.5 | Helvetica | #222222 |
| Beam B01 (YMPrint h2) | 24.4 | Helvetica | #222222 |
| `## Moment check` (hcH1) | 20.0 | DejaVuSans-Bold | #0B5F66 |
| `### Factored moment` (hcH2) | 14.5 | DejaVuSans-Bold | #0B5F66 |
| `#### Note level` (hcH3) | 12.0 | DejaVuSans-Bold | #1B2B2C |

Here the calc headings happen to be smaller than their parent heading. That stops
holding one level deeper. Under heading-count levels, an `_hc` block under an h3
heading (19.5 pt) opens with a 20 pt `##` heading, larger than its parent. Under
today's container counting, the same list-style layout puts the parent at h4
(15.6 pt). Including partials makes this the normal situation, because a calc gets
placed under whatever level the include site happens to be at.

### What goes wrong

1. **Size order:** a calc heading can be larger than the document heading above it, or
   two levels smaller. Its size depends on `base_size`, not on where the calc sits.
2. **Mixed typography:** two heading fonts and two heading colours on one page. With a
   serif `_style`, the mismatch is obvious.
3. **Structure:** to a reader, an outline or a screen reader, `## Moment check` has no
   defined relationship to `Beam B01`. If YMPrint adds bookmarks later, calc headings
   need levels that continue the document's (see "Why correct levels will matter more
   later").
4. **Partials make it unavoidable.** The same `.py` should look right under h2 in one
   report and under h4 in another. A fixed scale can't do that.

### Options

**A. Leave them independent (today's behaviour).** The calc keeps its own visual
language, a self-contained calc sheet set into the report.

- No work, and it suits people who see a calc as a separate exhibit.
- All four problems above remain. Making the style consistent becomes the author's job,
  through `base_size` and `theme_color` on every block.

**B. Keep headings out of the calc source (a convention).** Put structure in the YAML
around the `_hc` blocks and keep `.py` files heading-free.

- It needs no code, and it matches "headingless partials" above: the YAML owns the
  structure.
- It's often impractical. A `path:` block runs one whole file, so splitting a
  calculation under several headings means several `.py` files, and running them in
  order through shared variables. Headings in the `.py` are also useful when the
  calculation runs on its own (in Jupyter, or in ym-handcalcs's `build_pdf`).
- A `section:` option that runs only part of a file was considered and rejected. It
  would make the YAML depend on comment text inside the `.py`.

**C. Inherit typography only (the idea you raised).** The block takes fonts and colours
from the **active** text style family, but keeps its own three-step size scale.

- It fixes problem 2 and leaves 1, 3 and 4. A calc heading can still be larger than
  its parent.
- **Fonts need care.** ym-handcalcs uses three families: sans for **math**, serif for
  prose comments, mono for code. Only the heading and prose fonts should come from the
  document. The math font must cover Greek, sub/superscripts and math operators.
  YMPrint's default font is Helvetica, a base-14 PDF font with no Greek. Inheriting it
  for math would break symbols like `σ` and `φ`. Math stays DejaVuSans unless a
  separate setting overrides it.
- Colour: should calc headings take the document's heading colour, or the calc's
  `theme_color`? The data and values inside the calc keep the theme palette either
  way. For headings, the document colour is the better default, with `theme_color`
  still applying when given explicitly.

**D. Continue the document's hierarchy.** A calc heading becomes a document heading,
relative to where the block sits. If the next YAML heading at that spot would be level
L, then `##` renders as h(L), `###` as h(L+1), and `####` as h(L+2), capped at h6. A
`##` heading then behaves like a YAML key written in the same place.

- It fixes all four problems, and partials compose: the same `.py` looks right at any
  depth.
- It needs the heading-count fix from earlier. Without it, L is already too deep and
  calc headings reach h6 almost immediately.
- Calc headings get the document's sizes. At L = 2, `##` grows from 20 pt to 24.4 pt,
  which may feel heavy inside a dense calc sheet. That's a visual judgement, not a
  structural one, and the decoration (the accent rule under levels 1–2) can stay.

**E. Flatten them.** Render calc headings as bold labels inside the calc with no
heading level: no hierarchy, no outline entries, and sizes close to the body.

- Simple and predictable. The calc never competes with the document's structure, and
  the comments still label the steps.
- The structure is lost, which hurts a long calculation with many steps.

### Recommendation

These options can live side by side, so offer them as one option on the block, with D
as the default when ym-handcalcs runs inside YMPrint:

```yaml
- _hc:
    path: beam_calc
    headings: document   # D (default inside YMPrint): continue the document's levels and typography
    # headings: calc     # A: today's independent look (C's font inheritance still applies)
    # headings: flat     # E: bold labels, no hierarchy
```

- `document` includes C. Sizes, fonts and colours come from the active family's `h{n}`
  styles, while the math font and the calc palette stay as they are.
- `calc` keeps today's look for people who want a separate exhibit. It should still
  inherit the heading and prose fonts (C), because mixed fonts are seldom what anyone
  wants.
- B stays the recommended convention for partials that are mostly YAML. It isn't
  enforced.
- A project-wide default (`headings: calc` for a firm that wants a calc-sheet look)
  can come later. It needs somewhere in the config to hold block defaults, which
  YMPrint doesn't have yet.

### Implementation details

**In YMPrint:**

1. **Tell blocks where they are.** Before `convert_blocks`, `build_story` sets a new
   context key and restores it afterwards (the same `swapped` helper as in
   `scoped_includes.yml`):

   ```python
   with swapped(context, section={"level": level, "text_style": current_style}):
       story.extend(convert_blocks(k, v, context))
   ```

   `level` is the level the next YAML heading would get in this frame (with the
   heading-count fix), and `text_style` is the name of the active family. This is a
   public API addition. It helps any block, not just `_hc`: admonitions or `_p` could
   follow the active family too. Document the key alongside `content_box(context)`.
2. **Partials need nothing extra.** `_include` already builds its content at the
   include site's level, so a calc inside a partial gets the right `section.level`.
3. **Bookmarks later.** If YMPrint gains a PDF outline, it should read the same
   `hc_outline` attribute (or a generic `ym_outline` attribute) from flowables, so
   calc headings join the document outline without YMPrint knowing about handcalcs.

**In ym-handcalcs:**

1. **A `headings` option** in `block_options` (`OPTIONS` in `block.py`), checked against
   `document | calc | flat`.
2. **Heading styles passed in, not built in.** `ReportLabRenderer` gains an optional
   `heading_styles: dict[int, ParagraphStyle]`. In `document` mode, `convert_hc_block`
   builds it from the context:

   ```python
   section = context.get("section")             # None on older ymprint: fall back to "calc"
   family = context["styles"]["families"][section["text_style"]]
   sheet = family["rl"]
   heading_styles = {n: sheet[f"h{min(section['level'] + n - 1, 6)}"] for n in (1, 2, 3)}
   ```

   `heading_flowables` uses `heading_styles[level]` when given, and keeps the accent
   rule as decoration. `hc_outline` levels shift by `section["level"] - 1`, so they
   continue the document's outline.
3. **`base_size` from the active family** rather than always the default family
   (`family["ymprint"].body.size`). This is a small fix in its own right: today an
   `_hc` block after `_textstyle: fine-print` still uses the default body size.
4. **Font inheritance (C)** builds a `Fonts` whose `serif` (prose comments) and heading
   faces come from the family's `body.font` and `headings.font`, keeping `sans` (math)
   and `mono`. Fonts are only inherited if every face they need is registered.
   `fonts.missing_fonts` already checks for that. Otherwise the block falls back to
   DejaVu, so a missing bold face never breaks a render.
5. **Compatibility:** if `context` has no `section` key (an older YMPrint), `document`
   mode falls back to `calc`. ym-handcalcs's standalone `build_pdf` never has a
   context, so it keeps today's look. The default changes from `calc` to `document`
   inside YMPrint, which changes the look of existing rendered calcs. Ship it in a
   minor version of ym-handcalcs with a changelog note, and require that version from
   the matching YMPrint extra (`ymprint[hc]`).

### Order of work

1. YMPrint: heading-count levels and the h6 cap (this document, above).
2. YMPrint: the `section` context key.
3. ym-handcalcs: `base_size` from the active family (it doesn't need step 2's levels,
   only `text_style`).
4. ym-handcalcs: the `headings` option with `document` and `flat`, plus font
   inheritance.
5. YMPrint: `_include` (`scoped_includes.yml`), which now composes with calcs at any
   depth.

### Tests to add

- An `_hc` block under h2 renders `##` at h2 size and `###` at h3 in `document` mode,
  and moves by one level when placed under h3. The same partial gives both results.
- A calc heading never exceeds h6, and never renders larger than the YAML heading above
  it in `document` mode.
- After `_textstyle: fine-print`, an `_hc` block uses that family's body size and
  heading fonts. The math font stays DejaVuSans.
- `headings: calc` matches today's sizes and colours exactly, apart from inherited
  fonts. `headings: flat` produces no heading styles and no `hc_outline`.
- With a family whose font lacks a bold face, the block falls back to DejaVu without
  raising an error.
