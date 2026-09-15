---
name: jira-story
description: "Generate a Jira story document in markdown — Suggested Title, Type, Description, Value Statement, Acceptance Criteria, Definition of Done, Out of Scope, and optional Reference Documents / Proposed Subtasks / Notes for Time Logging. Use this skill whenever the user wants to: write a Jira story, draft a Jira ticket, create a story document, turn a plan or design doc into a Jira story, scope a spike or implementation story, or produce a story-shaped markdown ready to import into Jira. Also trigger when the user mentions 'story document', 'acceptance criteria', 'value statement', or asks to draft a ticket / spike / implementation story for a piece of work, even if they don't say 'Jira'."
---

# Jira Story Generator

Generate a single markdown document describing a Jira story (or spike) with a consistent shape: a suggested title, the story type, a description, a value statement, numbered acceptance criteria, a definition of done, an explicit out-of-scope list, and a few optional sections that depend on the story.

The output is portable to any repo. The skill works in two modes:

- **Source-doc mode (preferred when available):** the user points at an existing plan, design doc, RFC, or evaluation note. The skill reads it and drafts the story from that material, using the interview only to fill gaps and confirm choices.
- **Interview mode (fallback):** no source doc exists. The skill asks a single up-front questionnaire, then drafts.

## When this skill is invoked

Follow these steps in order. Do not skip the up-front questionnaire — even when a source doc is provided, the user still needs to confirm output location, story type, and a few optional sections.

### Step 1 — Identify source material

Before asking anything, scan the current conversation for:

- A plan, design doc, RFC, evaluation note, or feature description the user has already mentioned or you have already read.
- A folder the user keeps such docs in (common shapes: `plans/`, `docs/`, `rfcs/`).
- A nearby existing story file in the same folder. **If you find one, read it before drafting** — not to copy it, but so you understand the conventions the team already uses (heading structure, AC numbering style, what they put in Out of Scope, whether they include subtasks). Conventions vary by team and adopting the local one is part of the value of the skill.

If you find candidates, surface them as part of the questionnaire ("I see you have X and Y open — should I draft from those?"). The user may still say no.

### Step 2 — Ask one consolidated questionnaire

Ask all the following questions in a single message. Group them so the user can answer in one pass. Skip any question that is already answered unambiguously from conversation context — but say which ones you skipped and why, so the user can correct you.

**A. Required**

1. **Working title or one-line summary** — what is the story about? (You will refine the title yourself; this is just the seed.)
2. **Source material** — paths to any plan / design / RFC / evaluation docs the skill should draft from. Say "none, interview me" if there is nothing to read.
3. **Output location** — propose a path based on context (e.g. if the user is in a repo with a `plans/`, `docs/jira/`, or similar folder containing other story docs, suggest that folder with a sensible filename). **Always ask the user to confirm**, even if the suggestion is obvious.

**B. Story-type signals (for inference)**

Do not ask the user to pick the type from a menu. Instead ask one or two open questions whose answers will let you infer the type:

4. **What kind of work is this?** — e.g. "I want to investigate options before committing", "I want to implement X", "I want to fix bug Y", "I want to clean up Z".
5. **Will this story produce production code, or just a document / decision / recommendation?**

You will infer the story type from these answers in Step 3.

**C. Optional sections — ask explicitly**

6. **Subtasks** — does the user want a "Proposed Subtasks" section in the story? (Default: ask; do not assume yes or no based on type.)
7. **Notes for Time Logging** — does the user want this section? (Common for spike stories where time tracking is the deliverable.)
8. **Reference Documents** — get the paths the user wants listed. This section is broader than the source doc: it can include any related material that would help an implementer or reviewer get context — sibling stories, other plans, evaluation notes, **and pointers to relevant source-code files / configs / tests / dashboards / Confluence pages**. If the user gave you a source doc, it goes in here too. Ask the user which references to include; if they say "you decide", look for code files, configs, or sibling docs that the story's AC will touch and propose them.

**D. Anything else**

9. **Stakeholder / audience constraints** — is there a specific Jira project, epic, audience, or convention to honour? (Optional; only relevant if the user volunteers it.)

### Step 3 — Infer and confirm the story type

From the answers to questions 4 and 5, infer one of:

- **Spike / Research** — investigation, scoping, recommendation, decision-record. No production code. The deliverable is a document or a decision.
- **Implementation** — produces production code, config, or build changes. Has verification / testing built in.
- **Bug fix** — narrow correction of incorrect behaviour. Reproduction steps and a fix verification matter more than scoping.
- **Tech debt / Cleanup** — removal, migration, or refactor with no behaviour change visible to end users. Often has a "no functional change" success criterion.
- **Other** — if nothing fits, name what you inferred and explain in one sentence.

Tell the user explicitly: "I'm reading this as a `<type>` story because <one-sentence reason>. OK to proceed, or do you want to recast it?" Wait for confirmation before drafting.

This confirmation is cheap and prevents the most common failure mode: drafting the wrong shape and rewriting the whole document.

### Step 4 — Read the source material

If source docs were provided, read them in full before drafting. Look specifically for:

- The motivation / why-this-matters, which becomes the **Description** and **Value Statement**.
- Concrete deliverables, which become numbered **Acceptance Criteria**.
- Anything explicitly carved out of scope, which becomes **Out of Scope**.
- Sub-decisions, dependencies, follow-up work — these often surface as **Reference Documents** entries or as **Subtasks** items.
- Any "Definition of Done" / "Success Criteria" / "Verification" section — feed it into the **Definition of Done**.

If the source doc is long, skim for headings first, then read the sections that match the story spine.

A long, detailed source doc is a gift — the resulting story should be richer than one drafted from a thin brief. If the source has 50+ pages of design detail, the AC should reflect that detail (specific files, specific config keys, specific verification steps), not flatten it back to generic prose.

### Step 5 — Draft the document

Use the spine below. Sections marked **always** appear in every story; sections marked **optional** appear only when the relevant condition is met.

```
# Jira Story — <Concise Subject>

## Suggested Title              (always)
## Type                          (always)
## Description                   (always)
## Value Statement               (always)
## Acceptance Criteria           (always)
## Verification Evidence         (optional — add once implementation work has begun/completed; one subsection per AC)
## Definition of Done            (always)
## Out of Scope                  (always)
## Reference Documents           (optional — include if the user provided any related docs, or the source material was a plan doc)
## Proposed Subtasks             (optional — include only if the user said yes in question 6)
## Notes for Time Logging        (optional — include only if the user said yes in question 7)
```

**Section guidance:**

- **Suggested Title.** A single concrete sentence in imperative or noun-phrase form. Optionally offer 1–2 alternative phrasings underneath.
- **Type.** One short phrase — e.g. "Implementation story.", "Spike / Research story (no production code changes).", "Bug fix.", "Tech debt / Cleanup.". Match the inferred type.
- **Description.** Two to four short paragraphs. Lead with the current state ("today, X works like this"), then the change being asked for, then any constraint that explains why now. Avoid restating the title.
- **Value Statement.** Use the "**As** ... **we want** ... **so that** ..." form for clarity. Follow with a short bulleted list of expected downstream benefits when the story lands. Keep benefits concrete (a metric, a workflow shortened, a risk eliminated) — not aspirational.
- **Acceptance Criteria.** Numbered list. Each item should be a verifiable outcome, not an implementation step. Aim for 5–12 items; if you have more than 15, the story is probably too big and should be split. Pick a presentation style that fits the story type — e.g. for implementation stories with many discrete deliverables, leading each item with a short bold label and then the criterion makes scanning easier; for spike stories with fewer, narrative-shaped items, plain numbered prose reads better. Use whatever the source doc or sibling stories in the same folder do, and otherwise pick what fits.
- **Verification Evidence.** Omit this section on first-pass creation. Before any implementation exists there is nothing to evidence, and pre-filling it only invites placeholder text — exactly the failure mode the no-placeholders discipline exists to prevent. Add it once you have executed against the story (typically during the close-of-execution re-read in Step 7). Once present, every AC gets its own subsection that answers two questions: how *you* verified the AC during execution, and what the *user* runs to re-verify it cold. Code-review verification cites file paths with line numbers; tooling-verified ACs quote the exact command plus its exit code and the key output; reviewed ACs name the subagent or reviewer. For the user-facing half, give concrete commands or "read this file" pointers written as if the user has zero session context — and where an AC has a runtime/sandbox dimension you could not exercise yourself (common for SDK-integration or UI ACs), name that deferred verification explicitly and point at whichever later story or phase will actually run it. Use this per-AC shape:

  ```markdown
  ### AC N — <short restatement>

  - **Verified by <code review | tooling | command output | subagent review | …>.**
    <The evidence. file:line for code review; command + exit code + key output for tooling; etc.>
  - **User verification:** <steps the user can run, OR "none beyond code review", OR a pointer to the later story that owns the deferred runtime check.>
  ```

  Three worked examples, one per kind of evidence:

  ```markdown
  ### AC 3 — `init` signature and behaviour
  - **Verified by code review.** `src/vendor-connector.ts:45` declares
    `override async init(config: unknown): Promise<InitResult>`; lines 51–72 capture the
    agent identity; line 81 returns `new InitResult({ isSilentLogin: true })`.
  - **User verification:** none beyond code review.

  ### AC 8 — Build gates green
  - **Verified by running the commands from the package root.** `npm run typecheck` —
    exit 0, no diagnostics. `npm run build` — exit 0. `dist/main.js` byte-identical
    before and after (97868 bytes).
  - **User verification:** `npm run typecheck` (must exit 0), `npm run build` (must
    exit 0), then check `dist/main.js` is ~97868 bytes.

  ### AC 11 — Behaviour under a live session
  - **Verified by review only.** The code path is exercised solely inside the vendor
    runtime, which is not available in this environment, so nothing here was executed.
  - **User verification:** deferred — owned by the integration story, which runs the
    connector against a real session. Named here so the gap is visible rather than
    implied.
  ```

  The point of the section is that "verified by code review" is worth nothing unless a
  reader can follow the pointer and confirm it — so make every pointer exact, and where
  you could not verify something yourself, say so and name who will. An AC quietly left
  without evidence reads as verified.
- **Definition of Done.** Short bulleted list. Repeat the bar that has to be crossed — typically "all AC met, code reviewed and merged, docs updated, [type-specific bar]". Keep this distinct from AC: AC describes *what* must be true, DoD describes *the process* by which the team agrees the story is finished.
- **Out of Scope.** Bulleted list of things a reasonable reader might assume are part of this story but aren't. This section earns its keep — it is the cheapest way to prevent scope creep and reviewer confusion. If the source doc has a "Further Considerations" or "Deferred" section, mine it for entries.
- **Reference Documents.** Bulleted list of markdown links / paths with a one-line note on what each contributes. Include the source doc the story was drafted from. Also include relevant code files, configs, tests, dashboards, or sibling docs that the implementer or reviewer would benefit from opening — this section is not just for prose docs. If the user did not name specific references, propose a sensible set based on what the AC touch (and say so in the report so they can prune).
- **Proposed Subtasks.** Numbered subsections (`### Subtask N — <name>`) each with three short blocks: **Summary** (one sentence on what the subtask covers), **Scope** (a bulleted list of the concrete changes / files / actions the subtask touches), and **Done when** (one or two sentences naming the verification, with explicit references to the AC numbers from this story that the subtask satisfies — e.g. "Done when AC 3 and AC 5 pass on a fresh build."). Tying "Done when" to AC numbers is what keeps the subtasks honest: if a subtask doesn't satisfy any AC, it probably shouldn't be in the story. End the section with a brief "Dependencies and ordering" paragraph that says which subtasks block which. Each subtask should be small enough to be reviewed and merged on its own.

  Example shape:

  ```
  ### Subtask 1 — Add path mapping and barrel coverage check

  **Summary:** Prepare the TypeScript build so downstream code can import from `<package>/index`.

  **Scope:**
  - Add a `paths` entry for `<package>/index` → `src/index` in `tsconfig.json`.
  - Audit symbols imported by the test client; add missing exports to `src/index.ts`.

  **Done when:** AC 1 and AC 5 pass — `tsc --noEmit` succeeds with the path mapping in place and every symbol the test client uses is reachable from the barrel.
  ```
- **Notes for Time Logging.** A single short paragraph saying which activities should be logged against this story (typical for spikes: "All scoping, exploration, stakeholder clarification, document drafting, and review activity").

**Voice.** No fixed house style. Read any sibling story in the output folder and follow its voice; if there is none, default to terse, concrete, "why before how", verbs over abstractions, no marketing language. Avoid filler like "in order to", "leverage", "enable", "empower" unless the source doc itself uses them.

**Don't underdeliver on rich source material.** When the source doc is long and detailed, the AC must be specific enough that a reviewer reading only the story can tell whether the implementation matches the design. A 200-line plan should not collapse to 5 generic AC items — pull the concrete deliverables out of the source and surface them.

**The story is a living document.** Drafting it is the start, not the end. As the plan executes the code drifts from the story, and a story that describes code that no longer exists is worse than no story — it sends reviewers to the wrong place. The calling agent is responsible for reconciling the two: update on scope deviations, re-read every AC against merged code before declaring done, and treat the story as part of the review surface. See Step 7 for the full discipline.

### Step 6 — Save and report

Write the document to the path the user confirmed. Then report:

- Path of the file written.
- The inferred story type and the AC count.
- Anything you flagged as a gap or assumption while drafting (so the user can patch it).
- A one-line offer to iterate ("Want me to tighten any section?").

Do not mention the skill itself in the output document. The reader of the story should not see "generated by jira-story".

### Step 7 — Keep the story honest (and stamp it) once work lands

A story written by this skill is correct as of the moment it is written, but it is a **living document**: the implementation diverges from it as the plan executes — files move, methods get renamed, an AC is retired, an out-of-scope item gets pulled in, the assumed merge target shifts. The calling agent owns reconciling the document with reality. Not the user, not a downstream reviewer — you. The "Verified by code review" claim on each AC is only meaningful if the AC text still accurately describes the code a reviewer will open.

Re-open and reconcile the story on three triggers:

1. **Mid-execution scope deviation.** When the plan changes during execution — files moved, methods renamed, an AC retired, an out-of-scope item dragged into scope, a new dependency surfaced — update the affected story sections in the same commit that introduces the deviation (or a tight follow-up). Don't let the story rot until the end; small drifts compound.
2. **At the close of execution, before declaring the work done.** Re-read every AC against the *merged-state* code and tighten any wording that has drifted. Common drift modes to check explicitly: methods listed on the wrong class, async signatures described as "synchronous" (or vice versa), import specifiers / `paths` aliases / module names that the code actually spells differently, merge targets or branch names that have moved, file paths that were renamed. This is also where you populate the `## Verification Evidence` section (see Step 5) — one subsection per AC, with the exact pointers a reviewer can follow.
3. **Before merging the story-closing commit.** Treat the story as part of the review surface. If a reviewer rejects a code change in a way that changes an AC, the AC moves with it.

**Stamp the Jira number — the last action of the close-of-execution pass.** Once the AC re-read is done and Verification Evidence is populated, give the story its real ticket identity:

- **Rename the file** to carry the Jira number as a leading `<KEY-NNN>` prefix, e.g. `PROJ-1234-vendor-connector-skeleton.md`. The prefix makes the story files sort and grep by ticket, which is the whole point of stamping it.
- **Stamp the number at the top of the document** as a leading `**Jira:** <KEY-NNN>` field directly above `## Suggested Title`.
- **If the number is not known at completion** — the ticket has not been cut yet, or you never learned it — **ask the user for it** before renaming and stamping. Do not guess, do not invent a placeholder, do not silently skip. If the user confirms there is genuinely no number yet, leave the descriptive file name in place and note in your report that the Jira number is still pending so it can be stamped later.
- **Fix inbound references after renaming.** Renaming the file breaks every link that pointed at the old name — sibling story docs, plan docs, READMEs, the breakdown doc. After you rename, grep the repo for the old filename and collect the files that reference it. **Present that list to the user and ask for explicit approval before editing them** — do not update them silently, because some references may be intentional (e.g. a changelog recording the old name, or a doc outside the story's scope). On approval, update each link to the new filename; report which files you changed. If the grep finds nothing, say so. Skip this whole step when the file was not renamed (number still pending).

## Edge cases and judgement calls

- **No source doc and a thin description.** If the user has nothing written down and gives only a one-line summary, the AC and DoD will be guesses. Say so explicitly in the report and recommend the user expand the description before sharing the story for review. Do not invent specifics.
- **Source doc covers multiple stories.** Plans and RFCs often span work that should be several stories. If the source doc is clearly larger than one story, point this out and offer to either (a) draft just the slice the user names, or (b) draft a brief breakdown into multiple stories first.
- **User asks for "just the AC".** Drop everything else and produce a numbered AC list. The full story shape is the default, not a requirement.
- **User is updating an existing story.** Read the existing file, identify the sections to change, edit in place. Do not rewrite the whole document if only one section needs work.
- **Sibling story already exists for the same plan.** Flag it before writing. The user may have forgotten, or may want the new draft to supersede or refine it — but they should make that call, not the skill.

## What this skill does not do

- It does not push the story to Jira (no API calls, no CSV export, no clipboard).
- It does not invent acceptance criteria. If the source material is too thin to derive AC, the skill says so and asks for more input rather than fabricating.
- It does not enforce a fixed style guide beyond the spine. Voice follows the source doc or sibling stories.
