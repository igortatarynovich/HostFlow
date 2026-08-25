#!/usr/bin/env python3
"""Block deprecated foundation tokens in git diff added lines (CI)."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from foundation_ratchet_base import RatchetDecision, context_from_env, decide_ratchet
from foundation_tokens_lib import SRC_SUFFIXES, find_in_text, invalid_allow_lines, line_suppressed

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def _rev_parse(ref: str) -> str | None:
    result = _git("rev-parse", "--verify", ref)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def materialize_decision(decision: RatchetDecision) -> RatchetDecision | int:
    """Resolve refs. Return an int exit code on fail-closed / skip-handled by caller."""
    if decision.action == "skip":
        return decision
    if decision.action == "fail":
        return decision

    from_sha = _rev_parse(decision.from_ref)
    to_sha = _rev_parse(decision.to_ref)
    if from_sha is None or to_sha is None:
        missing = decision.from_ref if from_sha is None else decision.to_ref
        print(
            "check-foundation-tokens: cannot resolve "
            f"{missing!r} (mode={decision.mode}). Fail-closed — no fallback to "
            "main or HEAD~1.",
            file=sys.stderr,
        )
        return 1

    if decision.mode.startswith("push-") and decision.to_ref != "HEAD":
        head_sha = _rev_parse("HEAD")
        if head_sha and to_sha != head_sha:
            print(
                "check-foundation-tokens: push after "
                f"{decision.to_ref} does not match HEAD {head_sha[:12]}. "
                "Fail-closed.",
                file=sys.stderr,
            )
            return 1

    return decision


def list_src_files() -> list[str]:
    paths: list[str] = []
    for path in SRC.rglob("*"):
        if path.suffix in SRC_SUFFIXES and path.is_file():
            paths.append(str(path.relative_to(ROOT)))
    return paths


def parse_diff(spec: str) -> list[tuple[str, int, str, str]]:
    """Return (file, line, added_line, previous_line) tuples from unified diff."""
    cmd = ["git", "diff", "--unified=0", spec, "--", *list_src_files()]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if result.returncode > 1:
        cmd = ["git", "diff", "--unified=0", spec, "--", "src"]
        result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=True)

    entries: list[tuple[str, int, str, str]] = []
    current_file = ""
    line_no = 0
    previous = ""

    for raw in result.stdout.splitlines():
        if raw.startswith("diff --git "):
            m = re.search(r" b/(.*)$", raw)
            current_file = m.group(1) if m else ""
            previous = ""
            continue
        if raw.startswith("+++") or raw.startswith("---"):
            continue
        if raw.startswith("@@"):
            m = re.search(r"\+(\d+)", raw)
            line_no = int(m.group(1)) if m else 0
            previous = ""
            continue
        if not raw.startswith("+"):
            continue

        added = raw[1:]
        entries.append((current_file, line_no, added, previous))
        previous = added
        line_no += 1

    return entries


def main() -> int:
    decision = decide_ratchet(context_from_env())
    materialized = materialize_decision(decision)
    if isinstance(materialized, int):
        return materialized
    decision = materialized

    if decision.action == "skip":
        print(f"check-foundation-tokens: skip ({decision.mode}). {decision.reason}")
        return 0
    if decision.action == "fail":
        print(f"check-foundation-tokens: fail-closed ({decision.mode}). {decision.reason}", file=sys.stderr)
        return 1

    findings = []
    for file, line_no, added, previous in parse_diff(decision.spec):
        if not file or not any(file.endswith(s) for s in SRC_SUFFIXES):
            continue

        for item in invalid_allow_lines(added, file=file):
            findings.append((file, line_no, item.category, item.token, item.snippet))

        if line_suppressed(added, previous):
            continue
        for item in find_in_text(added, file=file):
            findings.append((file, line_no, item.category, item.token, item.snippet))

    if not findings:
        print(
            "check-foundation-tokens: diff clean "
            f"(mode={decision.mode}, spec={decision.spec})."
        )
        return 0

    print(
        f"check-foundation-tokens: {len(findings)} deprecated foundation "
        f"token(s) in diff (mode={decision.mode}, spec={decision.spec}).\n"
    )
    for file, line_no, category, token, snippet in findings:
        print(f"  {file}:{line_no} [{category}] {token}")
        print(f"    {snippet}")

    print(
        "\nNew deprecated foundation tokens are forbidden."
        "\nThis is a ratchet on the change range, not a migration of backlog."
        "\nSuppress only with: foundation-allow: <reason, min 8 chars>"
        "\nSee docs/specs/frontend/FOUNDATION_V1.md",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
