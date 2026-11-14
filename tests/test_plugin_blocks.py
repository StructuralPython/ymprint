"""Blocks provided by installed packages (the `ymprint.blocks` entry-point group)."""
import pathlib
import textwrap
from importlib.metadata import EntryPoint

import pymupdf as mu
import pytest
from reportlab.platypus import Paragraph

from ymprint import Ymprint, plugins
from ymprint.errors import BlockError

PLUGIN_MODULE = '''
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet

IMPORTS = []
IMPORTS.append(1)

def stamp_block(block_key, block_value, context):
    return [Paragraph(f"STAMP {block_value}", getSampleStyleSheet()["Normal"])]

not_callable = 42
'''


@pytest.fixture
def installed(tmp_path, monkeypatch):
    """Returns install(**entries): fakes installed `ymprint.blocks` entry points."""
    (tmp_path / "fake_plugin.py").write_text(PLUGIN_MODULE)
    (tmp_path / "broken_plugin.py").write_text("raise ImportError('missing dependency: shapely')\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.delitem(__import__("sys").modules, "fake_plugin", raising=False)

    def install(**entries):
        eps = [EntryPoint(name, value, plugins.BLOCKS_ENTRY_POINT_GROUP) for name, value in entries.items()]
        monkeypatch.setattr(
            plugins, "entry_points",
            lambda group: eps if group == plugins.BLOCKS_ENTRY_POINT_GROUP else [],
        )
        monkeypatch.setattr(plugins, "_plugin_blocks", None)

    yield install
    plugins._plugin_blocks = None


def render(app: Ymprint, tmp_path: pathlib.Path, body: str) -> str:
    doc = tmp_path / "report.yml"
    doc.write_text(textwrap.dedent(body))
    out = tmp_path / "report.pdf"
    app.render(doc, out, discover_config=False)
    return "".join(page.get_text() for page in mu.open(out))


def test_plugin_block_renders_in_any_app(installed, tmp_path):
    installed(_stamp="fake_plugin:stamp_block")
    text = render(Ymprint(), tmp_path, """
        Report:
          - _stamp_a: approved
    """)
    assert "STAMP approved" in text


def test_code_may_leave_out_the_underscore(installed):
    installed(stamp="fake_plugin:stamp_block")
    assert "_stamp" in plugins.plugin_blocks()
    assert "_stamp" in Ymprint().render_blocks()


def test_plugin_is_imported_only_when_used(installed, tmp_path):
    import sys

    installed(_stamp="fake_plugin:stamp_block")
    render(Ymprint(), tmp_path, "Report:\n  - Just text.\n")
    assert "fake_plugin" not in sys.modules
    render(Ymprint(), tmp_path, "Report:\n  - _stamp: once\n  - _stamp_b: twice\n")
    assert sys.modules["fake_plugin"].IMPORTS == [1]


def test_app_blocks_win_over_plugin_blocks(installed, tmp_path):
    installed(_stamp="fake_plugin:stamp_block", _p="fake_plugin:stamp_block")
    app = Ymprint()

    @app.block("_stamp")
    def own(block_key, block_value, context):
        return [Paragraph(f"OWN {block_value}", context["styles"]["rl"]["_style"]["body"])]

    registry = app.render_blocks()
    assert registry.get("_stamp") is own
    assert registry.get("_p") is app.blocks.get("_p")  # Built-ins win too.
    text = render(app, tmp_path, "Report:\n  - _stamp: mine\n")
    assert "OWN mine" in text and "STAMP" not in text


def test_registering_after_a_plugin_is_installed_does_not_conflict(installed):
    installed(_stamp="fake_plugin:stamp_block")
    app = Ymprint()
    app.register_block("_stamp", lambda k, v, c: [])  # No BlockExistsError.
    assert "_stamp" in app.blocks


def test_plugin_blocks_can_be_turned_off(installed, tmp_path):
    installed(_stamp="fake_plugin:stamp_block")
    app = Ymprint(plugin_blocks=False)
    assert "_stamp" not in app.render_blocks()
    # An unknown code is not a block, so the key renders as plain text.
    assert "STAMP" not in render(app, tmp_path, "Report:\n  - _stamp: x\n")


def test_broken_plugin_fails_only_its_blocks(installed, tmp_path):
    installed(_stamp="fake_plugin:stamp_block", _broken="broken_plugin:anything")
    app = Ymprint()
    assert "STAMP ok" in render(app, tmp_path, "Report:\n  - _stamp: ok\n")
    with pytest.raises(BlockError, match="failed to load.*missing dependency: shapely"):
        render(app, tmp_path, "Report:\n  - _broken_x: 1\n")


def test_non_callable_entry_is_reported(installed, tmp_path):
    installed(_odd="fake_plugin:not_callable")
    with pytest.raises(BlockError, match="not callable"):
        render(Ymprint(), tmp_path, "Report:\n  - _odd: 1\n")


@pytest.mark.parametrize("name", ["_two_parts", "_ul", "bad-code", "_"])
def test_invalid_codes_are_skipped_with_a_warning(installed, name):
    installed(**{name: "fake_plugin:stamp_block", "_stamp": "fake_plugin:stamp_block"})
    with pytest.warns(UserWarning, match="invalid block code"):
        blocks = plugins.plugin_blocks()
    assert list(blocks) == ["_stamp"]


def test_duplicate_codes_keep_the_first_with_a_warning():
    class Dist:
        def __init__(self, name):
            self.name, self.version = name, "1.0"

    class EP:
        def __init__(self, dist, value):
            self.name, self.value, self.dist = "_stamp", value, Dist(dist)

    with pytest.warns(UserWarning, match="provided by both 'alpha' and 'beta'"):
        blocks = plugins._discover_blocks([EP("beta", "b:x"), EP("alpha", "a:x")])
    assert blocks["_stamp"].owner == "alpha"
