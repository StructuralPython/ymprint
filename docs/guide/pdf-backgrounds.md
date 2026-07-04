# PDF backgrounds

You can design a template in any tool that exports PDF — a page layout program, a form
designer, even a word processor — and use it as the **background** for your YMPrint
document. Your rendered content is overlaid on top of the background's content, giving the
illusion of a sophisticated page-layout workflow while you keep writing plain YAML.

## Using a background

Point `_doc.background` at a PDF file:

```yaml
_doc:
  background: background.pdf

Custom styling with PDF backgrounds:
  - >
    Your content is overlaid on top of the existing background content. The background
    can carry your letterhead, borders, watermarks, and form fields.
```

The path is resolved relative to the report file. Each page of your document is composited
over the corresponding page of the background.

:::{tip}
Give the first page its own background using `_doc.first-page.background` — useful for a
title page or a cover sheet that differs from the body pages. See
[Configuration → Document template](#cfg-doc).
:::

## Auto-populated form fields

One of the original design intents of [document variables](variables.md) is to fill PDF
form fields dynamically. A form field is **automatically populated when a document variable
name exactly matches the field name**. After filling, the form fields are **flattened** so
the values look like normal, static PDF content.

```yaml
_doc:
  background: background.pdf
_vars:
  field_a: 1645
  field_b: 99 Sycamore St, Canada
  field_c: $4434.04
  field_d: An enormous moose

Auto-populated PDF form fields from variables:
  - >
    The form fields named field_a … field_d in background.pdf are filled from the
    variables above and then flattened.
```

This lets you build documents with dynamic headers — reference numbers, addresses,
totals — that update automatically from your variables.

## Avoiding accidental fills

Because matching is by name, a variable can fill a field you didn't intend to. To prevent
that:

- **Namespace your field names.** Adopt a naming convention for form fields that your
  ordinary variable names will never match.
- **Or avoid form fields** in the background entirely and rely purely on overlaid content.
