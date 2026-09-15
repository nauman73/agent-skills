# jira-story

Turn a plan, design doc or a short brief into one story-shaped markdown document, and keep
it true to the code once the work lands.

## The problem

A story written from a thin brief is guesswork, and a story written from a 200-line plan
usually collapses that plan into five generic acceptance criteria — throwing away the
detail that made the plan worth writing. Both failures look the same on the board: a
ticket nobody can review against, because it never said anything a reviewer could check.

The second problem arrives later. The story was accurate the day it was written, and then
the implementation moved. Files got renamed, an AC was dropped, something out of scope got
pulled in. A story describing code that no longer exists is worse than no story at all —
it sends reviewers to the wrong place, with confidence.

## What it does

Produces a single markdown file with a consistent spine: Suggested Title, Type,
Description, Value Statement, numbered Acceptance Criteria, Definition of Done and Out of
Scope, plus Reference Documents, Proposed Subtasks and Notes for Time Logging when they
apply.

It works in two modes. Given a plan, design doc or RFC it drafts from that material and
uses questions only to fill gaps. Given nothing, it asks one consolidated questionnaire
and drafts from the answers.

The story type — spike, implementation, bug fix, tech debt — is inferred from what the
work produces rather than picked from a menu, then stated back for confirmation before
drafting. Confirming a one-word inference is cheap; rewriting a whole document in the
wrong shape is not.

## Three design choices worth knowing

**It adopts the local conventions rather than imposing its own.** Before drafting it looks
for a sibling story in the same folder and reads it — for heading structure, AC numbering,
what that team puts in Out of Scope, whether stories carry subtasks. Teams differ, and a
story that looks unlike its neighbours gets read as an outsider's.

**It will not invent acceptance criteria.** If the source material is too thin to derive
them, it says so and asks for more rather than producing plausible filler. Invented AC are
worse than missing ones: they look verifiable, so nobody checks whether they came from
anywhere.

**The story is treated as a living document.** Drafting it is the start. The skill defines
when to reconcile it with reality — on a scope deviation mid-execution, at the close of
execution before declaring the work done, and before merging the story-closing commit —
and what drift to look for each time. It also defines a `Verification Evidence` section,
deliberately absent on first draft because there is nothing to evidence yet, in which
every AC later gets a pointer exact enough for a reviewer to follow: a file and line, or a
command with its exit code. Where something could not be verified in the session that did
the work, it is recorded as deferred and the story that will verify it is named. An AC
left quietly without evidence reads as verified.

## What it does not do

It does not talk to Jira. There is no API call, no CSV export, no clipboard — the output
is a markdown file you paste or import yourself. It does not enforce a house style beyond
the spine, and it does not mention itself in the document it produces.

## Requirements and portability

Markdown and a conversation, so it runs on any agent that can read a skill folder. The
only Claude Code affinity is that the up-front questionnaire is nicer as a set of buttons
than as prose; elsewhere it degrades to a numbered list of questions in one message, which
is what the skill asks for anyway.
