#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["typer>=0.21.0"]
# ///
from __future__ import annotations

import json
import math
import os
import platform
import re
import shutil
import subprocess
from collections import defaultdict, deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

import typer
from rich.console import Console

console = Console()

app = typer.Typer(add_completion=False, help="Bootstrap your environment: link dotfiles, check dependencies, and more.")
defaults_app = typer.Typer(help="Manage macOS system defaults.")
app.add_typer(defaults_app, name="defaults")


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


class ReadStatus(str, Enum):
    ok = "ok"
    key_missing = "key_missing"
    domain_missing = "domain_missing"


@dataclass(frozen=True)
class DefaultEntry:
    domain: str
    key: str
    type: str
    value: object
    description: str
    category: str
    restart: str | None = None


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


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


def validate_json_schema(
    json_path: Path,
    schema_path: Path,
    array_key: str,
    *,
    skip_type_check_fields: frozenset[str] = frozenset(),
    extra_item_validator: Callable[[int, dict, dict, list[str]], None] | None = None,
    extra_validator: Callable[[list, list[str]], None] | None = None,
) -> list[str]:
    errors: list[str] = []

    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        return [f"cannot load {json_path.name}: {exc}"]

    try:
        with open(schema_path, encoding="utf-8") as f:
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

    items = data.get(array_key)
    if items is not None:
        if not isinstance(items, list):
            errors.append(f"'{array_key}' must be an array")
        else:
            item_schema = (
                schema.get("properties", {}).get(array_key, {}).get("items", {})
            )
            required_fields = item_schema.get("required", [])
            allowed_fields = set(item_schema.get("properties", {}).keys())
            no_additional = item_schema.get("additionalProperties") is False

            for i, item in enumerate(items):
                if not isinstance(item, dict):
                    errors.append(f"{array_key}[{i}]: must be an object")
                    continue
                for field in required_fields:
                    if field not in item:
                        errors.append(f"{array_key}[{i}]: missing required field: {field}")
                if no_additional:
                    for key in item:
                        if key not in allowed_fields:
                            errors.append(f"{array_key}[{i}]: unexpected field: {key}")
                for field, prop_schema in item_schema.get("properties", {}).items():
                    if field not in item:
                        continue
                    val = item[field]
                    if field not in skip_type_check_fields:
                        if prop_schema.get("type") == "string" and not isinstance(
                            val, str
                        ):
                            errors.append(f"{array_key}[{i}].{field}: must be a string")
                    enum_vals = prop_schema.get("enum")
                    if enum_vals and val not in enum_vals:
                        errors.append(
                            f"{array_key}[{i}].{field}: must be one of {enum_vals}, got '{val}'"
                        )
                if extra_item_validator:
                    extra_item_validator(i, item, item_schema, errors)

            if extra_validator:
                extra_validator(items, errors)

    return errors


def validate_deps_schema() -> list[str]:
    def _item_validator(i: int, item: dict, item_schema: dict, errors: list[str]) -> None:
        depends = item.get("depends")
        if isinstance(depends, list):
            for dep_val in depends:
                if not isinstance(dep_val, str):
                    errors.append(f"checks[{i}].depends: items must be strings")

    def _extra_validator(items: list, errors: list[str]) -> None:
        all_labels = {
            item["label"]
            for item in items
            if isinstance(item, dict) and "label" in item
        }
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            for dep in item.get("depends", []):
                if dep not in all_labels:
                    errors.append(
                        f"checks[{i}].depends: unknown label '{dep}'"
                    )

        in_degree: dict[str, int] = defaultdict(int)
        dependents: dict[str, list[str]] = defaultdict(list)
        for item in items:
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

    return validate_json_schema(
        repo_root() / "scripts" / "deps.json",
        repo_root() / "scripts" / "deps.schema.json",
        "checks",
        extra_item_validator=_item_validator,
        extra_validator=_extra_validator,
    )


def validate_defaults_schema() -> list[str]:
    return validate_json_schema(
        repo_root() / "scripts" / "macos-defaults.json",
        repo_root() / "scripts" / "macos-defaults.schema.json",
        "defaults",
        skip_type_check_fields=frozenset({"value"}),
    )


def validate_links_schema() -> list[str]:
    return validate_json_schema(
        repo_root() / "scripts" / "links.json",
        repo_root() / "scripts" / "links.schema.json",
        "links",
    )


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


def git_config_get(key: str) -> str | None:
    r = subprocess.run(
        ["git", "config", "--global", key],
        capture_output=True, text=True,
    )
    return r.stdout.strip() or None if r.returncode == 0 else None


def verify_gpg_signing() -> tuple[int, int]:
    ok = fail = 0

    gpg_sign = git_config_get("commit.gpgsign")
    if gpg_sign == "true":
        console.print("[green]OK[/green]      commit.gpgsign = true")
        ok += 1
    else:
        console.print(f"[red]FAIL[/red]    commit.gpgsign = {gpg_sign or '(unset)'}")
        fail += 1

    signing_key = git_config_get("user.signingkey")
    if signing_key:
        r = subprocess.run(
            ["gpg", "--list-secret-keys", "--keyid-format", "long", signing_key],
            capture_output=True, text=True,
        )
        if r.returncode == 0 and signing_key in r.stdout:
            console.print(f"[green]OK[/green]      signing key {signing_key[:16]}...")
            ok += 1
        else:
            console.print(f"[red]FAIL[/red]    signing key {signing_key} not found in GPG keyring")
            fail += 1
    else:
        console.print("[red]FAIL[/red]    user.signingkey not set")
        fail += 1

    agent_conf = Path.home() / ".gnupg" / "gpg-agent.conf"
    if agent_conf.is_file() and "pinentry-mac" in agent_conf.read_text():
        pinentry = shutil.which("pinentry-mac")
        if pinentry:
            console.print(f"[green]OK[/green]      pinentry-mac ({pinentry})")
            ok += 1
        else:
            console.print("[red]FAIL[/red]    pinentry-mac configured but binary not found")
            fail += 1
    else:
        console.print("[red]FAIL[/red]    pinentry-mac not configured in gpg-agent.conf")
        fail += 1

    return ok, fail


def require_darwin() -> None:
    if platform.system() != "Darwin":
        console.print("[red]ERROR[/red]  This command only works on macOS")
        raise typer.Exit(1)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand:
        return
    print(ctx.get_help())


@app.command("list")
def list_items() -> None:
    """List available link targets and current status."""
    print_status(load_link_items())


@app.command()
def status() -> None:
    """Alias for list."""
    print_status(load_link_items())


@app.command()
def verify() -> None:
    """Run all verification checks on your environment."""
    ok = fail = 0

    # 1. Symlink health
    console.rule("[bold]Symlink health[/bold]", align="left")
    for item in load_link_items():
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
            hints: list[str] = []
            if label in required_by:
                deps = ", ".join(sorted(required_by[label]))
                hints.append(f"required by: {deps}")
            install_url = check.get("install")
            if install_url:
                hints.append(f"install: {install_url}")
            hint = f" ({', '.join(hints)})" if hints else ""
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

    defaults_schema_errors = validate_defaults_schema()
    if defaults_schema_errors:
        for err in defaults_schema_errors:
            console.print(f"[red]FAIL[/red]    {err}")
            fail += 1
    else:
        console.print("[green]OK[/green]      scripts/macos-defaults.json")
        ok += 1

    links_schema_errors = validate_links_schema()
    if links_schema_errors:
        for err in links_schema_errors:
            console.print(f"[red]FAIL[/red]    {err}")
            fail += 1
    else:
        console.print("[green]OK[/green]      scripts/links.json")
        ok += 1
    console.print()

    # 4. JSON formatting
    console.rule("[bold]JSON formatting[/bold]", align="left")
    for json_name in ("deps.json", "macos-defaults.json", "links.json"):
        json_file = repo_root() / "scripts" / json_name
        if check_json_formatting(json_file):
            console.print(f"[green]OK[/green]      scripts/{json_name}")
            ok += 1
        else:
            console.print(
                f"[red]FAIL[/red]    scripts/{json_name} not formatted"
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

    # 6. GPG signing
    console.rule("[bold]GPG signing[/bold]", align="left")
    gpg_ok, gpg_fail = verify_gpg_signing()
    ok += gpg_ok
    fail += gpg_fail
    console.print()

    # 7. Pre-commit hooks
    console.rule("[bold]Pre-commit hooks[/bold]", align="left")
    hook_file = repo_root() / ".git" / "hooks" / "pre-commit"
    if hook_file.is_file() and "pre-commit" in hook_file.read_text():
        console.print("[green]OK[/green]      git hooks installed")
        ok += 1
    else:
        console.print("[red]FAIL[/red]    git hooks not installed (run: pre-commit install)")
        fail += 1
    console.print()

    # 8. macOS defaults
    if platform.system() == "Darwin":
        console.rule("[bold]macOS defaults[/bold]", align="left")
        entries = load_defaults_entries()
        for entry in entries:
            st, raw = read_default(entry.domain, entry.key)
            if st != ReadStatus.ok or raw is None:
                console.print(
                    f"[red]DRIFT[/red]   {entry.key} - {st.value}"
                    f" (expected {entry.value!r})"
                )
                fail += 1
                continue
            current = parse_default_value(raw, entry.type)
            if values_equal(current, entry.value, entry.type):
                console.print(f"[green]OK[/green]      {entry.key} = {current!r}")
                ok += 1
            else:
                console.print(
                    f"[red]DRIFT[/red]   {entry.key}:"
                    f" saved={entry.value!r} current={current!r}"
                )
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


# ── macOS defaults helpers ──────────────────────────────────────────────


def load_defaults_entries() -> list[DefaultEntry]:
    defaults_file = repo_root() / "scripts" / "macos-defaults.json"
    with open(defaults_file, encoding="utf-8") as f:
        data = json.load(f)
    return [
        DefaultEntry(
            domain=item["domain"],
            key=item["key"],
            type=item["type"],
            value=item["value"],
            description=item["description"],
            category=item["category"],
            restart=item.get("restart"),
        )
        for item in data["defaults"]
    ]


def run_defaults_cmd(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["defaults", *args],
        capture_output=True, text=True,
    )


def read_default(domain: str, key: str) -> tuple[ReadStatus, str | None]:
    r = run_defaults_cmd("read", domain, key)
    if r.returncode != 0:
        stderr = r.stderr.strip()
        if "does not exist" in stderr:
            if "domain" in stderr.split("does not exist")[0].lower():
                return ReadStatus.domain_missing, None
            return ReadStatus.key_missing, None
        return ReadStatus.key_missing, None
    return ReadStatus.ok, r.stdout.strip()


def parse_default_value(raw: str, type_: str) -> object:
    if type_ == "bool":
        return raw.strip() in {"1", "true", "YES"}
    if type_ == "int":
        return int(raw.strip())
    if type_ == "float":
        return float(raw.strip())
    return raw.strip()


def format_write_value(value: object, type_: str) -> list[str]:
    if type_ == "bool":
        return ["-bool", "TRUE" if value else "FALSE"]
    if type_ == "int":
        return ["-int", str(value)]
    if type_ == "float":
        return ["-float", str(value)]
    return ["-string", str(value)]


def values_equal(a: object, b: object, type_: str) -> bool:
    if type_ == "bool":
        return bool(a) == bool(b)
    if type_ == "float":
        try:
            return math.isclose(float(a), float(b), rel_tol=1e-9)
        except (TypeError, ValueError):
            return False
    return a == b


# ── defaults commands ───────────────────────────────────────────────────


@defaults_app.command("export")
def defaults_export() -> None:
    """Read current system values and update macos-defaults.json."""
    require_darwin()

    defaults_file = repo_root() / "scripts" / "macos-defaults.json"
    with open(defaults_file, encoding="utf-8") as f:
        data = json.load(f)

    updated = 0
    for item in data["defaults"]:
        st, raw = read_default(item["domain"], item["key"])
        if st != ReadStatus.ok or raw is None:
            console.print(f"[yellow]SKIP[/yellow]    {item['domain']} {item['key']} - {st.value}")
            continue
        current = parse_default_value(raw, item["type"])
        if not values_equal(current, item["value"], item["type"]):
            console.print(
                f"[cyan]UPDATE[/cyan]  {item['key']}: {item['value']!r} -> {current!r}"
            )
            item["value"] = current
            updated += 1

    if updated:
        with open(defaults_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        console.print(f"\n[green]Updated {updated} value(s)[/green]")
    else:
        console.print("[green]No updates needed[/green]")


@defaults_app.command("apply")
def defaults_apply(
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes without applying."),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmations."),
) -> None:
    """Apply saved defaults values to the system."""
    require_darwin()

    entries = load_defaults_entries()
    changes: list[DefaultEntry] = []

    for entry in entries:
        st, raw = read_default(entry.domain, entry.key)
        if st == ReadStatus.ok and raw is not None:
            current = parse_default_value(raw, entry.type)
            if values_equal(current, entry.value, entry.type):
                continue
        changes.append(entry)

    if not changes:
        console.print("[green]All defaults already match[/green]")
        return

    for entry in changes:
        console.print(f"  defaults write {entry.domain} {entry.key} {' '.join(format_write_value(entry.value, entry.type))}")

    if dry_run:
        console.print(f"\n[cyan]{len(changes)} change(s) would be applied[/cyan]")
        return

    if not yes:
        if not typer.confirm(f"\nApply {len(changes)} change(s)?", default=False):
            console.print("Aborted.")
            return

    restart_apps: set[str] = set()
    for entry in changes:
        args = ["write", entry.domain, entry.key, *format_write_value(entry.value, entry.type)]
        r = run_defaults_cmd(*args)
        if r.returncode != 0:
            console.print(f"[red]FAIL[/red]    {entry.domain} {entry.key}: {r.stderr.strip()}")
        else:
            console.print(f"[green]OK[/green]      {entry.domain} {entry.key}")
            if entry.restart:
                restart_apps.add(entry.restart)

    for app_name in sorted(restart_apps):
        console.print(f"[cyan]Restarting {app_name}...[/cyan]")
        subprocess.run(["killall", app_name], capture_output=True)


@defaults_app.command("diff")
def defaults_diff() -> None:
    """Show differences between saved and current system values."""
    require_darwin()

    entries = load_defaults_entries()
    by_category: dict[str, list[DefaultEntry]] = defaultdict(list)
    for entry in entries:
        by_category[entry.category].append(entry)

    has_diff = False
    for category in sorted(by_category):
        items = by_category[category]
        for entry in items:
            st, raw = read_default(entry.domain, entry.key)
            if st != ReadStatus.ok or raw is None:
                console.print(f"[yellow]MISSING[/yellow] [{category}] {entry.key} - expected {entry.value!r} ({st.value})")
                has_diff = True
                continue
            current = parse_default_value(raw, entry.type)
            if values_equal(current, entry.value, entry.type):
                console.print(f"[green]OK[/green]      [{category}] {entry.key} = {current!r}")
            else:
                console.print(f"[red]DIFF[/red]    [{category}] {entry.key}: saved={entry.value!r} current={current!r}")
                has_diff = True

    if has_diff:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
