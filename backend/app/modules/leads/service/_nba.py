"""Lead next-best-action (NBA) snapshots.

Extracted from ``backend/app/modules/leads/service/__init__.py`` (Phase 1 #3
god-module split, step 5/N): plan-gating helper, funnel-derived insight
groups, and the public ``lead_next_actions_snapshot`` endpoint that powers
GET /next-actions.

Re-exported via ``service/__init__.py`` so router/tests keep using the
historical ``service.lead_next_actions_snapshot`` access pattern.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Literal, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.constants.spa_paths import (
    CANDIDATES_NO_NEXT_ACTION_PAGE,
    LEADS as SPA_LEADS,
    TASKS,
)
from backend.app.modules.leads.schemas import (
    LeadNextActionsResponse,
    NextActionGroupOut,
    NextActionQueryParams,
)
from backend.app.services.plan_feature_gates import (
    plan_allows_team_tier_features,
    plan_is_pro_tier,
    resolve_tenant_plan_code,
)

from ._funnel import ConversionFunnelSliceParams, lead_conversion_funnel_snapshot
from ._listing import (
    count_candidate_overdue_reminders_for_assignee,
    count_candidates_no_next_action_for_assignee,
    count_leads,
)


def _nba_lead_locked_and_required(
    min_plan: Optional[str],
    *,
    plan: str,
    team_ok: bool,
    tenant_id: str | None = None,
) -> tuple[bool, Optional[str]]:
    """If bucket requires a higher plan, return (locked, required_plan code for UI)."""
    if not min_plan:
        return False, None
    mp = str(min_plan).strip().lower()
    if mp == "team":
        if team_ok:
            return False, None
        return True, "team"
    if mp == "pro":
        if plan_is_pro_tier(plan, tenant_id=tenant_id):
            return False, None
        return True, "pro"
    return False, None


NBA_FUNNEL_MIN_TOTAL_WIN = 5
NBA_FUNNEL_MIN_AT_OR_BEYOND = 6
NBA_FUNNEL_WEAK_SHARE_MAX = 0.49
NBA_FUNNEL_SLOW_DWELL_DAYS = 5.0
NBA_FUNNEL_MIN_DWELL_SAMPLE = 3


async def nba_conversion_funnel_insight_groups(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None,
    plan: str,
    team_ok: bool,
) -> List[NextActionGroupOut]:
    """
    Deterministic §2.12 funnel signals merged into GET /next-actions (bridge toward NBA).
    No extra HTTP round-trip on the dashboard.
    Same paywall as conversion-funnel slices: Team-tier unlocks actionable insight chips (§2.12).
    """
    funnel = await lead_conversion_funnel_snapshot(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        slice_params=ConversionFunnelSliceParams(),
    )
    if not funnel.stages:
        return []
    total_win = int(sum(int(s.count) for s in funnel.stages))
    if total_win < NBA_FUNNEL_MIN_TOTAL_WIN:
        return []
    insight_locked, insight_required_plan = _nba_lead_locked_and_required(
        "team", plan=plan, team_ok=team_ok, tenant_id=tenant_id
    )
    out: List[NextActionGroupOut] = []

    worst_idx: Optional[int] = None
    worst_share: Optional[float] = None
    for i, edge in enumerate(funnel.edges):
        if edge.progressed_share is None:
            continue
        at_here = int(funnel.stages[i].at_or_beyond)
        if at_here < NBA_FUNNEL_MIN_AT_OR_BEYOND:
            continue
        sh = float(edge.progressed_share)
        if worst_share is None or sh < worst_share:
            worst_share = sh
            worst_idx = i

    if worst_idx is not None and worst_share is not None and worst_share <= NBA_FUNNEL_WEAK_SHARE_MAX:
        from_root = str(funnel.stages[worst_idx].stage)
        at_top = int(funnel.stages[worst_idx].at_or_beyond)
        at_next = (
            int(funnel.stages[worst_idx + 1].at_or_beyond) if worst_idx + 1 < len(funnel.stages) else 0
        )
        drop = max(0, at_top - at_next)
        if drop > 0:
            pct = max(0, min(100, int(round(worst_share * 100))))
            out.append(
                NextActionGroupOut(
                    id="leads_funnel_weak_step",
                    entity="lead",
                    reason="funnel_weak_conversion_step",
                    title="Lead funnel: weak handoff between stages",
                    count=drop,
                    priority=17,
                    query=NextActionQueryParams(status="processed", conversion_root=from_root),
                    path=SPA_LEADS,
                    locked=insight_locked,
                    required_plan=insight_required_plan,
                    nba_detail={"conversion_root": from_root, "pct": pct},
                )
            )

    slow_stage: Optional[str] = None
    slow_days = 0.0
    slow_bucket_count = 0
    for s in funnel.stages:
        n = int(s.dwell_sample_size or 0)
        if n < NBA_FUNNEL_MIN_DWELL_SAMPLE:
            continue
        if s.dwell_avg_days is None:
            continue
        d = float(s.dwell_avg_days)
        if d >= NBA_FUNNEL_SLOW_DWELL_DAYS and d > slow_days:
            slow_days = d
            slow_stage = str(s.stage)
            slow_bucket_count = int(s.count)

    if slow_stage and slow_bucket_count > 0:
        out.append(
            NextActionGroupOut(
                id="leads_funnel_slow_stage",
                entity="lead",
                reason="funnel_slow_stage_dwell",
                title="Lead funnel: slow stage dwell",
                count=slow_bucket_count,
                priority=16,
                query=NextActionQueryParams(status="processed", conversion_root=slow_stage),
                path=SPA_LEADS,
                locked=insight_locked,
                required_plan=insight_required_plan,
                nba_detail={"conversion_root": slow_stage, "days": round(slow_days, 1)},
            )
        )

    return out


async def lead_next_actions_snapshot(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None = None,
    actor_user_id: str | None = None,
) -> LeadNextActionsResponse:
    """
    NBA: lead buckets (tenant / own_company) + assignee-scoped candidate buckets (§2.3).
    Plan gating: some lead buckets locked on solo/starter — counts still returned; sort: unlocked first.
    """
    plan = await resolve_tenant_plan_code(db, tenant_id)
    team_ok = plan_allows_team_tier_features(plan, tenant_id=tenant_id)
    nba_tier: Literal["solo", "team"] = "team" if team_ok else "solo"

    # (id, reason, title, priority, status, stage, next_action, min_plan)
    specs: List[tuple[str, str, str, int, Optional[str], Optional[str], Optional[str], Optional[str]]] = [
        (
            "leads_no_next_action",
            "no_next_action_on_processed",
            "Processed leads without a next action",
            30,
            "processed",
            None,
            "no_next_action",
            None,
        ),
        (
            "leads_next_overdue",
            "lead_reminder_overdue",
            "Leads with an overdue next action",
            25,
            "processed",
            None,
            "overdue",
            None,
        ),
        (
            "leads_stuck_in_stage",
            "lead_stuck_in_stage",
            "Leads stuck in stage (SLA)",
            20,
            None,
            None,
            "stuck",
            "team",
        ),
        (
            "leads_needs_routing",
            "needs_routing",
            "Leads waiting for routing",
            90,
            "needs_routing",
            None,
            None,
            None,
        ),
        (
            "leads_failed",
            "lead_failed",
            "Failed leads",
            80,
            "failed",
            None,
            None,
            None,
        ),
        (
            "leads_new_unprocessed",
            "lead_new_unprocessed",
            "New leads (not yet processed)",
            15,
            "new",
            None,
            None,
            None,
        ),
    ]
    groups: List[NextActionGroupOut] = []
    for gid, reason, title, priority, st, stg, na, min_plan in specs:
        cnt = await count_leads(
            db,
            tenant_id=tenant_id,
            own_company_id=own_company_id,
            status=st,
            stage=stg,
            next_action=na,
        )
        locked, req = _nba_lead_locked_and_required(min_plan, plan=plan, team_ok=team_ok, tenant_id=tenant_id)
        groups.append(
            NextActionGroupOut(
                id=gid,
                entity="lead",
                reason=reason,
                title=title,
                count=cnt,
                priority=priority,
                query=NextActionQueryParams(status=st, stage=stg, next_action=na),
                locked=locked,
                required_plan=req,
            )
        )

    # §2.10: NBA drill-down for Meta fit gate errors (exact Lead.error, needs_routing).
    for gid, reason, title, priority, pe in (
        ("leads_fit_no_match", "lead_fit_no_match", "Leads: no vacancy fit (pipeline)", 92, "LEAD_FIT_NO_MATCH"),
        ("leads_fit_needs_info", "lead_fit_needs_info", "Leads: need more info (pipeline)", 91, "LEAD_FIT_NEEDS_INFO"),
    ):
        cnt_fit = await count_leads(
            db,
            tenant_id=tenant_id,
            own_company_id=own_company_id,
            status="needs_routing",
            pipeline_error=pe,
        )
        locked_fit, req_fit = _nba_lead_locked_and_required(None, plan=plan, team_ok=team_ok, tenant_id=tenant_id)
        groups.append(
            NextActionGroupOut(
                id=gid,
                entity="lead",
                reason=reason,
                title=title,
                count=cnt_fit,
                priority=priority,
                query=NextActionQueryParams(status="needs_routing", pipeline_error=pe),
                locked=locked_fit,
                required_plan=req_fit,
            )
        )

    aid = (actor_user_id or "").strip()
    if aid:
        c_nna = await count_candidates_no_next_action_for_assignee(
            db,
            tenant_id=tenant_id,
            assignee_id=aid,
            own_company_id=own_company_id,
        )
        groups.append(
            NextActionGroupOut(
                id="candidates_no_next_action",
                entity="candidate",
                reason="candidate_no_next_action",
                title="Candidates without a next action (you)",
                count=c_nna,
                priority=28,
                query=NextActionQueryParams(),
                path=CANDIDATES_NO_NEXT_ACTION_PAGE,
                locked=False,
                required_plan=None,
            )
        )
        c_ov = await count_candidate_overdue_reminders_for_assignee(
            db,
            tenant_id=tenant_id,
            assignee_id=aid,
            own_company_id=own_company_id,
        )
        groups.append(
            NextActionGroupOut(
                id="candidates_next_overdue",
                entity="candidate",
                reason="candidate_reminder_overdue",
                title="Candidate reminders overdue (you)",
                count=c_ov,
                priority=23,
                query=NextActionQueryParams(
                    tab="tasks",
                    t_status="active",
                    t_entity="candidate",
                    t_due_bucket="overdue",
                ),
                path=TASKS,
                locked=False,
                required_plan=None,
            )
        )

    funnel_groups = await nba_conversion_funnel_insight_groups(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        plan=plan,
        team_ok=team_ok,
    )
    groups.extend(funnel_groups)

    groups.sort(key=lambda g: (g.locked, -g.priority, -g.count, g.id))
    return LeadNextActionsResponse(
        generated_at=datetime.now(timezone.utc),
        own_company_id=own_company_id,
        plan_code=plan,
        nba_tier=nba_tier,
        groups=groups,
    )
