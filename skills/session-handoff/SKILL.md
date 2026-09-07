---
name: session-handoff
description: Save or resume from a structured task-state snapshot under the project's .claude/ folder so work can carry across cleared/compacted Claude Code or GitHub Copilot sessions. Has two modes. SAVE mode — use when the user says "save the session", "save context", "create a handoff", "I need to /clear", "compact is coming", "snapshot this task", "checkpoint this work", "update the handoff", "refresh the snapshot". RESUME mode — use when the user says "resume from the handoff", "pick up where we left off", "continue from .claude/handoff-...", "read the handoff and continue", "load the handoff", or opens a fresh session pointing at a `.claude/handoff-*.md` file. Optionally archives the full session transcript (Claude Code or GitHub Copilot chat) as a readable Markdown or raw JSONL file alongside the handoff. Do NOT use this for general memory/preferences (use persistent memory) or recurring scheduled work (use a scheduled-task mechanism).
---

# session-handoff

Capture the current task's state into a self-contained markdown doc that a future, context-less session can read to pick up exactly where this one left off.

## Why this exists

Agent sessions get cleared, compacted, or run out of context. The assistant's persistent memory captures durable facts about the user and project, but not in-flight task state. This skill writes a focused, time-stamped handoff for one specific task — goal, progress, next step, open questions — so a fresh agent can resume without the user re-explaining.

The skill runs the same way whether the live session is **Claude Code** or **GitHub Copilot** (which can now run Claude Code skills directly). The handoff save/resume logic is identical in both — it summarizes the session you are currently in. The one place the two environments differ is the optional transcript archive, because each stores its session JSONL in a different location and format; that step asks you which environment you are in.

## Two modes

This skill has two modes. Decide which one applies from the user's phrasing before doing anything else.

**SAVE mode** — write or update a handoff doc. Trigger when the user signals they want to preserve current task state:
- "save this session" / "save context" / "snapshot this"
- "I'm about to /clear" / "compact is going to hit" / "context is filling up"
- "checkpoint this work" / "I'll resume tomorrow" / "create a handoff"
- "update the handoff" / "refresh the snapshot" (update an existing doc)

**RESUME mode** — load an existing handoff doc and prepare to continue. Trigger when the user signals they want to pick up prior work:
- "resume from the handoff" / "pick up where we left off"
- "read .claude/handoff-<slug>.md and continue"
- "load the handoff" / "continue from the snapshot"
- a fresh session that opens with a reference to a `.claude/handoff-*.md` path

If the user is just asking you to remember a preference or fact, that is the assistant's persistent memory's job, not this. If the user wants a recurring background task, that is a scheduled-task mechanism's job. This skill is specifically for "I want a future session to continue this exact task."

These two modes are the entire scope. Copilot support is **not** a third mode — it is the same SAVE and RESUME flows, which work identically inside a GitHub Copilot session (Copilot can run Claude Code skills). The only environment-dependent part is the optional transcript archive in SAVE mode, which is covered in its own section below.

## Where handoffs live

Write to `.claude/handoff-<slug>.md` relative to the project root. The project-local `.claude/` folder is the canonical place for project-scoped Claude artifacts (settings, allowlists, and now handoffs and their optional transcripts) — if it doesn't exist, create it. Note this is the *project's* `.claude/`, not the user-level `~/.claude/`; the two are distinct (see "Path qualification" below).

Use `.claude/` for both Claude Code and GitHub Copilot sessions. It is this skill's artifact folder regardless of which environment runs it; keeping one predictable location means RESUME never has to guess where a handoff lives, and the handoff flow never has to know which environment produced it.

The slug should be short, kebab-case, and describe the task — `auth-refresh-bug`, `phase-7-config`, `users-feature-cleanup`. Infer it from the conversation; only ask the user if you genuinely cannot tell what the task is about.

## Path qualification — every referenced file must be locatable

A handoff is read by a future session with no memory of where files live. A bare path like `.claude/foo.md` is ambiguous: is it under the project root, the user-level Claude folder, somewhere else? The risk is especially sharp now that handoffs live in the project's `.claude/` — the name is the same as the user-level `~/.claude/` and the two are easy to confuse. If the future session searches the wrong root, it wastes turns and may even silently work on the wrong file. Eliminate that ambiguity by qualifying every path you write.

Use these conventions consistently throughout the handoff:

- **Project files** — write project-relative paths as-is: `frontend/src/lib/api.ts`, `.claude/handoff-users-feature.md`, `backend/app/models/user.py`. These are the default and need no decoration; the project root is implied by `git status` / `git log` checks. A bare `.claude/...` always means the project's `.claude/`, never the user-level one.
- **User-level Claude files** (skills, settings, memory under `~/.claude/`) — always prefix with `~/.claude/`: `~/.claude/skills/session-handoff/SKILL.md`, `~/.claude/CLAUDE.md`, `~/.claude/projects/<encoded-cwd>/...`. Never write these as bare `.claude/...` — that collides with the project's own `.claude/` directory and is the most likely source of confusion in this new layout.
- **Absolute paths** (anything outside both roots — system configs, other repos on the machine, network mounts, a Copilot chat JSONL under `%APPDATA%\Code\User\workspaceStorage\...`) — spell out the full path: `C:\Users\<user>\Documents\notes\foo.md`, `/etc/nginx/nginx.conf`, `D:\Work\Other\sibling-repo\src\bar.py`.

**On first mention of any non-project path in the doc, add a brief parenthetical so the reader doesn't have to deduce the location.** Example:

> Related skill: `~/.claude/skills/session-handoff/SKILL.md` (user-level Claude skills folder, not the project `.claude/`).

Subsequent mentions of the same path can drop the parenthetical — the reader already knows where it lives.

This matters most in the **Pending TODOs** and **How to resume** sections, where a future agent will act on the path directly. A path that turns out to live outside the repo silently breaks "commit and push" instructions, since user-level files cannot be part of a project commit. If a TODO involves a path outside the project root, call that out explicitly: *"Note: `~/.claude/skills/foo/SKILL.md` is user-level (outside the repo) and is NOT part of this commit."*

## SAVE mode — what to write

The handoff must be **self-contained**. The future session has zero memory of this conversation. Don't write "continue what we were doing" — write the goal explicitly. Don't write "the file we edited" — write the path. Don't reference earlier turns.

Use this exact template:

```markdown
# Handoff: <Task title>

**Created:** <YYYY-MM-DD HH:MM> · **Branch:** <git branch> · **Status:** <in-progress | blocked | ready-for-review>

## Goal
<1–3 sentences. What is the user trying to accomplish? Why does it matter? Be concrete enough that someone with no context understands the objective.>

## Current state
<What has been done so far. Bullet points. Reference exact files and line numbers where relevant, e.g. `frontend/src/lib/api.ts:42-58`. Qualify any path that is not project-relative (see "Path qualification" above). Mention commits if any were made.>

## Next step
<The single next concrete action to take. Be specific: which file, which function, what change. If there are multiple parallel threads, list them in priority order.>

## Pending TODOs
- [ ] <item>
- [ ] <item>

## Key decisions & context
<Non-obvious decisions made in this session that aren't captured in the code or git log. Why a particular approach was chosen, what was ruled out, what constraints apply. Skip this section if there's nothing surprising.>

## Open questions / blockers
<Anything waiting on the user, a teammate, an external system, or an unresolved design question. If nothing, write "None.">

## How to resume
1. Read this file in full.
2. `git status` and `git log -5` to confirm branch state matches "Branch" above.
3. <Any project-specific setup: env vars to set, services to start, migrations to run>
4. Begin from "Next step".
```

End your reply to the user with a single line:

> To resume in a new session: read `.claude/handoff-<slug>.md`

That line is the user's copy-paste prompt for the fresh session.

## RESUME mode — load and wait

When the user wants to pick up prior work, do NOT immediately start coding. The point of the handoff is shared situational awareness — confirm both sides have it before acting.

Steps, in order:

1. **Find the doc.** If the user named a path, use it. If they said "the handoff" without specifying, run `Glob .claude/handoff-*.md` and pick the most recently modified one — but if there's more than one match and the right one isn't obvious, ask the user which. If `.claude/` has no matches, also try the legacy location `Glob plans/handoff-*.md` for handoffs written before this skill moved its default location; if you find one there, note the legacy location to the user when you echo back the summary so they know to expect future handoffs in `.claude/`.
2. **Read the doc in full** with the Read tool. Do not skim or read partial ranges.
3. **Verify the working state matches.** Run `git status` and `git log -5 --oneline`. Compare against the "Branch" line in the handoff. If they don't match (different branch, missing modified files, advanced commits), surface the discrepancy to the user before proceeding — do not silently reconcile.
4. **Echo back a tight summary** to the user: 2–4 lines covering the goal, the next step from the doc, and any open question or blocker. This proves you read it and gives the user a chance to correct stale info.
5. **Stop and wait for explicit instruction.** Do not begin "Next step" automatically. End with something like *"Ready to continue from `<next-step>` — say the word and I'll start, or tell me to do something else."*

Why wait: the handoff was written at one point in time. Things may have changed externally (the user may have already done part of the work, decided to abandon the task, or want to take a different angle). Auto-executing the next step risks redoing work or going in the wrong direction. The cost of one short confirmation turn is much lower than the cost of unwanted edits.

If `git status` shows uncommitted changes the handoff did not mention, flag them — they may be the user's in-progress work from another session and must not be overwritten.

## SAVE mode — optionally save the full session transcript

A handoff is a *snapshot* — it intentionally drops the running narrative. But sometimes a future session (or the user) really does need the conversational detail: *why* a particular path was tried and abandoned, the exact wording of a user instruction, an error message that scrolled past. Saving the full transcript alongside the handoff gives the future session an escape hatch for those cases — without bloating the handoff itself.

After the handoff doc is written and **before** you print the "To resume…" line, run this short flow.

### Step 1 — ask the user

Use `AskUserQuestion` with a single question:

> **Save the full session transcript alongside this handoff?**
> A future session can refer to it if the handoff alone isn't enough.

Options:
- **Yes, save it** — proceed to Step 2.
- **No, skip it** — finish the save and print the "To resume…" line; do not add a transcript reference to the handoff. Stop here.

The wording "alongside" matters — the user should understand the transcript is *supplementary*, not a replacement for the handoff.

### Step 1.5 — ask which environment this session is

The transcript lives in a different place and format depending on whether this is a **Claude Code** session or a **GitHub Copilot** chat. We do not auto-detect this — detection is not reliable enough to silently act on, and a wrong guess archives the wrong conversation. Ask, and act on the answer.

Use `AskUserQuestion`:

> **Which environment is this session?**
> This determines where the session transcript is read from.

Options:
- **Claude Code** — transcript comes from `~/.claude/projects/<encoded-cwd>/<session-id>.jsonl`.
- **GitHub Copilot** — transcript comes from VS Code's `workspaceStorage/<hash>/chatSessions/<session-id>.jsonl`.

This is the only question that branches the flow. The format choice (Step 2) and the destination (Step 3) are the same regardless of the answer; only Step 4 (locate) and Step 5 (produce) differ. Remember the answer — it selects the discovery method and the converter in those two steps.

### Step 2 — ask which format to save in

The native transcript on disk is JSONL (one event per line, exactly what the agent wrote). That is fully lossless — every tool call, tool result, thinking block, system reminder is preserved — but it is awkward to skim. A rendered Markdown view is easier for a human to read and scan but folds/omits some structural detail. Both are legitimate; the right choice depends on whether the future consumer is a person browsing or another agent loading specific detail.

Use `AskUserQuestion`:

> **Save the transcript in which format?**

Options:
- **`.jsonl` (raw copy)** — verbatim copy of the session's native JSONL. Lossless, machine-readable, awkward to skim.
- **`.md` (human-readable)** — rendered Markdown conversation log. Easier to scan, slightly lossy on structural detail.

Note on the Copilot raw form: Copilot's JSONL is event-sourced (incremental patches rather than one self-contained record per turn), so a raw `.jsonl` copy is faithful but very hard to read by hand — the `.md` rendering is usually the better choice for a Copilot session unless a machine consumer specifically needs the raw events.

Remember the choice — it determines both the file extension you propose in Step 3 and the action you take in Step 5.

### Step 3 — propose default filename and location

Default filename: `transcript-<handoff-slug>-<YYYY-MM-DD-HHMM>.<ext>` — same `<slug>` as the handoff doc, so the pair is obvious. Use `.jsonl` or `.md` depending on the Step 2 choice.

Default location: `<project-root>/.claude/` — the same project-local Claude folder where the handoff lives. The two files sit side by side (`.claude/handoff-<slug>.md` and `.claude/transcript-<slug>-<timestamp>.<ext>`); the differing filename prefixes are what distinguish primary doc from reference material. Create the folder if it does not exist.

Use a second `AskUserQuestion` so the user can accept or change both:

> **Save transcript as:**
> Default: `.claude/transcript-<slug>-<YYYY-MM-DD-HHMM>.<ext>`

Options:
- **Use default path** — proceed with the defaults.
- **Change filename only** — keep `.claude/`, take a new filename from the user (free-text "Other"). If the user supplies a filename without an extension, append the one matching the Step 2 format choice.
- **Change location only** — keep the default filename, take a new directory from the user.
- **Change both** — take both from the user.

If the user picks any "change" option, follow up with a plain question to collect the new value(s). Validate that the directory exists or can be created; do not silently fall back to the default if the user-supplied path is unusable — surface the problem and re-ask.

### Step 4 — locate the current session's transcript file

This step branches on the Step 1.5 answer. In both environments, prefer the **deterministic** mechanism and fall back to recency only if it yields nothing — and tell the user which method was used, because the fallback can be wrong.

#### Claude Code

Claude Code stores each session as `~/.claude/projects/<encoded-cwd>/<session-id>.jsonl`.

**Deterministic (primary):** Claude Code sets the environment variable `CLAUDE_CODE_SESSION_ID` to the current session's id — set **per session**, so even two sessions open in the same folder each see their own. The transcript is then exactly:

```bash
echo "$CLAUDE_CODE_SESSION_ID"
# -> ~/.claude/projects/<encoded-cwd>/$CLAUDE_CODE_SESSION_ID.jsonl
```

The `<encoded-cwd>` is the working directory with **both the drive-letter colon and every path separator replaced by `-`** — so `C:\Users\foo\src\bar` becomes `C--Users-foo-src-bar` (note the **double** dash from `C:` + `\`). A common past bug was dropping the colon (yielding a single dash, `C-Users-...`), which points at a directory that does not exist on Windows. If unsure of the exact encoding, just list `~/.claude/projects/` and match the folder, or locate the file by its known session-id filename across the projects tree.

**Recency (fallback):** if `CLAUDE_CODE_SESSION_ID` is unset (older Claude Code), use the most-recently-modified `*.jsonl` in the project dir:

```powershell
$projDir = "$env:USERPROFILE\.claude\projects\<encoded-cwd>"
Get-ChildItem $projDir -Filter *.jsonl | Sort-Object LastWriteTime -Descending | Select-Object -First 1
```

…or on POSIX, `ls -t ~/.claude/projects/<encoded-cwd>/*.jsonl | head -1`. This is reliable for a single session (the active session is the one being written) but can pick the wrong file if **two sessions are open in the same folder** and the other one was just touched — so warn the user when you fall back to it.

#### GitHub Copilot

Copilot Chat stores each session as `%APPDATA%\Code\User\workspaceStorage\<hash>\chatSessions\<session-id>.jsonl`. The `<hash>` is opaque, and the active session id is not exposed via an env var — both must be resolved from VS Code's own state. The bundled `copilot_discover.py` does all of this; do not hand-roll it.

```powershell
python "$env:USERPROFILE\.claude\skills\session-handoff\scripts\copilot_discover.py" --project-root "<project-root>"
```

…or on POSIX, `python ~/.claude/skills/session-handoff/scripts/copilot_discover.py --project-root <project-root>`. It prints JSON with `path`, `session_id`, `title`, `method`, and `workspace_hash`. How it works (and what to surface to the user):

1. **Workspace hash** — it scans every `workspaceStorage/*/workspace.json` and matches the recorded `folder` URI against `--project-root`. Deterministic.
2. **Active session (primary, `method: "active-pointer"`)** — it reads `state.vscdb` (read-only, lock-safe even while VS Code is running) for the focused chat under `memento/interactive-session-view-copilot` and base64-decodes the session id. Exact, even with several chats open.
3. **Recency (fallback, `method: "recency-fallback"`)** — most-recently-modified `chatSessions/*.jsonl`. Same concurrent-session caveat as Claude Code; if `method` comes back as the fallback, warn the user.

To let the user pick a *past* (not currently-focused) Copilot chat, run `copilot_discover.py --project-root <root> --list` to print all sessions (id, title, date, size, which is active) and confirm the target with them.

**Live-session caveat (both environments, but pronounced in Copilot):** the transcript of the session you are *currently in* may not be fully flushed to disk yet. In Copilot specifically, per-turn completion data (`completedAt`/`elapsedMs`) is written late, so a just-started session often has **no timing records** — the converter reports active work honestly as `≥0s` with upper bounds rather than a fabricated number. The conversation text is still captured correctly; only the timing header is mostly bounds. This is expected, not an error.

In either environment, if you cannot find a transcript file, tell the user honestly — do not invent one or save a partial reconstruction.

### Step 5 — produce the transcript at the destination

The action depends on the Step 2 format choice and the Step 1.5 environment. All four bundled scripts require only the Python standard library — no extra installs.

**If `.jsonl` was chosen** (either environment) — copy the located source file to the destination verbatim (PowerShell `Copy-Item`, or `cp` on POSIX). Do not transform or summarize: the value of the raw form is its fidelity, and any future reader expects the native on-disk format.

**If `.md` was chosen — Claude Code** — invoke `jsonl_to_md.py`, which walks the JSONL deterministically and renders a readable Markdown log (rich metadata header) without spending Claude turns or context:

```powershell
python "$env:USERPROFILE\.claude\skills\session-handoff\scripts\jsonl_to_md.py" `
  "<source-jsonl-path>" "<destination-md-path>" `
  --session-name "<session name>" `
  --participants "<User Name> (<email>) · Claude Code (<model>, <context window>)" `
  --note "<one-line session-specific narrative>"
```

Its header table has: **Session name, Date, Participants, JSONL source, Session start, Session end, Total duration, Active work**. The calculation component `scripts/session_stats.py` derives every deterministic field (date, start/end, total, active, idle) from the JSONL; you supply only what the JSONL cannot know, via flags:

- `--session-name` — the session's name (omit if unnamed; header then shows `_(unnamed session)_`).
- `--participants` — human (name + email; email is in `~/.claude/CLAUDE.md` if set) and assistant (model + context window, e.g. `Opus 4.8, 1M context`). If omitted, falls back to `Claude Code (<model-id from JSONL>)`.
- `--note` — one line of session-specific narrative appended to the active-work sentence. Optional.

Its **active-work definition**: a *turn* starts at each human user prompt; its active span runs to the last assistant timestamp before the next human prompt; active work sums those spans, excluding idle gaps. Wall-clock **Total duration** can be far larger when a session is left open — expected, which is why both are shown. Run `session_stats.py <jsonl> --json` on its own to inspect the numbers first.

**If `.md` was chosen — GitHub Copilot** — invoke `copilot_jsonl_to_md.py`. Copilot's JSONL is a different, event-sourced format, so it has its own converter:

```powershell
python "$env:USERPROFILE\.claude\skills\session-handoff\scripts\copilot_jsonl_to_md.py" `
  "<source-jsonl-path>" "<destination-md-path>" `
  --session-name "<override title — optional>" `
  --participants "<optional participants row>" `
  --note "<one-line session-specific narrative — optional>"
```

What it does that the Claude Code converter does not have to:

- **Reconstructs each turn's full response** by accumulating appended request objects and replaying the incremental `i`-indexed response splices. Reading only the first append would drop most of the assistant's text — this is essential, not optional.
- **Timing from `elapsedMs`/`completedAt`** (millisecond epochs, not ISO timestamps). Turns whose completion event was never flushed are **flagged with an upper bound** (gap to the next turn) rather than dropped, and active work is shown as a `≥` floor with an `(n/total turns)` count. As noted in Step 4, a currently-open session often has *no* timing yet — that is handled gracefully, not an error.
- **Title** defaults to the first `customTitle` in the JSONL (VS Code's descriptive auto-title); `--session-name` overrides it. The header table has **Session ID, Source, Model, Session start, Session end, Total duration, Active work, Idle/think, Turns, JSONL source** (and a Participants row only if you pass `--participants`).
- **Extracts interactive Q&A.** When the agent asks clarifying questions, Copilot stores them as a `questionCarousel` response item (a sibling of the text, *not* part of the `vscode_askQuestions` tool call) with the user's picked/freeform answers in its `data` map. These are rendered inline as a "Clarifying questions asked" block where they occurred — without it, the design decisions a handoff most needs would silently vanish.
- Output is normalized to clean LF line endings (Copilot stores user text with embedded CRLF).

All flags on both converters are optional; with none, each still emits a valid header.

If any copy or conversion fails (path too long, permission denied, disk full, script error), report the exact error to the user and ask how to proceed. Do not write a misleading reference into the handoff for a file that does not actually exist or is empty.

### Step 6 — reference the transcript in the handoff

Open the handoff doc and add a new section just before "How to resume":

```markdown
## Full session transcript (reference only)

The complete conversation transcript for the session that produced this handoff is saved at:

`<relative path to the transcript file, e.g. .claude/transcript-<slug>-<YYYY-MM-DD-HHMM>.jsonl>`

**Consult this transcript only when necessary.** The handoff above is the intended source of truth; the transcript is here for cases where you need the exact wording of a prior instruction, the full text of an error, or the reasoning behind a path that was tried and abandoned. Do not load or read it as part of normal resume — read it only if a specific question cannot be answered from the handoff alone.
```

The "reference only" framing matters. Without it, a resuming session may try to read the entire transcript as part of resume setup, which defeats the point of having a concise handoff. State explicitly that the transcript is on-demand, not default reading.

### Step 7 — finish

Print the standard "To resume…" line as before. The user now has both the handoff (primary) and the transcript (fallback) saved together.

## SAVE mode — update an existing doc

If a handoff for this task already exists (check `.claude/handoff-<slug>.md` first; also check the legacy `plans/handoff-<slug>.md` in case the file predates the move to `.claude/`), update it instead of creating a new one. If you find a legacy file in `plans/`, move it to `.claude/` as part of the update so the layout stays consistent:
- Bump the `Created:` line to `Updated: <new timestamp>` (keep the original Created date on a separate line).
- Rewrite "Current state" and "Next step" to reflect now, not history. The future session does not need a changelog of how the task evolved — it needs an accurate snapshot of where things stand.
- Carry forward "Key decisions" entries that still apply; drop ones that have been superseded.

## Quality checks before finishing

Before declaring done, re-read the doc with this question: *if I handed this to a colleague who had never seen this codebase, could they pick up the next step?* If the answer is no, fix it. Common gaps:
- Vague goal ("fix the bug" — which bug?)
- Missing file paths
- **Ambiguous file paths** — every path should be locatable from the doc alone. Bare `.claude/handoff-foo.md` or `src/foo.ts` is fine for project files; user-level Claude files must be written as `~/.claude/skills/foo/SKILL.md`; absolute paths must be fully spelled out. The collision between project `.claude/` and user `~/.claude/` is the trap to watch for — never write a bare `.claude/...` when you mean the user-level folder. The first mention of any non-project path should carry a brief parenthetical explaining where it lives. Watch especially for items in **Pending TODOs** that imply a commit — a user-level path silently can't be part of a project commit.
- "Next step" that assumes context from the conversation
- TODOs phrased as reminders to self instead of actionable items

## What NOT to include

- Full conversation transcripts or running commentary inlined into the handoff body — the doc is a snapshot, not a log. (Saving the transcript as a *separate* referenced file under `.claude/` is fine and is covered by "SAVE mode — optionally save the full session transcript" above.)
- Information already in the project's AI-instructions file (`CLAUDE.md` and/or `.github/copilot-instructions.md`), README, or obvious from the code — link/reference instead.
- User preferences or durable facts — those belong in the assistant's persistent memory.
- Secrets, tokens, or credentials — even if they came up in the session.
