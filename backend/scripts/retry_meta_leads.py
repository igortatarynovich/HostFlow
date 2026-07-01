#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

# Добавляем корень проекта в путь для импортов ДО всех остальных импортов
THIS = Path(__file__).resolve()
if THIS.parent.name == "scripts" and THIS.parent.parent.name == "backend":
    BACKEND_DIR = THIS.parent.parent
    PROJECT_ROOT = BACKEND_DIR.parent
else:
    PROJECT_ROOT = THIS.parent.parent
    BACKEND_DIR = PROJECT_ROOT / "backend"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import argparse
import asyncio
import json
from typing import List, Optional

from backend.app.core.settings import settings  # noqa: F401 - ensure settings initialised
from backend.app.db.session import async_session_maker
from backend.app.modules.leads import service


def _parse_statuses(values: Optional[List[str]]) -> Optional[List[str]]:
    if not values:
        return None
    normalized: List[str] = []
    for value in values:
        text = (value or "").strip().lower()
        if text:
            normalized.append(text)
    return normalized or None


async def _run(
    tenant_id: str,
    lead_ids: Optional[List[str]],
    statuses: Optional[List[str]],
    limit: Optional[int],
    refresh_graph: bool,
) -> None:
    async with async_session_maker() as session:
        outcomes = await service.retry_meta_leads(
            session,
            tenant_id=tenant_id,
            own_company_id=None,
            lead_ids=lead_ids,
            statuses=statuses,
            limit=limit,
            refresh_graph=refresh_graph,
        )

        summary = {
            "total": len(outcomes),
            "processed": sum(1 for item in outcomes if item.processed),
            "failed": sum(
                1
                for item in outcomes
                if not item.processed and (item.message is None or "payload" not in (item.message or "").lower())
            ),
            "skipped": sum(
                1
                for item in outcomes
                if item.message and "payload is empty" in item.message.lower()
            ),
        }
        print(json.dumps(summary, indent=2))

        if outcomes:
            details = [
                {
                    "lead_id": item.lead_id,
                    "status_before": item.status_before,
                    "status_after": item.status_after,
                    "candidate_id": item.candidate_id,
                    "error_before": item.error_before,
                    "error_after": item.error_after,
                    "processed": item.processed,
                    "message": item.message,
                }
                for item in outcomes
            ]
            print(json.dumps(details, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Retry Meta leads ingestion for existing records.")
    parser.add_argument("--tenant", default="11111111-1111-1111-1111-111111111111", help="Tenant UUID scope")
    parser.add_argument("--lead", action="append", dest="leads", help="Specific lead ID to retry")
    parser.add_argument(
        "--status",
        action="append",
        dest="statuses",
        help="Retry leads with given status (default: failed, needs_routing)",
    )
    parser.add_argument("--limit", type=int, default=None, help="Limit number of leads to retry")
    parser.add_argument("--no-graph", action="store_true", help="Skip Graph API hydration during retry")

    args = parser.parse_args()

    statuses = _parse_statuses(args.statuses)
    if statuses is None and not args.leads:
        statuses = ["failed", "needs_routing"]

    asyncio.run(
        _run(
            tenant_id=args.tenant,
            lead_ids=args.leads,
            statuses=statuses,
            limit=args.limit,
            refresh_graph=not args.no_graph,
        )
    )


if __name__ == "__main__":
    main()
