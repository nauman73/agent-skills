---
name: conventional-commits
description: Conventional Commits format (type(scope)?: subject) — scope optional
---

## Format
`<type>(<scope>)?: <subject>`

Scope is optional; omit the parentheses entirely when not applicable.

## Example
`feat(auth): add JWT login`
`fix: correct null pointer in worker` (no scope)

## Fields
- **type** — commit type, e.g. `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.
- **scope** — area of the codebase affected, in parentheses, e.g. `auth`. Optional: leave blank and the parentheses are dropped.
- **subject** — short imperative description of the change, lowercase, no trailing period.
