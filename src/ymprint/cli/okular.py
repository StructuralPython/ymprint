"""Platform-aware detection and installation of the Okular PDF viewer.

Okular is the external viewer that ``ym live`` uses to display the rendered PDF
and hot-reload it as the source changes. The helpers in this module check
whether Okular is available and, when it is not, offer to install it using the
platform-specific instructions published at https://okular.kde.org/download/.
"""
from __future__ import annotations

import platform
import shutil
import subprocess
from dataclasses import dataclass, field

import typer
from rich.console import Console

DOWNLOAD_URL = "https://okular.kde.org/download/"

# Flatpak application id used on Linux (see the download page).
FLATPAK_APP_ID = "org.kde.okular"

# Microsoft Store product id for Okular (see the download page).
WINDOWS_STORE_ID = "9N41MSQ1WNM8"


@dataclass
class Installer:
    """A single platform-specific way to install Okular.

    ``tool`` is the executable that must already be present for the method to be
    usable, and ``command`` is the argument list run to perform the install.
    """

    name: str
    tool: str
    command: list[str] = field(default_factory=list)


def okular_launch_command() -> list[str] | None:
    """Return the command used to launch Okular, or ``None`` if unavailable.

    A native ``okular`` on ``PATH`` is preferred; a Flatpak install is used as a
    fallback (it is launched through ``flatpak run`` rather than a bare binary).
    """
    if shutil.which("okular"):
        return ["okular"]
    if _flatpak_has_okular():
        return ["flatpak", "run", FLATPAK_APP_ID]
    return None


def is_okular_installed() -> bool:
    """Return ``True`` if Okular can be launched on this system."""
    return okular_launch_command() is not None


def _flatpak_has_okular() -> bool:
    """Return ``True`` if Okular is installed as a Flatpak."""
    flatpak = shutil.which("flatpak")
    if not flatpak:
        return False
    try:
        result = subprocess.run(
            [flatpak, "info", FLATPAK_APP_ID],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return False
    return result.returncode == 0


def _linux_installers() -> list[Installer]:
    """Return installation methods available on this Linux system.

    Native distribution packages are preferred (they integrate best with the
    desktop); Flathub is offered as a distribution-agnostic fallback.
    """
    candidates = [
        Installer("apt (Debian/Ubuntu)", "apt", ["sudo", "apt", "install", "-y", "okular"]),
        Installer("dnf (Fedora)", "dnf", ["sudo", "dnf", "install", "-y", "okular"]),
        Installer("pacman (Arch)", "pacman", ["sudo", "pacman", "-S", "--noconfirm", "okular"]),
        Installer("zypper (openSUSE)", "zypper", ["sudo", "zypper", "install", "-y", "okular"]),
        Installer(
            "Flatpak (Flathub)",
            "flatpak",
            ["flatpak", "install", "-y", "flathub", FLATPAK_APP_ID],
        ),
    ]
    return [i for i in candidates if shutil.which(i.tool)]


def _macos_installers() -> list[Installer]:
    """Return installation methods available on macOS."""
    candidates = [
        Installer("Homebrew", "brew", ["brew", "install", "--cask", "okular"]),
    ]
    return [i for i in candidates if shutil.which(i.tool)]


def _windows_installers() -> list[Installer]:
    """Return installation methods available on Windows."""
    candidates = [
        Installer(
            "Microsoft Store (winget)",
            "winget",
            [
                "winget",
                "install",
                "--id",
                WINDOWS_STORE_ID,
                "--source",
                "msstore",
                "--accept-package-agreements",
                "--accept-source-agreements",
            ],
        ),
    ]
    return [i for i in candidates if shutil.which(i.tool)]


def available_installers() -> list[Installer]:
    """Return the installation methods usable on the current platform."""
    system = platform.system()
    if system == "Linux":
        return _linux_installers()
    if system == "Darwin":
        return _macos_installers()
    if system == "Windows":
        return _windows_installers()
    return []


def _print_manual_instructions(console: Console) -> None:
    """Point the user at the official, platform-specific install instructions."""
    console.print(
        "Please install Okular manually. Instructions for every platform are "
        f"available at [underline]{DOWNLOAD_URL}[/underline]."
    )


def run_installer(installer: Installer, console: Console) -> bool:
    """Run ``installer`` and return ``True`` if it completes successfully."""
    console.print(f"[cyan]Installing Okular via {installer.name}…[/cyan]")
    console.print(f"  [dim]{' '.join(installer.command)}[/dim]")
    try:
        result = subprocess.run(installer.command)
    except OSError as exc:
        console.print(f"[red]Could not run the installer: {exc}[/red]")
        return False
    return result.returncode == 0


def ensure_okular(console: Console) -> list[str] | None:
    """Ensure Okular is installed, offering to install it if it is missing.

    Returns the command used to launch Okular, or ``None`` if it is unavailable
    and could not (or should not) be installed.
    """
    launch = okular_launch_command()
    if launch is not None:
        return launch

    console.print(
        "[yellow]Okular does not appear to be installed on this system.[/yellow]"
    )

    installers = available_installers()
    if not installers:
        _print_manual_instructions(console)
        return None

    installer = installers[0]
    console.print(
        f"Okular can be installed with [bold]{installer.name}[/bold]."
    )
    if not typer.confirm("Would you like to install Okular now?", default=True):
        console.print(
            "[dim]Skipping installation — Okular is required for live mode.[/dim]"
        )
        return None

    if not run_installer(installer, console):
        console.print("[red]Okular installation failed.[/red]")
        _print_manual_instructions(console)
        return None

    launch = okular_launch_command()
    if launch is None:
        console.print(
            "[red]Okular still could not be found after installation.[/red]"
        )
        _print_manual_instructions(console)
    return launch
