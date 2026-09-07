#!/usr/bin/env python3
"""Quick regression check: questionCarousel Q&A survives Copilot JSONL -> MD.

The dynamic-logging handoff session asked 10 clarifying questions across three
turns; every one was silently dropped before the converter learned to render
`questionCarousel` items. This asserts the rendered Markdown contains both the
question titles and the user's recorded answers, so the regression can't return
unnoticed.

Usage:
    python test_carousel_extraction.py <fixture.jsonl>

Exit codes: 0 = all assertions passed, 1 = a check failed / bad args.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

# Question titles and answer fragments known to exist in the fixture session.
EXPECTED = [
    ("Module identification", "Match by Caption"),
    (None, "registry install path"),
    (None, "wildcard"),
    (None, "Keep existing static path unchanged"),
    (None, "Primary/runtime log only"),
    (None, "Just before archiving starts"),
]


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: test_carousel_extraction.py <fixture.jsonl>", file=sys.stderr)
        return 1
    fixture = Path(sys.argv[1]).expanduser()
    if not fixture.exists():
        print(f"fixture not found: {fixture}", file=sys.stderr)
        return 1

    converter = Path(__file__).with_name("copilot_jsonl_to_md.py")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out.md"
        proc = subprocess.run(
            [sys.executable, str(converter), str(fixture), str(out)],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            print(f"converter failed: {proc.stderr}", file=sys.stderr)
            return 1
        md = out.read_text(encoding="utf-8")

    failures = []
    if "Clarifying questions asked" not in md:
        failures.append("no 'Clarifying questions asked' block rendered")
    for title, answer in EXPECTED:
        if title and title not in md:
            failures.append(f"missing question title: {title!r}")
        if answer not in md:
            failures.append(f"missing answer fragment: {answer!r}")
    if "*Answer:*" not in md:
        failures.append("no '*Answer:*' lines rendered")

    if failures:
        print("FAIL:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print(f"PASS: all {len(EXPECTED)} questions + answers present in rendered Markdown")
    return 0


if __name__ == "__main__":
    sys.exit(main())
