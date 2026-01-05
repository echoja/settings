#!/usr/bin/env -S uv run --script
import os
import re
import shutil
from typing import Optional

import typer

app = typer.Typer(add_completion=False)


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

    counts = {"ok": 0, "missing": 0, "warn": 0, "skipped": 0}

    def report_ok(message: str) -> None:
        typer.echo(f"OK      {message}")
        counts["ok"] += 1

    def report_missing(message: str) -> None:
        typer.echo(f"MISSING {message}")
        counts["missing"] += 1

    def report_warn(message: str) -> None:
        typer.echo(f"WARN    {message}")
        counts["warn"] += 1

    def report_skip(message: str) -> None:
        typer.echo(f"SKIP    {message}")
        counts["skipped"] += 1

    def check_cmd(label: str, cmd: str, hint: Optional[str]) -> None:
        msg = f"command: {cmd}"
        if hint:
            msg = f"{msg} (used by: {hint})"
        if shutil.which(cmd):
            report_ok(f"{label} - {msg}")
        else:
            report_missing(f"{label} - {msg}")

    def check_dir(label: str, path: str, hint: Optional[str]) -> None:
        msg = f"dir: {path}"
        if hint:
            msg = f"{msg} (used by: {hint})"
        if os.path.isdir(path):
            report_ok(f"{label} - {msg}")
        else:
            report_missing(f"{label} - {msg}")

    def check_file(label: str, path: str, hint: Optional[str]) -> None:
        msg = f"file: {path}"
        if hint:
            msg = f"{msg} (used by: {hint})"
        if os.path.isfile(path):
            report_ok(f"{label} - {msg}")
        else:
            report_missing(f"{label} - {msg}")

    def check_file_or_cmd(
        label: str, path: str, cmd: str, hint: Optional[str]
    ) -> None:
        msg = f"file: {path}"
        if hint:
            msg = f"{msg} (used by: {hint})"
        if os.access(path, os.X_OK):
            report_ok(f"{label} - {msg}")
            return

        found = shutil.which(cmd)
        if found:
            report_warn(f"{label} - {msg} (found {cmd} at: {found})")
        else:
            report_missing(f"{label} - {msg}")

    def run_check(
        label: str,
        pattern: str,
        kind: str,
        target: str,
        hint: Optional[str],
        cmd: Optional[str] = None,
    ) -> None:
        if pattern and not has_pattern(pattern, zshrc_path):
            report_skip(f"{label} - not referenced in .zshrc")
            return

        if kind == "command":
            check_cmd(label, target, hint)
        elif kind == "dir":
            check_dir(label, target, hint)
        elif kind == "file":
            check_file(label, target, hint)
        elif kind == "file_or_cmd":
            check_file_or_cmd(label, target, cmd or target, hint)
        else:
            typer.echo(f"error: unknown check kind: {kind}")
            raise typer.Exit(2)

    home = os.path.expanduser("~")
    checks = [
        (
            "homebrew",
            "/opt/homebrew/bin/brew",
            "file_or_cmd",
            "/opt/homebrew/bin/brew",
            "/opt/homebrew/bin/brew shellenv",
            "brew",
        ),
        ("git", r"plugins=\(git", "command", "git", "plugins=(git ...)", None),
        (
            "oh-my-zsh",
            "oh-my-zsh.sh",
            "file",
            os.path.join(home, ".oh-my-zsh/oh-my-zsh.sh"),
            "source $ZSH/oh-my-zsh.sh",
            None,
        ),
        (
            "powerlevel10k",
            "powerlevel10k",
            "dir",
            os.path.join(
                home, ".oh-my-zsh/custom/themes/powerlevel10k"
            ),
            "ZSH_THEME=powerlevel10k/powerlevel10k",
            None,
        ),
        (
            "zsh-syntax-highlighting",
            "zsh-syntax-highlighting",
            "dir",
            os.path.join(
                home, ".oh-my-zsh/custom/plugins/zsh-syntax-highlighting"
            ),
            "plugins=(... zsh-syntax-highlighting)",
            None,
        ),
        ("fzf", "fzf --zsh", "command", "fzf", "fzf --zsh", None),
        ("direnv", "direnv hook zsh", "command", "direnv", "direnv hook zsh", None),
        ("zoxide", "zoxide init zsh", "command", "zoxide", "zoxide init zsh", None),
        ("go", "go env GOPATH", "command", "go", "go env GOPATH", None),
        (
            "go-bin",
            "/usr/local/go/bin",
            "dir",
            "/usr/local/go/bin",
            "/usr/local/go/bin in PATH",
            None,
        ),
        (
            "vscode-code",
            "code --locate-shell-integration-path",
            "command",
            "code",
            "code --locate-shell-integration-path zsh",
            None,
        ),
        ("kubectl", "kubectl", "command", "kubectl", 'alias k="kubectl"', None),
        ("kubectx", "kubectx", "command", "kubectx", 'alias kx="kubectx"', None),
        ("pnpm", "pnpm", "command", "pnpm", 'alias p="pnpm"', None),
        ("curlie", "curlie", "command", "curlie", 'alias c="curlie"', None),
        ("codex", "codex", "command", "codex", 'alias cdx="codex ..."', None),
        ("skim", "sk", "command", "sk", "gs() uses sk", None),
        ("terraform", "terraform", "command", "terraform", 'alias tf="terraform"', None),
        ("nvim", "nvim", "command", "nvim", 'alias vim="nvim"', None),
        ("tv", "tv text", "command", "tv", 'alias tt="tv text"', None),
        ("fd", "fd --type f", "command", "fd", "SKIM_DEFAULT_COMMAND uses fd", None),
        ("rg", "rg --files", "command", "rg", "SKIM_DEFAULT_COMMAND uses rg", None),
        (
            "chromium",
            "chromium",
            "command",
            "chromium",
            "PUPPETEER_EXECUTABLE_PATH uses chromium",
            None,
        ),
        ("python3", "python3", "command", "python3", "alias python=python3", None),
        ("pip3", "pip3", "command", "pip3", "alias pip=pip3", None),
        ("npm", "npm config", "command", "npm", "addcert/delcert aliases", None),
        (
            "mysql-client",
            "/opt/homebrew/opt/mysql-client/bin",
            "dir",
            "/opt/homebrew/opt/mysql-client/bin",
            "PATH includes mysql-client",
            None,
        ),
        (
            "ruby",
            "/opt/homebrew/opt/ruby/bin",
            "dir",
            "/opt/homebrew/opt/ruby/bin",
            "PATH includes ruby",
            None,
        ),
        (
            "android-platform-tools",
            "Android/sdk/platform-tools",
            "dir",
            os.path.join(home, "Library/Android/sdk/platform-tools"),
            "PATH includes Android SDK",
            None,
        ),
        (
            "vscode-app-bin",
            "Visual Studio Code.app/Contents/Resources/app/bin",
            "dir",
            "/Applications/Visual Studio Code.app/Contents/Resources/app/bin",
            "PATH includes VS Code",
            None,
        ),
        ("choose", "choose 0", "command", "choose", "killnode alias uses choose", None),
    ]

    typer.echo(f"Checking dependencies from: {zshrc_path}")
    for label, pattern, kind, target, hint, cmd in sorted(
        checks, key=lambda item: item[0].casefold()
    ):
        run_check(label, pattern, kind, target, hint, cmd)

    typer.echo("")
    typer.echo(
        "Summary: ok={ok} missing={missing} warn={warn} skipped={skipped}".format(
            **counts
        )
    )

    if counts["missing"] > 0:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
