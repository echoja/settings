# `templates/thoughts` — thoughts system bootstrap

This directory is **a template bundle**, not a directory structure
that gets preserved verbatim. Its contents are copied to the **root
of a target project** when you apply the template. The word
`thoughts` here is the **name of the bundle**, not a destination
path component.

## What it installs

When applied to `<project>`:

| Source in this template                         | Lands at (in target project)            |
|---|---|
| `.githooks/pre-commit`                            | `<project>/.githooks/pre-commit`          |
| `.claude/skills/research-codebase/SKILL.md`       | `<project>/.claude/skills/research-codebase/SKILL.md` |
| `.claude/skills/create-plan/SKILL.md`             | `<project>/.claude/skills/create-plan/SKILL.md` |
| `scripts/validate-frontmatter`                    | `<project>/scripts/validate-frontmatter`  |

Together these turn an empty project into one that:

- Tracks plans and research under `thoughts/plans/` and
  `thoughts/research/` (created on first use).
- Validates frontmatter on every commit via a `pre-commit` hook
  that calls `scripts/validate-frontmatter`.
- Exposes two Claude Code skills (`create-plan`,
  `research-codebase`) that walk the user through producing those
  documents with the required frontmatter.

## Why the name "thoughts"

The three things above exist to support the **thoughts document
workflow** — the convention of writing plans and research under a
`thoughts/` directory in each project. The template is named after
the workflow it enables, not after any path it creates.

If more templates are added later (e.g. `templates/ci-checks/`,
`templates/docker/`), they will sit alongside this one and be
applied with the same conventions.

## How to apply it to a new project

There is no automated copy script yet. The manual flow is:

```bash
cp -R ~/settings/templates/thoughts/.githooks  <project>/.githooks
cp -R ~/settings/templates/thoughts/.claude    <project>/.claude
cp -R ~/settings/templates/thoughts/scripts    <project>/scripts
```

Then commit the added files in the target project and enable the
pre-commit hook (`git config core.hooksPath .githooks` or equivalent).

## Note on the Claude Code skill files

Both `.claude/skills/*/SKILL.md` files are marked
`metadata.internal: true` so the Vercel Labs
[`skills` CLI](https://github.com/vercel-labs/skills) hides them
from `npx skills add` listings when a project containing this
template is scanned. They are project-internal tooling, not
public skills.
