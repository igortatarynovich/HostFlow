from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.services.risk_intel_v1 import compute_candidate_risk_map_for_ids


@dataclass(frozen=True)
class CandidateRisk:
    risk_score: int  # 0..100
    risk_band: str  # low|medium|high|critical
    risk_updated_at: datetime
    risk_drivers: List[str]
    risk_version: str


async def compute_candidate_risk_scores(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidates_by_id: Dict[str, Candidate],
    now: datetime,
) -> Dict[str, CandidateRisk]:
    """Candidate list risk fields — risk_model_v1 via `compute_candidate_risk_map_for_ids` (tenant config)."""
    if not candidates_by_id:
        return {}
    now_utc = now.astimezone(timezone.utc) if now.tzinfo else now.replace(tzinfo=timezone.utc)
    raw = await compute_candidate_risk_map_for_ids(
        db,
        tenant_id,
        list(candidates_by_id.keys()),
        now=now_utc,
    )
    out: Dict[str, CandidateRisk] = {}
    for cid, row in raw.items():
        ru = row.get("risk_updated_at") or now_utc
        if isinstance(ru, datetime) and ru.tzinfo is None:
            ru = ru.replace(tzinfo=timezone.utc)
        out[cid] = CandidateRisk(
            risk_score=int(row["risk_score"]),
            risk_band=str(row["risk_band"]),
            risk_updated_at=ru if isinstance(ru, datetime) else now_utc,
            risk_drivers=list(row.get("risk_drivers") or []),
            risk_version=str(row.get("risk_version") or "risk_model_v1"),
        )
    return out
