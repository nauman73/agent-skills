#!/usr/bin/env python3
"""Compute timing statistics for a Claude Code session JSONL transcript.

This is the calculation component of the session-handoff skill. It walks the
session JSONL once and derives the figures used in the Markdown transcript
header — session start/end, total wall-clock duration, and **active work time**
(the sum of each turn's first-user -> last-assistant span, which excludes the
idle/think gaps between turns).

It is both importable (``compute(path) -> SessionStats``) and runnable as a CLI
(prints a human summary, or ``--json`` for machine-readable output). Standard
library only.

Turn model
----------
A "turn" begins at each *human* user prompt — a JSONL entry of type ``user``
whose message carries real text (a string, or a content list containing a
non-empty ``text`` block). Tool-result entries (``user`` entries whose content
is only ``tool_result`` blocks) and assistant entries are NOT turn starts. A
turn's active span runs from that human prompt's timestamp to the timestamp of
the *last assistant entry* before the next human prompt. Active work is the sum
of those spans; idle time is total wall-clock minus active.

Usage:
    python session_stats.py <input.jsonl>           # human summary
    python session_stats.py <input.jsonl> --json     # JSON

Exit codes:
    0 = success
    1 = bad args / source missing / no timestamped entries
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path


# --------------------------------------------------------------------------- #
# Parsing helpers
# --------------------------------------------------------------------------- #

def _parse_ts(value: str) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _is_human_prompt(entry: dict) -> bool:
    """True if this entry is a real user prompt (turn start), not a tool result."""
    if entry.get("type") != "user":
        return False
    msg = entry.get("message") or {}
    content = msg.get("content")
    if isinstance(content, str):
        return bool(content.strip())
    if isinstance(content, list):
        # Real prompt iff at least one non-empty text block is present.
        for block in content:
            if (
                isinstance(block, dict)
                and block.get("type") == "text"
                and str(block.get("text", "")).strip()
            ):
                return True
    return False


def _model_id(entry: dict) -> str | None:
    if entry.get("type") != "assistant":
        return None
    msg = entry.get("message") or {}
    model = msg.get("model")
    return str(model) if model else None


# --------------------------------------------------------------------------- #
# Core computation
# --------------------------------------------------------------------------- #

@dataclass
class SessionStats:
    source: str
    session_id: str
    date: str                 # YYYY-MM-DD (UTC, from first entry)
    start_clock: str          # "HH:MM:SS UTC"
    end_clock: str            # "HH:MM:SS UTC"
    total_seconds: int
    active_seconds: int
    idle_seconds: int
    total_human: str
    active_human: str
    idle_human: str
    turn_count: int
    entry_count: int          # timestamped user/assistant entries
    model_id: str | None


def humanize(seconds: float) -> str:
    """Round to the nearest minute and render as 'H h M min' / 'M min'."""
    if seconds < 60:
        return f"{int(round(seconds))} sec"
    total_min = int(round(seconds / 60))
    h, m = divmod(total_min, 60)
    if h and m:
        return f"{h} h {m} min"
    if h:
        return f"{h} h"
    return f"{m} min"


def _clock(dt: datetime) -> str:
    return dt.strftime("%H:%M:%S") + " UTC"


def compute(src: Path) -> SessionStats:
    """Parse the JSONL and return the derived SessionStats. Raises ValueError
    if there are no timestamped user/assistant entries."""
    # events: (datetime, type, is_human)
    events: list[tuple[datetime, str, bool]] = []
    model_id: str | None = None

    with src.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            etype = entry.get("type")
            if etype not in ("user", "assistant"):
                continue
            dt = _parse_ts(entry.get("timestamp", ""))
            if dt is None:
                continue
            events.append((dt, etype, _is_human_prompt(entry)))
            if model_id is None:
                model_id = _model_id(entry)

    if not events:
        raise ValueError("No timestamped user/assistant entries found.")

    start_dt = events[0][0]
    end_dt = events[-1][0]
    total = (end_dt - start_dt).total_seconds()

    # Active work: sum per-turn (first human prompt -> last assistant before next)
    turn_starts = [i for i, e in enumerate(events) if e[2]]
    active = 0.0
    for k, si in enumerate(turn_starts):
        nxt = turn_starts[k + 1] if k + 1 < len(turn_starts) else len(events)
        last_assistant_dt = None
        for j in range(si, nxt):
            if events[j][1] == "assistant":
                last_assistant_dt = events[j][0]
        if last_assistant_dt is not None:
            active += (last_assistant_dt - events[si][0]).total_seconds()

    idle = max(0.0, total - active)

    return SessionStats(
        source=str(src),
        session_id=src.stem,
        date=start_dt.strftime("%Y-%m-%d"),
        start_clock=_clock(start_dt),
        end_clock=_clock(end_dt),
        total_seconds=int(round(total)),
        active_seconds=int(round(active)),
        idle_seconds=int(round(idle)),
        total_human=humanize(total),
        active_human=humanize(active),
        idle_human=humanize(idle),
        turn_count=len(turn_starts),
        entry_count=len(events),
        model_id=model_id,
    )


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main() -> int:
    args = sys.argv[1:]
    as_json = "--json" in args
    positional = [a for a in args if not a.startswith("--")]
    if len(positional) != 1:
        print(__doc__, file=sys.stderr)
        return 1

    src = Path(positional[0]).expanduser()
    if not src.exists():
        print(f"Source not found: {src}", file=sys.stderr)
        return 1

    try:
        stats = compute(src)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if as_json:
        print(json.dumps(asdict(stats), indent=2))
    else:
        print(f"Source         : {stats.source}")
        print(f"Session ID     : {stats.session_id}")
        print(f"Date           : {stats.date}")
        print(f"Session start  : {stats.start_clock}")
        print(f"Session end    : {stats.end_clock}")
        print(f"Total duration : {stats.total_human}  ({stats.total_seconds} s)")
        print(f"Active work    : {stats.active_human}  ({stats.active_seconds} s)")
        print(f"Idle/think     : {stats.idle_human}  ({stats.idle_seconds} s)")
        print(f"Turns          : {stats.turn_count}")
        print(f"Model          : {stats.model_id or '(unknown)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
