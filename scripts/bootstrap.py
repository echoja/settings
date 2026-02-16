#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["typer>=0.21.0"]
# ///
from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from collections import defaultdict, deque
from typing import Iterable

import typer
from rich.console import Console

console = Console()

app = typer.Typer(add_completion=False, help="Bootstrap your environment: link dotfiles, check dependencies, and more.")


class ReplaceMode(str, Enum):
    safe = "safe"
    backup = "backup"
    force = "force"


@dataclass(frozen=True)
class LinkItem:
    key: str
    title: str
    description: str
    source: Path
    target: Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def available_items() -> list[LinkItem]:
    root = repo_root()
    home = Path.home()
    return [
        LinkItem(
            key=".zshrc",
            title=".zshrc",
            description="Zsh config",
            source=root / ".zshrc",
            target=home / ".zshrc",
        ),
        LinkItem(
            key=".codex/config.toml",
            title=".codex/config.toml",
            description="Codex CLI config",
            source=root / ".codex" / "config.toml",
            target=home / ".codex" / "config.toml",
        ),
        LinkItem(
            key=".claude/settings.json",
            title=".claude/settings.json",
            description="Claude Code settings",
            source=root / ".claude" / "settings.json",
            target=home / ".claude" / "settings.json",
        ),
        LinkItem(
            key=".claude/notify.sh",
            title=".claude/notify.sh",
            description="Claude Code stop-hook notification script",
            source=root / ".claude" / "notify.sh",
            target=home / ".claude" / "notify.sh",
        ),
        LinkItem(
            key=".claude/CLAUDE.md",
            title=".claude/CLAUDE.md",
            description="User-scope Claude Code instructions",
            source=root / ".claude" / "CLAUDE.md",
            target=home / ".claude" / "CLAUDE.md",
        ),
    ]


def resolve_items(keys: Iterable[str], use_all: bool) -> list[LinkItem]:
    items = available_items()
    if use_all:
        return items

    lookup = {item.key: item for item in items}
    chosen: list[LinkItem] = []
    unknown: list[str] = []

    for raw in keys:
        key = raw.strip()
        if key in lookup:
            item = lookup[key]
        else:
            unknown.append(raw)
            continue
        if item not in chosen:
            chosen.append(item)

    if unknown:
        raise typer.BadParameter(
            f"Unknown target(s): {', '.join(unknown)}. Use 'list' to see options."
        )

    return chosen


def display_path(path: Path) -> str:
    home = Path.home()
    try:
        return f"~/{path.relative_to(home)}"
    except ValueError:
        return str(path)


def is_source_present(item: LinkItem) -> bool:
    return item.source.exists() or item.source.is_symlink()


def link_target_summary(item: LinkItem) -> str:
    return f"{display_path(item.source)} -> {display_path(item.target)}"


def status_of(item: LinkItem) -> tuple[str, str]:
    if not is_source_present(item):
        return "missing-source", "source missing"

    target = item.target
    if target.is_symlink():
        target_resolved = target.resolve(strict=False)
        source_resolved = item.source.resolve(strict=False)
        if target_resolved == source_resolved:
            return "linked", f"points to {display_path(target_resolved)}"
        if not target.exists():
            return "broken-link", f"points to {display_path(target_resolved)}"
        return "linked-elsewhere", f"points to {display_path(target_resolved)}"

    if target.exists():
        if target.is_dir():
            return "target-dir", "target is a directory"
        return "exists", "target exists"

    return "absent", "target missing"


def status_label(status: str) -> str:
    labels = {
        "linked": "LINKED",
        "absent": "ABSENT",
        "exists": "EXISTS",
        "missing-source": "MISSING",
        "linked-elsewhere": "OTHER",
        "broken-link": "BROKEN",
        "target-dir": "DIR",
    }
    return labels.get(status, status.upper())


def print_status(items: Iterable[LinkItem]) -> None:
    for item in items:
        status, detail = status_of(item)
        label = status_label(status)
        detail_text = f" ({detail})" if detail else ""
        typer.echo(f"{label:<7} {item.key:<22} {link_target_summary(item)}{detail_text}")


def ensure_parent_dir(path: Path, dry_run: bool) -> None:
    parent = path.parent
    if parent.exists():
        return
    if dry_run:
        typer.echo(f"DRYRUN  mkdir -p {display_path(parent)}")
        return
    parent.mkdir(parents=True, exist_ok=True)


def backup_path_for(target: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return target.with_name(f"{target.name}.bak.{timestamp}")


def remove_target(target: Path, mode: ReplaceMode, dry_run: bool) -> Path | None:
    if not (target.exists() or target.is_symlink()):
        return None

    if target.exists() and target.is_dir() and not target.is_symlink():
        raise typer.Exit(2)

    if mode == ReplaceMode.safe:
        return None

    if mode == ReplaceMode.backup:
        backup = backup_path_for(target)
        if dry_run:
            typer.echo(
                f"DRYRUN  mv {display_path(target)} {display_path(backup)}"
            )
            return backup
        target.rename(backup)
        return backup

    if dry_run:
        typer.echo(f"DRYRUN  rm {display_path(target)}")
        return None

    target.unlink()
    return None


def create_link(item: LinkItem, dry_run: bool) -> None:
    ensure_parent_dir(item.target, dry_run=dry_run)
    if dry_run:
        typer.echo(
            f"DRYRUN  ln -s {display_path(item.source)} {display_path(item.target)}"
        )
        return
    item.target.symlink_to(item.source)


def link_items(
    items: Iterable[LinkItem],
    mode: ReplaceMode,
    dry_run: bool,
) -> None:
    had_errors = False
    for item in items:
        status, detail = status_of(item)
        if status == "missing-source":
            typer.echo(
                f"ERROR   {item.key:<22} source missing: {display_path(item.source)}"
            )
            had_errors = True
            continue
        if status == "linked":
            typer.echo(f"SKIP    {item.key:<22} already linked")
            continue
        if status == "target-dir":
            typer.echo(
                f"ERROR   {item.key:<22} target is a directory: {display_path(item.target)}"
            )
            had_errors = True
            continue

        backup = None
        if item.target.exists() or item.target.is_symlink():
            if mode == ReplaceMode.safe:
                typer.echo(
                    f"SKIP    {item.key:<22} target exists (use --mode backup/force)"
                )
                continue
            backup = remove_target(item.target, mode=mode, dry_run=dry_run)

        if backup and not dry_run:
            typer.echo(f"BACKUP  {item.key:<22} {display_path(backup)}")

        create_link(item, dry_run=dry_run)
        action = "DRYRUN" if dry_run else "LINKED"
        typer.echo(f"{action:<7} {item.key:<22} {link_target_summary(item)}")

    if had_errors:
        raise typer.Exit(2)


def confirm_mode(mode: ReplaceMode, dry_run: bool, yes: bool) -> bool:
    if dry_run or yes or mode == ReplaceMode.safe:
        return True
    return typer.confirm(
        f"Mode '{mode.value}' will modify existing targets. Continue?",
        default=False,
    )


def select_items_interactively(items: list[LinkItem]) -> list[LinkItem]:
    typer.echo("Link wizard")
    typer.echo("Available targets:")
    for idx, item in enumerate(items, start=1):
        status, detail = status_of(item)
        label = status_label(status)
        detail_text = f" ({detail})" if detail else ""
        typer.echo(
            f"{idx:>2}) {label:<7} {item.key:<22} {link_target_summary(item)}{detail_text}"
        )

    prompt = "Select items [1,2/all/none]"
    while True:
        selection = typer.prompt(prompt, default="all")
        cleaned = selection.strip().lower()
        if cleaned in {"all", "a"}:
            return items
        if cleaned in {"none", "n"}:
            return []

        tokens = [token for token in cleaned.replace(",", " ").split() if token]
        chosen: list[LinkItem] = []
        for token in tokens:
            if not token.isdigit():
                continue
            idx = int(token)
            if 1 <= idx <= len(items):
                item = items[idx - 1]
                if item not in chosen:
                    chosen.append(item)
        if chosen:
            return chosen
        typer.echo("Invalid selection. Try again.")


def select_mode_interactively(default: ReplaceMode) -> ReplaceMode:
    choices = {mode.value for mode in ReplaceMode}
    prompt = "Mode [safe/backup/force]"
    while True:
        selection = typer.prompt(prompt, default=default.value).strip().lower()
        if selection in choices:
            return ReplaceMode(selection)
        typer.echo("Invalid mode. Try again.")


def run_wizard() -> None:
    items = available_items()
    chosen = select_items_interactively(items)
    if not chosen:
        typer.echo("Nothing selected.")
        return

    needs_replace = any(
        status_of(item)[0]
        in {"exists", "linked-elsewhere", "broken-link", "target-dir"}
        for item in chosen
    )
    default_mode = ReplaceMode.backup if needs_replace else ReplaceMode.safe
    mode = select_mode_interactively(default_mode)
    dry_run = typer.confirm("Dry run only?", default=False)

    typer.echo("Plan:")
    for item in chosen:
        typer.echo(f"- {item.key}: {link_target_summary(item)}")

    if not typer.confirm("Proceed?", default=True):
        typer.echo("Aborted.")
        return

    link_items(chosen, mode=mode, dry_run=dry_run)


KIND_PREDICATE: dict[str, object] = {
    "command": shutil.which,
    "dir": os.path.isdir,
    "file": os.path.isfile,
}


def load_dep_checks() -> list[dict]:
    checks_file = repo_root() / "scripts" / "deps.json"
    with open(checks_file, encoding="utf-8") as f:
        data = json.load(f)
    home = str(Path.home())
    for check in data["checks"]:
        check["target"] = check["target"].replace("$HOME", home)
    return data["checks"]


def validate_deps_schema() -> list[str]:
    checks_file = repo_root() / "scripts" / "deps.json"
    schema_file = repo_root() / "scripts" / "deps.schema.json"
    errors: list[str] = []

    try:
        with open(checks_file, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        return [f"cannot load deps.json: {exc}"]

    try:
        with open(schema_file, encoding="utf-8") as f:
            schema = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        return [f"cannot load schema: {exc}"]

    if not isinstance(data, dict):
        return ["root must be an object"]

    for key in schema.get("required", []):
        if key not in data:
            errors.append(f"missing required key: {key}")

    allowed_keys = set(schema.get("properties", {}).keys())
    if schema.get("additionalProperties") is False:
        for key in data:
            if key not in allowed_keys:
                errors.append(f"unexpected key: {key}")

    checks = data.get("checks")
    if checks is not None:
        if not isinstance(checks, list):
            errors.append("'checks' must be an array")
        else:
            item_schema = (
                schema.get("properties", {}).get("checks", {}).get("items", {})
            )
            required_fields = item_schema.get("required", [])
            allowed_fields = set(item_schema.get("properties", {}).keys())
            no_additional = item_schema.get("additionalProperties") is False
            kind_enum = (
                item_schema.get("properties", {}).get("kind", {}).get("enum")
            )

            for i, item in enumerate(checks):
                if not isinstance(item, dict):
                    errors.append(f"checks[{i}]: must be an object")
                    continue
                for field in required_fields:
                    if field not in item:
                        errors.append(f"checks[{i}]: missing required field: {field}")
                if no_additional:
                    for key in item:
                        if key not in allowed_fields:
                            errors.append(f"checks[{i}]: unexpected field: {key}")
                for field, prop_schema in item_schema.get("properties", {}).items():
                    if field not in item:
                        continue
                    val = item[field]
                    if prop_schema.get("type") == "string" and not isinstance(
                        val, str
                    ):
                        errors.append(f"checks[{i}].{field}: must be a string")
                    if (
                        field == "kind"
                        and kind_enum
                        and val not in kind_enum
                    ):
                        errors.append(
                            f"checks[{i}].kind: must be one of {kind_enum}, got '{val}'"
                        )
                    if field == "depends" and isinstance(val, list):
                        for dep_val in val:
                            if not isinstance(dep_val, str):
                                errors.append(
                                    f"checks[{i}].depends: items must be strings"
                                )

            # Label reference check: every depends entry must match an existing label
            all_labels = {
                item["label"]
                for item in checks
                if isinstance(item, dict) and "label" in item
            }
            for i, item in enumerate(checks):
                if not isinstance(item, dict):
                    continue
                for dep in item.get("depends", []):
                    if dep not in all_labels:
                        errors.append(
                            f"checks[{i}].depends: unknown label '{dep}'"
                        )

            # Cycle detection via topological sort (Kahn's algorithm)
            in_degree: dict[str, int] = defaultdict(int)
            dependents: dict[str, list[str]] = defaultdict(list)
            for item in checks:
                if not isinstance(item, dict) or "label" not in item:
                    continue
                label = item["label"]
                in_degree.setdefault(label, 0)
                for dep in item.get("depends", []):
                    if dep in all_labels:
                        dependents[dep].append(label)
                        in_degree[label] += 1

            queue: deque[str] = deque(
                label for label, deg in in_degree.items() if deg == 0
            )
            visited = 0
            while queue:
                node = queue.popleft()
                visited += 1
                for child in dependents[node]:
                    in_degree[child] -= 1
                    if in_degree[child] == 0:
                        queue.append(child)

            if visited < len(in_degree):
                cycle_members = sorted(
                    label for label, deg in in_degree.items() if deg > 0
                )
                errors.append(
                    f"dependency cycle detected among: {', '.join(cycle_members)}"
                )

    return errors


def check_json_formatting(file_path: Path) -> bool:
    with open(file_path, encoding="utf-8") as f:
        raw = f.read()
    data = json.loads(raw)
    expected = json.dumps(data, indent=2) + "\n"
    return raw == expected


def check_hardcoded_paths(file_path: Path) -> list[tuple[int, str]]:
    regex = re.compile(r"/(Users|home)/[^\s/]+")
    violations: list[tuple[int, str]] = []
    with open(file_path, encoding="utf-8", errors="ignore") as f:
        for lineno, line in enumerate(f, start=1):
            if regex.search(line):
                violations.append((lineno, line.rstrip()))
    return violations


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand:
        return
    print(ctx.get_help())


@app.command("list")
def list_items() -> None:
    """List available link targets and current status."""
    print_status(available_items())


@app.command()
def status() -> None:
    """Alias for list."""
    print_status(available_items())


@app.command()
def verify() -> None:
    """Run all verification checks on your environment."""
    ok = fail = 0

    # 1. Symlink health
    console.rule("[bold]Symlink health[/bold]", align="left")
    for item in available_items():
        st, detail = status_of(item)
        if st == "linked":
            console.print(f"[green]OK[/green]      {item.key}")
            ok += 1
        else:
            label = status_label(st)
            console.print(f"[red]FAIL[/red]    {item.key} - {label}: {detail}")
            fail += 1
    console.print()

    # 2. Dependencies
    console.rule("[bold]Dependencies[/bold]", align="left")
    checks = load_dep_checks()

    # Build reverse dependency map: label -> list of labels that depend on it
    required_by: dict[str, list[str]] = defaultdict(list)
    for check in checks:
        for dep in check.get("depends", []):
            required_by[dep].append(check["label"])

    for check in sorted(checks, key=lambda c: c["label"].casefold()):
        label = check["label"]
        kind = check["kind"]
        target = check["target"]

        predicate = KIND_PREDICATE.get(kind)
        if predicate and predicate(target):
            console.print(f"[green]OK[/green]      {label} - {kind}: {target}")
            ok += 1
        else:
            hint = ""
            if label in required_by:
                deps = ", ".join(sorted(required_by[label]))
                hint = f" (required by: {deps})"
            console.print(f"[red]MISSING[/red] {label} - {kind}: {target}{hint}")
            fail += 1
    console.print()

    # 3. JSON schema validation
    console.rule("[bold]JSON schema validation[/bold]", align="left")
    schema_errors = validate_deps_schema()
    if schema_errors:
        for err in schema_errors:
            console.print(f"[red]FAIL[/red]    {err}")
            fail += 1
    else:
        console.print("[green]OK[/green]      scripts/deps.json")
        ok += 1
    console.print()

    # 4. JSON formatting
    console.rule("[bold]JSON formatting[/bold]", align="left")
    deps_file = repo_root() / "scripts" / "deps.json"
    if check_json_formatting(deps_file):
        console.print("[green]OK[/green]      scripts/deps.json")
        ok += 1
    else:
        console.print(
            "[red]FAIL[/red]    scripts/deps.json not formatted"
            " (run: python3 -m json.tool --indent 2)"
        )
        fail += 1
    console.print()

    # 5. Hardcoded home paths
    console.rule("[bold]Hardcoded home paths[/bold]", align="left")
    violations = check_hardcoded_paths(repo_root() / ".zshrc")
    if violations:
        for lineno, line in violations:
            console.print(f"[red]FAIL[/red]    .zshrc:{lineno}: {line}")
            fail += 1
    else:
        console.print("[green]OK[/green]      No hardcoded paths found")
        ok += 1
    console.print()

    # 6. Pre-commit
    console.rule("[bold]Pre-commit[/bold]", align="left")
    if shutil.which("pre-commit"):
        console.print("[green]OK[/green]      pre-commit installed")
        ok += 1
    else:
        console.print("[red]MISSING[/red] pre-commit not found")
        fail += 1
    console.print()

    # Summary
    summary = f"[green]{ok} ok[/green]"
    if fail:
        summary += f", [red]{fail} fail[/red]"
    else:
        summary += f", {fail} fail"
    console.rule(f"[bold]Summary: {summary}[/bold]", align="left")
    if fail > 0:
        raise typer.Exit(1)


@app.command()
def link(
    targets: list[str] = typer.Argument(
        None,
        help="Target keys (use 'list' to see options).",
        show_default=False,
    ),
    all_targets: bool = typer.Option(
        False, "--all", help="Link all available targets."
    ),
    mode: ReplaceMode = typer.Option(
        ReplaceMode.safe,
        "--mode",
        help="How to handle existing targets (safe/backup/force).",
    ),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmations."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview actions."),
) -> None:
    """Link selected targets."""
    if not targets and not all_targets:
        typer.echo("No targets specified. Use --all or run the wizard.")
        raise typer.Exit(2)

    items = resolve_items(targets or [], use_all=all_targets)
    if not confirm_mode(mode, dry_run=dry_run, yes=yes):
        typer.echo("Aborted.")
        raise typer.Exit(1)

    link_items(items, mode=mode, dry_run=dry_run)


if __name__ == "__main__":
    app()
