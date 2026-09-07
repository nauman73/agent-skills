# Nauman's Agent Skills

Practical skills for engineering work with coding agents. Straight out of the
`.claude/skills/` folder I actually work in.

## What this is

A skill is a folder with a `SKILL.md` in it: a name, a description of *when* to use
it, and the procedure the agent should follow. Your agent reads only the description
at startup and pulls in the full body when the work matches — which is why a set of
skills scales where one ever-growing instructions file does not.

Nothing here is a framework. Each skill is plain markdown you can read in a few
minutes, disagree with, and edit. Take the ones that fit how you work and rewrite
the rest.

This repo is published gradually — skills land here once they have earned their
keep in real work and carry no employer- or project-specific detail.

## The skills

| Skill | What it does |
|---|---|
| [`session-handoff`](skills/session-handoff/) | Carries one task across a cleared or compacted session. Writes a self-contained snapshot — goal, state, next step, decisions, blockers — and can archive the full Claude Code or GitHub Copilot transcript alongside it |

## Bring them in

### As a Claude Code plugin (easiest, stays updated)

Two commands inside Claude Code:

```
/plugin marketplace add nauman73/agent-skills
/plugin install agent-skills@nauman73
```

Plugin skills are namespaced, so you invoke them as `/agent-skills:session-handoff`.
`/plugin marketplace update` pulls new skills as I add them, and `/plugin` disables
the whole set any time.

> **If the first command fails with `Permission denied (publickey)`:** the
> `owner/repo` shorthand prefers SSH, and your SSH key is not authenticating to
> GitHub. Recent Claude Code versions fall back to HTTPS on their own; if yours does
> not, pass the HTTPS URL directly, which needs no key:
>
> ```
> /plugin marketplace add https://github.com/nauman73/agent-skills.git
> ```

### As editable files, in any agent

The [`skills`](https://github.com/vercel-labs/skills) CLI installs skills into
whatever directory your agent expects — it discovers this repo's root-level `skills/`
folder natively, and also reads the plugin manifests in `.claude-plugin/`.

```bash
npx skills add nauman73/agent-skills --list                      # see what's here first
npx skills add nauman73/agent-skills --skill session-handoff     # just the one
npx skills add nauman73/agent-skills -a claude-code -a cursor    # pick your agents
npx skills add nauman73/agent-skills -g                          # install globally
```

By default it symlinks into each agent's directory; pass `--copy` if you would rather
have independent copies to edit freely, and `-y` to skip the prompts. Repeat `--skill`
once per skill rather than listing several after one flag.

> **Note:** that CLI reports install telemetry for repositories GitHub confirms are
> public, which includes this one. Set `DISABLE_TELEMETRY=1` or `DO_NOT_TRACK=1` to
> turn it off, or use the plugin or clone-and-copy routes, which do not involve it.

### Or just clone and copy

They are only markdown and a few Python scripts:

```bash
git clone https://github.com/nauman73/agent-skills.git

# into a project
cp -r agent-skills/skills/session-handoff your-project/.claude/skills/

# or globally, for every project
cp -r agent-skills/skills/session-handoff ~/.claude/skills/
```

### Or ask your agent

This works fine too:

> Clone https://github.com/nauman73/agent-skills, look at the skills in `skills/`,
> and copy the ones that fit this project into my `.claude/skills/` folder. Tell me
> which ones you picked and why.

For the last two, restart your session (or run `/skills`) and they will show up.

## Using these with other agents

Skills are just markdown. There is no Claude-specific runtime here, so most of this
works anywhere an agent can read files.

Copy a skill folder to the location your agent reads, or let `npx skills` do it:

| Agent | Per-project | Global |
|---|---|---|
| Claude Code | `.claude/skills/` | `~/.claude/skills/` |
| GitHub Copilot | `.agents/skills/` | `~/.copilot/skills/` |
| Cursor | `.agents/skills/` | `~/.cursor/skills/` |
| Codex | `.agents/skills/` | `~/.codex/skills/` |

Copilot can run Claude Code skills directly, and `session-handoff` is built for that
— it handles Copilot's own chat transcript format explicitly, not just Claude Code's.
The `skills` CLI supports many more agents than the four above; run it to see the
current list.

**Anything with no skills mechanism** still works, boringly: keep the folder in your
repo and point at it from `AGENTS.md` (or the equivalent), telling the agent to read
the matching `SKILL.md` before starting that kind of work.

Two things to adjust when you port them:

- **Slash-command syntax.** Skills that reference each other by name assume Claude
  Code's invocation. Elsewhere, say "use the session-handoff skill" instead.
- **Script paths.** A skill that shells out to its own bundled scripts assumes where
  it was installed. If you put it somewhere non-default, check those paths.

## Read them before you trust them

A skill you have not read is just a longer prompt you do not control. Each folder
has a `README.md` explaining what the skill is for and why it works the way it does,
and a `SKILL.md` with the procedure itself.

## License

MIT, see [LICENSE](LICENSE). Take them, fork them, rewrite them.
