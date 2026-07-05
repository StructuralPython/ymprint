# Fonts reference

YMPrint **bundles** a select set of font families so your documents render identically on any
machine — no system font installation required. Reference a family by name in
[`_style`](#cfg-style).

## Using a font

```yaml
_style:
  body:
    font: NotoSans
  headings:
    font: AppleGaramond
```

The name is the family name (case-sensitive). Each bundled family ships with regular, bold,
italic, and bold-italic variants, so **bold** and *italic* inline formatting render
correctly. 

## Bundled families

| Family | Style | Good for |
| --- | --- | --- |
| `AppleGaramond` | Serif | Elegant headings and body text. |
| `DejaVuSans` | Sans-serif | A robust, wide-coverage default. |
| `DejaVuSansCondensed` | Sans-serif (condensed) | Fitting more text per line. |
| `DejaVuSansMono` | Monospace | Code and tabular figures (used for inline `code`). |
| `DejaVuSerif` | Serif | Long-form body text. |
| `DejaVuSerifCondensed` | Serif (condensed) | Dense serif layouts. |
| `Inter` | Sans-serif | Clean, modern UI-style text. |
| `Montserrat` | Sans-serif (geometric) | Strong, contemporary headings. |
| `NotoSans` | Sans-serif | Broad language coverage. |
| `NotoSerif` | Serif | Broad language coverage, serif. |
| `Playfair` | Serif (display) | High-contrast display headings. |
| `Poppins` | Sans-serif (geometric) | Friendly, rounded headings. |
| `Roboto` | Sans-serif | Neutral, highly legible body text. |

## Standard PDF fonts

The built-in defaults also use the standard PDF core fonts (Helvetica, Times, and Courier), which are
always available. You can name them directly:

```yaml
_style:
  body:
    font: Helvetica
  headings:
    font: Times 
```

## Inline code font

Inline `` `code` `` spans always render in `DejaVuSansMono` on a light-grey background,
independent of your body font, so code is always visually distinct.
