from __future__ import annotations

import json
import platform
import socket
import subprocess
from collections import defaultdict

import typer

from .defaults import (
    DefaultEntry,
    ReadStatus,
    format_write_value,
    load_defaults_entries,
    parse_default_value,
    read_default,
    run_defaults_cmd,
    values_equal,
)
from .deps import KIND_PREDICATE, load_dep_checks
from .git import verify_gpg_signing, verify_ssh_keys
from .symlinks import (
    ReplaceMode,
    confirm_mode,
    link_items,
    load_link_items,
    print_status,
    resolve_items,
    status_label,
    status_of,
)
from .launchd import (
    _plist_path,
    bootstrap_job,
    bootout_job,
    is_job_loaded,
    is_plist_current,
    is_script_executable,
    is_script_present,
    load_job_entries,
    write_plist,
)
from .utils import console, display_path, repo_root, require_darwin
from .validation import (
    check_hardcoded_paths,
    check_json_formatting,
    validate_defaults_schema,
    validate_deps_schema,
    validate_jobs_schema,
    validate_links_schema,
)

app = typer.Typer(add_completion=False, help="Bootstrap your environment: link dotfiles, check dependencies, and more.")
defaults_app = typer.Typer(help="Manage macOS system defaults.")
app.add_typer(defaults_app, name="defaults")
jobs_app = typer.Typer(help="Manage launchd jobs.")
app.add_typer(jobs_app, name="jobs")


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
    console.rule("[bold]Symlink health[/bold]", align="left", style="dim")
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
    console.rule("[bold]Dependencies[/bold]", align="left", style="dim")
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
    console.rule("[bold]JSON schema validation[/bold]", align="left", style="dim")
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

    jobs_schema_errors = validate_jobs_schema()
    if jobs_schema_errors:
        for err in jobs_schema_errors:
            console.print(f"[red]FAIL[/red]    {err}")
            fail += 1
    else:
        console.print("[green]OK[/green]      scripts/jobs.json")
        ok += 1
    console.print()

    # 4. JSON formatting
    console.rule("[bold]JSON formatting[/bold]", align="left", style="dim")
    for json_name in ("deps.json", "macos-defaults.json", "links.json", "jobs.json"):
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
    console.rule("[bold]Hardcoded home paths[/bold]", align="left", style="dim")
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
    console.rule("[bold]GPG signing[/bold]", align="left", style="dim")
    gpg_ok, gpg_fail = verify_gpg_signing()
    ok += gpg_ok
    fail += gpg_fail
    console.print()

    # 7. SSH keys
    console.rule("[bold]SSH keys[/bold]", align="left", style="dim")
    ssh_ok, ssh_fail = verify_ssh_keys()
    ok += ssh_ok
    fail += ssh_fail
    console.print()

    # 8. Keychain hygiene
    console.rule("[bold]Keychain hygiene[/bold]", align="left", style="dim")
    r = subprocess.run(
        ["security", "find-generic-password", "-s", "bw-master", "-a", "bitwarden"],
        capture_output=True, text=True,
    )
    if r.returncode == 0:
        console.print("[green]OK[/green]      Bitwarden master password in Keychain")
        ok += 1
    else:
        console.print("[red]FAIL[/red]    Bitwarden master password not in Keychain")
        fail += 1
    console.print()

    # 9. Pre-commit hooks
    console.rule("[bold]Pre-commit hooks[/bold]", align="left", style="dim")
    hook_file = repo_root() / ".git" / "hooks" / "pre-commit"
    if hook_file.is_file() and "pre-commit" in hook_file.read_text():
        console.print("[green]OK[/green]      git hooks installed")
        ok += 1
    else:
        console.print("[red]FAIL[/red]    git hooks not installed (run: pre-commit install)")
        fail += 1
    console.print()

    # 10. Pyright type-checking
    console.rule("[bold]Pyright type-checking[/bold]", align="left", style="dim")
    pyright_result = subprocess.run(
        ["uv", "run", "--frozen", "pyright"],
        capture_output=True, text=True, cwd=repo_root(),
    )
    if pyright_result.returncode == 0:
        console.print("[green]OK[/green]      pyright")
        ok += 1
    else:
        console.print("[red]FAIL[/red]    pyright")
        output = (pyright_result.stdout + pyright_result.stderr).strip()
        if output:
            console.print(output)
        fail += 1
    console.print()

    # 11. macOS defaults
    if platform.system() == "Darwin":
        console.rule("[bold]macOS defaults[/bold]", align="left", style="dim")
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

    # 12. Remote access
    if platform.system() == "Darwin":
        console.rule("[bold]Remote access[/bold]", align="left", style="dim")
        remote_checks: list[tuple[str, int, str]] = [
            ("Remote Login (SSH)", 22, "sudo systemsetup -f -setremotelogin on"),
            ("Screen Sharing", 5900, "sudo launchctl load -w /System/Library/LaunchDaemons/com.apple.screensharing.plist"),
        ]
        for label, port, hint in remote_checks:
            try:
                with socket.create_connection(("localhost", port), timeout=1.0):
                    console.print(f"[green]OK[/green]      {label} (port {port})")
                    ok += 1
            except (OSError, TimeoutError):
                console.print(
                    f"[red]FAIL[/red]    {label} not enabled"
                    f" (enable: {hint})"
                )
                fail += 1

        # Tailscale
        ts = subprocess.run(
            ["/Applications/Tailscale.app/Contents/MacOS/Tailscale", "status"],
            capture_output=True, text=True,
        )
        if ts.returncode == 0:
            console.print("[green]OK[/green]      Tailscale connected")
            ok += 1
        else:
            console.print("[red]FAIL[/red]    Tailscale not running (open Tailscale app)")
            fail += 1
        console.print()

    # 13. Launchd jobs
    if platform.system() == "Darwin":
        console.rule("[bold]Launchd jobs[/bold]", align="left", style="dim")
        for entry in load_job_entries():
            if not is_script_present(entry):
                console.print(f"[red]FAIL[/red]    {entry.label} - script missing: {entry.script}")
                fail += 1
                continue
            if not is_script_executable(entry):
                console.print(f"[red]FAIL[/red]    {entry.label} - script not executable: {entry.script}")
                fail += 1
                continue
            if not is_plist_current(entry):
                console.print(
                    f"[red]FAIL[/red]    {entry.label} - plist missing or outdated"
                    " (run: ./scripts/bootstrap.py jobs apply -y)"
                )
                fail += 1
                continue
            if not is_job_loaded(entry.label):
                console.print(
                    f"[red]FAIL[/red]    {entry.label} - not loaded"
                    " (run: ./scripts/bootstrap.py jobs apply -y)"
                )
                fail += 1
                continue
            console.print(f"[green]OK[/green]      {entry.label}")
            ok += 1
        console.print()

    # Summary
    summary = f"[green]{ok} ok[/green]"
    if fail:
        summary += f", [red]{fail} fail[/red]"
    else:
        summary += f", {fail} fail"
    console.rule(f"[bold]Summary: {summary}[/bold]", align="left", style="dim")
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


# ── jobs commands ──────────────────────────────────────────────────────


@jobs_app.command("apply")
def jobs_apply(
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmations."),
) -> None:
    """Generate plist files and load launchd jobs."""
    require_darwin()

    entries = load_job_entries()
    actions: list[str] = []
    for entry in entries:
        if not is_script_present(entry):
            console.print(f"[red]FAIL[/red]    {entry.label} - script missing: {entry.script}")
            raise typer.Exit(1)
        needs_plist = not is_plist_current(entry)
        needs_load = not is_job_loaded(entry.label)
        if needs_plist or needs_load:
            parts = []
            if needs_plist:
                parts.append("write plist")
            if needs_load:
                parts.append("load")
            actions.append(f"  {entry.label}: {', '.join(parts)}")

    if not actions:
        console.print("[green]All jobs already applied[/green]")
        return

    for line in actions:
        console.print(line)

    if not yes:
        if not typer.confirm(f"\nApply {len(actions)} job(s)?", default=False):
            console.print("Aborted.")
            return

    for entry in entries:
        needs_plist = not is_plist_current(entry)
        needs_load = not is_job_loaded(entry.label)
        if not needs_plist and not needs_load:
            continue

        if is_job_loaded(entry.label):
            bootout_job(entry.label)

        path = write_plist(entry)
        console.print(f"[green]OK[/green]      wrote {display_path(path)}")

        r = bootstrap_job(entry.label)
        if r.returncode != 0:
            console.print(f"[red]FAIL[/red]    launchctl bootstrap: {r.stderr.strip()}")
        else:
            console.print(f"[green]OK[/green]      loaded {entry.label}")


@jobs_app.command("remove")
def jobs_remove(
    labels: list[str] = typer.Argument(
        None,
        help="Job labels to remove (default: all).",
        show_default=False,
    ),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmations."),
) -> None:
    """Unload launchd jobs and delete plist files."""
    require_darwin()

    entries = load_job_entries()
    if labels:
        label_set = set(labels)
        entries = [e for e in entries if e.label in label_set]
        unknown = label_set - {e.label for e in entries}
        if unknown:
            console.print(f"[red]Unknown label(s): {', '.join(sorted(unknown))}[/red]")
            raise typer.Exit(1)

    if not entries:
        console.print("No jobs to remove.")
        return

    for entry in entries:
        console.print(f"  {entry.label}")

    if not yes:
        if not typer.confirm(f"\nRemove {len(entries)} job(s)?", default=False):
            console.print("Aborted.")
            return

    for entry in entries:
        if is_job_loaded(entry.label):
            r = bootout_job(entry.label)
            if r.returncode != 0:
                console.print(f"[red]FAIL[/red]    bootout {entry.label}: {r.stderr.strip()}")
            else:
                console.print(f"[green]OK[/green]      unloaded {entry.label}")
        plist = _plist_path(entry.label)
        if plist.is_file():
            plist.unlink()
            console.print(f"[green]OK[/green]      deleted {display_path(plist)}")


@jobs_app.command("status")
def jobs_status() -> None:
    """Show status of all launchd jobs."""
    require_darwin()

    entries = load_job_entries()
    if not entries:
        console.print("No jobs configured.")
        return

    for entry in entries:
        parts: list[str] = []

        if is_script_present(entry):
            if is_script_executable(entry):
                parts.append("[green]script ok[/green]")
            else:
                parts.append("[red]script not executable[/red]")
        else:
            parts.append("[red]script missing[/red]")

        if is_plist_current(entry):
            parts.append("[green]plist ok[/green]")
        else:
            parts.append("[red]plist missing/outdated[/red]")

        if is_job_loaded(entry.label):
            parts.append("[green]loaded[/green]")
        else:
            parts.append("[red]not loaded[/red]")

        console.print(f"  {entry.label}: {', '.join(parts)}")
        console.print(f"    {entry.description}")
