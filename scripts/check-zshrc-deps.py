#!/usr/bin/env -S uv run --script
import json
import os
import re
import shutil
from typing import Optional

import typer

app = typer.Typer(add_completion=False)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHECKS_FILE = os.path.join(SCRIPT_DIR, "zshrc-deps.json")

KIND_PREDICATE = {
    "command": shutil.which,
    "dir": os.path.isdir,
    "file": os.path.isfile,
}


def find_zshrc_path(arg_path: Optional[str]) -> str:
    if arg_path:
        return arg_path

    cwd_zshrc = os.path.join(os.getcwd(), ".zshrc")
    if os.path.isfile(cwd_zshrc):
        return cwd_zshrc

    home = os.path.expanduser("~")
    home_zshrc = os.path.join(home, ".zshrc")
    if os.path.isfile(home_zshrc):
        return home_zshrc

    typer.echo("error: .zshrc not found. Provide a path or set ZSHRC_PATH.")
    raise typer.Exit(2)


def has_pattern(pattern: str, zshrc_path: str) -> bool:
    try:
        regex = re.compile(pattern)
    except re.error:
        return False

    with open(zshrc_path, "r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if line.lstrip().startswith("#"):
                continue
            if regex.search(line):
                return True
    return False


def load_checks() -> list[dict]:
    with open(CHECKS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    home = os.path.expanduser("~")
    for check in data["checks"]:
        check["target"] = check["target"].replace("$HOME", home)
    return data["checks"]


@app.command()
def main(
    zshrc_path: Optional[str] = typer.Argument(
        None, help="Path to .zshrc (defaults to ./.zshrc or ~/.zshrc)"
    )
) -> None:
    zshrc_path = find_zshrc_path(zshrc_path)
    if not os.path.isfile(zshrc_path):
        typer.echo(f"error: .zshrc not found at: {zshrc_path}")
        raise typer.Exit(2)

    checks = load_checks()
    counts = {"ok": 0, "missing": 0, "skipped": 0}

    def report(status: str, msg: str) -> None:
        typer.echo(f"{status:<8}{msg}")
        key = status.strip().lower()
        if key == "skip":
            counts["skipped"] += 1
        else:
            counts[key] += 1

    typer.echo(f"Checking dependencies from: {zshrc_path}")
    for check in sorted(checks, key=lambda c: c["label"].casefold()):
        label = check["label"]
        pattern = check["pattern"]
        kind = check["kind"]
        target = check["target"]

        if pattern and not has_pattern(pattern, zshrc_path):
            report("SKIP", f"{label} - not referenced in .zshrc")
            continue

        predicate = KIND_PREDICATE.get(kind)
        if predicate is None:
            typer.echo(f"error: unknown check kind: {kind}")
            raise typer.Exit(2)

        msg = f"{label} - {kind}: {target}"
        if predicate(target):
            report("OK", msg)
        else:
            report("MISSING", msg)

    typer.echo("")
    typer.echo(
        "Summary: ok={ok} missing={missing} skipped={skipped}".format(**counts)
    )

    if counts["missing"] > 0:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
