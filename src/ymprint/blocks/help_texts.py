"""
Short help for the built-in blocks and document keys, shown by `_help: _name`.

Each entry has a one-line 'summary', the 'keys' a mapping value takes (name, meaning),
and one 'example' in YAML. 'kind' is "block" for a block and "key" for a structural
or document key (handled by ymprint itself rather than registered as a block). Keep
each entry short: the docs (docs/reference/blocks.md) have the full story.
"""
from __future__ import annotations

HELP_TEXTS: dict[str, dict] = {
    "_img": {
        "kind": "block",
        "summary": "An image (PNG, JPEG, ...) with an optional caption.",
        "keys": [
            ("source", "Required. Path to the image, relative to the .yml file, or absolute."),
            ("caption", "Text below the image."),
            ("width_ratio", "Fraction of the content width. Default 1; shrunk to fit."),
            ("link", "A URL or file path that opens when the image is clicked."),
        ],
        "example": "_img:\n  source: images/beam.png\n  caption: \"Figure 1: Beam B1\"\n  width_ratio: 0.6",
    },
    "_matplotfig": {
        "kind": "block",
        "summary": "A matplotlib Figure built in a _py block, passed as $var.",
        "keys": [
            ("fig", "Required. The Figure, as $var."),
            ("caption", "Text below the figure."),
            ("scale_ratio", "Fraction of the content width. Default 0.8."),
        ],
        "example": "_matplotfig:\n  fig: $fig\n  caption: \"Figure 2: Moment diagram\"",
    },
    "_info": {
        "kind": "block",
        "summary": "An \"info\" callout box. The value is its text.",
        "keys": [],
        "example": "_info: Loads are factored to NBCC 2020.",
    },
    "_warning": {
        "kind": "block",
        "summary": "A \"warning\" callout box. The value is its text.",
        "keys": [],
        "example": "_warning: Check the connection for uplift.",
    },
    "_danger": {
        "kind": "block",
        "summary": "A \"danger\" callout box. The value is its text.",
        "keys": [],
        "example": "_danger: Do not remove shoring before 28 days.",
    },
    "_tip": {
        "kind": "block",
        "summary": "A \"tip\" callout box. The value is its text.",
        "keys": [],
        "example": "_tip: Use _data so documents contain no paths.",
    },
    "_note": {
        "kind": "block",
        "summary": "A \"note\" callout box. The value is its text.",
        "keys": [],
        "example": "_note: Dimensions are in millimetres.",
    },
    "_blockquote": {
        "kind": "block",
        "summary": "A quotation with an attribution line.",
        "keys": [
            ("quote", "Required. The quotation."),
            ("attribution", "Who said it."),
        ],
        "example": "_blockquote:\n  quote: Measure twice, cut once.\n  attribution: Carpenters",
    },
    "_code": {
        "kind": "block",
        "summary": "Code or text shown verbatim (not run). Use _py to run Python.",
        "keys": [
            ("source", "Required. The text; use a | block scalar to keep line breaks."),
            ("line_numbers", "Show line numbers."),
            ("caption", "Caption shown with the code."),
            ("width_ratio", "Fraction of the content width. Default 0.75."),
            ("theme", "light or dark. Default from the text style."),
            ("size", "Text size in points. Default from the text style."),
        ],
        "example": "_code:\n  source: |\n    ym build --all",
    },
    "_py": {
        "kind": "block",
        "summary": "Runs Python in the document's variables; what it creates is usable afterwards.",
        "keys": [
            ("source", "Required. The Python to run."),
            ("echo", "Show the source as a code block. Default true."),
            ("namespace", "Put the new variables under this name ({{ns.var}})."),
            ("line_numbers, caption, width_ratio, theme, size", "As for _code."),
        ],
        "example": "_py:\n  echo: false\n  source: |\n    import math\n    c = math.hypot(3, 4)",
    },
    "_hc": {
        "kind": "block",
        "summary": "Runs Python and typesets it as handcalcs calculations (needs ymprint[hc]).",
        "keys": [
            ("source", "The Python (or give the value as the source itself)."),
            ("path", "Read the source from a .py file: a _data name or an absolute path."),
            ("namespace", "Put the results under this name."),
            ("theme_color", "A dark #RRGGBB the palette is derived from."),
            ("base_size", "Font size every calc style scales from. Default: body size."),
            ("headings", "document, calc or flat. Default document."),
            ("fractions", "stacked or inline. Default stacked."),
        ],
        "example": "_hc: |\n  ## Factored load\n  w_f = 1.25 * w_DL + 1.5 * w_LL\n  M_f = w_f * L**2 / 8",
    },
    "_loadjson": {
        "kind": "block",
        "summary": "Loads variables from a JSON file at render time.",
        "keys": [
            ("path", "Required. The JSON file, relative to the .yml file."),
            ("namespace", "Put the values under this name."),
        ],
        "example": "_loadjson:\n  path: extra_vars.json\n  namespace: extra",
    },
    "_dumpjson": {
        "kind": "block",
        "summary": "Writes variables to a JSON file at render time.",
        "keys": [
            ("path", "Required. The JSON file; may use {{ }}."),
            ("vars", "Required. The names to write; dotted names nest (beam.span)."),
            ("namespace", "Look the names up inside this mapping."),
        ],
        "example": "_dumpjson:\n  path: out/values.json\n  vars: [beam.span, phi]",
    },
    "_table": {
        "kind": "block",
        "summary": "A table from data (a list of mappings), with display options.",
        "keys": [
            ("data", "Required. A $var, a variable or _data name, or a list of mappings."),
            ("columns", "The columns to show, in order."),
            ("headers", "Header text per column."),
            ("format", "A format string per column, e.g. \"{:.2f}\"."),
            ("sort", "Columns to sort by; prefix - for descending."),
            ("row_style", "A Jinja template (row = the row) giving a row style name."),
            ("caption", "Text below the table."),
        ],
        "example": "_table:\n  data: $rows\n  columns: [Member, DCR]\n  format: {DCR: \"{:.2f}\"}\n  sort: [-DCR]",
    },
    "_p": {
        "kind": "block",
        "summary": "A paragraph with no heading, optionally in a named text style.",
        "keys": [
            ("content", "Required (or give the text as the value). text is an alias."),
            ("style", "A text style family from _style.styles. Default default."),
        ],
        "example": "_p:\n  content: Values are approximate.\n  style: fine-print",
    },
    "_pagebreak": {
        "kind": "block",
        "summary": "A page break; a value switches to that page template (name or index).",
        "keys": [],
        "example": "- _pagebreak:\n- _pagebreak: body",
    },
    "_nextpagetemplate": {
        "kind": "block",
        "summary": "Sets the page template used after the next page break, without a break.",
        "keys": [],
        "example": "_nextpagetemplate: body",
    },
    "_hrule": {
        "kind": "block",
        "summary": "A horizontal rule. null draws one with the defaults.",
        "keys": [
            ("width_ratio", "Fraction of the content width. Default 1.0."),
            ("thickness", "Line thickness in points. Default 1."),
            ("color", "Default #111111."),
            ("cap", "square or round. Default square."),
        ],
        "example": "_hrule:\n  width_ratio: 0.6\n  thickness: 2\n  color: \"#bb3322\"",
    },
    "_spacer": {
        "kind": "block",
        "summary": "Vertical space. The value is its height in points.",
        "keys": [],
        "example": "_spacer: 12",
    },
    "_help": {
        "kind": "block",
        "summary": "Shows help over the page while you write. Remove it before ym build.",
        "keys": [
            ("(no value) or blocks", "Lists every block and document key."),
            ("_name", "Help for that block or key, e.g. _help: _img."),
            ("$var or any value", "Shows the value: its type, size and contents."),
        ],
        "example": "- _help: _table\n- _help: $beam",
    },
    # Structural keys: handled by ymprint itself, not registered blocks.
    "_ul": {
        "kind": "key",
        "summary": "A bulleted list. Nest a list in an item to indent it.",
        "keys": [],
        "example": "_ul:\n  - The handrail is loose.\n  - - a sub-point",
    },
    "_ol": {
        "kind": "key",
        "summary": "A numbered list. Nest a list in an item for a nested list.",
        "keys": [],
        "example": "_ol:\n  - Re-secure the handrail.\n  - Replace the tiles.",
    },
    "_textstyle": {
        "kind": "key",
        "summary": "Switches the text style for the rest of this section and its children.",
        "keys": [],
        "example": "- _textstyle: fine-print\n- This paragraph is fine print.",
    },
    "_include": {
        "kind": "key",
        "summary": "Builds a partial document in place, at this heading level.",
        "keys": [
            ("path", "Required. The partial's _data name, or an absolute path."),
            ("with", "Parameters, over the partial's _vars defaults."),
            ("namespace", "Run in its own scope; results land in _vars[namespace]."),
        ],
        "example": "_include:\n  path: beam_check\n  with: {span: 6.0}",
    },
    "_slide": {
        "kind": "key",
        "summary": "Slide mode only: the first item of a slide, choosing its layout and template.",
        "keys": [
            ("layout", "The slide layout (or give the layout name as the value)."),
            ("template", "The page template."),
        ],
        "example": "- _slide: two-column",
    },
    "_frame": {
        "kind": "key",
        "summary": "Slide mode only: sends the content that follows into a frame of the layout.",
        "keys": [],
        "example": "- _frame: right",
    },
    "_vars": {
        "kind": "key",
        "summary": "Top of a document: variables for {{ }} text, $var values and Python.",
        "keys": [],
        "example": "_vars:\n  span: 6.0\n  load: 12.5",
    },
    "_data": {
        "kind": "key",
        "summary": "Data sources by name: a path, or a mapping with path, loader and from.",
        "keys": [
            ("path", "The file, relative to the file that declares it."),
            ("loader", "yaml or json. Default from the extension."),
            ("from", "The document(s) or script(s) that produce it."),
        ],
        "example": "_data:\n  design: 4-design/design.yml\n  frame:\n    from: 3-analysis/frame.py",
    },
    "_export": {
        "kind": "key",
        "summary": "Values this document hands to others, evaluated after its content is built.",
        "keys": [],
        "example": "_export:\n  Mr: $M_r\n  section: \"{{ design.B01.section }}\"",
    },
    "_doc": {
        "kind": "key",
        "summary": "The page: size, orientation, slide mode and named page templates.",
        "keys": [
            ("page-size", "a4, letter, ... or [width, height] in points."),
            ("landscape", "true to rotate a named size."),
            ("slides", "true for slide mode."),
            ("templates", "name -> margins and background. The first is the start."),
        ],
        "example": "_doc:\n  page-size: letter\n  templates:\n    body:\n      margins: {top: 72, left: 72, right: 72, bottom: 72}",
    },
    "_style": {
        "kind": "key",
        "summary": "Text styles: headings, body, code, and named families under styles.",
        "keys": [],
        "example": "_style:\n  body: {font: Helvetica, size: 10}\n  styles:\n    fine-print:\n      body: {size: 7}",
    },
    "_tablestyle": {
        "kind": "key",
        "summary": "How tables are drawn: cell padding, header and body text, row colours.",
        "keys": [
            ("cell-padding", "Inner padding of every cell, in points."),
            ("headers.text / body.text", "Font, size, colour (and bold for headers)."),
            ("body.rows.color", "Row banding: even and odd colours."),
            ("body.rows.styles", "Named row colours for _table row_style."),
        ],
        "example": "_tablestyle:\n  body:\n    rows:\n      styles: {ok: \"#d4edda\"}",
    },
}
