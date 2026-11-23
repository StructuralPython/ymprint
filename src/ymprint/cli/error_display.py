"""Render :class:`YmprintAuthoringError` instances as compact, friendly output.

Python-block tracebacks are truncated to their *top and bottom*: the first few
frames (the calling context — which block triggered the failure) and the last
few frames (the exact line that blew up), with the middle collapsed, except for
frames in the document's own code (a function an earlier block defined, say). This keeps
even a deep stack readable while still telling the author both *where their
document caused it* and *what to fix*.
"""
from __future__ import annotations

import traceback
from typing import Optional

from rich.console import Group, RenderableType
from rich.text import Text

from ..errors import (
    BlockError,
    PythonBlockError,
    YamlSyntaxError,
    YmprintAuthoringError,
    block_key_of,
)

# How many stack frames to keep from each end before collapsing the middle.
HEAD_FRAMES = 2
TAIL_FRAMES = 3


def format_authoring_error(exc: YmprintAuthoringError) -> RenderableType:
    """Return a rich renderable describing an authoring error."""
    body = _format_error(exc)
    chain = getattr(exc, "include_chain", None)
    if not chain:
        return body
    names = [getattr(p, "name", None) or "the document" for p in chain]
    where = f"In the partial {names[-1]}, included from " + " → ".join(names[:-1])
    return Group(body, Text(where, style="yellow"))


def _format_error(exc: YmprintAuthoringError) -> RenderableType:
    if isinstance(exc, YamlSyntaxError):
        return _format_yaml_error(exc)
    if isinstance(exc, PythonBlockError):
        return _format_python_error(exc)
    if isinstance(exc, BlockError):
        return _format_block_error(exc)
    return Text(str(exc), style="red")


def _format_block_error(exc: BlockError) -> RenderableType:
    parts: list[RenderableType] = [
        Text(f"Error in block '{exc.block_key}'", style="bold red"),
        Text(str(exc), style="red"),
        Text("Fix the block in your document, then save to reload.", style="dim italic"),
    ]
    return Group(*parts)


def _format_yaml_error(exc: YamlSyntaxError) -> RenderableType:
    location = exc.filepath.name
    if exc.line is not None:
        location += f", line {exc.line}, column {exc.column}"

    parts: list[RenderableType] = [
        Text(f"YAML syntax error in {location}", style="bold red")
    ]
    if exc.problem:
        parts.append(Text(exc.problem, style="red"))
    if exc.snippet:
        parts.append(Text(exc.snippet, style="yellow"))
    parts.append(Text("Fix the YAML above, then save to reload.", style="dim italic"))
    return Group(*parts)


def _format_python_error(exc: PythonBlockError) -> RenderableType:
    original = exc.original
    parts: list[RenderableType] = [
        Text(f"Error in Python block '{exc.block_key}'", style="bold red")
    ]

    if isinstance(original, SyntaxError):
        # A SyntaxError fails at compile time, so there is no frame of the block in
        # the traceback. Use the exception's own line/offset instead, and detect
        # the common cause: forgetting the `|` block scalar, which folds the code
        # into a single line.
        parts.extend(_syntax_error_parts(exc, original))
        message = original.msg
    else:
        frames = traceback.extract_tb(original.__traceback__)
        source_lines = exc.source.splitlines()
        own = _own_filename(frames)
        failing = _failing_source_line(frames, source_lines, own)
        if failing is not None:
            parts.append(failing)
        parts.append(Text("Traceback (most relevant frames):", style="dim"))
        parts.extend(_compact_frames(frames, source_lines, own))
        message = str(original)

    parts.append(Text(f"{type(original).__name__}: {message}", style="bold red"))
    return Group(*parts)


def _syntax_error_parts(
    exc: PythonBlockError, original: SyntaxError
) -> list[RenderableType]:
    parts: list[RenderableType] = []
    single_line = "\n" not in exc.source.strip()
    text = (original.text or "").rstrip("\n")
    lineno = original.lineno or 1

    if text:
        line = Text()
        line.append(f"→ line {lineno}: ", style="bold yellow")
        line.append(text.strip(), style="yellow")
        parts.append(line)

    if single_line:
        # The code collapsed onto one line — almost always a missing block scalar.
        parts.append(
            Text(
                "Hint: this block parsed as a single line. If the code was meant "
                "to span multiple lines, use a YAML block scalar — write "
                "'source: |' and indent the code beneath it.",
                style="yellow",
            )
        )
    return parts


def _own_filename(frames: list[traceback.FrameSummary]) -> Optional[str]:
    """The filename the failing block's source was compiled as.

    A block's source runs as a module, so its outermost frame is the first
    `<module>` frame; anything below that came from the block's own code or
    from code it called.
    """
    for frame in frames:
        if frame.name == "<module>":
            return frame.filename
    return None


def _is_author_code(frame: traceback.FrameSummary) -> bool:
    """A frame in a document's code (a block's source), not in a library."""
    return frame.filename.startswith("<") and frame.filename.endswith(">")


def _frame_source(
    frame: traceback.FrameSummary, source_lines: list[str], own: Optional[str]
) -> Optional[str]:
    """Text of the frame's line; frames of the failing block map to its source."""
    if frame.line:
        return frame.line.strip()
    if frame.filename == own and 1 <= frame.lineno <= len(source_lines):
        return source_lines[frame.lineno - 1].strip()
    return None


def _frame_where(frame: traceback.FrameSummary, own: Optional[str]) -> str:
    if frame.filename == own:
        return "your Python block"
    key = block_key_of(frame.filename)
    if key is not None:
        return f"an earlier block '{key}'"
    if _is_author_code(frame):
        return "an earlier block"
    return frame.filename


def _render_frame(
    frame: traceback.FrameSummary, source_lines: list[str], own: Optional[str] = None
) -> Text:
    text = Text("  ")
    text.append(_frame_where(frame, own), style="cyan")
    text.append(f", line {frame.lineno}, in {frame.name}", style="dim")
    line = _frame_source(frame, source_lines, own)
    if line:
        text.append("\n      ")
        text.append(line, style="white")
    return text


def _compact_frames(
    frames: list[traceback.FrameSummary],
    source_lines: list[str],
    own: Optional[str] = None,
) -> list[RenderableType]:
    """The first and last frames, and every frame in the document's own code."""
    count = len(frames)
    shown = [
        i < HEAD_FRAMES or i >= count - TAIL_FRAMES or _is_author_code(frame)
        for i, frame in enumerate(frames)
    ]
    parts: list[RenderableType] = []
    hidden = 0
    for frame, show in zip(frames, shown):
        if not show:
            hidden += 1
            continue
        if hidden:
            parts.append(Text(f"  … {hidden} frame(s) hidden …", style="dim italic"))
            hidden = 0
        parts.append(_render_frame(frame, source_lines, own))
    return parts


def _failing_source_line(
    frames: list[traceback.FrameSummary],
    source_lines: list[str],
    own: Optional[str] = None,
) -> Optional[Text]:
    """Highlight the block's own line that raised (its deepest frame)."""
    own_frames = [f for f in frames if f.filename == own]
    if not own_frames:
        return None
    lineno = own_frames[-1].lineno
    if not (1 <= lineno <= len(source_lines)):
        return None
    text = Text()
    text.append(f"→ line {lineno}: ", style="bold yellow")
    text.append(source_lines[lineno - 1].strip(), style="yellow")
    return text
