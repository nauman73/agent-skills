#!/usr/bin/env python3
"""Convert a Claude Code session JSONL transcript into a human-readable Markdown file.

The JSONL under ~/.claude/projects/<encoded-cwd>/<session-id>.jsonl is one event per
line — user turns, assistant turns, tool calls, tool results, thinking blocks, system
reminders, etc. This script walks the file in order and renders each turn as a Markdown
section, folding bulky content (tool calls, tool results, thinking) inside <details>
tags so the doc stays scannable.

The header is a metadata table (session name, date, participants, JSONL source,
start/end, total duration, active work) plus an active-work blockquote. Timing
is computed by the bundled `session_stats.py`; the non-computable fields
(session name, participants, narrative note) are passed in as flags.

Usage:
    python jsonl_to_md.py <input.jsonl> <output.md> \
        [--session-name NAME] [--participants STR] [--note STR]

Exit codes:
    0 = success
    1 = bad args / source missing / write failed
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# session_stats lives next to this script; its directory is on sys.path when this
# file is run directly. It provides the timing calculation used in the header.
from session_stats import compute


def _stringify(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict) and "text" in item:
                parts.append(str(item["text"]))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    if value is None:
        return ""
    return str(value)


def render_content_block(block: dict) -> str:
    btype = block.get("type")
    if btype == "text":
        return _stringify(block.get("text", ""))
    if btype == "thinking":
        text = _stringify(block.get("thinking", ""))
        return f"<details><summary>Thinking</summary>\n\n{text}\n\n</details>"
    if btype == "tool_use":
        name = block.get("name", "?")
        try:
            inp = json.dumps(block.get("input", {}), indent=2, ensure_ascii=False)
        except (TypeError, ValueError):
            inp = str(block.get("input", ""))
        return (
            f"<details><summary>Tool call: <code>{name}</code></summary>\n\n"
            f"```json\n{inp}\n```\n\n</details>"
        )
    if btype == "tool_result":
        content = _stringify(block.get("content", ""))
        return (
            f"<details><summary>Tool result</summary>\n\n"
            f"```\n{content}\n```\n\n</details>"
        )
    return ""


def render_entry(entry: dict, idx: int) -> str | None:
    etype = entry.get("type")
    if etype not in ("user", "assistant"):
        return None
    msg = entry.get("message") or {}
    role = (msg.get("role") or etype).capitalize()
    raw_content = msg.get("content", "")
    if isinstance(raw_content, str):
        body = raw_content
    elif isinstance(raw_content, list):
        rendered = [render_content_block(b) for b in raw_content if isinstance(b, dict)]
        body = "\n\n".join(part for part in rendered if part.strip())
    else:
        body = ""
    if not body.strip():
        return None
    return f"## {role} — entry {idx}\n\n{body}\n"


def build_header(stats, session_name: str | None, participants: str | None,
                 note: str | None) -> list[str]:
    """Build the rich metadata header (table + active-work blockquote).

    Computable fields come from `stats`; the non-computable ones — session name,
    participant display string, and the session-specific narrative note — are
    supplied by the caller (the skill fills these from conversation/context).
    """
    blockquote = (
        "Active work is the sum of each turn's first-user → last-assistant "
        f"span; the ~{stats.idle_human} difference is idle/think time between "
        "turns. All times UTC."
    )
    if note:
        blockquote += " " + note.strip()

    name = session_name.strip() if session_name else "_(unnamed session)_"
    if participants and participants.strip():
        parts = participants.strip()
    else:
        parts = f"Claude Code ({stats.model_id or 'unknown model'})"

    title = f"# Session transcript — {name}" if session_name else "# Session transcript"
    return [
        title,
        "",
        "| | |",
        "|---|---|",
        f"| **Session name** | {name} |",
        f"| **Date** | {stats.date} |",
        f"| **Participants** | {parts} |",
        f"| **JSONL source** | `{stats.source}` |",
        f"| **Session start** | `{stats.start_clock}` |",
        f"| **Session end** | `{stats.end_clock}` |",
        f"| **Total duration** | {stats.total_human} |",
        f"| **Active work** | {stats.active_human} |",
        "",
        f"> {blockquote}",
        "",
        "---",
        "",
    ]


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Render a Claude Code session JSONL as Markdown with a rich "
                    "metadata header (session timing + active-work calculation)."
    )
    ap.add_argument("input", help="path to the session .jsonl")
    ap.add_argument("output", help="destination .md path")
    ap.add_argument("--session-name", default=None,
                    help="session name shown in the header (skill supplies this)")
    ap.add_argument("--participants", default=None,
                    help="participants string, e.g. 'Jane Doe (jane@x.com) · "
                         "Claude Code (Opus 4.8, 1M context)'")
    ap.add_argument("--note", default=None,
                    help="session-specific narrative appended to the blockquote")
    ns = ap.parse_args()

    src = Path(ns.input).expanduser()
    dst = Path(ns.output).expanduser()

    if not src.exists():
        print(f"Source not found: {src}", file=sys.stderr)
        return 1

    try:
        stats = compute(src)
    except ValueError as exc:
        print(f"Cannot compute session stats: {exc}", file=sys.stderr)
        return 1

    header = build_header(stats, ns.session_name, ns.participants, ns.note)

    sections: list[str] = []
    total = 0
    rendered_count = 0
    with src.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            section = render_entry(entry, total)
            if section:
                sections.append(section)
                rendered_count += 1

    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        dst.write_text("\n".join(header + sections), encoding="utf-8")
    except OSError as exc:
        print(f"Failed to write {dst}: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {dst} ({rendered_count}/{total} entries rendered)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
