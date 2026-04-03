# User Preferences

## Language
- Always respond in English, even if the user writes in Korean or other languages.
- The user is an English learner — use clear, natural English.
- When the user's English has a grammar or phrasing issue, briefly point it out with a suggested correction (e.g., "Tip: '...' → '...'"). Skip minor issues to avoid being noisy.

## Memory
- Do not proactively save memories. Only save when I explicitly ask you to remember something.
- When the user says "remember this" or "기억해줘", update the **project CLAUDE.md** (not the memory/ directory).

## Settings repo (`~/settings`)
- The user's dotfiles and system config are managed in `~/settings` (git repo: `echoja/settings`).
- Dotfiles are symlinked from `~/settings/` to `~/` via `scripts/links.json`.
- Dependencies are tracked in `scripts/deps.json`.
- When the user wants to save something to settings (e.g., a new dotfile, config change, dependency):
  1. Make the appropriate changes in `~/settings` (edit/add files, update `links.json` or `deps.json` as needed).
  2. If adding a new dotfile, create a symlink from `~/<key>` → `~/settings/<key>`.
  3. Run `cd ~/settings && ./v` to verify everything is correct.
  4. Commit and push: `cd ~/settings && git add -A && git commit -m "<message>" && git push`.
