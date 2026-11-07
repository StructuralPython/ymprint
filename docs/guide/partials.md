# Partial documents — `_include`

Some content gets used again and again: a calculation shown with an `_hc` block followed
by its figure, a standard notes section, a sign-off block. Write it once as a **partial**,
keep it in a library folder (inside the project or outside it), and include it wherever
it's needed:

```yaml
Beam B01:
  - _include:
      path: beam_check
      namespace: b1
      with: {span: 6.0, w: 12.5}
  - "Governing moment: {{ b1.M_f }}"
```

## Writing a partial

A partial is an ordinary YAML content file. It may start with two kinds of front matter:

- `_data`: files the partial uses, with paths **relative to the partial**.
- `_vars`: defaults for its parameters.

```yaml
# ~/eng-lib/partials/beam_check.yml
_data:
  calc: beam_check.py          # next to this file
_vars:
  caption: Bending moment diagram
_content:
  - _hc:
      path: calc
  - _matplotfig:
      fig: $fig
      caption: "{{ caption }}"
```

The content goes under `_content` because YAML can't follow front matter (a mapping)
with a bare list. A partial with no front matter can be a plain list, and a partial
whose content starts with a heading can write the heading directly after its front
matter (`Moment check:` instead of `_content:`).

This partial has no heading of its own, which is usually the best style. The document
supplies the heading where it includes the partial (`Beam B01:` above), so the partial
fits under any heading. A partial may have headings too (see
[Headings](#partial-headings)).

A partial can't use `_doc`, `_style`, `_tablestyle`, `_export` or `_render`. Those
belong to whole documents. Its `_data` can't declare produced data (`from:`).

## Declaring and including it

As with [`_hc` `path`](#block-hc), a document names a partial rather than giving its
path. Declare it once in the project config:

```yaml
# project.ymprint.yml
_data:
  beam_check: ../eng-lib/partials/beam_check.yml
```

Then include it by name. The short form is `_include: beam_check`. The long form takes
these options:

| Option | Required | Meaning |
| --- | --- | --- |
| `path` | ✅ | The partial's `_data` name, or an absolute path. A relative path is an error. |
| `with` | | Parameters: a mapping of names to values. They override the partial's `_vars`. A `$var` value passes the variable's object. |
| `namespace` | | Run the partial in its own scope, and put the variables it sets under this name afterwards. |

`_include` works as a key (`_include: …`) or as a list item (`- _include: …`), and
`_include_<id>` keeps keys unique within one mapping, as with blocks.

## What the partial sees

While a partial is built:

- Relative paths in it (`_img`, `_loadjson`, `_dumpjson`, links) resolve against the
  **partial's** folder.
- Its own `_data` names are available, on top of the project's: in Jinja, in `_py`
  and `_hc` code, as `$name`, to `_hc` `path:`, and to `ym.path()`.
- The active [text style](#block-textstyle) carries into the partial. A `_textstyle`
  inside the partial applies only within the partial.

Partials can include other partials. A partial that includes itself, directly or
through others, is an error that shows the whole chain.

## Scope: shared or namespaced

**Without `namespace`**, the partial runs in the document's variables, the same as if
its content were pasted in. Its `_vars` fill in names the document hasn't set, then its
`with` parameters are set, and whatever it computes stays in the document afterwards.
Including the same partial twice overwrites the first include's values.

**With `namespace`**, the partial runs in a copy of the document's variables, with its
`_vars` and then its `with` parameters applied on top. Afterwards, the names it created
or changed (its parameters included) are put under the namespace, and the document's
other variables are left as they were:

```yaml
Beam B01:
  - _include: {path: beam_check, namespace: b1, with: {span: 6.0}}
Beam B02:
  - _include: {path: beam_check, namespace: b2, with: {span: 4.5}}
Summary: "B01: {{ b1.M_f }}, B02: {{ b2.M_f }}"
```

The copy is shallow. A partial that changes an object it got from the document (for
example by appending to a list) changes the document's object too. To give a partial a
value, pass it in `with`.

(partial-headings)=
## Headings

A partial's content is built where the `_include` is, at the current heading level.
Its first heading becomes a sub-heading of the heading that holds the `_include`:

```yaml
Calculations:          # h1
  - Beam B01:          # h2
    - _include: beam_check   # a heading in the partial is h3
```

So the same partial fits at any depth. See [Heading levels](#heading-levels). Heading
comments in an `_hc` calculation continue the same way (see
[Calc headings](../reference/blocks.md#calc-headings)).

## `ym live` and `ym build`

The partial and every file it reads (its `_data`, JSON, images, `_hc` `.py` files) are
inputs of the document. `ym live` re-renders when any of them changes, and `ym build`
rebuilds the document.
