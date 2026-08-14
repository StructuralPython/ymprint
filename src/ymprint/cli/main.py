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


@app.command(
    name='convert',
    short_help="Convert will render a single YAML file to a PDF file.",
    no_args_is_help=True
)
def convert(
    src: str,
    dest: str | None = None,
    config_dir: str | None = None
    ):
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
    short_help='Live mode renders your PDF file and opens it with Okular. Any changes are hot-reloaded.',
    no_args_is_help=True
)
def live(
    src: Annotated[str, "YAML file path to render to PDF"],
    dest: Annotated[Optional[str], "File path of output PDF file. If not provided file name and path of source file will be used (wtih .pdf extension)."] = None,
    config_file: Annotated[Optional[str], "Location of optional document config *.ymprint.yml file"] = None,
):
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
