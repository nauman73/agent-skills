#!/usr/bin/env python3
"""Locate the GitHub Copilot chat-session transcript for a workspace.

GitHub Copilot Chat stores each session as a JSONL file under
``%APPDATA%/Code/User/workspaceStorage/<hash>/chatSessions/<session-id>.jsonl``.
The ``<hash>`` is an opaque per-workspace id; ``workspace.json`` in that hash
directory records which on-disk folder the hash belongs to.

This script maps a project root -> workspace hash -> the *current* chat session,
so the session-handoff skill can find the transcript without the user pasting a
path. Discovery is deterministic where possible:

1. **Workspace hash** — scan every ``workspaceStorage/*/workspace.json`` and
   match its ``folder`` URI against the given project root.
2. **Active session (primary)** — ``state.vscdb`` (a SQLite DB in the hash dir)
   stores the focused chat session under the key
   ``memento/interactive-session-view-copilot``; its ``sessionResource.path`` is
   the base64-encoded session id. This is exact: even with several chats open in
   one folder, this points at the one currently in view.
3. **Recency (fallback)** — if the DB or pointer is unavailable, fall back to the
   most-recently-modified ``chatSessions/*.jsonl``. This can pick the wrong chat
   if several were touched close together, so the chosen method is always
   reported back.

Session titles come from ``chat.ChatSessionStore.index`` when present.

The DB is read **read-only** (``mode=ro``, with a copy-to-temp fallback) so the
script never blocks — or is blocked by — a running VS Code.

Usage:
    python copilot_discover.py [--project-root DIR] [--storage-root DIR]
    python copilot_discover.py --list [--project-root DIR]   # all sessions

Output: JSON on stdout. Single-session mode yields
``{path, session_id, title, method, workspace_hash}``; ``--list`` yields
``{workspace_hash, sessions: [...]}`` newest-first.

Exit codes:
    0 = success
    1 = bad args / workspace hash not found / no chat sessions
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import urllib.parse
from pathlib import Path


# --------------------------------------------------------------------------- #
# Workspace-hash resolution
# --------------------------------------------------------------------------- #

def default_storage_root() -> Path:
    """%APPDATA%/Code/User/workspaceStorage (Windows) or the OS equivalent."""
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "Code" / "User" / "workspaceStorage"
    # POSIX VS Code locations (best-effort; Copilot is mostly used on desktop).
    home = Path.home()
    for cand in (
        home / ".config" / "Code" / "User" / "workspaceStorage",
        home / "Library" / "Application Support" / "Code" / "User" / "workspaceStorage",
    ):
        if cand.exists():
            return cand
    return home / ".config" / "Code" / "User" / "workspaceStorage"


def _folder_uri_to_path(uri: str) -> str | None:
    """Decode a workspace.json ``folder`` URI to a filesystem path.

    e.g. ``file:///c%3A/Users/me/proj`` -> ``c:/Users/me/proj``.
    """
    if not uri:
        return None
    decoded = urllib.parse.unquote(uri)
    for prefix in ("file:///", "file://"):
        if decoded.startswith(prefix):
            decoded = decoded[len(prefix):]
            break
    return decoded


def _norm(path_str: str) -> str:
    """Normalize for cross-format comparison (case + separators + drive)."""
    return os.path.normcase(os.path.normpath(path_str.replace("/", os.sep)))


def find_workspace_hash(project_root: Path, storage_root: Path) -> str | None:
    """Return the workspaceStorage hash whose folder == project_root, or None."""
    target = _norm(str(project_root))
    if not storage_root.exists():
        return None
    for ws_json in storage_root.glob("*/workspace.json"):
        try:
            data = json.loads(ws_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        folder = _folder_uri_to_path(data.get("folder", ""))
        if folder and _norm(folder) == target:
            return ws_json.parent.name
    return None


# --------------------------------------------------------------------------- #
# state.vscdb access (read-only, lock-safe)
# --------------------------------------------------------------------------- #

def _read_item_table(db_path: Path, keys: list[str]) -> dict[str, str]:
    """Read specific keys from VS Code's ItemTable, read-only and lock-safe.

    Opens with ``mode=ro``; if the file is locked or that fails, copies the DB to
    a temp file and reads the copy. Returns only the keys that were found.
    """
    if not db_path.exists():
        return {}

    def _query(conn: sqlite3.Connection) -> dict[str, str]:
        out: dict[str, str] = {}
        cur = conn.cursor()
        for key in keys:
            try:
                cur.execute("SELECT value FROM ItemTable WHERE key = ?", (key,))
                row = cur.fetchone()
            except sqlite3.Error:
                continue
            if row and row[0] is not None:
                out[key] = row[0]
        return out

    # Primary: open read-only without touching WAL/locks.
    try:
        uri = f"file:{db_path.as_posix()}?mode=ro&immutable=1"
        conn = sqlite3.connect(uri, uri=True, timeout=2.0)
        try:
            return _query(conn)
        finally:
            conn.close()
    except sqlite3.Error:
        pass

    # Fallback: copy to temp and read the copy (handles exclusive locks).
    tmp_dir = tempfile.mkdtemp(prefix="copilot_discover_")
    try:
        tmp_db = Path(tmp_dir) / "state.vscdb"
        shutil.copy2(db_path, tmp_db)
        conn = sqlite3.connect(tmp_db.as_posix(), timeout=2.0)
        try:
            return _query(conn)
        finally:
            conn.close()
    except (OSError, sqlite3.Error):
        return {}
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _active_session_id(db_items: dict[str, str]) -> str | None:
    """Decode the focused chat session id from the view-state memento."""
    raw = db_items.get("memento/interactive-session-view-copilot")
    if not raw:
        return None
    try:
        memento = json.loads(raw)
    except json.JSONDecodeError:
        return None
    resource = memento.get("sessionResource") or {}
    encoded = resource.get("path") or ""
    encoded = encoded.lstrip("/")
    if not encoded:
        return None
    try:
        return base64.b64decode(encoded).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None


def _session_titles(db_items: dict[str, str]) -> dict[str, dict]:
    """Map session-id -> index entry (title, lastMessageDate, ...)."""
    raw = db_items.get("chat.ChatSessionStore.index")
    if not raw:
        return {}
    try:
        index = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    entries = index.get("entries")
    return entries if isinstance(entries, dict) else {}


# --------------------------------------------------------------------------- #
# Discovery
# --------------------------------------------------------------------------- #

_KEYS = [
    "memento/interactive-session-view-copilot",
    "chat.ChatSessionStore.index",
]


def discover(project_root: Path, storage_root: Path) -> dict:
    ws_hash = find_workspace_hash(project_root, storage_root)
    if not ws_hash:
        raise SystemExit(
            f"No VS Code workspace hash maps to {project_root}. "
            f"Searched {storage_root}."
        )

    hash_dir = storage_root / ws_hash
    sessions_dir = hash_dir / "chatSessions"
    db_items = _read_item_table(hash_dir / "state.vscdb", _KEYS)
    titles = _session_titles(db_items)

    def title_for(sid: str) -> str:
        entry = titles.get(sid) or {}
        return entry.get("title") or "(untitled)"

    # Primary: active-session pointer.
    active_id = _active_session_id(db_items)
    if active_id:
        candidate = sessions_dir / f"{active_id}.jsonl"
        if candidate.exists():
            return {
                "path": str(candidate),
                "session_id": active_id,
                "title": title_for(active_id),
                "method": "active-pointer",
                "workspace_hash": ws_hash,
            }

    # Fallback: most-recently-modified chat JSONL.
    if sessions_dir.exists():
        jsonls = sorted(
            sessions_dir.glob("*.jsonl"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if jsonls:
            newest = jsonls[0]
            sid = newest.stem
            return {
                "path": str(newest),
                "session_id": sid,
                "title": title_for(sid),
                "method": "recency-fallback",
                "workspace_hash": ws_hash,
            }

    raise SystemExit(f"No chat sessions found under {sessions_dir}.")


def list_sessions(project_root: Path, storage_root: Path) -> dict:
    ws_hash = find_workspace_hash(project_root, storage_root)
    if not ws_hash:
        raise SystemExit(
            f"No VS Code workspace hash maps to {project_root}. "
            f"Searched {storage_root}."
        )
    hash_dir = storage_root / ws_hash
    sessions_dir = hash_dir / "chatSessions"
    db_items = _read_item_table(hash_dir / "state.vscdb", _KEYS)
    titles = _session_titles(db_items)
    active_id = _active_session_id(db_items)

    rows = []
    if sessions_dir.exists():
        for p in sessions_dir.glob("*.jsonl"):
            sid = p.stem
            entry = titles.get(sid) or {}
            rows.append({
                "session_id": sid,
                "title": entry.get("title") or "(untitled)",
                "last_message_date": entry.get("lastMessageDate"),
                "size_bytes": p.stat().st_size,
                "mtime": p.stat().st_mtime,
                "is_active": sid == active_id,
                "path": str(p),
            })
    rows.sort(
        key=lambda r: (r["last_message_date"] or 0, r["mtime"]),
        reverse=True,
    )
    return {"workspace_hash": ws_hash, "active_session_id": active_id, "sessions": rows}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project-root", default=os.getcwd(),
                    help="workspace folder to resolve (default: CWD)")
    ap.add_argument("--storage-root", default=None,
                    help="override workspaceStorage location (default: %%APPDATA%%/Code/...)")
    ap.add_argument("--list", action="store_true",
                    help="list all chat sessions for the workspace instead of "
                         "resolving the current one")
    ns = ap.parse_args()

    project_root = Path(ns.project_root).expanduser()
    storage_root = Path(ns.storage_root).expanduser() if ns.storage_root else default_storage_root()

    result = list_sessions(project_root, storage_root) if ns.list else discover(project_root, storage_root)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
