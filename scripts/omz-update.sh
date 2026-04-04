#!/bin/bash
set -euo pipefail

ZSH="${HOME}/.oh-my-zsh"

if [ ! -d "$ZSH" ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] oh-my-zsh not found at $ZSH"
  exit 1
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] updating oh-my-zsh..."

current=$(git -C "$ZSH" rev-parse --short HEAD 2>/dev/null || echo "unknown")

if git -C "$ZSH" pull --rebase --quiet origin master 2>/dev/null; then
  new=$(git -C "$ZSH" rev-parse --short HEAD 2>/dev/null || echo "unknown")
  if [ "$current" != "$new" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] updated: ${current} -> ${new}"
    if command -v terminal-notifier &>/dev/null; then
      terminal-notifier \
        -title "Oh My Zsh" \
        -message "Updated: ${current} -> ${new}" \
        -group "com.echoja.omz-update"
    fi
  else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] already latest (${current})"
  fi
else
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] update failed"
  exit 1
fi
