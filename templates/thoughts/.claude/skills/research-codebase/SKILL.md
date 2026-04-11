---
name: research-codebase
description: Research and document codebase patterns in thoughts/research/ with validated frontmatter
metadata:
  internal: true
---

# Research Codebase

Conduct comprehensive codebase research and document findings. Your job is to **document what exists**, not suggest improvements.

## Document Standard

- **Path**: `thoughts/research/YYYY-MM-DD-description.md` (kebab-case)
- **Frontmatter validation**: Run `scripts/validate-frontmatter` after writing

### Required Frontmatter

```yaml
---
date: 2026-02-26T14:30:00+09:00  # ISO datetime with timezone
researcher: <name>                 # who conducted this research
topic: "Research topic"            # what was researched
tags: [research, component-name]   # relevant tags (array format)
status: complete                   # in-progress | complete | outdated
---
```

## Critical Rules

- DO NOT suggest improvements or changes unless explicitly asked
- DO NOT critique the implementation or identify problems
- DO NOT recommend refactoring or optimization
- ONLY describe what exists, where it exists, how it works, and how components interact
- You are creating a technical map of the existing system

## Process

### Step 1: Understand the Question

When invoked:

1. **If parameters provided** — read them immediately (FULLY, no limit/offset)
2. **If no parameters** — ask:
   ```
   I'm ready to research the codebase. Please provide your research question or area of interest.
   ```

### Step 2: Research

1. Break down the query into composable research areas
2. Spawn parallel agents:
   - **codebase-locator** — find WHERE files and components live
   - **codebase-analyzer** — understand HOW specific code works
   - **codebase-pattern-finder** — find examples of existing patterns
   - **thoughts-locator** — find existing research/plans on the topic
3. Wait for ALL agents to complete before synthesizing

### Step 3: Write

Write to `thoughts/research/YYYY-MM-DD-description.md`:

````markdown
---
date: <ISO datetime>
researcher: <name>
topic: "<research topic>"
tags: [research, <components>]
status: complete
---

# Research: [Topic]

## Research Question
[Original query]

## Summary
[High-level documentation answering the question]

## Detailed Findings

### [Component/Area 1]
- Description of what exists (`file.ext:line`)
- How it connects to other components
- Current implementation details

### [Component/Area 2]
...

## Code References
- `path/to/file.py:123` — description
- `another/file.ts:45-67` — description

## Architecture Documentation
[Patterns, conventions, design implementations]

## Related Research
[Links to other thoughts/ documents]

## Open Questions
[Areas needing further investigation]
````

### Step 4: Validate

1. Run `scripts/validate-frontmatter thoughts/research/<filename>.md`
2. Fix any issues

### Step 5: Present

- Present a concise summary with key file references
- Ask if there are follow-up questions

### Follow-up Research

If the user has follow-ups:
- Append to the same document under `## Follow-up Research [timestamp]`
- Update frontmatter: add `last_updated` and `last_updated_by`

## Guidelines

- Always use parallel agents for efficiency
- Focus on concrete file paths and line numbers
- Research documents should be self-contained
- Document cross-component connections
- Prioritize live codebase findings over existing docs
