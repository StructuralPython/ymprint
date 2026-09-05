# TEMP design doc — `_p` block (paragraph block)

> Scratch/handoff doc for the `_p` feature. **Delete before merging.**
> Branch: `features/p-block`. Work in micro-commits.

## Goal
Let an author emit a standalone paragraph *after another block* without first
introducing a heading key. Normally body text appears either as the value of a
heading key or as a bare list item; `_p` gives an explicit, self-contained
paragraph flowable with a selectable text style.

## Design
`_p` is a registered block (like `_info`, `_blockquote`). Two value forms:

1. **Bare string** — quickest path, default style:
   ```yaml
   - _p: A quick paragraph after a block.
   ```
2. **Mapping** — with an explicit text style:
   ```yaml
   - _p:
       content: Some fine print after a figure.
       style: fine-print
   ```

### Attributes (mapping form)
| Attr | Required | Default | Meaning |
| --- | --- | --- | --- |
| `content` | ✅ (or `text`) | — | The paragraph text. `text` accepted as an alias. |
| `style` | | `default` | Named text style **family** (same names as `_textstyle` / `_style.styles`). |

- "Text style" in this library == a *style family* (`_textstyle` switches it;
  `_style.styles` defines named ones). So `_p`'s `style` selects a family and the
  paragraph renders in that family's **body** role.
- Unknown `style` → `YMPrintSyntaxException` listing available families
  (mirrors `story_builder._resolve_style`).

## Implementation
- New file `src/ymprint/blocks/p_block.py` with `convert_p_block` +
  `register_block("_p", convert_p_block)`.
- Reuse `content_converters.convert_paragraph(text, context, "body", style)` —
  gives inline markdown, Jinja var interpolation, underline, spacer, for free.
- Validate `style` against `context["styles"]["families"]` locally (avoid importing
  story_builder → circular import; blocks are imported *by* story_builder).
- Register import in `report_reader.py` (alongside the other `from .blocks import ...`).

## Tests (`tests/test_p_block.py`)
- bare-string form → one body paragraph, default family size.
- mapping form with `content` → same.
- `text` alias works.
- `style` selects a named family (font size differs).
- unknown `style` raises `YMPrintSyntaxException`.
- inline markdown / Jinja var rendered.
- end-to-end via `build_story` (block appears after another block, no heading).

## Docs
- `docs/reference/blocks.md`: catalogue row + `(block-p)=` section.
  ⚠️ NOTE: this file already contains a **committed git merge-conflict marker**
  around the catalogue table (`<<<<<<< HEAD` ... `>>>>>>>`). Pre-existing, not mine.
  Touch only what's needed; do not try to resolve that conflict as part of this feature.
- `README.md`: add `_p` row to the blocks table.

## Checklist
- [ ] design doc committed
- [ ] p_block.py + registration
- [ ] tests
- [ ] docs (blocks.md + README)
- [ ] full test suite green
- [ ] delete this design doc
