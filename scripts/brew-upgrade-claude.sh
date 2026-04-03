#!/bin/bash
set -euo pipefail

if ! command -v brew &>/dev/null; then
  exit 1
fi

outdated=$(brew outdated --formula claude 2>/dev/null || true)

if [ -n "$outdated" ]; then
  brew upgrade claude
  if command -v terminal-notifier &>/dev/null; then
    terminal-notifier \
      -title "Homebrew" \
      -message "Claude CLI upgraded" \
      -group "com.echoja.brew-upgrade-claude"
  fi
fi
