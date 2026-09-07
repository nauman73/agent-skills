#!/usr/bin/env python3
"""Convert a GitHub Copilot chat-session JSONL into a readable Markdown transcript.

Copilot's on-disk format is very different from Claude Code's. Rather than one
self-contained event per line, it is an *event-sourced* log:

* ``kind=0`` — session metadata (creation date, session id, default model).
* ``kind=1`` — scalar patches (``k`` is a key-path, ``v`` the value). Per-request
  completion data lives here: ``modelState.completedAt`` and ``elapsedMs``.
* ``kind=2`` — array patches. ``k == ['requests']`` with no ``i`` *appends* one or
  more request (turn) objects. ``k == ['requests', N, 'response']`` *with* an
  ``i`` is a splice: it replaces ``response[i:]`` with new items. The final
  response for a turn only exists after every such splice is applied in order —
  reading just the first append misses most of the assistant's text.

So reconstruction is: accumulate appended requests, then for each turn replay its
response splices to rebuild the full ``response`` array, then render it.

Timing comes from each request's ``elapsedMs`` (== ``completedAt - timestamp``,
verified equal). Turns whose completion event was never flushed (e.g. VS Code
closed mid-session) have neither field; rather than silently dropping them, they
are flagged and given an upper bound from the gap to the next turn's start, so
the active-work figure reads honestly as a floor.

Usage:
    python copilot_jsonl_to_md.py <input.jsonl> <output.md>
        [--session-name NAME] [--participants STR] [--note STR]

Exit codes:
    0 = success
    1 = bad args / source missing / write failed / unparseable session
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path


# --------------------------------------------------------------------------- #
# Loading & reconstruction
# --------------------------------------------------------------------------- #

def _load(src: Path) -> dict:
    """Parse the JSONL into ordered turns with reconstructed responses + timing.

    Returns a dict with: title, session_id, model_label, and turns[] where each
    turn has {timestamp, model_id, user_text, response[], elapsed_ms}.
    """
    raw_lines = src.read_text(encoding="utf-8").splitlines()
    if not raw_lines:
        raise ValueError("empty file")

    meta = json.loads(raw_lines[0]).get("v", {}) if raw_lines else {}
    session_id = meta.get("sessionId", src.stem)
    sel = meta.get("inputState", {}).get("selectedModel", {}) if isinstance(meta, dict) else {}
    sel_meta = sel.get("metadata", {}) if isinstance(sel, dict) else {}
    model_label = None
    if sel_meta.get("id"):
        vendor = sel_meta.get("vendor")
        model_label = f"{sel_meta['id']} ({vendor})" if vendor else sel_meta["id"]

    title = "GitHub Copilot Chat Session"
    title_set = False  # VS Code may rewrite customTitle later; keep the first
    completed_at: dict[int, int] = {}
    elapsed_ms: dict[int, int] = {}
    initial_turns: dict[int, dict] = {}
    patches: dict[int, list[tuple[int, list]]] = {}

    for line in raw_lines:
        obj = json.loads(line)
        kind = obj.get("kind")
        k = obj.get("k", [])
        v = obj.get("v")
        i_val = obj.get("i")

        if kind == 1 and isinstance(k, list):
            if k == ["customTitle"] and not title_set:
                # The first customTitle is VS Code's descriptive auto-title;
                # later rewrites tend to be terse ("implement"). Keep the first.
                if v:
                    title = v
                    title_set = True
            elif len(k) == 3 and k[0] == "requests" and k[2] == "modelState":
                if isinstance(v, dict) and "completedAt" in v:
                    completed_at[k[1]] = v["completedAt"]
            elif len(k) == 3 and k[0] == "requests" and k[2] == "elapsedMs":
                elapsed_ms[k[1]] = v

        elif kind == 2 and isinstance(k, list) and isinstance(v, list):
            if k == ["requests"] and i_val is None:
                # Append new request(s) to the requests array.
                for item in v:
                    if isinstance(item, dict) and "message" in item and "response" in item:
                        initial_turns[len(initial_turns)] = item
            elif len(k) == 3 and k[0] == "requests" and k[2] == "response" and i_val is not None:
                patches.setdefault(k[1], []).append((i_val, v))

    def apply_patches(base: list, patch_list: list[tuple[int, list]]) -> list:
        resp = list(base)
        for i_val, items in sorted(patch_list, key=lambda x: x[0]):
            resp = resp[:i_val] + list(items)
        return resp

    turns = []
    for idx in sorted(initial_turns):
        t = initial_turns[idx]
        full_resp = apply_patches(t.get("response", []), patches.get(idx, []))
        start = t.get("timestamp", 0)
        span = elapsed_ms.get(idx)
        if span is None and idx in completed_at:
            span = completed_at[idx] - start
        turns.append({
            "timestamp": start,
            "model_id": t.get("modelId", "unknown"),
            "user_text": (t.get("message", {}) or {}).get("text", "").strip(),
            "response": full_resp,
            "elapsed_ms": span,
        })

    return {
        "title": title,
        "session_id": session_id,
        "model_label": model_label,
        "turns": turns,
    }


# --------------------------------------------------------------------------- #
# Rendering helpers
# --------------------------------------------------------------------------- #

# Response item kinds that carry no user-facing prose.
_SKIP_KINDS = {
    "mcpServersStarting", "thinking", "progressMessage",
    "codeblockUri", "inlineReference", "textEditGroup", "undoStop",
}


def _render_question_carousel(item: dict) -> str:
    """Render an interactive ``questionCarousel`` item to Markdown.

    Copilot stores the clarifying questions an agent asks — and the answers the
    user picked — as their own response item (a sibling of the text chunks), not
    inside the ``vscode_askQuestions`` tool call. Each question's ``id`` is
    ``"<resolveId>:<n>"`` and the user's choice lives in ``data[id].selectedValue``
    (freeform answers land there too). Dropping this item loses the entire Q&A
    exchange — exactly the design rationale a handoff most needs to preserve — so
    render each question with its matched answer inline where it occurred.
    """
    questions = item.get("questions") or []
    if not questions:
        return ""
    data = item.get("data") or {}
    lines = ["**Clarifying questions asked:**", ""]
    for n, q in enumerate(questions, start=1):
        if not isinstance(q, dict):
            continue
        title = (q.get("title") or "").strip()
        message = (q.get("message") or "").strip()
        head = f"{n}. **{title}**" if title else f"{n}."
        if message:
            head += f" — {message}"
        lines.append(head)
        ans = data.get(q.get("id"))
        selected = ans.get("selectedValue") if isinstance(ans, dict) else None
        if selected and str(selected).strip():
            lines.append(f"   - *Answer:* {str(selected).strip()}")
        else:
            lines.append("   - *Answer:* (skipped / no response recorded)")
    return "\n".join(lines)


def _render_response(resp_items: list) -> str:
    """Render a reconstructed response array to Markdown.

    Adjacent text chunks are concatenated (Copilot streams text in fragments);
    tool calls become quoted ``> *Tool:* ...`` lines; interactive question
    carousels become a questions+answers block; thinking and structural items
    are dropped.
    """
    parts: list[str] = []
    pending: list[str] = []

    def flush():
        combined = "".join(pending).strip()
        if combined:
            parts.append(combined)
        pending.clear()

    for item in resp_items:
        if not isinstance(item, dict):
            continue
        kind = item.get("kind")
        if kind in _SKIP_KINDS:
            continue
        if kind == "questionCarousel":
            rendered = _render_question_carousel(item)
            if rendered:
                flush()
                parts.append(rendered)
            continue
        if kind == "toolInvocationSerialized":
            flush()
            past = item.get("pastTenseMessage", {})
            label = past.get("value", "") if isinstance(past, dict) else str(past)
            if not label:
                inv = item.get("invocationMessage", {})
                label = inv.get("value", "(tool call)") if isinstance(inv, dict) else "(tool call)"
            label = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", label)  # strip md links
            parts.append("> *Tool:* " + label)
            continue
        if "value" in item and isinstance(item["value"], str):
            pending.append(item["value"])

    flush()
    return "\n\n".join(parts) if parts else "*(no text response)*"


def _ms_to_utc(ms: int | None) -> str:
    if not ms:
        return ""
    dt = datetime.datetime.fromtimestamp(ms / 1000, tz=datetime.timezone.utc)
    return dt.strftime("%H:%M:%S UTC")


def _fmt_dur(ms: int | None) -> str:
    """H h M min (drop seconds when hours present) / M min S s / S s."""
    if not ms or ms <= 0:
        return "0s"
    total_s = round(ms / 1000)
    h, rem = divmod(total_s, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m}min"
    if m:
        return f"{m}min {s}s"
    return f"{s}s"


def _ordinal_join(nums: list[int]) -> str:
    """[5] -> '5'; [5,11] -> '5 and 11'; [5,11,14] -> '5, 11, and 14'."""
    strs = [str(n) for n in nums]
    if len(strs) == 1:
        return strs[0]
    if len(strs) == 2:
        return f"{strs[0]} and {strs[1]}"
    return ", ".join(strs[:-1]) + ", and " + strs[-1]


# --------------------------------------------------------------------------- #
# Document build
# --------------------------------------------------------------------------- #

def build_markdown(data: dict, source: str,
                   session_name: str | None, participants: str | None,
                   note: str | None) -> str:
    turns = data["turns"]
    n = len(turns)

    # Per-turn spans & event timeline.
    timeline: list[int] = []
    spans: list[int | None] = []
    for t in turns:
        start = t["timestamp"]
        span = t["elapsed_ms"]
        spans.append(span)
        if start:
            timeline.append(start)
        if span:
            timeline.append(start + span)

    first_start = turns[0]["timestamp"] if turns else 0
    last_event = max(timeline) if timeline else 0
    total_ms = last_event - first_start
    active_ms = sum(s for s in spans if s)
    known = sum(1 for s in spans if s)
    idle_ms = max(0, total_ms - active_ms)

    # Upper bounds for turns lacking a completion record.
    missing = [i for i, s in enumerate(spans) if not s]
    bounds: dict[int, int | None] = {}
    for i in missing:
        if i + 1 < n:
            bounds[i] = turns[i + 1]["timestamp"] - turns[i]["timestamp"]
        else:
            bounds[i] = None  # last turn — no next start to bound it

    title = session_name.strip() if session_name else data["title"]
    model_label = data["model_label"] or "unknown"

    out: list[str] = []
    out.append(f"# {title}")
    out.append("")
    out.append("| | |")
    out.append("|---|---|")
    out.append(f"| **Session ID** | `{data['session_id']}` |")
    out.append("| **Source** | GitHub Copilot Chat (VS Code) |")
    out.append(f"| **Model** | {model_label} |")
    if participants and participants.strip():
        out.append(f"| **Participants** | {participants.strip()} |")
    out.append(f"| **Session start** | {_ms_to_utc(first_start)} |")
    out.append(f"| **Session end** | {_ms_to_utc(last_event)} |")
    out.append(f"| **Total duration** | {_fmt_dur(total_ms)} |")
    active_suffix = f" ({known}/{n} turns)" if missing else ""
    active_prefix = "≥" if missing else ""
    out.append(f"| **Active work** | {active_prefix}{_fmt_dur(active_ms)}{active_suffix} |")
    out.append(f"| **Idle / think time** | ~{_fmt_dur(idle_ms)} |")
    out.append(f"| **Turns** | {n} |")
    out.append(f"| **JSONL source** | `{source}` |")
    out.append("")

    # Active-work explanation blockquote.
    if missing:
        bound_strs = []
        for i in missing:
            tn = i + 1
            if bounds[i] is None:
                bound_strs.append(f"Turn {tn} = unknown (last turn)")
            else:
                bound_strs.append(f"Turn {tn} ≤{_fmt_dur(bounds[i])}")
        blockquote = (
            f"**Active work** is the sum of `elapsedMs` "
            f"(= `completedAt − requestTimestamp`) for the {known} turns whose "
            f"completion state was flushed to the JSONL. "
            f"Turns {_ordinal_join([i + 1 for i in missing])} have no `elapsedMs` "
            f"or `completedAt` record at all — their kind=1 completion events "
            f"were never written, most likely because the VS Code session was "
            f"closed before those turn states were flushed. Their true generation "
            f"time is unknown; upper bounds from the gap to the next turn start "
            f"are: {', '.join(bound_strs)}. Actual active work is higher than the "
            f"{_fmt_dur(active_ms)} shown by an unquantifiable amount from those "
            f"{len(missing)} turns."
        )
    else:
        blockquote = (
            f"**Active work** is the sum of each turn's `elapsedMs` "
            f"(= `completedAt − requestTimestamp`). The ~{_fmt_dur(idle_ms)} "
            f"remainder is idle/think time between turns. All times UTC."
        )
    if note and note.strip():
        blockquote += " " + note.strip()
    out.append(f"> {blockquote}")
    out.append("")
    out.append("---")
    out.append("")

    for i, t in enumerate(turns):
        tn = i + 1
        start = t["timestamp"]
        span = spans[i]
        header = f"## Turn {tn}"
        if start:
            header += f" · {_ms_to_utc(start)}"
        if span:
            header += f" ({_fmt_dur(span)})"
        elif bounds.get(i) is None:
            header += " (no completion record, last turn)"
        else:
            header += f" (≤{_fmt_dur(bounds[i])}, no completion record)"
        out.append(header)
        out.append("")
        out.append("### User")
        out.append("")
        out.append(t["user_text"] or "*(no message)*")
        out.append("")
        out.append(f"### Assistant ({t['model_id']})")
        out.append("")
        out.append(_render_response(t["response"]))
        out.append("")
        out.append("---")
        out.append("")

    # Copilot stores user text with embedded CRLF; normalize the whole document
    # to clean LF so the output never carries mixed or stray \r sequences.
    return "\n".join(out).replace("\r\n", "\n").replace("\r", "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Render a Copilot chat JSONL as Markdown.")
    ap.add_argument("input", help="path to the Copilot chat .jsonl")
    ap.add_argument("output", help="destination .md path")
    ap.add_argument("--session-name", default=None,
                    help="override the document title (default: customTitle from JSONL)")
    ap.add_argument("--participants", default=None,
                    help="optional participants row, e.g. 'Jane Doe (jane@x.com)'")
    ap.add_argument("--note", default=None,
                    help="session-specific narrative appended to the blockquote")
    ns = ap.parse_args()

    src = Path(ns.input).expanduser()
    dst = Path(ns.output).expanduser()
    if not src.exists():
        print(f"Source not found: {src}", file=sys.stderr)
        return 1

    try:
        data = _load(src)
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"Cannot parse Copilot session: {exc}", file=sys.stderr)
        return 1
    if not data["turns"]:
        print("No conversation turns found in session.", file=sys.stderr)
        return 1

    markdown = build_markdown(data, str(src), ns.session_name, ns.participants, ns.note)
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        # newline="\n" disables platform translation so the LF-normalized
        # document is written verbatim (no \r\r\n on Windows).
        with open(dst, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(markdown)
    except OSError as exc:
        print(f"Failed to write {dst}: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {dst} ({len(data['turns'])} turns)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
