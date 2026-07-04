# YMPrint documentation

This directory contains the [Sphinx](https://www.sphinx-doc.org/) documentation site for
YMPrint, using the [Shibuya](https://shibuya.lepture.com/) theme (light) by lepture and
authored in [MyST](https://myst-parser.readthedocs.io/) markdown.

## Build

```bash
# From the repo root, into an isolated environment:
uv run --with-requirements docs/requirements.txt \
    sphinx-build -b html docs docs/_build/html

# Or with a plain virtualenv:
pip install -r docs/requirements.txt
sphinx-build -b html docs docs/_build/html
```

Open `docs/_build/html/index.html` in a browser.

## Live rebuild while writing

```bash
uv run --with-requirements docs/requirements.txt \
    --with sphinx-autobuild \
    sphinx-autobuild docs docs/_build/html
```

## Layout

| Path | Contents |
| --- | --- |
| `conf.py` | Sphinx configuration (Shibuya light theme, MyST). |
| `index.md` | Landing page. |
| `installation.md`, `quickstart.md` | Getting started. |
| `guide/` | Task-oriented guides (structure, configuration, variables, PDF backgrounds). |
| `reference/` | Reference material (blocks, CLI, fonts). |
| `_static/custom.css` | Small theme refinements. |
