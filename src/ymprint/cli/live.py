"""Live mode: render a document, show it in Okular, and hot-reload on every save.

``ym live`` and ``Ymprint.live`` are thin wrappers around :func:`run_live`. Every
refresh is an ``app.render(...)``, so the application's blocks and render hooks
apply in live mode exactly as they do for ``convert``.
"""
from __future__ import annotations

import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Optional

import typer
from rich import box
from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text
from rich.traceback import Traceback

from ..errors import YmprintAuthoringError
from ..render import RenderCallbackError
from .error_display import format_authoring_error
from .okular import ensure_okular
from .throbber import FPS, ThrobberState

if TYPE_CHECKING:
    from ..app import Ymprint


class FileWatcher:
    def __init__(self, path: Path):
        self.path = path
        self._mtime: Optional[float] = self._read_mtime()

    def __repr__(self):
        return str(self.path.resolve())

    def _read_mtime(self) -> Optional[float]:
        try:
            return self.path.stat().st_mtime
        except FileNotFoundError:
            return None

    def changed(self) -> bool:
        mtime = self._read_mtime()
        if mtime != self._mtime:
            self._mtime = mtime
            return True
        return False

    def sync(self) -> None:
        """Accept the file's current state as seen, without reporting a change."""
        self._mtime = self._read_mtime()


def format_callback_error(exc: RenderCallbackError) -> RenderableType:
    original = exc.original
    headline = Text()
    name = getattr(exc.callback, "__qualname__", repr(exc.callback))
    headline.append(f"✗ {exc.stage} hook {name} failed\n", style="bold red")
    headline.append(f"{type(original).__name__}: {original}", style="red")
    trace = Traceback.from_exception(
        type(original), original, original.__traceback__, max_frames=3
    )
    return Group(headline, Text(), trace)


def build_live_panel(
    state: ThrobberState,
    watchers: list[FileWatcher],
    lower: RenderableType,
    border_style: str,
) -> Panel:
    """Assemble the two-part live panel: watch list + throbber over a status area."""
    header = Text()
    header.append("👁  ", style="bold")
    header.append("YMPrint live", style="bold cyan")
    header.append("  ·  hot-reloading", style="dim")

    files = Text()
    for watcher in watchers:
        files.append("   • ", style="dim")
        files.append(f"{watcher.path.name}\n", style="cyan")
    files.append("     ", style="dim")
    files.append(str(watchers[0].path.resolve().parent), style="dim")

    upper = Group(header, Text(), files, Text(), state.render())
    body = Group(upper, Rule(style=border_style), lower)

    return Panel(
        body,
        title="[bold]✨ ymprint ✨[/bold]",
        subtitle="[dim]Ctrl+C to quit[/dim]",
        border_style=border_style,
        box=box.ROUNDED,
        padding=(1, 2),
    )


def _initialize_document(source: Path, starter_document: str, console: Console) -> bool:
    """
    Offer to create a starter document at `source` when it does not exist.

    Returns True if a document now exists at `source` (it was created), False if
    the user declined.
    """
    console.print(
        f"[yellow]The document [bold]{source}[/bold] does not exist yet.[/yellow]"
    )
    if not typer.confirm(f"Create a new starter document at {source}?", default=True):
        return False
    try:
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(starter_document.format(title=source.stem or "Untitled document"))
    except OSError as exc:
        console.print(f"[red]Could not create {source}: {exc}[/red]")
        return False
    console.print(f"[green]Created {source}.[/green]")
    return True


def run_live(
    app: "Ymprint",
    source: str | Path,
    destination: Optional[str | Path] = None,
    config_path: Optional[str | Path] = None,
    *,
    watch: Iterable[str | Path] = (),
    console: Optional[Console] = None,
) -> int:
    """
    Render `source` with `app`, open it in Okular, and hot-reload on every change.

    Blocks until Ctrl+C and returns a process exit code (0 on a normal exit).

    Args:
        app: The Ymprint application whose blocks, hooks and config are used.
        source: YAML document to render and watch. If it does not exist, the
            user is offered the app's starter document at that path.
        destination: Output PDF. Defaults to `source` with a ``.pdf`` suffix.
        config_path: An explicit config file or directory, layered over the app's
            config and any ``*.ymprint.yml`` found next to the source.
        watch: Extra files whose changes should also trigger a re-render, e.g.
            the inputs a ``before_render`` hook reads.
        console: Rich console to draw on. Defaults to a new ``Console()``.

    Files changed by the hooks themselves (for instance, a ``before_render``
    that regenerates the source document) do not trigger another render.
    """
    source = Path(source)
    if destination is None:
        destination = source.parent / f"{source.stem}.pdf"
    else:
        destination = Path(destination)
    console = console or Console()

    # Live mode can bootstrap a new document: if the source does not exist yet,
    # offer to create a starter file so the user can begin editing immediately.
    if not source.exists():
        if not _initialize_document(source, app.starter_document, console):
            console.print("[dim]No document to render. Exiting.[/dim]")
            return 0

    file_watchers = [FileWatcher(source)]
    config_layers = app.config_layers(source.resolve().parent, config_path)
    file_watchers.extend(FileWatcher(p) for p in config_layers if p.is_file())
    file_watchers.extend(FileWatcher(Path(p)) for p in watch)

    # Live mode relies on Okular to display and hot-reload the PDF. Make sure it
    # is available, offering a platform-specific install if it is missing.
    okular_cmd = ensure_okular(console)
    if okular_cmd is None:
        return 1

    state = ThrobberState()
    frame_time = 1.0 / FPS

    def render(trigger: Optional[Path] = None) -> tuple[RenderableType, str]:
        """Attempt a render; return the (lower panel, border colour) to show."""
        try:
            app.render(source, destination, config_path, trigger=trigger, mode="live")
        except YmprintAuthoringError as exc:
            state.trigger_error_explosion()
            return format_authoring_error(exc), "red"
        except RenderCallbackError as exc:
            state.trigger_error_explosion()
            return format_callback_error(exc), "red"
        finally:
            # Ignore changes the hooks made to watched files so they do not
            # retrigger a render in an endless loop.
            for watcher in file_watchers:
                watcher.sync()
        names = ", ".join(w.path.name for w in file_watchers)
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return Text(f"✓ Reloaded {names} at {stamp}", style="green"), "green"

    # Initial render before opening the viewer.
    lower, border = render()
    subprocess.Popen(
        [*okular_cmd, str(destination)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    with Live(
        build_live_panel(state, file_watchers, lower, border),
        console=console,
        refresh_per_second=FPS,
        transient=False,
    ) as live:
        try:
            while True:
                t0 = time.monotonic()

                changed = next((w for w in file_watchers if w.changed()), None)
                if changed is not None:
                    # A save clears any prior error immediately and shows the
                    # reload in progress before we attempt it.
                    state.trigger_explosion()
                    lower = Text(f"⟳ reloading ({changed.path.name}) …", style="yellow")
                    border = "yellow"
                    live.update(build_live_panel(state, file_watchers, lower, border))
                    lower, border = render(changed.path)

                state.advance()
                live.update(build_live_panel(state, file_watchers, lower, border))

                elapsed = time.monotonic() - t0
                time.sleep(max(0.0, frame_time - elapsed))

        except KeyboardInterrupt:
            console.print("\n[dim]Live mode ended.[/dim]\n")
    return 0
