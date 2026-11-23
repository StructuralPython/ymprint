"""Exception types for ymprint.

These represent problems in the *author's document* — a YAML syntax mistake or
an exception raised by the author's own Python (`_py`) block — as opposed to a
bug inside ymprint itself. The CLI catches :class:`YmprintAuthoringError` and
presents it in a friendly, compact way; anything else is a genuine ymprint bug
and is allowed to propagate as a normal traceback.
"""
from __future__ import annotations

import hashlib
import linecache
import pathlib
from typing import Optional

# The blocks whose source was compiled by `block_filename`: filename -> block key.
_BLOCK_FILENAMES: dict[str, str] = {}


def block_filename(block_key: str, source: str) -> str:
    """A filename to compile a block's source with, so tracebacks show its lines.

    The source is registered with :mod:`linecache` under this name, so every
    frame in the block (including frames in functions it defines, called from
    later blocks) shows its own line, and the error display can tell which block
    a frame came from.
    """
    digest = hashlib.sha1(source.encode("utf-8")).hexdigest()[:10]
    filename = f"<ymprint {block_key} {digest}>"
    lines = source.splitlines(keepends=True)
    # mtime None: linecache.checkcache leaves the entry alone.
    linecache.cache[filename] = (len(source), None, lines, filename)
    _BLOCK_FILENAMES[filename] = block_key
    return filename


def block_key_of(filename: str) -> Optional[str]:
    """The key of the block compiled as 'filename' by `block_filename`, if any."""
    return _BLOCK_FILENAMES.get(filename)


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


class BlockError(YmprintAuthoringError):
    """A block could not be rendered because of a problem in the author's document.

    Covers a missing required field, an empty/`None` block value, or the wrong
    data shape being passed to a block — author mistakes that would otherwise
    surface as a raw ``KeyError``/``TypeError``/``AttributeError`` and crash
    live mode. Retains the block key so the report can point at the offending
    block.
    """

    def __init__(self, block_key: str, message: str):
        self.block_key = block_key
        super().__init__(message)


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


class BackgroundNotFoundError(YmprintAuthoringError):
    """A page template's background PDF does not exist.

    Names the template, the path as written, where it resolved to and the
    `relative-to` rule that resolved it, since a wrong base directory is the
    usual cause.
    """

    def __init__(self, template: str, filepath: str, resolved: pathlib.Path, relative_to: Optional[str]):
        self.template = template
        self.filepath = filepath
        self.resolved = resolved
        self.relative_to = relative_to
        rule = f"relative-to: {relative_to}" if relative_to else "relative to the file that declares it"
        super().__init__(
            f"The background PDF of page template {template!r} was not found: {filepath!r} "
            f"resolved ({rule}) to {resolved}"
        )


class IncludeError(YmprintAuthoringError):
    """An `_include` could not be resolved, or the partial it names is invalid.

    Covers a missing or relative path, a partial that is empty or uses a key only
    a document may use (`_doc`, `_export`, ...), and a partial that includes
    itself. Errors raised while a partial renders keep the chain of partials in
    `include_chain` instead.
    """
