from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

import typer

from .utils import display_path, repo_root


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


def load_link_items() -> list[LinkItem]:
    links_file = repo_root() / "scripts" / "links.json"
    with open(links_file, encoding="utf-8") as f:
        data = json.load(f)
    root = repo_root()
    home = Path.home()
    return [
        LinkItem(
            key=item["key"],
            title=item["key"],
            description=item["description"],
            source=root / item["key"],
            target=home / item["key"],
        )
        for item in data["links"]
    ]


def resolve_items(keys: Iterable[str], use_all: bool) -> list[LinkItem]:
    items = load_link_items()
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
