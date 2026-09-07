# session-handoff

Carry one task across a cleared or compacted agent session, without re-explaining it.

## The problem

Agent sessions end badly. Context fills up and auto-compact silently drops the
middle of your conversation; you run `/clear` to get room back; you stop for the
day and come back tomorrow to a session that has no idea what you were doing.

Persistent memory does not solve this. Memory is for durable facts — who you are,
how the project is laid out, what you prefer. It is deliberately not a record of
*in-flight task state*: which file you were halfway through editing, which
approach you already tried and rejected, what you were blocked on.

So that state gets reconstructed by hand, from scratch, every time. You re-explain
the goal, re-locate the files, and re-derive the decision you already made
yesterday — and the agent confidently redoes work you had already finished.

## What it does

Two modes, chosen from how you phrase the request.

**SAVE** — writes a self-contained snapshot to `.claude/handoff-<slug>.md`:
the goal, what is done so far with exact file paths and line numbers, the single
next concrete action, pending TODOs, the non-obvious decisions that are not visible
in the code or git log, and open blockers.

Say any of: *"save the session"*, *"I'm about to /clear"*, *"compact is coming"*,
*"checkpoint this work"*, *"update the handoff"*.

**RESUME** — finds the handoff, reads it in full, checks `git status` and
`git log -5` against the branch the handoff recorded, echoes back a short summary,
and then **stops and waits**.

Say any of: *"resume from the handoff"*, *"pick up where we left off"*,
*"read .claude/handoff-auth-bug.md and continue"*.

## Two design choices worth knowing

**Resume does not auto-start the work.** The handoff was true when it was written.
You may have already done part of it, changed your mind, or want a different angle.
Auto-executing "Next step" risks redoing finished work or driving hard in the wrong
direction, so the skill confirms first. One short confirmation turn costs far less
than a batch of unwanted edits. If `git status` shows uncommitted changes the
handoff never mentioned, it flags them rather than working over the top of them.

**Every path is written to be locatable from the doc alone.** A future session has
no idea where anything lives, and `.claude/` is ambiguous — the project has one and
so does your home directory. So project files stay relative (`src/api.ts:42-58`),
user-level files are always written `~/.claude/...`, and anything else is spelled
out in full. This matters most in TODOs that imply a commit: a user-level file
cannot be part of a project commit, and the skill calls that out explicitly instead
of letting a future session discover it the hard way.

## Optional: archive the full transcript

A handoff is a snapshot, so it drops the running narrative on purpose. Occasionally
that narrative is what you need — the exact wording of an instruction, the full text
of an error that scrolled past, why a path was tried and abandoned.

So SAVE mode can also archive the complete session transcript next to the handoff,
as either a verbatim `.jsonl` copy or a rendered Markdown log with a metadata header
(session start/end, total duration, and active work time excluding idle gaps). It is
referenced from the handoff as **read-on-demand**, explicitly not part of normal
resume — otherwise a resuming session loads the entire transcript and you have
defeated the point of having a concise handoff.

This works for both **Claude Code** and **GitHub Copilot** chats. The skill asks
which environment you are in rather than guessing, because a wrong guess archives
the wrong conversation. Copilot needs the more careful handling of the two: its
JSONL is event-sourced, so reconstructing a turn means replaying incremental
splices rather than reading one record, and clarifying-question carousels have to be
extracted separately or the design decisions a handoff most needs vanish silently.

Both converters prefer a deterministic lookup for the active session and fall back
to "most recently modified" only when that fails — and they tell you when they fell
back, since that fallback can pick the wrong file if you have two sessions open in
the same folder.

## Requirements

Nothing for the handoff itself. The optional transcript archive runs Python 3
(standard library only — no pip installs) via the scripts in
[`scripts/`](scripts/).

## The procedure

[`SKILL.md`](SKILL.md) is the full instruction set the agent follows, including the
handoff template, the transcript flow step by step, and the quality checks it runs
before declaring done. It is worth reading before you rely on it — a skill you have
not read is just a longer prompt you do not control.
