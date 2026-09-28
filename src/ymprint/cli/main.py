import subprocess
import time
from datetime import datetime
from typing import Optional, Annotated
from pathlib import Path
from .throbber import ThrobberState, FPS
from .error_display import format_authoring_error
from ..errors import YmprintAuthoringError
from rich import box
from rich.text import Text
from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.rule import Rule
import typer
from typer import Typer

from ..report_reader import load_report
from .config import locate_config_file
from .okular import ensure_okular

app = Typer(name='ymp', no_args_is_help=True)


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


def _resolve_config(config_file: Optional[str], source: Path) -> Optional[Path]:
    if config_file is not None:
        return Path(config_file)
    return locate_config_file(source.resolve().parent)


# A minimal, valid starter document written when the user opts to initialize a new
# file in live mode. It renders to a one-heading, one-paragraph PDF.
STARTER_DOCUMENT = """\
{title}:
  - >
    Start writing your report here. This paragraph sits under the heading above.
    Edit this file and save — live mode will hot-reload the PDF.
"""


def _initialize_document(source: Path, console: Console) -> bool:
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
        source.write_text(STARTER_DOCUMENT.format(title=source.stem or "Untitled document"))
    except OSError as exc:
        console.print(f"[red]Could not create {source}: {exc}[/red]")
        return False
    console.print(f"[green]Created {source}.[/green]")
    return True


@app.command(
    name='convert',
    short_help="Convert will render a single YAML file to a PDF file.",
    no_args_is_help=True
)
def convert(
    src: Annotated[str, typer.Argument(
        help="Path to YAML source file to be converted to PDF."
    )],
    dest: Annotated[str | None, typer.Option(
        help='File path of the PDF to be created. If not provided the destination file name will match the source file name.'
    )] = None,
    config_dir: Annotated[str | None, typer.Option(
        help=
            "Path to specific config directory to use. "
            "Config directory must have an *.ymprint.yml file in it. "
            "If not provided, ymprint will recursively search the source file's parent directories until an *.ymprint.yml file is found. "
            "If no config file is found, ymprint will use the default config file."
        )] = None
):
    """
    Render a single YAML source file to a PDF, once.

    Writes the PDF next to the source file (or to DEST if given) and exits.
    Errors in the authored document are reported without a traceback.
    """
    source = Path(src)
    destination = Path(dest) if dest is not None else None
    if destination is None:
        destination = source.parent / f"{source.stem}.pdf"

    config_path = _resolve_config(config_dir, source)
    console = Console()

    try:
        load_report(source, destination, config_path)
    except YmprintAuthoringError as exc:
        # This is a problem in the author's document, not an ymprint crash. Make
        # that explicit and show the actionable, compact error.
        console.print(
            Panel(
                format_authoring_error(exc),
                title="[bold red]ymprint convert — error in your document[/bold red]",
                subtitle="[dim]this is an error in the file you authored, not an ymprint bug[/dim]",
                border_style="red",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )
        raise typer.Exit(code=1)

    console.print(
        f"✍️ .... 📝 ... PDF created: {destination.resolve()}"
    )



@app.command(
    name='live',
    short_help='Live mode renders your PDF file and opens it with Okular. Any changes are hot-reloaded. If the source file does not exist, you can create a starter document to begin authoring.',
    no_args_is_help=True
)
def live(
    src: Annotated[str, typer.Argument(
        help="YAML file to render and watch. If it does not exist, live mode offers to create a starter document at that path."
    )],
    dest: Annotated[Optional[str], typer.Option(
        help="File path of output PDF file. If not provided file name and path of source file will be used (with .pdf extension)."
    )] = None,
    config_file: Annotated[Optional[str], typer.Option(
        help="Location of optional document config *.ymprint.yml file"
    )] = None,
):
    """
    Render SRC to a PDF, open it in Okular, and hot-reload on every save.

    Live mode watches the source file (and the config file, if one is in play)
    and rebuilds the PDF whenever they change. If SRC does not exist, you'll be
    prompted to create a minimal starter document at that path and drop straight
    into live editing. Press Ctrl+C to stop.
    """
    source = Path(src)
    if dest is None:
        destination = source.parent / f"{source.stem}.pdf"
    else:
        destination = Path(dest)

    config_path = _resolve_config(config_file, source)

    file_watchers = [FileWatcher(source)]
    if config_path is not None and config_path.is_file():
        file_watchers.append(FileWatcher(config_path))

    console = Console()

    # Live mode can bootstrap a new document: if the source does not exist yet,
    # offer to create a starter file so the user can begin editing immediately.
    if not source.exists():
        if not _initialize_document(source, console):
            console.print("[dim]No document to render. Exiting.[/dim]")
            raise typer.Exit(code=0)
        # Refresh the watcher so the first render sees the file we just created.
        file_watchers[0] = FileWatcher(source)

    # Live mode relies on Okular to display and hot-reload the PDF. Make sure it
    # is available, offering a platform-specific install if it is missing.
    okular_cmd = ensure_okular(console)
    if okular_cmd is None:
        raise typer.Exit(code=1)

    state = ThrobberState()
    frame_time = 1.0 / FPS

    def render() -> tuple[RenderableType, str]:
        """Attempt a render; return the (lower panel, border colour) to show."""
        try:
            load_report(source, destination, config_path)
        except YmprintAuthoringError as exc:
            state.trigger_error_explosion()
            return format_authoring_error(exc), "red"
        names = ", ".join(w.path.name for w in file_watchers)
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return Text(f"✓ Reloaded {names} at {stamp}", style="green"), "green"

    # Initial render before opening the viewer.
    lower, border = render()
    okular_sub = subprocess.Popen(
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
                    lower, border = render()

                state.advance()
                live.update(build_live_panel(state, file_watchers, lower, border))

                elapsed = time.monotonic() - t0
                time.sleep(max(0.0, frame_time - elapsed))

        except KeyboardInterrupt:
            console.print("\n[dim]Live mode ended.[/dim]\n")
