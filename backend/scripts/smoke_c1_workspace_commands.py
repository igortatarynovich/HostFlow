#!/usr/bin/env python3
"""Authenticated C1 close-out smoke: Workspace Commands on one Thread.

Avoids importing the communications package (circular import under -m).
Creates an isolated smoke thread via SQL, mints a JWT, runs HTTP Commands.
"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import psycopg

from backend.app.auth.jwt_tools import encode as encode_jwt
from backend.app.core.settings import settings

TENANT_ID = "11111111-1111-1111-1111-111111111111"
BASE = "http://127.0.0.1:8000/api/v1/communications"
REQUIRED_CONTEXT_KEYS = (
    "context_version",
    "generated_at",
    "identity",
    "work_state",
    "workspace",
    "capabilities",
    "source",
)


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def _dsn() -> str:
    url = str(getattr(settings, "SYNC_DATABASE_URL", "") or "")
    if not url:
        _fail("SYNC_DATABASE_URL missing")
    # settings may use postgresql+psycopg:// — normalize for psycopg
    return url.replace("postgresql+psycopg://", "postgresql://").replace(
        "postgresql+psycopg2://", "postgresql://"
    )


def _work_version(ctx: dict[str, Any]) -> int:
    ws = ctx.get("work_state") or {}
    return int(ws.get("work_version") or 0)


def _queues(ctx: dict[str, Any]) -> set[str]:
    ws = ctx.get("work_state") or {}
    return set(ws.get("active_queues") or [])


def _assert_full_context(ctx: dict[str, Any], label: str) -> None:
    if not isinstance(ctx, dict):
        _fail(f"{label}: context missing")
    missing = [k for k in REQUIRED_CONTEXT_KEYS if k not in ctx]
    if missing:
        _fail(f"{label}: incomplete ThreadContext missing {missing}")
    ws = ctx.get("work_state") or {}
    if "work_version" not in ws:
        _fail(f"{label}: work_state.work_version missing")
    if "active_queues" not in ws:
        _fail(f"{label}: work_state.active_queues missing")


def _prepare() -> tuple[str, str, str]:
    thread_id = str(uuid.uuid4())
    due = datetime.now(timezone.utc) + timedelta(hours=2)
    with psycopg.connect(_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id::text, email, role::text
                FROM users
                WHERE tenant_id = %s AND is_active IS TRUE
                ORDER BY CASE WHEN email = 'admin@hostflow.dev' THEN 0 ELSE 1 END, created_at
                LIMIT 1
                """,
                (TENANT_ID,),
            )
            user = cur.fetchone()
            if not user:
                _fail("no active user in demo tenant")
            actor_id, email, role = user

            cur.execute(
                """
                SELECT id::text FROM own_companies
                WHERE tenant_id = %s AND is_archived IS FALSE
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (TENANT_ID,),
            )
            oc = cur.fetchone()
            if not oc:
                _fail("no own_company for demo tenant")
            oc_id = oc[0]

            cur.execute(
                """
                INSERT INTO communication_threads (
                    id, tenant_id, own_company_id, channel, status, subject,
                    unread_count, assignee_id, sla_due_at, work_version,
                    last_inbound_at, is_archived, participants_json, tags_json,
                    thread_meta, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, 'email', 'open', %s,
                    0, NULL, %s, 1,
                    NOW(), FALSE, '[]'::jsonb, '[]'::jsonb,
                    '{}'::jsonb, NOW(), NOW()
                )
                """,
                (thread_id, TENANT_ID, oc_id, f"C1 smoke {thread_id[:8]}", due),
            )
            # Minimal SLA START so Pause/Resume have a clock.
            cur.execute(
                """
                INSERT INTO communication_thread_sla_events (
                    id, tenant_id, thread_id, event_type, at, actor_user_id, payload,
                    created_at, updated_at
                ) VALUES (
                    %s, %s, %s, 'start', NOW(), %s,
                    %s::jsonb, NOW(), NOW()
                )
                """,
                (
                    str(uuid.uuid4()),
                    TENANT_ID,
                    thread_id,
                    actor_id,
                    json.dumps({"target_due_at": due.isoformat()}),
                ),
            )
        conn.commit()

    now = datetime.now(timezone.utc)
    token = encode_jwt(
        {
            "sub": actor_id,
            "email": email,
            "role": role,
            "tenant_id": TENANT_ID,
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=2)).timestamp()),
        }
    )
    return thread_id, actor_id, token


def _audit_count(thread_id: str, command_id: str) -> int:
    with psycopg.connect(_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) FROM communication_command_audits
                WHERE tenant_id = %s AND thread_id = %s AND command_id = %s
                """,
                (TENANT_ID, thread_id, command_id),
            )
            return int(cur.fetchone()[0])


def _post(
    client: httpx.Client,
    token: str,
    thread_id: str,
    command: str,
    body: dict[str, Any] | None,
) -> tuple[int, dict[str, Any]]:
    url = f"{BASE}/threads/{thread_id}/commands/{command}"
    resp = client.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=body if body is not None else {},
        timeout=30.0,
    )
    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}
    return resp.status_code, data if isinstance(data, dict) else {"raw": data}


def _get_context(
    client: httpx.Client, token: str, thread_id: str
) -> tuple[int, dict[str, Any]]:
    url = f"{BASE}/threads/{thread_id}/context"
    resp = client.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
    )
    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}
    return resp.status_code, data if isinstance(data, dict) else {"raw": data}


def run() -> None:
    thread_id, actor_id, token = _prepare()
    print(f"SMOKE thread={thread_id} actor={actor_id}")
    results: list[dict[str, Any]] = []
    prev_version = 1

    with httpx.Client() as client:
        code, ctx0 = _get_context(client, token, thread_id)
        if code != 200:
            _fail(f"GET context HTTP {code}: {ctx0}")
        _assert_full_context(ctx0, "baseline")
        prev_version = _work_version(ctx0)
        print(f"baseline work_version={prev_version} queues={sorted(_queues(ctx0))}")

        steps: list[tuple[str, dict[str, Any] | None, dict[str, Any]]] = [
            (
                "AssignThread",
                {
                    "assignee_id": actor_id,
                    "reason": "manual",
                    "expected_work_version": prev_version,
                },
                {
                    "expect_applied": True,
                    "queues_any": {"assigned_to_me"},
                    "queues_none": {"unassigned"},
                },
            ),
            (
                "AssignThread",
                {"assignee_id": actor_id, "reason": "manual"},
                {"expect_applied": False, "noop": True},
            ),
            (
                "MarkThreadUnread",
                {},
                {"expect_applied": True, "queues_any": {"new_inbound"}},
            ),
            (
                "MarkThreadUnread",
                {},
                {"expect_applied": False, "noop": True},
            ),
            (
                "MarkThreadRead",
                {},
                {"expect_applied": True, "queues_none": {"new_inbound"}},
            ),
            (
                "MarkThreadRead",
                {},
                {"expect_applied": False, "noop": True},
            ),
            (
                "SetNextAction",
                {
                    "action_type": "call_back",
                    "owner_id": actor_id,
                    "source": "manual",
                    "note": "C1 smoke",
                },
                {"expect_applied": True},
            ),
            (
                "CompleteNextAction",
                {},
                {"expect_applied": True},
            ),
            (
                "CompleteNextAction",
                {},
                {"expect_applied": False, "noop": True},
            ),
            (
                "PauseSLA",
                {},
                {"expect_applied": True},
            ),
            (
                "PauseSLA",
                {},
                {"expect_applied": False, "noop": True},
            ),
            (
                "ResumeSLA",
                {},
                {"expect_applied": True},
            ),
            (
                "ResumeSLA",
                {},
                {"expect_applied": False, "noop": True},
            ),
            (
                "CloseThread",
                {},
                {"expect_applied": True, "queues_any": {"closed"}},
            ),
            (
                "CloseThread",
                {},
                {"expect_applied": False, "noop": True},
            ),
            (
                "ReopenThread",
                {},
                {"expect_applied": True, "queues_none": {"closed"}},
            ),
            (
                "ReopenThread",
                {},
                {"expect_applied": False, "noop": True},
            ),
        ]

        for command, body, expect in steps:
            audits_before = _audit_count(thread_id, command)
            code, payload = _post(client, token, thread_id, command, body)
            if code >= 500:
                _fail(f"{command}: HTTP {code} {payload}")
            if code != 200:
                _fail(f"{command}: HTTP {code} {payload}")

            applied = bool(payload.get("applied"))
            ctx = payload.get("context") or {}
            _assert_full_context(ctx, command)
            version = _work_version(ctx)
            audit_id = payload.get("audit_id")
            audits_after = _audit_count(thread_id, command)

            want_applied = bool(expect.get("expect_applied"))
            if applied != want_applied:
                _fail(
                    f"{command}: applied={applied} expected={want_applied} "
                    f"payload={json.dumps(payload)[:500]}"
                )

            if want_applied:
                if version != prev_version + 1:
                    _fail(
                        f"{command}: work_version {prev_version} -> {version}, expected +1"
                    )
                if not audit_id:
                    _fail(f"{command}: applied but audit_id missing")
                if audits_after != audits_before + 1:
                    _fail(
                        f"{command}: audit count {audits_before} -> {audits_after}, expected +1"
                    )
                prev_version = version
            else:
                if version != prev_version:
                    _fail(
                        f"{command}: no-op changed work_version {prev_version} -> {version}"
                    )
                if audit_id is not None:
                    _fail(f"{command}: no-op returned audit_id={audit_id}")
                if audits_after != audits_before:
                    _fail(
                        f"{command}: no-op created audit ({audits_before} -> {audits_after})"
                    )

            qs = _queues(ctx)
            for q in expect.get("queues_any") or set():
                if q not in qs:
                    _fail(f"{command}: expected queue {q} in {sorted(qs)}")
            for q in expect.get("queues_none") or set():
                if q in qs:
                    _fail(f"{command}: unexpected queue {q} in {sorted(qs)}")

            if command == "CloseThread" and applied:
                if (ctx.get("identity") or {}).get("thread", {}).get("status") != "closed":
                    _fail("CloseThread: identity.status != closed")
                if not (ctx.get("work_state") or {}).get("is_archived"):
                    _fail("CloseThread: is_archived not true")
            if command == "ReopenThread" and applied:
                status = (ctx.get("identity") or {}).get("thread", {}).get("status")
                if status == "closed":
                    _fail("ReopenThread: still closed")
                if (ctx.get("work_state") or {}).get("is_archived"):
                    _fail("ReopenThread: still archived")

            row = {
                "command": command,
                "http": code,
                "applied": applied,
                "work_version": version,
                "audit_delta": audits_after - audits_before,
                "queues": sorted(qs),
            }
            results.append(row)
            print(
                f"OK {command}: applied={applied} wv={version} "
                f"audits+{row['audit_delta']} queues={row['queues']}"
            )

        code, ctx_final = _get_context(client, token, thread_id)
        if code != 200:
            _fail(f"final GET context HTTP {code}: {ctx_final}")
        _assert_full_context(ctx_final, "final")
        if _work_version(ctx_final) != prev_version:
            _fail(
                f"final context work_version mismatch: "
                f"{_work_version(ctx_final)} vs {prev_version}"
            )

    print("SUMMARY")
    print(
        json.dumps(
            {
                "thread_id": thread_id,
                "final_work_version": prev_version,
                "steps": results,
            },
            indent=2,
        )
    )
    print("SMOKE_PASS")


if __name__ == "__main__":
    run()
