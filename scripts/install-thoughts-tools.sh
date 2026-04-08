#!/usr/bin/env bash
set -euo pipefail

#
# Install thoughts/ tools into a target repository.
#
# Copies from ~/settings/templates/thoughts/ into the target repo:
#   - scripts/validate-frontmatter
#   - .githooks/pre-commit
#   - .claude/skills/create-plan/SKILL.md
#   - .claude/skills/research-codebase/SKILL.md
#   - thoughts/plans/  (directory, if missing)
#   - thoughts/research/  (directory, if missing)
#
# Also configures: git config core.hooksPath .githooks
#
# Usage:
#   install-thoughts-tools.sh <repo-path>
#   install-thoughts-tools.sh .              # current directory
#

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

TEMPLATE_DIR="$HOME/settings/templates/thoughts"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <repo-path>"
  echo "  Install thoughts/ tools into a git repository."
  exit 1
fi

TARGET=$(cd "$1" && pwd)

# verify target is a git repo
if ! git -C "$TARGET" rev-parse --show-toplevel &>/dev/null; then
  printf "${RED}ERROR${NC}  %s is not a git repository\n" "$TARGET"
  exit 1
fi

echo "=== Installing thoughts tools ==="
echo "Template: $TEMPLATE_DIR"
echo "Target:   $TARGET"
echo ""

# --- copy files ---
copy_file() {
  local rel="$1"
  local src="$TEMPLATE_DIR/$rel"
  local dst="$TARGET/$rel"

  if [[ ! -f "$src" ]]; then
    printf "  ${RED}SKIP${NC}  %s (template not found)\n" "$rel"
    return
  fi

  mkdir -p "$(dirname "$dst")"

  if [[ -f "$dst" ]]; then
    if diff -q "$src" "$dst" &>/dev/null; then
      printf "  ${GREEN}OK${NC}    %s (already up to date)\n" "$rel"
      return
    fi
    printf "  ${YELLOW}UPDATE${NC}  %s\n" "$rel"
  else
    printf "  ${GREEN}ADD${NC}   %s\n" "$rel"
  fi

  cp "$src" "$dst"
}

copy_file "scripts/validate-frontmatter"
copy_file ".githooks/pre-commit"
copy_file ".claude/skills/create-plan/SKILL.md"
copy_file ".claude/skills/research-codebase/SKILL.md"

# --- make scripts executable ---
chmod +x "$TARGET/scripts/validate-frontmatter" 2>/dev/null || true
chmod +x "$TARGET/.githooks/pre-commit" 2>/dev/null || true

# --- ensure thoughts directories exist ---
for dir in thoughts/plans thoughts/research; do
  if [[ ! -d "$TARGET/$dir" ]]; then
    mkdir -p "$TARGET/$dir"
    printf "  ${GREEN}ADD${NC}   %s/\n" "$dir"
  else
    printf "  ${GREEN}OK${NC}    %s/ (exists)\n" "$dir"
  fi
done

# --- configure git hooks path ---
echo ""
CURRENT_HOOKS_PATH=$(git -C "$TARGET" config --get core.hooksPath 2>/dev/null || echo "")
if [[ "$CURRENT_HOOKS_PATH" == ".githooks" ]]; then
  printf "  ${GREEN}OK${NC}    core.hooksPath = .githooks\n"
else
  git -C "$TARGET" config core.hooksPath .githooks
  printf "  ${GREEN}SET${NC}   core.hooksPath = .githooks\n"
fi

echo ""
echo "=== Done ==="
echo ""
echo "Next steps:"
echo "  1. Review and commit the new files"
echo "  2. Existing .githooks/pre-commit may need merging if the repo already had one"
