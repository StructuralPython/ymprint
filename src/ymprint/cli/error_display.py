"""Render :class:`YmprintAuthoringError` instances as compact, friendly output.

Python-block tracebacks are truncated to their *top and bottom*: the first few
frames (the calling context — which block triggered the failure) and the last
few frames (the exact line that blew up), with the middle collapsed. This keeps
even a deep stack readable while still telling the author both *where their
document caused it* and *what to fix*.
"""
from __future__ import annotations

import traceback
from typing import Optional

from rich.console import Group, RenderableType
from rich.text import Text

from ..errors import PythonBlockError, YamlSyntaxError, YmprintAuthoringError

# How many stack frames to keep from each end before collapsing the middle.
HEAD_FRAMES = 2
TAIL_FRAMES = 3


def format_authoring_error(exc: YmprintAuthoringError) -> RenderableType:
    """Return a rich renderable describing an authoring error."""
    if isinstance(exc, YamlSyntaxError):
        return _format_yaml_error(exc)
    if isinstance(exc, PythonBlockError):
        return _format_python_error(exc)
    return Text(str(exc), style="red")


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
        # A SyntaxError fails at compile time, so there is no `<string>` frame in
        # the traceback. Use the exception's own line/offset instead, and detect
        # the common cause: forgetting the `|` block scalar, which folds the code
        # into a single line.
        parts.extend(_syntax_error_parts(exc, original))
        message = original.msg
    else:
        frames = traceback.extract_tb(original.__traceback__)
        source_lines = exc.source.splitlines()
        failing = _failing_source_line(frames, source_lines)
        if failing is not None:
            parts.append(failing)
        parts.append(Text("Traceback (most relevant frames):", style="dim"))
        parts.extend(_compact_frames(frames, source_lines))
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


def _frame_source(frame: traceback.FrameSummary, source_lines: list[str]) -> Optional[str]:
    """Text of the frame's line, mapping exec'd `<string>` frames to the block."""
    if frame.line:
        return frame.line.strip()
    if frame.filename == "<string>" and 1 <= frame.lineno <= len(source_lines):
        return source_lines[frame.lineno - 1].strip()
    return None


def _render_frame(frame: traceback.FrameSummary, source_lines: list[str]) -> Text:
    where = "your Python block" if frame.filename == "<string>" else frame.filename
    text = Text("  ")
    text.append(where, style="cyan")
    text.append(f", line {frame.lineno}, in {frame.name}", style="dim")
    line = _frame_source(frame, source_lines)
    if line:
        text.append("\n      ")
        text.append(line, style="white")
    return text


def _compact_frames(
    frames: list[traceback.FrameSummary], source_lines: list[str]
) -> list[RenderableType]:
    if len(frames) <= HEAD_FRAMES + TAIL_FRAMES:
        return [_render_frame(f, source_lines) for f in frames]

    hidden = len(frames) - HEAD_FRAMES - TAIL_FRAMES
    head = [_render_frame(f, source_lines) for f in frames[:HEAD_FRAMES]]
    tail = [_render_frame(f, source_lines) for f in frames[-TAIL_FRAMES:]]
    marker = Text(f"  … {hidden} frame(s) hidden …", style="dim italic")
    return [*head, marker, *tail]


def _failing_source_line(
    frames: list[traceback.FrameSummary], source_lines: list[str]
) -> Optional[Text]:
    """Highlight the author's own line that raised (the deepest `<string>` frame)."""
    string_frames = [f for f in frames if f.filename == "<string>"]
    if not string_frames:
        return None
    lineno = string_frames[-1].lineno
    if not (1 <= lineno <= len(source_lines)):
        return None
    text = Text()
    text.append(f"→ line {lineno}: ", style="bold yellow")
    text.append(source_lines[lineno - 1].strip(), style="yellow")
    return text
