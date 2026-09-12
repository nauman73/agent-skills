# smart-commit

Commit in the format this branch already uses, with the message shown to you before anything
is written.

## The problem

Two things go wrong with agent-written commits. The first is format: every repo has a first-line
convention — a ticket prefix, a release line, plain Conventional Commits — and an agent that
doesn't know it produces a history that reads as though two different projects were merged. The
second is scope: `git add -A` is the easy path, so half-finished work, a stray `.env`, and the
scratch file you forgot about all land in the same commit.

This skill fixes both by being deliberately slow in the places that matter. It never stages
blindly, it asks before including untracked files, and it shows you the finished message before
committing.

## What it does

Five steps, strictly in order — each finishes, including any question it asks you, before the
next begins:

1. **Gather context** — `status`, `diff`, `diff --cached`, `log`.
2. **Stage** — all modified tracked files by explicit name. Untracked files are only staged if
   they're attributable to the current session's work, and then only after asking you.
3. **Build the message** — first line from your chosen convention, body generated from the diff.
4. **Review** — the full message, shown for approval. Nothing is committed until you say yes.
5. **Commit** — commit only, or commit and push. Your choice, asked each time.

## Conventions

The first line comes from one of four places: the previous commit's first line, a saved
convention, the last convention used this session, or a new one you define on the spot.

Saved conventions live in `references/conventions/` as one Markdown file each — frontmatter with
`name` and `description`, then `## Format`, `## Example` and `## Fields`. The skill reads the
frontmatter to build its menu, and the `## Fields` list to interview you for values, suggesting
each from the diff so most runs are a series of confirmations rather than typing.

One convention ships as a seed: `conventional-commits`. It's there as much to show the file
format as to be used. Define your own on first run and the skill writes the file for you, after
echoing back the format it inferred so a misunderstanding gets caught before it's saved.

> **Known limitation — conventions you define may not survive a plugin update.** They are written
> into the skill's own `references/conventions/` folder. When the skill is installed as a Claude
> Code plugin, that folder lives inside the versioned plugin cache
> (`~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/skills/smart-commit/`), which is
> replaced wholesale on `claude plugin update` — and your saved conventions go with it. Installed
> as a user-level skill in `~/.claude/skills/smart-commit/`, or copied in by hand, the folder is
> yours and they persist normally. If you define conventions you'd hate to lose, either install
> this skill by hand rather than as a plugin, or keep a copy of the `.md` files somewhere outside
> the skill folder.

## Flags

- `--fresh` / `-f` — ignore any preferences from earlier in the session; ask at every step.
- `--reuse` / `-r` — reuse the previous run's staging approach, convention, field values and
  action without re-asking. The recalled choices are shown above the message at review time, so
  nothing is silently applied — and if files with changes are being left out, they are listed
  with a warning before you confirm.

Without a flag, a repeat run offers you the previous preferences and waits for a yes or no.

## What it will not do

- Never `git add -A` or `git add .`.
- Never stage a file that looks like it holds secrets (`.env`, credentials, keys) without warning
  you first.
- Never push without asking.
- Never amend an existing commit unless you ask.
- Never skip hooks with `--no-verify`. A failing pre-commit hook is investigated and fixed, then
  committed fresh — not bypassed.

## Notes

The instructions run git commands as separate calls rather than chaining them with `&&`, and pass
the commit message as a quoted string rather than a heredoc. Both are deliberate: on Windows Git
Bash, chained git calls trigger intermittent `add_item` fatal errors, and heredoc syntax crashes
the shell process outright. On other platforms the difference is invisible.
