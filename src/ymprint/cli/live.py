"""Live mode: render a document, show it in Okular, and hot-reload on every save.

``ym live`` and ``Ymprint.live`` are thin wrappers around :func:`run_live`. Every
refresh is an ``app.render(...)``, so the application's blocks and render hooks
apply in live mode exactly as they do for ``convert``.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Optional

import platformdirs
import typer
from rich import box
from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text
from rich.traceback import Traceback

from ..config.pdf_postprocessing import DestinationLockedError, replace_destination, staging_path
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


def format_render_error(exc: Exception) -> RenderableType:
    headline = Text()
    headline.append("✗ Render failed\n", style="bold red")
    headline.append(f"{type(exc).__name__}: {exc}", style="red")
    trace = Traceback.from_exception(type(exc), exc, exc.__traceback__, max_frames=3)
    return Group(headline, Text(), trace)


# Seconds to keep retrying when saving the preview to a locked destination on exit.
PUBLISH_LOCK_TIMEOUT = 10.0


def preview_path(destination: Path) -> Path:
    """
    The local copy live mode renders to once `destination` is found locked. It is
    keyed by the destination's full path and keeps its file name for the viewer.
    """
    digest = hashlib.sha1(str(destination.resolve()).encode()).hexdigest()[:12]
    return Path(platformdirs.user_cache_dir("ymprint")) / "live" / digest / destination.name


def publish_preview(preview: Path, destination: Path, console: Console) -> bool:
    """Copy the local preview over `destination`; return True if it was saved."""
    staged = staging_path(destination)
    try:
        shutil.copyfile(preview, staged)
        replace_destination(staged, destination, timeout=PUBLISH_LOCK_TIMEOUT)
    except OSError as exc:
        console.print(
            f"[red]Could not save {destination}: {exc}[/red]\n"
            f"The latest PDF is at [bold]{preview}[/bold]; copy it there by hand."
        )
        return False
    console.print(f"[green]Saved {destination}.[/green]")
    return True


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
    vars: Optional[dict] = None,
    only: Optional[dict] = None,
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
        vars: Variables layered over the document's ``_vars``.
        only: Select one parameter set of a document rendered per parameter
            set (e.g. ``{"member_name": "B02"}``): live mode renders that set,
            to its ``output`` unless `destination` is given.
        console: Rich console to draw on. Defaults to a new ``Console()``.

    Files changed by the hooks themselves (for instance, a ``before_render``
    that regenerates the source document) do not trigger another render.

    If `destination` stays locked by another program (e.g. a sync client on a
    shared drive), live mode switches to rendering a local preview copy, opens
    it in a new viewer, and saves it over `destination` when the session ends.
    """
    source = Path(source)
    console = console or Console()
    vars = dict(vars or {})
    params: dict = {}
    if only:
        try:
            selected = app.instances(source, config_path, only=only) if source.exists() else []
        except (ValueError, YmprintAuthoringError) as exc:
            console.print(f"[red]{exc}[/red]")
            return 2
        if len(selected) != 1:
            console.print(
                f"[red]--only must select exactly one parameter set of {source.name}; "
                f"it matches {len(selected)}.[/red]"
            )
            return 2
        params = selected[0].params
        vars = {**params, **vars}
        if destination is None:
            destination = selected[0].destination
            destination.parent.mkdir(parents=True, exist_ok=True)
    if destination is None:
        destination = source.parent / f"{source.stem}.pdf"
    else:
        destination = Path(destination)

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
    # Set once the destination is found locked; every later render goes here.
    preview: Optional[Path] = None
    preview_rendered = False
    viewer_opened = False

    def open_viewer(path: Path) -> None:
        nonlocal viewer_opened
        subprocess.Popen(
            [*okular_cmd, str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        viewer_opened = True

    def watch_inputs(event) -> None:
        # Data files the document read (its `_data` sources) are watched too, so
        # editing the data re-renders the document that uses it.
        watched = {w.path.resolve() for w in file_watchers}
        file_watchers.extend(FileWatcher(p) for p in sorted(event.inputs) if p not in watched)

    def render_once(trigger: Optional[Path]) -> None:
        nonlocal preview, preview_rendered
        try:
            event = app.render(
                source, destination, config_path,
                trigger=trigger, mode="live", output=preview, vars=vars, params=params,
            )
        except DestinationLockedError:
            if preview is not None:
                raise
            preview = preview_path(destination)
            preview.parent.mkdir(parents=True, exist_ok=True)
            event = app.render(
                source, destination, config_path,
                trigger=trigger, mode="live", output=preview, vars=vars, params=params,
            )
            if viewer_opened:
                open_viewer(preview)
        watch_inputs(event)
        if preview is not None:
            preview_rendered = True

    def render(trigger: Optional[Path] = None) -> tuple[RenderableType, str]:
        """Attempt a render; return the (lower panel, border colour) to show."""
        try:
            render_once(trigger)
        except YmprintAuthoringError as exc:
            state.trigger_error_explosion()
            return format_authoring_error(exc), "red"
        except RenderCallbackError as exc:
            state.trigger_error_explosion()
            return format_callback_error(exc), "red"
        except Exception as exc:
            # Anything else (e.g. an unwritable destination) is shown, not fatal:
            # the next save tries again.
            state.trigger_error_explosion()
            return format_render_error(exc), "red"
        finally:
            # Ignore changes the hooks made to watched files so they do not
            # retrigger a render in an endless loop.
            for watcher in file_watchers:
                watcher.sync()
        names = ", ".join(w.path.name for w in file_watchers)
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = Text(f"✓ Reloaded {names} at {stamp}", style="green")
        if preview is not None:
            status.append(
                f"\n⚠ {destination.name} is locked by another program (e.g. a sync client).\n"
                f"  Previewing a local copy; it is saved to the destination when live mode ends.",
                style="yellow",
            )
        return status, "green"

    exit_code = 0
    try:
        # Initial render before opening the viewer.
        lower, border = render()
        open_viewer(preview or destination)

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
    finally:
        # Also runs if the session crashes, so the latest render is not stranded
        # in the local preview.
        if preview_rendered and not publish_preview(preview, destination, console):
            exit_code = 1
    return exit_code
