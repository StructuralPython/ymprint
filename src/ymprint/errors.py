"""Exception types for ymprint.

These represent problems in the *author's document* — a YAML syntax mistake or
an exception raised by the author's own Python (`_py`) block — as opposed to a
bug inside ymprint itself. The CLI catches :class:`YmprintAuthoringError` and
presents it in a friendly, compact way; anything else is a genuine ymprint bug
and is allowed to propagate as a normal traceback.
"""
from __future__ import annotations

import pathlib
from typing import Optional


class YmprintAuthoringError(Exception):
    """Base class for errors caused by the author's document, not by ymprint."""


class YamlSyntaxError(YmprintAuthoringError):
    """A YAML file could not be parsed.

    Wraps a ``ruamel.yaml`` error, pulling out the line/column and a source
    snippet where available so the author can jump straight to the problem.
    """

    def __init__(self, filepath: str | pathlib.Path, original: Exception):
        self.filepath = pathlib.Path(filepath)
        self.original = original
        self.problem = str(getattr(original, "problem", "") or "").strip()
        self.line: Optional[int] = None
        self.column: Optional[int] = None
        self.snippet: Optional[str] = None

        # ruamel's MarkedYAMLError exposes a `problem_mark` with 0-based
        # line/column and a `get_snippet()` helper that renders a caret.
        mark = getattr(original, "problem_mark", None)
        if mark is not None:
            self.line = mark.line + 1
            self.column = mark.column + 1
            try:
                self.snippet = mark.get_snippet()
            except Exception:
                self.snippet = None

        super().__init__(self.problem or str(original))


class PythonBlockError(YmprintAuthoringError):
    """An author's Python (`_py`) block raised an exception during execution.

    Retains the block key and the author's source so the failing line can be
    shown, plus the original exception (with its traceback) for a compact
    top-and-bottom stack rendering.
    """

    def __init__(self, block_key: str, source: str, original: BaseException):
        self.block_key = block_key
        self.source = source
        self.original = original
        super().__init__(f"{type(original).__name__}: {original}")
