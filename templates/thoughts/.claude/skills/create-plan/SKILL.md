---
name: create-plan
description: Create implementation plans in thoughts/plans/ with validated frontmatter
metadata:
  internal: true
---

# Create Plan

Create detailed implementation plans through interactive research and iteration.

## Document Standard

- **Path**: `thoughts/plans/YYYY-MM-DD-description.md` (kebab-case)
- **Frontmatter validation**: Run `scripts/validate-frontmatter` after writing

### Required Frontmatter

```yaml
---
date: 2026-02-26T14:30:00+09:00  # ISO datetime with timezone
author: <author>                   # who wrote this
status: draft                      # draft | approved | implementing | completed | archived
topic: "Brief description"         # what this plan is about
tags: [plan, component-name]       # relevant tags (array format)
---
```

## Process

### Step 1: Understand the Task

When invoked:

1. **If parameters provided** — read them immediately
2. **If no parameters** — ask:
   ```
   I'll help create an implementation plan. Please provide:
   1. Task/ticket description or reference
   2. Context, constraints, or requirements
   3. Links to related research or implementations
   ```

### Step 2: Research

1. Read all mentioned files FULLY (no limit/offset)
2. Spawn parallel agents to research the codebase:
   - **codebase-locator** — find related files
   - **codebase-analyzer** — understand current implementation
   - **thoughts-locator** — find existing research/plans
3. Present findings with file:line references
4. Ask only questions that code investigation can't answer

### Step 3: Structure

Present an outline for approval before writing details:

```
## Overview
[1-2 sentence summary]

## Phases:
1. [Phase] — [what it accomplishes]
2. [Phase] — [what it accomplishes]
```

### Step 4: Write

Write to `thoughts/plans/YYYY-MM-DD-description.md`:

````markdown
---
date: <ISO datetime>
author: <author>
status: draft
topic: "<description>"
tags: [plan, <components>]
---

# [Feature] Implementation Plan

## Overview
[What and why]

## Current State Analysis
[What exists, what's missing, constraints]

## What We're NOT Doing
[Out-of-scope items]

## Implementation Approach
[High-level strategy]

## Phase 1: [Name]

### Overview
[What this phase accomplishes]

### Changes Required

#### 1. [Component]
**File**: `path/to/file.ext`
**Changes**: [Summary]

### Success Criteria

#### Automated Verification:
- [ ] Tests pass: `<test command>`
- [ ] Type check passes: `<typecheck command>`
- [ ] Lint passes: `<lint command>`

#### Manual Verification:
- [ ] [Feature works as expected]
- [ ] [No regressions]

---

## Testing Strategy
[Unit, integration, manual tests]

## References
- Related research: `thoughts/research/[file].md`
````

### Step 5: Validate

1. Run `scripts/validate-frontmatter thoughts/plans/<filename>.md`
2. Fix any issues before presenting to user
3. Iterate based on feedback

## Guidelines

- **Be skeptical** — question vague requirements, identify issues early
- **Be interactive** — get buy-in at each step, don't write everything at once
- **Be thorough** — include file:line references, measurable success criteria
- **No open questions in final plan** — resolve everything before finalizing
- **Separate success criteria** into automated (commands) and manual (human testing)
