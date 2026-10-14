#!/usr/bin/env python3
"""File-scoped HostFlow checks for Cursor hooks.

afterFileEdit reports failures as additional_context.
stop sends one follow-up when the final diff still fails a check.
beforeShellExecution asks before an unpinned FastAPI upgrade.

Repo-wide ADR-011 already has existing findings, so this hook flags only
arbitrary px classes introduced by the edit. It does not ask the agent to
clean the baseline.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CANONICAL_VERSIONS = "backend/alembic/versions/"
FASTAPI_PIN = "fastapi==0.115.6"
INSTRUMENTATOR_PIN = "prometheus-fastapi-instrumentator==7.0.0"

LAYOUT_ARBITRARY_PX = re.compile(
    r"""(?:^|[\s"'`])"""
    r"(?:m[trblxy]?|p[trblxy]?|gap(?:-[xy])?|space-[xy]|w|min-w|max-w|"
    r"h|min-h|max-h|size|rounded(?:-[trbl]{1,2})?|top|right|bottom|left|"
    r"inset(?:-[trblxy])?)"
    r"-\[[0-9]+px\]"
)
RAW_SECURITY_EVENT = re.compile(r"\bemit_security_event\s*\(")


def emit(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")


def rel_of(path: str) -> str | None:
    try:
        return Path(path).resolve().relative_to(REPO).as_posix()
    except (OSError, ValueError):
        return None


def px_tokens(text: str) -> list[str]:
    return [match.group(0).strip().strip("\"'`") for match in LAYOUT_ARBITRARY_PX.finditer(text)]


def new_px(old: str, new: str) -> list[str]:
    old_tokens = set(px_tokens(old))
    found: list[str] = []
    for token in px_tokens(new):
        if token not in old_tokens and token not in found:
            found.append(token)
    return found


def edits_of(payload: dict) -> list[dict]:
    edits = payload.get("edits")
    if isinstance(edits, list):
        return [edit for edit in edits if isinstance(edit, dict)]
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict) and "new_string" in tool_input:
        return [
            {
                "old_string": tool_input.get("old_string") or "",
                "new_string": tool_input.get("new_string") or "",
            }
        ]
    return []


def path_of(payload: dict) -> str:
    if payload.get("file_path"):
        return str(payload["file_path"])
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict) and tool_input.get("path"):
        return str(tool_input["path"])
    return ""


def run_check(args: list[str], timeout: int, fingerprint: str) -> tuple[int, str]:
    cache_path = Path("/tmp/hostflow-enforce-cache.json")
    key = " ".join(args) + "|" + fingerprint
    now = time.time()
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        cache = {}
    cached = cache.get(key)
    if isinstance(cached, dict) and now - float(cached.get("t", 0)) < 8:
        return int(cached.get("code", 1)), str(cached.get("output", ""))
    try:
        completed = subprocess.run(
            args,
            cwd=REPO,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    output = (completed.stdout or "") + (completed.stderr or "")
    lines = [line for line in output.splitlines() if line.strip()]
    tail = "\n".join(lines[-25:])
    cache[key] = {"t": now, "code": completed.returncode, "output": tail}
    try:
        cache_path.write_text(json.dumps(cache), encoding="utf-8")
    except OSError:
        pass
    return completed.returncode, tail


def migration_problem(rel: str) -> str | None:
    if "alembic/versions/" not in rel:
        return None
    if rel.startswith(CANONICAL_VERSIONS):
        return None
    return (
        f"Revision {rel} is outside {CANONICAL_VERSIONS}. "
        "Alembic revisions for this graph belong only there."
    )


def security_problem(edits: list[dict]) -> str | None:
    for edit in edits:
        new = str(edit.get("new_string") or "")
        old = str(edit.get("old_string") or "")
        if RAW_SECURITY_EVENT.search(new) and not RAW_SECURITY_EVENT.search(old):
            return (
                "This edit calls the legacy security-event helper. "
                "New security events must use emit_security_event_v1."
            )
    return None


def adr011_problem(rel: str, edits: list[dict]) -> str | None:
    if not rel.startswith("hostflow-frontend/"):
        return None
    if Path(rel).suffix not in {".ts", ".tsx", ".css"}:
        return None
    introduced: list[str] = []
    for edit in edits:
        introduced.extend(
            new_px(str(edit.get("old_string") or ""), str(edit.get("new_string") or ""))
        )
    unique = list(dict.fromkeys(introduced))
    if not unique:
        return None
    shown = ", ".join(unique[:8])
    return (
        f"ADR-011: this edit introduces arbitrary px utilities ({shown}). "
        "Use theme tokens. Do not clean unrelated existing findings."
    )


def problems_for_path(
    rel: str,
    edits: list[dict],
    *,
    run_repo_checks: bool,
    fingerprint: str,
) -> list[str]:
    found: list[str] = []
    migration = migration_problem(rel)
    if migration:
        found.append(migration)
    if rel.startswith("backend/") and rel.endswith(".py"):
        security = security_problem(edits)
        if security:
            found.append(security)
    adr = adr011_problem(rel, edits)
    if adr:
        found.append(adr)
    if not run_repo_checks:
        return found
    suffix = Path(rel).suffix
    if suffix == ".md":
        code, output = run_check(
            ["python3", "scripts/docs/check_doc_governance.py"],
            30,
            fingerprint,
        )
        if code != 0:
            found.append("make docs-lint failed:\n" + output)
    if rel.startswith("hostflow-frontend/") and suffix in {".ts", ".tsx"}:
        code, output = run_check(
            ["python3", "hostflow-frontend/scripts/check_ts_import_integrity.py"],
            30,
            fingerprint,
        )
        if code != 0:
            found.append("make check-ts-imports failed:\n" + output)
    return found


def fingerprint_for(rel: str, edits: list[dict]) -> str:
    raw = rel + "\n" + "\n".join(str(edit.get("new_string") or "") for edit in edits)
    return hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:16]


def handle_edit(payload: dict) -> dict:
    raw_path = path_of(payload)
    rel = rel_of(raw_path) if raw_path else None
    if not rel:
        return {}
    edits = edits_of(payload)
    found = problems_for_path(
        rel,
        edits,
        run_repo_checks=True,
        fingerprint=fingerprint_for(rel, edits),
    )
    if not found:
        return {}
    return {"additional_context": "HostFlow check failed after edit.\n" + "\n".join(found)}


def added_text_against_head(rel: str) -> str:
    path = REPO / rel
    if not path.is_file():
        return ""
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", rel],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    if tracked.returncode != 0:
        return path.read_text(encoding="utf-8", errors="replace")
    diff = subprocess.run(
        ["git", "diff", "-U0", "--no-color", "HEAD", "--", rel],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    lines = [
        line[1:]
        for line in (diff.stdout or "").splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]
    return "\n".join(lines)


def changed_files() -> list[str]:
    diff = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    names = []
    for chunk in (diff.stdout, untracked.stdout):
        names.extend(line.strip() for line in (chunk or "").splitlines() if line.strip())
    return list(dict.fromkeys(names))


def handle_stop(payload: dict) -> dict:
    if payload.get("status") != "completed":
        return {}
    if int(payload.get("loop_count") or 0) >= 1:
        return {}
    found: list[str] = []
    changed = changed_files()
    saw_md = False
    saw_ts = False
    for rel in changed:
        if rel.endswith(".md"):
            saw_md = True
        if rel.startswith("hostflow-frontend/") and rel.endswith((".ts", ".tsx")):
            saw_ts = True
        added = added_text_against_head(rel)
        edit = [{"old_string": "", "new_string": added}]
        found.extend(
            problems_for_path(rel, edit, run_repo_checks=False, fingerprint="stop")
        )
    if saw_md:
        code, output = run_check(
            ["python3", "scripts/docs/check_doc_governance.py"],
            40,
            "stop-docs",
        )
        if code != 0:
            found.append("make docs-lint failed:\n" + output)
    if saw_ts:
        code, output = run_check(
            ["python3", "hostflow-frontend/scripts/check_ts_import_integrity.py"],
            40,
            "stop-imports",
        )
        if code != 0:
            found.append("make check-ts-imports failed:\n" + output)
    if not found:
        return {}
    return {
        "followup_message": (
            "HostFlow checks failed on the current diff. Fix only these failures "
            "and do not expand the change.\n" + "\n".join(found)
        )
    }


def handle_pip(payload: dict) -> dict:
    command = str(payload.get("command") or "")
    allow = {"permission": "allow"}
    if re.search(r"(?:^|\s)(?:-r|--requirement)\b", command):
        return allow
    compact = re.sub(r"\s+", "", command)
    mentions_fastapi = "fastapi" in compact
    mentions_instrumentator = "prometheus-fastapi-instrumentator" in compact
    if not mentions_fastapi and not mentions_instrumentator:
        return allow
    missing = []
    if mentions_fastapi and FASTAPI_PIN not in compact:
        missing.append(FASTAPI_PIN)
    if mentions_instrumentator and INSTRUMENTATOR_PIN not in compact:
        missing.append(INSTRUMENTATOR_PIN)
    if not missing:
        return allow
    message = (
        "Keep "
        + " and ".join(missing)
        + ". An unpinned FastAPI upgrade makes every request return 500."
    )
    return {
        "permission": "ask",
        "user_message": message,
        "agent_message": message,
    }


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        emit({})
        return
    event = str(payload.get("hook_event_name") or "")
    if event == "beforeShellExecution":
        emit(handle_pip(payload))
        return
    if event == "stop":
        emit(handle_stop(payload))
        return
    if event in {"afterFileEdit", "postToolUse"}:
        emit(handle_edit(payload))
        return
    emit({})


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # fail open: a hook bug must not block the agent
        sys.stderr.write(f"hostflow enforce hook failed open: {exc}\n")
        emit({})
