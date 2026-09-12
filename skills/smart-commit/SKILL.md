---
name: smart-commit
description: Commit staged and unstaged changes following the branch's established commit message conventions. Use this skill whenever the user asks to commit, wants to commit changes, says "/smart-commit", or mentions committing recent work. Handles staging, message generation, user review, and the final commit.
---

# Smart Commit

Commit all changes since the last commit, following the branch's established first-line format and presenting the message for user review before committing.

## Skill directory

When this skill is triggered, the system message includes a line like `Base directory for this skill: /path/to/smart-commit`. That path is referred to as `SKILL_DIR` throughout these instructions. All references to `references/conventions/` below mean `SKILL_DIR/references/conventions/` — **not** the user's current working directory. Always resolve paths relative to the skill's base directory.

## Flags

- `--fresh` (or `-f`) — Skip preference recall (Step 0) and run through all steps from scratch, prompting at each.
- `--reuse` (or `-r`) — Auto-accept the preference recall prompt in Step 0. Instead of asking the user, the skill proceeds in fast mode. To keep the user aware of the reused choices, the recalled preferences (and any excluded-files warning) are folded into the Step 4 message review, so nothing is hidden from them.

## Workflow

**Execute steps strictly in order.** Complete each step fully — including any user confirmations — before moving to the next. Never combine questions or decisions from multiple steps into a single prompt. For example, do not ask about the commit message format (Step 3) while still confirming the file list (Step 2).

### Step 0: Recall previous preferences

This step provides a shortcut for repeat commits within the same session. If the `--fresh` (or `-f`) flag was passed, skip this step entirely and go to Step 1.

If the `--reuse` (or `-r`) flag was passed, auto-accept the preference recall — skip the Y/N prompt and proceed directly into fast mode (as described under "If the user says Yes" below). Carry forward the recalled preferences and any excluded-files list; they will be shown to the user in Step 4 alongside the proposed commit message, so the user remains aware of the reused choices before confirming the commit.

Look back through the conversation history for a previous invocation of this skill in the current session. If none is found, skip to Step 1.

If a previous invocation exists, extract the preferences that were used:

- **Staging approach** — whether untracked files were included or excluded.
- **Convention + field values** — which convention was used and the values supplied for each field (e.g., `type` = feat, `scope` = auth).
- **Action** — commit only or commit and push.

Run `git status` and `git diff` as **separate Bash calls** (not chained with `&&`) to determine what files currently have changes. On Windows Git Bash, chaining or even single calls can trigger intermittent `add_item` fatal errors — if a call fails, retry it once. Then present the recalled preferences along with the current file list (derived by applying the recalled staging approach to the current status).

If there are files with changes that will **not** be included in the commit (e.g., untracked files excluded by the staging preference, or unstaged files outside the recalled scope), add a prominent warning showing how many files are excluded and list each one. This ensures the user can make an informed decision before confirming.

Example with excluded files:

> **Previous smart-commit preferences found:**
> - Staging: tracked files only (untracked files were excluded)
>   - Files to commit: `src/auth.ts`, `src/login.ts`, `tests/auth.test.ts`
> - Convention: `conventional-commits` (`type` = feat, `scope` = auth)
> - Action: commit and push
>
> **Warning: 2 file(s) with changes will NOT be included in this commit:**
> - `config/settings.json`
> - `docs/notes.md`
>
> Use same preferences? (Y/N)

Example with no excluded files:

> **Previous smart-commit preferences found:**
> - Staging: tracked and untracked files
>   - Files to commit: `src/auth.ts`, `src/new-helper.ts`
> - Convention: `conventional-commits` (`type` = feat, `scope` = auth)
> - Action: commit only
>
> Use same preferences? (Y/N)

**If the user says Yes:**

Execute Steps 1–5 in fast mode — skip all user prompts except for the message review in Step 4 (since the body is freshly generated from the new diff). Specifically:

- **Step 1** — Gather context as normal.
- **Step 2** — Auto-stage files per the recalled staging approach. Show the file list for awareness but do not prompt for confirmation.
- **Step 3** — Build the first line using the recalled convention and field values (no field interview). Generate the body fresh from the current diff.
- **Step 4** — Present the full commit message for review. The user must still confirm here because the body is new.
- **Step 5** — Execute the recalled action (commit or commit-and-push) without asking again.

**If the user says No:**

Proceed to Step 1 and run through all steps normally, prompting at each.

### Step 1: Gather context

Run each of these as a **separate Bash call** (not chained with `&&`). On Windows Git Bash, chaining multiple git commands in a single shell invocation can trigger intermittent `add_item` fatal errors.

```bash
git status
```
```bash
git diff
```
```bash
git diff --cached
```
```bash
git log --oneline -5
```

If there are no changes (no modified, no staged files), tell the user there's nothing to commit and stop.

### Step 2: Stage files

Stage all **modified tracked files** — the files that show up under "Changes not staged for commit" in `git status`. Use `git add <file1> <file2> ...` with explicit file names.

**Untracked files** require judgment based on the current conversation context:

- If there are untracked files that appear related to work done in this chat session (e.g., files you created or that the user asked you to create), list them and ask the user whether they should be staged. Present the list clearly so the user can confirm or decline.
- If there is no session context to determine whether untracked files are related to the current work, inform the user that untracked files exist but will be ignored since they cannot be attributed to the current session's changes.

Never stage files that likely contain secrets (`.env`, credentials, keys) — warn the user if they ask to include such files.

**Ensure there are files to commit.** After processing tracked and untracked files above, check whether there are any files staged for commit (either already staged from Step 1, or newly staged in this step). If the combined set is empty:

1. Present the user with the full picture from `git status` — list any untracked files, unstaged changes, or other details that might help them decide what to include.
2. Ask the user which files, if any, should be staged.
3. If the user declines to stage anything (or there are genuinely no files available), stop and tell the user: "There are no files to commit. Stopping." Do not proceed to Step 3.

**Confirm the final file list.** Once there is at least one file to commit, present the complete list of files that will be included in the commit (both previously staged and newly staged) and ask the user to confirm before moving on. If the user wants to add or remove files, adjust accordingly and re-confirm.

### Step 3: Build the commit message

The commit message has two parts:

**First line:**

The first line can come from four sources: the most recent commit, a saved convention, the last convention used in this session, or a new convention the user defines on the spot. Saved conventions live in `SKILL_DIR/references/conventions/` as one Markdown file per convention (YAML frontmatter with `name` + `description`, then `## Format`, `## Example`, `## Fields` sections). They persist across sessions so the user doesn't re-describe their format every run.

1. **Gather the options:**
   - Read the most recent commit first line via `git log --oneline -1` (strip the leading short hash).
   - List files in `SKILL_DIR/references/conventions/*.md`. For each, read the frontmatter to get `name` and `description`.
   - Check the conversation history for a previous smart-commit invocation that used a convention. If found, note which convention and field values were used.

2. **Ask the user which source to use.** Adapt the question to what's available:
   - **If saved conventions exist**, present up to four choices:
     - (a) Use the most recent commit's first line (show it).
     - (b) Use a saved convention — list each as `<name> — <description>`, numbered for easy selection.
     - (c) Define a new convention.
     - (d) Last used convention — only show this option if a convention was used in a previous smart-commit invocation this session. Show the convention name and field values, e.g. `Last used: conventional-commits (type = feat, scope = skill)`.
   - **If no saved conventions exist yet**, present two choices: (a) use most recent, or (b) define a new convention. Include (d) if a convention was used earlier in the session.
   - **If there is no prior commit on the branch** (fresh repo), skip option (a).

3. **If the user picks "use most recent"** → use that line verbatim as the first line.

4. **If the user picks a saved convention:**
   - Read the full convention file.
   - For each field listed under `## Fields`, suggest a value based on the changes since the last commit (e.g., infer `type` from the nature of the diff, `scope` from the area of code affected). Present the suggestion and let the user accept or provide a different value. Respect any per-field rules noted in the convention (e.g., auto-prefix behaviour).
   - Assemble the first line by substituting the values into the pattern shown in `## Format`.

5. **If the user picks "last used convention":**
   - Retrieve the convention name and field values from the previous smart-commit invocation in this session.
   - Read the full convention file.
   - For each field, suggest a value based on the current changes (same as step 4). Pre-fill with the last-used value as a secondary reference if the diff-based suggestion is unclear.
   - Assemble the first line by substituting the values into the pattern shown in `## Format`.

6. **If the user picks "define a new convention":**
   a. Ask for a **name** (required). Slugify it for the filename (lowercase, spaces/punctuation → hyphens). If `SKILL_DIR/references/conventions/<slug>.md` already exists, tell the user and ask for a different name.
   b. Ask for a **one-line description** — this is what future runs show in the menu, so it should be distinctive.
   c. Ask for an **example first line** (or a template with angle-bracket placeholders like `<version>`). From this, infer the `## Format` pattern and the list of `## Fields`.
   d. Echo back the inferred `## Format`, `## Example`, and `## Fields` and ask the user to confirm or correct. This prevents saving a misunderstood format.
   e. Once confirmed, write `SKILL_DIR/references/conventions/<slug>.md` using the frontmatter + sections layout described above.
   f. Then fall through to step 4's field interview (with diff-based suggestions) to build the first line for this commit.

**Body (after a blank line):** Write a concise summary of what changed, focusing on the "why" rather than listing every file. Keep it to 2-5 sentences. Mention key behavioral changes, new features, or bug fixes.

### Step 4: Present for review

Show the full commit message to the user and ask them to approve or request changes. Do NOT commit until the user confirms.

**If the `--reuse` flag was used in Step 0**, prepend the recalled preferences summary (and any excluded-files warning) above the proposed message, so the user can see the choices being reused before confirming. Example:

```
Reusing previous preferences:
- Staging: tracked files only (untracked files were excluded)
  - Files to commit: src/auth.ts, src/login.ts
- Convention: conventional-commits (type = feat, scope = auth)
- Action: commit and push

Warning: 2 file(s) with changes will NOT be included in this commit:
- config/settings.json
- docs/notes.md

Proposed commit message:

feat(auth): add JWT login helper

<body text here>
```

**Otherwise**, format it clearly so the user can read it:

```
Proposed commit message:

fix(worker): correct null pointer on empty queue

<body text here>
```

Then ask: "Does this look good?"

- If the user says **Yes** (or **Y**), proceed to Step 5.
- If the user says **No** (or **N**), ask what changes they'd like, apply them, and present the updated message for another round of review.

### Step 5: Commit

Once the commit message is approved, ask the user to choose:

1. **Commit** — commit only
2. **Commit and push** — commit and push to remote

Then create the commit. Pass the message as a multi-line double-quoted string — this works reliably across all platforms including Windows Git Bash, where HEREDOC syntax (`$(cat <<'EOF' ... EOF)`) crashes the shell process.

```bash
git commit -m "First line of commit message

Body text here."
```

If the commit message body contains double quotes, escape them with `\"`.

After committing, run `git status` to confirm success and report the commit hash to the user.

If the user chose **Commit and push**, run `git push` (or `git push -u origin <branch>` if the branch has no upstream set).

If a pre-commit hook fails, investigate the issue, fix it, re-stage, and create a NEW commit (do not amend).

## Important

- Never push to remote without asking the user first.
- Never amend a previous commit unless the user explicitly asks.
- Never use `git add -A` or `git add .`.
- Never skip hooks (`--no-verify`).
- If the user requests changes to the message, apply them and show the updated message for another round of review.
