#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from typing import Any, Dict, Optional, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor


def _as_dict(value: Any) -> Dict[str, Any]:
    if not value:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return dict(parsed)
        except Exception:
            return {}
    return {}


def _normalize_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int,)):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if not text:
            return None
        if text in {"true", "yes", "1", "y", "да"}:
            return True
        if text in {"false", "no", "0", "n", "нет"}:
            return False
    return None


def _extract_fields(normalized: Dict[str, Any]) -> Tuple[Optional[str], Optional[bool], Optional[str]]:
    preferred_contact = normalized.get("preferred_contact")
    if isinstance(preferred_contact, str):
        preferred_contact = preferred_contact.strip() or None
    else:
        preferred_contact = None

    in_poland = _normalize_bool(normalized.get("in_poland"))

    poland_basis = normalized.get("poland_stay_basis")
    if isinstance(poland_basis, str):
        poland_basis = poland_basis.strip() or None
    else:
        poland_basis = None

    return preferred_contact, in_poland, poland_basis


def _process(conn, tenant_id: str, dry_run: bool) -> Dict[str, int]:
    stats = {"processed": 0, "updated": 0, "skipped_no_data": 0, "skipped_missing_candidate": 0}

    with conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, true)", (tenant_id,))

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, candidate_id, normalized
            FROM leads
            WHERE tenant_id = %s
              AND source = 'meta'
              AND candidate_id IS NOT NULL
            ORDER BY created_at ASC
            """,
            (tenant_id,),
        )
        leads = cur.fetchall()

    for lead in leads:
        stats["processed"] += 1
        normalized = _as_dict(lead["normalized"])
        if not normalized:
            stats["skipped_no_data"] += 1
            continue

        preferred_contact, in_poland, poland_basis = _extract_fields(normalized)
        if preferred_contact is None and in_poland is None and poland_basis is None:
            stats["skipped_no_data"] += 1
            continue

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, extra
                FROM candidates
                WHERE id = %s
                  AND tenant_id = %s
                """,
                (lead["candidate_id"], tenant_id),
            )
            candidate = cur.fetchone()

        if not candidate:
            stats["skipped_missing_candidate"] += 1
            continue

        extra = _as_dict(candidate["extra"])
        changed = False
        if preferred_contact is not None and extra.get("preferred_contact") != preferred_contact:
            extra["preferred_contact"] = preferred_contact
            changed = True
        if in_poland is not None and extra.get("in_poland") != in_poland:
            extra["in_poland"] = in_poland
            changed = True
        if poland_basis is not None and extra.get("poland_stay_basis") != poland_basis:
            extra["poland_stay_basis"] = poland_basis
            changed = True

        if not changed:
            continue

        stats["updated"] += 1
        if not dry_run:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE candidates SET extra = %s WHERE id = %s",
                    (json.dumps(extra, ensure_ascii=False, separators=(",", ":")), candidate["id"]),
                )

    if not dry_run and stats["updated"]:
        conn.commit()
    elif dry_run:
        conn.rollback()

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill candidate.extra fields (preferred_contact, in_poland, poland_stay_basis) from stored Meta leads."
    )
    parser.add_argument("--tenant", required=True, help="Tenant UUID to scope the update")
    parser.add_argument("--host", default="db", help="PostgreSQL host (default: db)")
    parser.add_argument("--port", type=int, default=5432, help="PostgreSQL port (default: 5432)")
    parser.add_argument("--user", default="hostflow", help="PostgreSQL user (default: hostflow)")
    parser.add_argument("--password", default="hostflow", help="PostgreSQL password (default: hostflow)")
    parser.add_argument("--database", default="hostflow", help="PostgreSQL database name (default: hostflow)")
    parser.add_argument("--dry-run", action="store_true", help="Do not persist changes, just print stats")

    args = parser.parse_args()

    conn = psycopg2.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        dbname=args.database,
    )
    try:
        stats = _process(conn=conn, tenant_id=args.tenant, dry_run=args.dry_run)
    finally:
        conn.close()

    result = {
        "tenant_id": args.tenant,
        "host": args.host,
        "port": args.port,
        "database": args.database,
        "dry_run": args.dry_run,
        **stats,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
