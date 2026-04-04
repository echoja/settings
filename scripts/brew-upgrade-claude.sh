#!/bin/bash
set -euo pipefail

if ! command -v brew &>/dev/null; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] brew not found"
  exit 1
fi

current=$(brew list --versions claude 2>/dev/null | awk '{print $2}' || echo "unknown")
echo "[$(date '+%Y-%m-%d %H:%M:%S')] checking claude (current: ${current})..."

outdated=$(brew outdated --formula claude 2>/dev/null || true)

if [ -n "$outdated" ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] upgrading claude..."
  brew upgrade claude
  new_ver=$(brew list --versions claude 2>/dev/null | awk '{print $2}' || echo "unknown")
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] upgraded: ${current} -> ${new_ver}"
  if command -v terminal-notifier &>/dev/null; then
    terminal-notifier \
      -title "Homebrew" \
      -message "Claude CLI upgraded: ${current} -> ${new_ver}" \
      -group "com.echoja.brew-upgrade-claude"
  fi
else
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] already latest (${current})"
fi
