from __future__ import annotations

import platform
from pathlib import Path

import typer
from rich.console import Console

console = Console()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def display_path(path: Path) -> str:
    home = Path.home()
    try:
        return f"~/{path.relative_to(home)}"
    except ValueError:
        return str(path)


def require_darwin() -> None:
    if platform.system() != "Darwin":
        console.print("[red]ERROR[/red]  This command only works on macOS")
        raise typer.Exit(1)
