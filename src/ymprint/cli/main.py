import subprocess
import time
from typing import Optional, Annotated
from pathlib import Path
from .throbber import ThrobberState, FPS
from rich.text import Text
from rich.console import Console
from rich.live import Live
import typer
from typer import Typer

from ..report_reader import load_report
from .config import locate_config_dir, CONFIG_FILENAMES
from .okular import ensure_okular
from ..config.config_loaders import load_config_directory

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


def build_display(state: ThrobberState, status: str) -> Text:
    bar = state.render()
    label = Text(f"\n {status}", style="dim white")
    bar.append_text(label)
    return bar


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
    # Identify config files and content files to watch here
    # ensure_demo_file()
    if config_dir is None:
        config_dir = locate_config_dir(Path.cwd())

    load_report(source, destination, config_dir)
    console = Console()
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
    config_dir: Annotated[Optional[str], "Directory of optional config files (doctemplate.yml, textstyles.yml, tablestyles.yml)"] = None,
):
    source = Path(src)
    if dest is None:
        destination = source.parent / f"{source.stem}.pdf"
    else:
        destination = Path(dest)
    # Identify config files and content files to watch here
    # ensure_demo_file()
    if config_dir is None:
        config_dir = locate_config_dir(Path.cwd())
    
    file_watchers = [FileWatcher(Path(source))]
    if config_dir is not None:
        config_dir = Path(config_dir)
        for filename in CONFIG_FILENAMES:
            if (config_dir / filename).exists():
                file_watchers.append(FileWatcher(config_dir / filename))
    else:
        config_dir = source.parent
    print(file_watchers)

    console = Console()

    # Live mode relies on Okular to display and hot-reload the PDF. Make sure it
    # is available, offering a platform-specific install if it is missing.
    okular_cmd = ensure_okular(console)
    if okular_cmd is None:
        raise typer.Exit(code=1)

    state = ThrobberState()
    # watcher = FileWatcher(WATCH_FILE)
    frame_time = 1.0 / FPS

    console.print(
        f"\n[bold cyan]YMPrint live mode[/bold cyan]  "
        f"[dim]watching [white]{str(source)}[/white] — "
        f"Ctrl+C to quit[/dim]\n"
    )
    load_report(source, destination, config_dir)
    okular_sub = subprocess.Popen([*okular_cmd, str(destination)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    status = ""
    with Live(
        build_display(state, status),
        console=console,
        refresh_per_second=FPS,
        transient=False,
    ) as live:
        try:
            while True:
                t0 = time.monotonic()
                for watcher in file_watchers:
                    if watcher.changed():
                        state.trigger_explosion()
                        status = f"change detected in {str(watcher.path)}!"
                        load_report(source, destination, config_dir)
                        break

                    elif not state.explosions:
                        status = f"watching {(str(file_watchers))} …"

                state.advance()
                live.update(build_display(state, status))

                elapsed = time.monotonic() - t0
                sleep = max(0.0, frame_time - elapsed)
                time.sleep(sleep)

        except KeyboardInterrupt:
            console.print("\n[dim]Live mode ended.[/dim]\n")