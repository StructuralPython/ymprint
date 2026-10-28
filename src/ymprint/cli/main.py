from typing import TYPE_CHECKING, Optional, Annotated
from pathlib import Path
from .error_display import format_authoring_error
from ..config.pdf_postprocessing import DestinationLockedError
from ..errors import YmprintAuthoringError
from ..render import RenderCallbackError
from rich import box
from rich.console import Console
from rich.panel import Panel
import typer
from typer import Typer

from .live import format_callback_error, run_live

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
            )] = None
    ):
        """
        Render a single YAML source file to a PDF, once.

        Writes the PDF next to the source file (or to DEST if given) and exits.
        Errors in the authored document are reported without a traceback.
        """
        console = Console()

        try:
            event = ym_app.render(src, dest, config_dir, mode="convert")
        except YmprintAuthoringError as exc:
            # This is a problem in the author's document, not an ymprint crash. Make
            # that explicit and show the actionable, compact error.
            console.print(
                Panel(
                    format_authoring_error(exc),
                    title=f"[bold red]{ym_app.name} convert — error in your document[/bold red]",
                    subtitle="[dim]this is an error in the file you authored, not an ymprint bug[/dim]",
                    border_style="red",
                    box=box.ROUNDED,
                    padding=(1, 2),
                )
            )
            raise typer.Exit(code=1)
        except RenderCallbackError as exc:
            console.print(
                Panel(
                    format_callback_error(exc),
                    title=f"[bold red]{ym_app.name} convert — {exc.stage} hook failed[/bold red]",
                    border_style="red",
                    box=box.ROUNDED,
                    padding=(1, 2),
                )
            )
            raise typer.Exit(code=1)
        except DestinationLockedError as exc:
            console.print(
                f"[red]Could not write {exc.path}: it is open in another program "
                f"(e.g. a PDF viewer or sync client). Close it or wait, then try again.[/red]"
            )
            raise typer.Exit(code=1)

        console.print(
            f"✍️ .... 📝 ... PDF created: {event.destination.resolve()}"
        )

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
    ):
        """
        Render SRC to a PDF, open it in Okular, and hot-reload on every save.

        Live mode watches the source file (and its config files) and rebuilds the
        PDF whenever they change. If SRC does not exist, you'll be prompted to
        create a minimal starter document at that path and drop straight into
        live editing. Press Ctrl+C to stop.
        """
        exit_code = run_live(ym_app, src, dest, config_file)
        if exit_code:
            raise typer.Exit(code=exit_code)

    return cli


def _default_cli() -> Typer:
    from ..app import default_app
    return default_app.cli()


app = _default_cli()
