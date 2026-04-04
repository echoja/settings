#!/bin/bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] fetching origin..."
git fetch origin

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] already up to date (${LOCAL:0:7})"
  exit 0
fi

if git merge-base --is-ancestor "$LOCAL" "$REMOTE"; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] pulling ${LOCAL:0:7} -> ${REMOTE:0:7}"
  git pull --ff-only
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] pull complete"
  if command -v terminal-notifier &>/dev/null; then
    terminal-notifier \
      -title "Settings" \
      -message "Auto-pulled latest changes" \
      -group "com.echoja.settings-pull"
  fi
else
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] local has diverged from origin/main, skipping"
fi
