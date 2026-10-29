from typing import TYPE_CHECKING, Optional, Annotated
from pathlib import Path
from .error_display import format_authoring_error
from ..config.pdf_postprocessing import DestinationLockedError
from ..errors import YmprintAuthoringError
from ..fanout import RenderUsageError, parse_assignments
from ..render import RenderCallbackError
from rich import box
from rich.console import Console
from rich.panel import Panel
import typer
from typer import Typer

from .live import format_callback_error, format_render_error, run_live

if TYPE_CHECKING:
    from ..app import Ymprint


def build_cli(ym_app: "Ymprint") -> Typer:
    """
    Returns a Typer app with `convert` and `live` commands that render with
    'ym_app' (its blocks, hooks and config). Applications can add their own
    commands to the returned Typer.
    """
    cli = Typer(name=ym_app.name, no_args_is_help=True)

    @cli.command(
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
                "It is layered over any *.ymprint.yml found by searching the source file's parent directories. "
                "If no config file is found, the default config is used."
            )] = None,
        var: Annotated[Optional[list[str]], typer.Option(
            "--var",
            help="Set a variable, NAME=VALUE (repeatable). Renders once with these values, "
                 "ignoring the document's parameter sets.",
        )] = None,
        only: Annotated[Optional[list[str]], typer.Option(
            "--only",
            help="Render only the parameter sets with NAME=VALUE (repeatable).",
        )] = None,
    ):
        """
        Render a YAML source file to PDF.

        Writes the PDF next to the source file (or to DEST if given) and exits.
        A document with a `_render` entry in the project config is rendered as
        it says: once per parameter set, to its `output`. Errors in the
        authored document are reported without a traceback.
        """
        console = Console()
        try:
            variables = parse_assignments(var, "--var")
            selection = parse_assignments(only, "--only")
        except ValueError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=2)

        try:
            if variables:
                # Explicit values: one render, whatever the document's `_render` entry says.
                events = [ym_app.render(src, dest, config_dir, mode="convert", vars=variables)]
                failures, written, notes = [], [], []
            else:
                run = ym_app.render_all(src, config_dir, destination=dest, only=selection, mode="convert")
                events, failures, written, notes = run.results, run.failures, run.written, run.notes
        except RenderUsageError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=2)
        except (YmprintAuthoringError, RenderCallbackError, DestinationLockedError) as exc:
            print_render_error(console, ym_app.name, exc)
            raise typer.Exit(code=1)

        for event in events:
            console.print(
                f"✍️ .... 📝 ... PDF created: {event.destination.resolve()}"
            )
        for path in written:
            console.print(f"📤 Exports written: {path}")
        for note in notes:
            console.print(f"[yellow]{note}[/yellow]")
        for failure in failures:
            print_render_error(console, ym_app.name, failure.error, label=failure.instance.key)
        if failures:
            console.print(
                f"[red]Rendered {len(events)} of {len(events) + len(failures)}. Failed:[/red]\n"
                + "\n".join(f"[red]  ✗ {failure.describe()}[/red]" for failure in failures)
            )
            raise typer.Exit(code=1)
        if not events:
            console.print(f"[red]No parameter set of {src} matches --only {' '.join(only or [])}.[/red]")
            raise typer.Exit(code=1)

    @cli.command(
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
        var: Annotated[Optional[list[str]], typer.Option(
            "--var", help="Set a variable, NAME=VALUE (repeatable).",
        )] = None,
        only: Annotated[Optional[list[str]], typer.Option(
            "--only",
            help="Preview one parameter set of a document rendered per parameter set, NAME=VALUE (repeatable).",
        )] = None,
    ):
        """
        Render SRC to a PDF, open it in Okular, and hot-reload on every save.

        Live mode watches the source file (and its config files) and rebuilds the
        PDF whenever they change. If SRC does not exist, you'll be prompted to
        create a minimal starter document at that path and drop straight into
        live editing. Press Ctrl+C to stop.

        A document rendered per parameter set previews its `_vars` defaults,
        or the set chosen with --only.
        """
        try:
            variables = parse_assignments(var, "--var")
            selection = parse_assignments(only, "--only")
        except ValueError as exc:
            Console().print(f"[red]{exc}[/red]")
            raise typer.Exit(code=2)
        exit_code = run_live(ym_app, src, dest, config_file, vars=variables, only=selection)
        if exit_code:
            raise typer.Exit(code=exit_code)

    return cli


def print_render_error(console: Console, app_name: str, exc: BaseException, label: str = "") -> None:
    """Prints a failed render's error; 'label' names the parameter set, if any."""
    where = f" ({label})" if label else ""
    if isinstance(exc, YmprintAuthoringError):
        # This is a problem in the author's document, not an ymprint crash. Make
        # that explicit and show the actionable, compact error.
        console.print(
            Panel(
                format_authoring_error(exc),
                title=f"[bold red]{app_name} convert{where} — error in your document[/bold red]",
                subtitle="[dim]this is an error in the file you authored, not an ymprint bug[/dim]",
                border_style="red",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )
    elif isinstance(exc, RenderCallbackError):
        console.print(
            Panel(
                format_callback_error(exc),
                title=f"[bold red]{app_name} convert{where} — {exc.stage} hook failed[/bold red]",
                border_style="red",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )
    elif isinstance(exc, DestinationLockedError):
        console.print(
            f"[red]Could not write {exc.path}: it is open in another program "
            f"(e.g. a PDF viewer or sync client). Close it or wait, then try again.[/red]"
        )
    else:
        console.print(Panel(format_render_error(exc), title=f"[bold red]{app_name} convert{where} — render failed[/bold red]", border_style="red"))


def _default_cli() -> Typer:
    from ..app import default_app
    return default_app.cli()


app = _default_cli()
