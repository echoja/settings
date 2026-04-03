#!/bin/bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

git fetch origin

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
  exit 0
fi

if git merge-base --is-ancestor "$LOCAL" "$REMOTE"; then
  git pull --ff-only
  if command -v terminal-notifier &>/dev/null; then
    terminal-notifier \
      -title "Settings" \
      -message "Auto-pulled latest changes" \
      -group "com.echoja.settings-pull"
  fi
fi
