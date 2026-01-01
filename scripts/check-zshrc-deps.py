#!/usr/bin/env -S uv run --script
import os
import re
import shutil
import sys


def usage() -> str:
    return """Usage: check-zshrc-deps.sh [path-to-zshrc] [--all]

Checks for tools and paths referenced by a .zshrc file.

Options:
  --all   Check all known items, even if not found in the .zshrc
  -h, --help  Show this help

Examples:
  scripts/check-zshrc-deps.sh
  scripts/check-zshrc-deps.sh ~/.zshrc
  scripts/check-zshrc-deps.sh --all
"""


def find_zshrc_path(arg_path: str) -> str:
    if arg_path:
        return arg_path

    cwd_zshrc = os.path.join(os.getcwd(), ".zshrc")
    if os.path.isfile(cwd_zshrc):
        return cwd_zshrc

    home = os.path.expanduser("~")
    home_zshrc = os.path.join(home, ".zshrc")
    if os.path.isfile(home_zshrc):
        return home_zshrc

    print("error: .zshrc not found. Provide a path or set ZSHRC_PATH.")
    sys.exit(2)


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


def main() -> int:
    check_all = False
    zshrc_path = ""

    for arg in sys.argv[1:]:
        if arg == "--all":
            check_all = True
        elif arg in ("-h", "--help"):
            print(usage(), end="")
            return 0
        else:
            if not zshrc_path:
                zshrc_path = arg
            else:
                print(f"error: unexpected argument: {arg}")
                print(usage(), end="")
                return 2

    zshrc_path = find_zshrc_path(zshrc_path)
    if not os.path.isfile(zshrc_path):
        print(f"error: .zshrc not found at: {zshrc_path}")
        return 2

    counts = {"ok": 0, "missing": 0, "warn": 0, "skipped": 0}

    def report_ok(message: str) -> None:
        print(f"OK      {message}")
        counts["ok"] += 1

    def report_missing(message: str) -> None:
        print(f"MISSING {message}")
        counts["missing"] += 1

    def report_warn(message: str) -> None:
        print(f"WARN    {message}")
        counts["warn"] += 1

    def report_skip(message: str) -> None:
        print(f"SKIP    {message}")
        counts["skipped"] += 1

    def check_cmd(label, cmd, hint):
        msg = f"command: {cmd}"
        if hint:
            msg = f"{msg} (used by: {hint})"
        if shutil.which(cmd):
            report_ok(f"{label} - {msg}")
        else:
            report_missing(f"{label} - {msg}")

    def check_dir(label, path, hint):
        msg = f"dir: {path}"
        if hint:
            msg = f"{msg} (used by: {hint})"
        if os.path.isdir(path):
            report_ok(f"{label} - {msg}")
        else:
            report_missing(f"{label} - {msg}")

    def check_file(label, path, hint):
        msg = f"file: {path}"
        if hint:
            msg = f"{msg} (used by: {hint})"
        if os.path.isfile(path):
            report_ok(f"{label} - {msg}")
        else:
            report_missing(f"{label} - {msg}")

    def check_file_or_cmd(label, path, cmd, hint):
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

    def run_check(label, pattern, kind, target, hint, cmd=None):
        if not check_all and pattern:
            if not has_pattern(pattern, zshrc_path):
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
            print(f"error: unknown check kind: {kind}")
            sys.exit(2)

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

    print(f"Checking dependencies from: {zshrc_path}")
    for label, pattern, kind, target, hint, cmd in checks:
        run_check(label, pattern, kind, target, hint, cmd)

    print("")
    print(
        "Summary: ok={ok} missing={missing} warn={warn} skipped={skipped}".format(
            **counts
        )
    )

    if counts["missing"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
