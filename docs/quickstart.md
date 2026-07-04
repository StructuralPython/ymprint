# Quickstart

This walkthrough takes you from an empty folder to a rendered PDF.

## 1. Write a report

Create a file called `report.yml`. The **top-level keys are your headings**, and their
values are the content underneath them.

```yaml
Site inspection report:
  - >
    This is the first paragraph. The `>` character tells YAML you are entering a
    multi-line string that should be word-wrapped. Leave a blank line to start a new
    paragraph.
  - Findings:
    - Bullets:
      - The handrail is loose on the north stair.
      - Two ceiling tiles are water-stained in the lobby.
    - Items observed:
      - Item Number: 12.01
        Description: There is a problem here. This report documents it.
        Location: Under the stairs
      - Item Number: 12.02
        Description: Five ladybugs on the table cloth.
        Location: Kitchen
```

A few things are happening here:

- `Site inspection report:` is the **document heading** (an `<h1>`).
- Each `-` under it is a **list item** rendered in document order.
- `Findings:` is a nested **sub-heading**, because it is a key whose value is more content.
- `Bullets:` renders a bulleted list; `Items observed:` renders a **table** because each
  list item is a mapping (the keys become column headers).

See [Document structure](guide/document-structure.md) for the full set of rules.

## 2. Render it

```bash
ym convert report.yml
```

```text
✍️ .... 📝 ... PDF created: /path/to/report.pdf
```

By default the PDF is written next to the source file with a `.pdf` extension. To choose a
destination:

```bash
ym convert report.yml output/inspection.pdf
```

## 3. Iterate live (optional)

While drafting, run [`ym live`](reference/cli.md#ym-live) to open the PDF and rebuild it
automatically every time you save:

```bash
ym live report.yml
```

Leave it running in a terminal, edit `report.yml` in your editor, and the preview refreshes
on save. Press `Ctrl+C` to stop.

## 4. Style it

Add configuration keys prefixed with an underscore at the top of the file. For example, to
change the body font and heading colour:

```yaml
_style:
  body:
    font: NotoSans
  headings:
    font: AppleGaramond
    color: "#dd9922"

Site inspection report:
  - >
    Everything below inherits the styles above.
```

Configuration can live inline (as above) or in a shared project config file so several
documents look alike. See [Configuration](guide/configuration.md).

## 5. Add richer content

When plain prose isn't enough, reach for a **block** — a key that starts with an
underscore and expands into custom content:

```yaml
Report:
  - Photos:
    _img:
      src: site.png
      caption: "Figure 1: The north stairwell"
      scale_ratio: 0.5
  - _info: Remember to file this report by end of week.
  - _pagebreak:
```

The full catalogue is in the [Blocks reference](reference/blocks.md).

## Where to go next

- [Document structure](guide/document-structure.md) — the mental model for YAML → PDF.
- [Blocks reference](reference/blocks.md) — every built-in block and its parameters.
- [Configuration](guide/configuration.md) — page templates, text styles, table styles.
- [Variables](guide/variables.md) — `_vars`, Jinja interpolation, and `$var` passing.
- [CLI reference](reference/cli.md) — `ym convert` and `ym live` in detail.
