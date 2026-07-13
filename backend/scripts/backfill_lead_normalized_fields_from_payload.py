#!/usr/bin/env python3
"""Backfill normalized lead fields from the raw Meta payload.

The lead list computes vacancy fit live from ``lead.normalized`` (see
``service/_listing.py``). Historically several Russian/Polish Meta form
questions were not recognised by the normalizer, so answers that clearly
existed in the payload (most importantly "стаж в ЕС" / EU CE experience)
never made it into ``normalized`` — which made every such lead render
"Не указан стаж в ЕС (лет)".

This script re-derives the standard normalized fields from each Meta lead's
stored payload and fills in the values that are currently MISSING. It never
overwrites values that are already present (so operator edits and pipeline
blocks are preserved) and is safe to run repeatedly.

Usage:
    cd /opt/HostFlow/backend
    python3 scripts/backfill_lead_normalized_fields_from_payload.py            # dry-run
    python3 scripts/backfill_lead_normalized_fields_from_payload.py --apply     # write
    python3 scripts/backfill_lead_normalized_fields_from_payload.py --apply --tenant <uuid>
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

THIS = Path(__file__).resolve()
BACKEND_DIR = THIS.parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
for p in (str(PROJECT_ROOT), str(BACKEND_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import psycopg  # noqa: E402

from backend.app.modules.leads.normalizer import normalize_meta_payload  # noqa: E402

# Fields the normalizer derives from the form answers. We only fill them when
# they are absent from the current normalized blob so nothing is clobbered.
STRING_FILL_KEYS = (
    "driving_experience_in_europe",
    "preferred_contact",
    "preferred_contact_raw",
    "poland_stay_basis",
    "poland_stay_basis_raw",
    "geo_country",
    "geo_country_raw",
)


def _sync_dsn() -> str:
    dsn = os.environ.get("SYNC_DATABASE_URL")
    if not dsn:
        env_path = BACKEND_DIR / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("SYNC_DATABASE_URL="):
                    dsn = line.split("=", 1)[1].strip()
                    break
    if not dsn:
        raise SystemExit("SYNC_DATABASE_URL not configured")
    # psycopg wants a libpq DSN, not the SQLAlchemy driver prefix.
    return dsn.replace("postgresql+psycopg://", "postgresql://").replace(
        "postgresql+asyncpg://", "postgresql://"
    )


def _as_dict(value) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


def _compute_patch(payload: dict, normalized: dict) -> dict:
    """Return the fields that are derivable now but missing in ``normalized``."""
    fresh = normalize_meta_payload(payload)
    patch: dict = {}

    exp = fresh.get("experience_eu_years")
    if isinstance(exp, int) and normalized.get("experience_eu_years") is None:
        patch["experience_eu_years"] = exp

    fresh_in_poland = fresh.get("in_poland")
    if isinstance(fresh_in_poland, bool) and normalized.get("in_poland") is None:
        patch["in_poland"] = fresh_in_poland

    for key in STRING_FILL_KEYS:
        val = fresh.get(key)
        if val is None:
            continue
        if key not in normalized or normalized.get(key) in (None, ""):
            patch[key] = val

    return patch


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Persist changes (default: dry-run)")
    parser.add_argument("--tenant", default=None, help="Restrict to a single tenant UUID")
    parser.add_argument("--limit", type=int, default=None, help="Process at most N leads")
    args = parser.parse_args()

    where = ["source = 'meta'", "payload IS NOT NULL"]
    params: list = []
    if args.tenant:
        where.append("tenant_id = %s")
        params.append(args.tenant)
    sql = f"SELECT id, payload, normalized FROM leads WHERE {' AND '.join(where)} ORDER BY created_at DESC"
    if args.limit:
        sql += f" LIMIT {int(args.limit)}"

    scanned = 0
    changed = 0
    exp_filled = 0
    samples: list[str] = []

    with psycopg.connect(_sync_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        for lead_id, payload_raw, normalized_raw in rows:
            scanned += 1
            payload = _as_dict(payload_raw)
            if not payload:
                continue
            normalized = _as_dict(normalized_raw)
            patch = _compute_patch(payload, normalized)
            if not patch:
                continue
            changed += 1
            if "experience_eu_years" in patch:
                exp_filled += 1
            if len(samples) < 15:
                samples.append(f"  {lead_id}: +{json.dumps(patch, ensure_ascii=False)}")
            if args.apply:
                merged = {**normalized, **patch}
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE leads SET normalized = %s WHERE id = %s",
                        (json.dumps(merged, ensure_ascii=False), lead_id),
                    )
        if args.apply:
            conn.commit()

    print("=== Backfill normalized lead fields ===")
    print(f"mode:            {'APPLY' if args.apply else 'DRY-RUN'}")
    print(f"scanned:         {scanned}")
    print(f"leads changed:   {changed}")
    print(f"experience_eu_years filled: {exp_filled}")
    if samples:
        print("sample patches:")
        print("\n".join(samples))
    if not args.apply:
        print("\n(dry-run — re-run with --apply to persist)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
