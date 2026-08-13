# Design: Explicit list syntax (`_ul` / `_ol`)

Status: prototype
Branch: `features/explicit-list-syntax` (off `main`)

## Problem

A YAML list under a heading is structurally identical whether the author means
"several paragraphs" or "an unordered list". Today YMPrint guesses from the list's
*contents*:

- a **pure** list of strings → `convert_ul` → bullets
- a **mixed** list (strings + block/subsection dicts) → each string becomes a
  paragraph

So the same `heading:\n  - >prose` renders as a bullet or a paragraph depending on
what else is in the list. A single wrapped paragraph under a heading silently comes
out as a one-item bullet list (observed under "Alignment and named styles" in the
text-styles example).

The ambiguity is **structural** — YAML gives identical structure to both intents —
so no heuristic can resolve it. One of the two meanings must be made explicit.

## Decision

Make **bullets explicit** and let a bare list mean "a sequence of content items".

- A YAML list is always a *sequence of blocks*: strings become paragraphs, mappings
  become subsections (heading + content), in order. It is never auto-bulleted.
- Unordered lists are written with the **`_ul`** block; ordered lists with **`_ol`**.
- The implicit detections (`check_for_nested_lists` → bullets, and the
  dict-with-integer-keys → numbered list) are retired from dispatch. The check
  functions remain (still unit-tested) but no longer drive `build_story`.

This yields a single rule with no guessing: *a list is content in order; bullets and
numbers are named constructs.*

### Rejected alternative

Making **paragraphs** explicit (`_p`) instead would avoid breaking existing bullet
lists, but it keeps the surprising default (bare list = bullets) and only adds an
escape hatch beside the ambiguity rather than removing it.

## Syntax

```yaml
Findings:
  - The inspection covered three areas.        # paragraph
  - _ul:                                        # unordered list
      - The handrail is loose on the north stair.
      - Two ceiling tiles are water-stained.
      - - a nested sub-point                    # nested list → sub-bullets
        - another sub-point
  - Recommended actions:                        # subsection heading
      _ol:                                      # ordered list
        - Re-secure the handrail.
        - Replace the stained tiles.
```

- `_ul` value is a list; nested lists produce sub-bullets (unchanged `convert_ul`).
- `_ol` value is a list; numbering is automatic by position; nested lists produce
  nested numbering. (`convert_ol` also still accepts a mapping for back-compat.)
- Both may be written as a list item (`- _ul: [...]`) or as the value of a heading
  key (`heading:\n  _ul: [...]`). Suffixes are allowed for uniqueness in a mapping
  (`_ul_left`, `_ol_steps`), consistent with other block codes.

## Implementation

`_ul` / `_ol` are intercepted **directly in `build_story`**, not registered in the
block registry. Two reasons:

1. They are structural (they change how a list is interpreted), sitting naturally
   beside the list-dispatch logic.
2. It keeps them **forward-compatible with scoped text styles**: `build_story` is
   where a `current_style` parameter lives (on the `features/scoped-text-styles`
   branch), so intercepting here lets `_ul`/`_ol` pass the active style into
   `convert_ul`/`convert_ol`. Routing them through the generic block registry —
   whose converters do not receive the active style — would make bullets ignore the
   surrounding `_textstyle` scope. (On this `main`-based branch there is no
   `current_style` yet; the interception point is chosen so the two features compose
   cleanly when merged.)

| File | Change |
| --- | --- |
| `story_builder.py` | Intercept `_ul`/`_ol` (list-item and heading-value forms, with suffixes) → `convert_ul`/`convert_ol`. Replace the implicit bullet/ordered dispatch: a bare list/mapping now always recurses (strings → paragraphs, mappings → subsections). |
| `content_converters.py` | `convert_ol` accepts a **list** (positional numbering; nested lists nest) as well as a mapping (back-compat). |
| test data / examples | Migrate bare-list bullets and integer-keyed ordered lists to `_ul` / `_ol`. Genuine multi-paragraph lists (e.g. report 2 "third topic") are left as lists and now render as paragraphs — the intended fix. |

## Backward compatibility

This is a **breaking** content change (consistent with the pre-1.0 status and the
earlier multi-page-template change): existing documents that relied on bare lists for
bullets, or integer-keyed mappings for numbered lists, must adopt `_ul` / `_ol`.

## Open questions

- Should `_ol` support an explicit `start:` offset or custom markers (a/i/…)?
- Should list items be allowed to contain blocks (e.g. an image inside a bullet)?
- When merged with scoped text styles, thread `current_style` into the `_ul`/`_ol`
  interception so bullets honour the active family.
