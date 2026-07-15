"""Canonical post-create hooks for Candidate records (ADR-018)."""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate

logger = logging.getLogger(__name__)


async def finalize_new_candidate_record(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
    source: Optional[str] = None,
) -> Optional[str]:
    """Single canonical post-create hook: Driver CE policy pin and future ADR-018 setup.

    Call after Candidate INSERT + flush/commit reload from every creation path.
    """
    from backend.app.services.requirement_policy_assignment import ensure_driver_ce_policy_pin

    try:
        pinned = await ensure_driver_ce_policy_pin(db, tenant_id=tenant_id, candidate=candidate)
        if pinned:
            logger.info(
                "candidate_policy_pinned",
                extra={
                    "event": "candidate_policy_pinned",
                    "candidate_id": str(candidate.id),
                    "tenant_id": tenant_id,
                    "policy_ref": pinned,
                    "source": source or "unknown",
                },
            )
        return pinned
    except Exception:
        logger.debug(
            "Driver CE policy auto-pin skipped for candidate %s (source=%s)",
            candidate.id,
            source,
            exc_info=True,
        )
        return None


__all__ = ["finalize_new_candidate_record"]
