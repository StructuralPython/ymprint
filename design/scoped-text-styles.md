# Design: Scoped, switchable text styles

Status: prototype
Branch: `features/scoped-text-styles` (off `main`)

## Motivation

Today `_style` defines exactly one text family: a `body` paragraph style plus a
`headings` family whose `h1…h6` sizes are derived from `body.size` via a musical
`ratio`. There is no way to define an alternate text style (e.g. "fine print",
"callout") and apply it to part of a document.

This feature adds **named text styles** and a way to **switch between them** within
the report source, while preserving YMPrint's "minimal config, maximal flexibility"
ethos and — critically — without introducing global mutable state during parsing.

## Why not annotate the heading key

The natural-looking syntax

```yaml
Legal disclaimer {style: fine-print}:   # ← INVALID
```

is not valid YAML: the `: ` (colon-space) inside the braces is a mapping-value
indicator and is illegal inside a block-context plain scalar (the parser raises
`ScannerError: mapping values are not allowed here`). It is only salvageable with a
colon-free marker (`{style=fine-print}`, `@fine-print`, …), which turns the key into
a bespoke micro-syntax that YMPrint must regex-parse and strip — exactly the "markup
soup" the project avoids, plus a collision risk with real heading text.

**Decision:** keep the style annotation as ordinary YAML *data* (a block), not baked
into the key string.

## Source syntax: the `_textstyle` block

`_textstyle` sets the active text style for everything that follows it **within its
recursion frame**, and is inherited by descendant frames. It renders no flowable of
its own.

```yaml
Legal disclaimer:
  - _textstyle: fine-print     # applies from here down in THIS section
  - This paragraph is fine-print.
  - Sub-clause:
    - Inherited fine-print.
  - _textstyle: default        # switch back
  - Back to the default style.

Next section:
  - Body style again (the disclaimer's scope ended with its list).
```

- Value is a **style name** (string). `default` is always available and refers to
  the top-level `body`/`headings`.
- It may appear as a mapping key (`_textstyle: name`) or as a single-key list item
  (`- _textstyle: name`); both are recognised.
- An unknown style name raises `YMPrintSyntaxException`.

### Decisions (locked)

1. **Whole family.** Switching swaps the *entire* family: body paragraphs, bullet
   lists, and the derived `h1…h6` headings all follow the active style. A named
   style with a smaller `body.size` therefore also shrinks headings within its
   scope (sizes are `body.size * ratio`).
2. **Anywhere, flips onward.** `_textstyle` may appear at any position in a section's
   list. It restyles every following sibling in that frame plus their descendants,
   and reverts automatically when the frame ends. This mirrors the ergonomics of
   `_pagebreak` / `_nextpagetemplate`.
3. **Inherit from body.** A named style specifies only what differs; unspecified
   fields fall back to the default family (`body` + `headings`). DRY, matching the
   config system's inherit-from-defaults behaviour.

## Config syntax: named styles under `_style.styles`

```yaml
_style:
  body:     { font: NotoSans, size: 10, color: black, spacing: 1.7, bullets: {...} }
  headings: { font: AppleGaramond, ratio: minor third, color: "#dd9922" }
  styles:                       # NEW: named, each inherits the default family
    fine-print:
      body: { size: 8, color: "#666666" }
    callout:
      body:     { size: 12 }
      headings: { ratio: major third }
```

Each entry under `styles` is a **sparse override** of the whole family. It is
deep-merged onto the default `{body, headings}` before being validated and built
into a complete stylesheet. `styles` can be declared at any config priority level
(document front matter or a project `*.ymprint.yml`).

## State management (the crux)

Unlike page templates — where ReportLab owns the "active template" across a linear
page stream via `NextPageTemplate` — there is no ReportLab mechanism for an active
paragraph style. Every `Paragraph` is constructed with an explicit style object.

The switch is therefore managed as a **frame-local parameter**, not global state:

- `build_story(source_data, context, level, current_style="default")` threads
  `current_style` through the recursion.
- When a `_textstyle` item is encountered, `build_story` updates its **local**
  `current_style` variable for the remainder of that loop and passes it into any
  child `build_story(...)` calls.
- Because it is a local variable, siblings after the switch see it, descendants
  inherit it, and when the frame returns the parent's `current_style` is untouched —
  scope is automatic, with no reset and no cross-branch leakage.

`_textstyle` is intercepted directly in `build_story` (before the block-registry
dispatch) because it changes parse state rather than producing a flowable. This
interception handles both the mapping-key form and the single-key list-item form.

### Why frame-local, not a global cursor

A global "active style" cursor (mutated in `context`) would be order-dependent and,
given the recursive descent, would bleed a switch made inside a nested list back out
to the parent's later siblings unless every descent snapshotted and restored it. The
frame-local parameter gets correct scoping for free.

## Implementation surface

| File | Change |
| --- | --- |
| `config/docstyles.py` | Split family-building into `StyleFamily` (body + headings → `StyleSheet1`); `ReportStyles` gains `styles: dict[str, dict]` and `build_families()` returning `{name: (StyleFamily, StyleSheet1)}` with sparse overrides deep-merged onto the default. |
| `context_builder.py` | Store `context['styles']['families'] = {name: {'ymprint': StyleFamily, 'rl': StyleSheet1}}`; keep `['ymprint']` / `['rl']['_style']` pointing at the default family for back-compat. |
| `story_builder.py` | Thread `current_style`; intercept `_textstyle`; pass style into paragraph / ul / ol conversions. |
| `content_converters.py` | `convert_paragraph` / `convert_ul` / `convert_ol` take `current_style` and resolve the family from `context['styles']['families']`. |
| `config_loaders.py` | Carry user-defined extension keys (`styles`) through the config merge instead of dropping them (defaults have no schema for them). |
| `exceptions.py` | Reuse `YMPrintSyntaxException` for unknown style names. |

## Scope limits of this prototype

- Only **paragraphs, headings, and bullet/numbered lists** honour the active style.
  Other blocks (admonitions, quote, code, images, tables) keep their existing
  styling; threading `current_style` into every block converter is deferred, since
  it would change every block's signature.
- Style **names only** (no index), since named styles have no natural order the way
  page templates do.
- Style **names only** (no index).

## Alignment and underline

Two independent per-style attributes compose with the family mechanism above; both
are inherited by named styles like any other field.

```yaml
_style:
  body:
    align: justify          # left | center | right | justify (default: left)
  headings:
    underline: true         # default: false
  styles:
    callout:
      body: { align: center }
```

- `align` maps to ReportLab's native `ParagraphStyle.alignment` in `build_sheet`
  (`convert_alignment` in `config/helpers.py`; accepts `centre`/`justified`
  spellings). An unknown value raises `YMPrintValueError`.
- `underline` is applied at **render time** in `convert_paragraph` by wrapping the
  rendered text in `<u>…</u>` — ReportLab's `ParagraphStyle` has no honored
  `underline` attribute, so the inline tag (already used for `<b>`/`<i>`) is the
  version-independent route. It applies to paragraphs and headings; bullets are not
  wrapped. (A rule-under-heading variant remains a possible future option.)

Both attributes live on the shared `FormatMixin`, so they are available on `body`,
`headings`, and every named style.

## Open questions for later

- Should other blocks (admonitions, quotes, code captions) inherit the active style?
- Do we want a one-off inline form (`{style: …}` on a single run) in addition to the
  scoped block?
- Should alignment be a per-style attribute (config) or also settable per-scope?
