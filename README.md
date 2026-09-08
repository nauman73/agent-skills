# Nauman's Agent Skills

Skills I use for day-to-day engineering work with coding agents, published one at a
time as each proves itself on real tasks.

## What a skill is

A folder containing a `SKILL.md`: frontmatter naming the skill and describing the
situations it applies to, followed by the procedure itself. The agent keeps only that
description in context and loads the body when your request matches it.

The practical consequence is that a skill costs you almost nothing until it fires.
Instructions you paste into one ever-growing project file are paid for on every
single turn, whether relevant or not — which is why that file eventually gets ignored
and a folder of skills does not.

Everything here is markdown and a little Python. Read it, argue with it, change the
parts that don't match how you work.

## The skills

| Skill | What it does |
|---|---|
| [`session-handoff`](skills/session-handoff/) | Carries one task across a cleared or compacted session. Writes a self-contained snapshot — goal, state, next step, decisions, blockers — and can archive the full Claude Code or GitHub Copilot transcript alongside it |

## Installing

### Claude Code plugin

**In your shell.** This route works wherever the `claude` CLI is installed, so it is
the one to use:

```bash
claude plugin marketplace add nauman73/agent-skills
claude plugin install nh-workbench@nauman73          # --scope user|project|local
claude plugin details nh-workbench                   # inventory + token cost
claude plugin list
```

The same operations exist as `/plugin` commands typed at the prompt **in the terminal
CLI** — `/plugin marketplace add nauman73/agent-skills`, then
`/plugin install nh-workbench@nauman73`. Note that **`/plugin` is not available in
the VS Code extension**, which answers `/plugin isn't available in this environment`.
Install from a shell instead; the extension loads and runs installed plugins
normally, it just cannot manage them.

Skills arrive namespaced — `/nh-workbench:session-handoff`. Start a new session
afterwards; a running one will not see them. Later, `claude plugin marketplace update`
pulls new skills, `claude plugin update nh-workbench` moves to the latest version, and
`claude plugin uninstall nh-workbench` removes the set.

> **Already have one of these skills in `~/.claude/skills/`?** You will then have it
> twice — once unnamespaced from your own folder, once as
> `/nh-workbench:session-handoff` — with both descriptions loaded at startup and no
> clear answer as to which fires. Move your copy aside first, or install to
> `--scope project` in a repo you are only testing in.

> **`Permission denied (publickey)` on the first command?** The `owner/repo` form is
> resolved over SSH, and yours isn't authenticating. Newer Claude Code builds retry
> over HTTPS by themselves; if yours doesn't, name the protocol explicitly:
>
> ```
> /plugin marketplace add https://github.com/nauman73/agent-skills.git
> ```

### The `skills` CLI, for any agent

In your shell. [`skills`](https://github.com/vercel-labs/skills) finds this repo's
root-level `skills/` directory on its own, and reads the manifests in
`.claude-plugin/` too:

```bash
npx skills add nauman73/agent-skills --list                      # inspect first
npx skills add nauman73/agent-skills --skill session-handoff     # one skill
npx skills add nauman73/agent-skills -a claude-code -a cursor    # chosen agents
npx skills add nauman73/agent-skills -g                          # global install
```

Installs are symlinks by default — add `--copy` for independent files you can edit
freely, and `-y` to run unattended. `--skill` repeats per skill; it does not take a
list.

> **Note:** this CLI reports install telemetry for repositories GitHub confirms are
> public, which includes this one. `DISABLE_TELEMETRY=1` or `DO_NOT_TRACK=1` turns it
> off, and neither the plugin nor the manual route below involves it.

### By hand

In your shell. A skill is a directory — put it where your agent looks:

```bash
git clone https://github.com/nauman73/agent-skills.git

cp -r agent-skills/skills/session-handoff your-project/.claude/skills/   # one project
cp -r agent-skills/skills/session-handoff ~/.claude/skills/              # everywhere
```

Start a new session, or run `/skills`, and it will be picked up.

## Where each agent looks

| Agent | Per-project | Global |
|---|---|---|
| Claude Code | `.claude/skills/` | `~/.claude/skills/` |
| GitHub Copilot | `.agents/skills/` | `~/.copilot/skills/` |
| Cursor | `.agents/skills/` | `~/.cursor/skills/` |
| Codex | `.agents/skills/` | `~/.codex/skills/` |

The `skills` CLI covers many more than these four; run it to see the current list.
Where an agent has no skills mechanism at all, commit the folder to your repo and
reference it from `AGENTS.md`, instructing the agent to consult the relevant
`SKILL.md` before that kind of task.

## Portability

These skills are written and used against Claude Code, so that is where they are
proven. The procedures themselves are just markdown and hold up on any agent that
can read a file and run a command.

What does not travel automatically is a dependency on something specific to Claude
Code — a tool like `AskUserQuestion`, or a path such as `~/.claude/projects/`. Where
a skill has one, its own README says which parts are affected and what the
alternative is, rather than leaving you to find out mid-task.

## Before you run any of this

These skills act on your repository, and one of them can copy your session history
into it. That is worth understanding rather than trusting. Each folder holds a
`README.md` covering what the skill is for and the reasoning behind how it behaves,
next to the `SKILL.md` the agent actually executes.

## Licence

[MIT](LICENSE). Fork it, strip it, rewrite it.
