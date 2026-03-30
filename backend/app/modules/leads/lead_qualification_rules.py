"""
§2.10 Qualification routing rules (trigger `lead.qualification` on AutomationRule).

Evaluated after explicit vacancy_id / ad map fails and before Tenant.settings lead_fit_routing_v1
ordered_vacancy_ids scan. Conditions use the same dot-path matcher as automation_rules (``eq``/legacy scalar,
``neq``, ``in``, ``exists``, ``not_exists``, ``$and``) with context:
``{ "source", "normalized": <lead normalized dict> }`` (``source`` in context is lowercased).

Actions (JSON): { "set_vacancy_id": "<uuid>", "set_recruiter_id": "<user uuid optional>",
  "note": "optional" }
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import Vacancy
from backend.app.models.automation_rule import AutomationRule
from backend.app.modules.leads import crud
from backend.app.modules.leads.lead_criteria_eval import evaluate_vacancy_for_lead
from backend.app.modules.leads.recruiter_validation import validate_tenant_recruiter_id
from backend.app.services.automation_rules import _matches_conditions

logger = logging.getLogger(__name__)

LEAD_QUALIFICATION_TRIGGER = "lead.qualification"


def _normalize_lq_rule_conditions(conditions: Dict[str, Any]) -> Dict[str, Any]:
    """Lowercase string `source` clause values so they align with qualification context."""
    if not isinstance(conditions, dict):
        return conditions
    out = dict(conditions)
    and_list = out.get("$and")
    if isinstance(and_list, list):
        out["$and"] = [
            _normalize_lq_rule_conditions(x) if isinstance(x, dict) else x for x in and_list
        ]
    src = out.get("source")
    if isinstance(src, str) and src.strip():
        out["source"] = src.strip().lower()
    elif isinstance(src, dict) and str(src.get("op") or "").strip():
        op = str(src.get("op") or "").strip().lower()
        nv = dict(src)
        v = nv.get("value", nv.get("v"))
        if op in ("eq", "==") and isinstance(v, str):
            nv["value"] = v.strip().lower()
        elif op == "in" and isinstance(v, list):
            nv["value"] = [str(x or "").strip().lower() for x in v]
        out["source"] = nv
    return out


def _loads_conditions(raw: Optional[str]) -> dict:
    if not raw:
        return {}
    try:
        v = json.loads(raw)
        return v if isinstance(v, dict) else {}
    except Exception:
        return {}


def _loads_actions(raw: Optional[str]) -> dict:
    if not raw:
        return {}
    try:
        v = json.loads(raw)
        return v if isinstance(v, dict) else {}
    except Exception:
        return {}


def _qualification_context(*, source: str, normalized: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "source": str(source or "").strip().lower(),
        "normalized": normalized if isinstance(normalized, dict) else {},
    }


async def pick_vacancy_via_qualification_rules(
    db: AsyncSession,
    *,
    tenant_id: str,
    source: str,
    normalized: Dict[str, Any],
    own_company_id: Optional[str] = None,
) -> Optional[Tuple[Vacancy, str, List[str]]]:
    """
    First matching enabled rule (priority desc, created_at asc).
    Stamps normalized['lead_qualification_rule_match_v1'] when a rule matches (even if fit fails later).
    Returns (vacancy, fit_status, fit_reasons) or None.
    """
    stmt = (
        select(AutomationRule)
        .where(
            AutomationRule.tenant_id == tenant_id,
            AutomationRule.enabled.is_(True),
            AutomationRule.trigger == LEAD_QUALIFICATION_TRIGGER,
        )
        .order_by(AutomationRule.priority.desc(), AutomationRule.created_at.asc())
    )
    rows = await db.execute(stmt)
    rules = list(rows.scalars().all())
    if not rules:
        return None

    ctx = _qualification_context(source=source, normalized=normalized)
    for rule in rules:
        conditions = _normalize_lq_rule_conditions(_loads_conditions(rule.conditions_json))
        if not _matches_conditions(conditions, ctx):
            continue
        actions = _loads_actions(rule.actions_json)
        vid = actions.get("set_vacancy_id")
        if not vid:
            logger.warning(
                "lead.qualification rule %s has no set_vacancy_id; tenant=%s",
                rule.id,
                tenant_id,
            )
            continue
        vacancy = await crud.resolve_vacancy_by_id(
            db, tenant_id, str(vid).strip(), scoped_own_company_id=own_company_id
        )
        if vacancy is None:
            continue
        st, rs = evaluate_vacancy_for_lead(normalized, vacancy.extra)
        rid_raw = actions.get("set_recruiter_id")
        rid_ok: Optional[str] = None
        if rid_raw is not None and str(rid_raw).strip():
            rid_ok = await validate_tenant_recruiter_id(
                db, tenant_id, str(rid_raw).strip()
            )
            if rid_ok is None:
                logger.warning(
                    "lead.qualification rule %s set_recruiter_id ignored (invalid/inactive user); tenant=%s",
                    rule.id,
                    tenant_id,
                )
        stamp: Dict[str, Any] = {
            "rule_id": str(rule.id),
            "title": rule.title,
            "priority": int(getattr(rule, "priority", 0) or 0),
            "vacancy_id": str(vacancy.id),
            "fit_status": st,
            "note": actions.get("note"),
        }
        if rid_ok:
            stamp["recruiter_id"] = rid_ok
        normalized["lead_qualification_rule_match_v1"] = stamp
        return vacancy, st, list(rs or [])
    return None
