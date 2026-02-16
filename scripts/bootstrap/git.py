from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .utils import console


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
