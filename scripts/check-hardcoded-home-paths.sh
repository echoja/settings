#!/usr/bin/env bash
set -euo pipefail

if [[ $# -eq 0 ]]; then
  exit 0
fi

regex='/(Users|home)/[^/[:space:]]+'
had_violation=0

for file in "$@"; do
  if [[ ! -f "$file" ]]; then
    continue
  fi

  if command -v rg >/dev/null 2>&1; then
    matches="$(rg -n --pcre2 "$regex" "$file" || true)"
  else
    matches="$(grep -nE "$regex" "$file" || true)"
  fi

  if [[ -n "$matches" ]]; then
    echo "Hardcoded home path detected in $file. Use \$HOME instead:" >&2
    echo "$matches" >&2
    had_violation=1
  fi
done

exit "$had_violation"
