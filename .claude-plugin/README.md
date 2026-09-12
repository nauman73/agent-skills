# Packaging: how this repo publishes its skills

This folder holds the manifests that turn the repo into a Claude Code marketplace. The skill
files themselves live at `skills/<name>/` and **never move** — everything described here is a
manifest-only decision, reversible by editing one or two JSON files.

There are two supported ways to package the same skills. Mechanism A is what this repo uses
today. Mechanism B is the alternative, and the steps to switch in either direction are below.

## Where skills come from

Skills are authored and maintained outside this repository, in the agent's own skills folder
(`~/.claude/skills/<name>/`), and copied in by `./tools/sync-skill.ps1 -Name <skill>`. That
folder is the source of truth.

**Always edit the source copy, never the copy under `skills/` here** — the next sync overwrites
this one without warning. The script prunes `__pycache__` and `*.pyc`, and preserves two
repo-owned files across a sync:

- `skills/<name>/README.md` — human-facing notes written for this repo.
- `skills/<name>/.syncignore` — paths this repo must not publish, one per line, relative to the
  skill folder (`#` comments and blank lines ignored). Applied after the copy, so it wins over
  whatever the source folder contains.

`.syncignore` exists because a skill can ship something that belongs in one place and not
another — a seed convention file specific to a different deployment, say. A listed path that
does not exist after the copy is reported as a warning rather than passing silently, since a
typo there would publish the very file it was meant to withhold.

## Why `skills/<name>/` never moves

The obvious way to package per-skill plugins is the folder-per-plugin layout used by
Anthropic's `skill-creator`:

```
session-handoff/.claude-plugin/plugin.json
session-handoff/skills/session-handoff/SKILL.md
```

**Don't adopt it here.** Root-level `skills/` is the second entry in the `skills` npm CLI's
(`vercel-labs/skills`) discovery list, and `skills/<name>/SKILL.md` is its named flat layout.
That is what makes this repo consumable by Copilot, Cursor and Codex users via
`.agents/skills/`, which the root README advertises. Burying skills one level deeper trades
that away for a naming style — and as Mechanism B shows, the naming style is available without
paying for it.

## Mechanism A — one plugin, many skills (current)

One marketplace entry whose source is the repo root. The root `plugin.json` defines the
plugin's identity; every skill under `skills/` ships inside it.

**Files:** `plugin.json` (name `nh-workbench`) + `marketplace.json` (one entry, `"source": "./"`).

**Installs as:**

```
claude plugin marketplace add nauman73/agent-skills
claude plugin install nh-workbench@nauman73
```

**Invoked as:** `/nh-workbench:session-handoff`

**Properties:** one install command regardless of skill count; one browse row in `/plugin`;
one version number for the whole set; every skill's `description` enters always-on context
whenever the plugin is enabled. Coupled skills are guaranteed present together — which matters,
because there is no dependency mechanism (see Gotchas).

## Mechanism B — one plugin per skill (alternative)

Several marketplace entries, all sourced from the repo root, each claiming one skill folder via
the `skills` key. The root `plugin.json` is **removed**; each entry carries its own identity
inline.

For this repo, the `session-handoff` entry would read:

```json
{
  "name": "session-handoff",
  "source": "./",
  "skills": ["./skills/session-handoff"],
  "description": "Save or resume a structured task-state snapshot under the project's .claude/ folder, so in-flight work survives a /clear, a compaction, or a move to another machine.",
  "version": "1.0.0",
  "author": { "name": "Nauman Hameed", "url": "https://github.com/nauman73" },
  "homepage": "https://github.com/nauman73/agent-skills",
  "repository": "https://github.com/nauman73/agent-skills",
  "license": "MIT",
  "category": "productivity",
  "keywords": ["skills", "session-handoff", "context-management"]
}
```

The entry `name` becomes the invocation namespace, so it is named for the skill rather than the
author. Anthropic's official marketplace uses this shape for `box`, a flat `skills/` repo with
no `plugin.json` anywhere, whose single entry claims five skill folders by path.

**Installs as:** one command per skill —
`claude plugin install session-handoff@nauman73`

**Invoked as:** `/session-handoff:session-handoff` (the `skill-creator:skill-creator` style)

**Properties:** one browse row per skill, so each is discoverable on its own; per-skill install,
enable/disable and versioning; a user pays context only for the skills they installed.

## Switching A → B

1. Delete `.claude-plugin/plugin.json`.

   Keeping it is the trap: with `"source": "./"` the root `plugin.json` takes precedence over
   the marketplace entry at install time, so a stale file silently overrides what the entries
   declare. `claude plugin validate` warns about this for `version` — see Gotchas.

2. Replace the single entry in `marketplace.json` with one entry per skill, shaped like the
   `session-handoff` example under Mechanism B above. Each must be self-contained, since there
   is no longer a `plugin.json` for it to inherit from — copy `author`, `homepage`,
   `repository` and `license` into every entry.

3. Group coupled skills rather than splitting blindly. A plugin may claim several paths —
   `"skills": ["./skills/plan-feature", "./skills/execute-plan", "./skills/review-branch"]` —
   and for skills that reference each other this is the only way to guarantee they arrive
   together.

4. Update the root `README.md` install commands and skills table: the install line becomes one
   per plugin, and `/nh-workbench:<skill>` becomes `/<plugin>:<skill>`.

5. Update any `SKILL.md` cross-references from `/nh-workbench:<skill>` to the new namespace.
   They are greppable: `grep -rn "nh-workbench:" skills/`.

6. `claude plugin validate .` — expect a clean pass.

## Switching B → A

1. Recreate `.claude-plugin/plugin.json` with `name`, `version`, `description`, `author`,
   `homepage`, `repository`, `license` (git history has the `nh-workbench` original).
2. Collapse `marketplace.json` back to a single entry with `"source": "./"` and no `skills`
   key — omitted, it picks up everything under `skills/`.
3. Reverse steps 4–6 above.

## Gotchas (all verified against `claude plugin validate` on 2026-09-11)

- **`validate` does not check that `skills` paths exist.** An entry pointing at
  `./skills/no-such-skill` passes validation clean. A typo'd path therefore ships silently and
  only surfaces as a skill that never loads. Check paths by eye, or against `ls skills/`.
- **`plugin.json` wins over the marketplace entry.** With both present, validate warns:
  *"Entry declares version X but plugin.json says Y. At install time, plugin.json wins
  (calculatePluginVersion precedence) — the entry version is silently ignored."* Hence step 1
  of A → B.
- **Multiple entries may share `"source": "./"`.** Two entries pointing at the same repo root
  with different `skills` arrays validate without complaint.
- **There is no dependency mechanism.** Across all 294 plugins in the official marketplace,
  no dependency-shaped key exists. A skill referencing a skill from another plugin fails
  silently for anyone who installed only one of them — bare and namespaced references fail
  alike, since the problem is absence, not addressing.
- **Namespace cross-references in `SKILL.md` regardless of mechanism.** A bare `/session-handoff`
  does resolve when unambiguous, but this repo's skills also exist at `~/.claude/skills/`, and
  which copy a bare name binds to is unspecified. Namespaced references are deterministic and
  fail findably if a skill is later regrouped.

**Untested:** whether the entry `name` or a leftover `plugin.json` `name` governs the installed
namespace. Step 1 of A → B sidesteps the question by removing the file. Confirm with a real
install (`claude plugin marketplace add <local path>`) before relying on a mixed setup.

## Choosing between them

The deciding factor is **coupling, not skill count**.

Anthropic's own marketplace ships both shapes: `skill-creator` is one plugin holding exactly one
skill, while `superpowers` is one plugin holding fourteen — because those fourteen cross-
reference each other (`using-superpowers` routes to `brainstorming`, which routes to
`writing-plans`) and share `hooks/` and `scripts/` that cannot be split across plugins.

Independent tools someone would want separately → Mechanism B. A family that cites its own
members → keep them in one plugin, whichever mechanism is in use. With a single published skill
the two are equivalent in practice, which is why A stands: it is the status quo, and switching
costs one JSON edit whenever a second skill makes the question real.
