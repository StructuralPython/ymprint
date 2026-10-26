"""
The optional `_hc` block, registered when ym-handcalcs is installed
(`pip install ymprint[hc]`).
"""
import subprocess
import sys
from importlib.util import find_spec

import pymupdf
import pytest

from ymprint import Ymprint, default_app
from ymprint.blocks.builtin import BUILTIN_BLOCKS
from ymprint.errors import PythonBlockError

HC_INSTALLED = find_spec("ym_handcalcs") is not None
needs_hc = pytest.mark.skipif(not HC_INSTALLED, reason="ym-handcalcs is not installed")


def test_hc_is_a_builtin_block_only_when_ym_handcalcs_is_installed():
    assert ("_hc" in BUILTIN_BLOCKS) == HC_INSTALLED


def test_importing_ymprint_does_not_import_handcalcs():
    code = "import sys, ymprint; print('ym_handcalcs' in sys.modules, 'handcalcs' in sys.modules)"
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert result.stdout.split() == ["False", "False"]


@needs_hc
def test_hc_block_renders_with_the_default_app(tmp_path):
    document = {
        "_vars": {"w": 3},
        "Beam": [
            {"_hc": "L = 6\nM = w * L * L / 8\n"},
            "The moment is {{ M }}.",
        ],
    }
    destination = tmp_path / "beam.pdf"
    default_app.render(document, destination)
    with pymupdf.open(destination) as pdf:
        text = " ".join("".join(page.get_text() for page in pdf).split())
    assert "M = w · L · L / 8 = 3 · 6 · 6 / 8 = 13.5" in text
    assert "The moment is 13.5." in text


@needs_hc
def test_hc_block_can_be_left_out_of_an_app():
    app = Ymprint(builtin_blocks=False)
    assert "_hc" not in app.blocks


@needs_hc
def test_a_failing_hc_block_is_a_python_block_error(tmp_path):
    with pytest.raises(PythonBlockError):
        default_app.render({"Calcs": [{"_hc": "x = 1 / 0\n"}]}, tmp_path / "out.pdf")
