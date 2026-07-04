# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------

project = "YMPrint"
copyright = "2026, Connor Ferster"
author = "Connor Ferster"
release = "0.1.0"
version = "0.1.0"

# -- General configuration ---------------------------------------------------

extensions = [
    "myst_parser",
    "sphinx_copybutton",
    "sphinx_design",
]

# MyST markdown extensions
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "fieldlist",
    "tasklist",
    "attrs_inline",
    "substitution",
]
myst_heading_anchors = 3

source_suffix = {
    ".md": "markdown",
    ".rst": "restructuredtext",
}

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "README.md", "requirements.txt"]

# -- Options for HTML output -------------------------------------------------

html_theme = "shibuya"
html_static_path = ["_static"]
html_title = "YMPrint"
html_css_files = ["custom.css"]

# Force the light version of the Shibuya theme by lepture.
html_theme_options = {
    "color_mode": "light",
    "accent_color": "violet",
    "github_url": "https://github.com/StructuralPython/yamlreports",
    "nav_links": [
        {"title": "Quickstart", "url": "quickstart"},
        {"title": "Blocks", "url": "reference/blocks"},
        {"title": "CLI", "url": "reference/cli"},
    ],
}

html_context = {
    "source_type": "github",
    "source_user": "StructuralPython",
    "source_repo": "yamlreports",
}

pygments_style = "friendly"
pygments_dark_style = "friendly"
