"""
Risk intelligence v1 — metric extraction + transparent weighted score (SSOT).

Phase A: on-demand aggregates. Phase B: hourly persistence + shadow cohort rows + trends/validation APIs.
Config: Tenant.settings["risk_model_v1"] overrides defaults.
"""

from __future__ import annotations

import logging
import math
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Literal, Mapping, MutableMapping, Optional, Sequence, Tuple

from sqlalchemy import and_, case, delete, func, or_, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from backend.app.constants.stages import ORDER as STAGE_ORDER, PIPELINE_COMPLETED_STAGE_CODES, TERMINAL_STATUSES
from backend.app.models import Candidate, CandidateStageHistory, ContactAttempt, Reminder, Tenant
from backend.app.models.risk_intel import RiskIntelEntityShadow, RiskIntelTenantHourly
from backend.app.models.communication import CommunicationMessage, CommunicationThread
from backend.app.models.reminder import ReminderStatus
from backend.app.services.automation_rules import RISK_BAND_ORDER

RiskBand = Literal["low", "medium", "high", "critical"]

logger = logging.getLogger(__name__)

ACTIVE_REMINDER_STATUSES = (
    ReminderStatus.pending,
    ReminderStatus.new,
    ReminderStatus.overdue,
)


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def decay_factor(delay: float, half_life: float) -> float:
    """SSOT: decay(t,h) = 0.5^(t/h); success weight 0..1."""
    if half_life <= 0:
        return 0.0 if delay > 0 else 1.0
    if delay <= 0:
        return 1.0
    return float(math.pow(0.5, delay / half_life))


def risk_from_delay_hours(delay_h: float, half_life_h: float) -> float:
    """0..100 risk from delay using decay complement."""
    return round(100.0 * (1.0 - decay_factor(delay_h, half_life_h)), 2)


def band_from_score(score: float) -> RiskBand:
    if score < 35:
        return "low"
    if score < 65:
        return "medium"
    if score < 85:
        return "high"
    return "critical"


def drivers_from_components(
    response_component: float,
    stagnation_risk: float,
    action_risk: float,
    context_risk: float,
) -> list[str]:
    drivers: list[tuple[str, float]] = [
        ("First response / inbound reply", response_component),
        ("Stage stagnation", stagnation_risk),
        ("Next action discipline", action_risk),
        ("Engagement (messages 7d)", context_risk),
    ]
    drivers.sort(key=lambda x: -x[1])
    labels = [f"{name}: {round(val, 1)}" for name, val in drivers[:3] if val >= 8.0]
    if not labels:
        labels = ["No strong risk drivers (v1 model)"]
    return labels


def hour_bucket_start(dt: datetime) -> datetime:
    u = _utc(dt) or datetime.now(timezone.utc)
    return u.replace(minute=0, second=0, microsecond=0)


def _stage_index(code: str | None) -> int:
    if not code:
        return -1
    try:
        return STAGE_ORDER.index(code)
    except ValueError:
        return len(STAGE_ORDER)


def _deep_merge_defaults(defaults: dict[str, Any], over: Any) -> dict[str, Any]:
    if not isinstance(over, dict):
        return dict(defaults)
    out: dict[str, Any] = dict(defaults)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge_defaults(out[k], v)  # type: ignore[arg-type]
        else:
            out[k] = v
    return out


def resolve_risk_config(tenant_settings: Mapping[str, Any] | None) -> dict[str, Any]:
    raw = {}
    if isinstance(tenant_settings, dict):
        raw = tenant_settings.get("risk_model_v1") or {}
    defaults: dict[str, Any] = {
        "weights": {
            "response": 0.35,
            "stagnation": 0.25,
            "action": 0.25,
            "context": 0.15,
        },
        "half_lives_hours": {
            "candidate_first_response": 30.0,
            "inbound_unanswered": 12.0,
        },
        "half_lives_days": {
            "stage_stagnation": 5.0,
        },
        "default_stage_baseline_days": 5.0,
        "stage_baseline_days": {},
        "context": {
            "low_interaction_messages_7d": 2,
            "low_interaction_risk": 45.0,
        },
        "stage_gate": {
            "enabled": False,
            "block_forward_without_next_action": True,
            "min_band": "critical",
        },
        "digest_email": {
            "enabled": False,
            "to": [],
            "to_roles": [],
            "min_band": "high",
            "max_rows": 25,
            "skip_if_empty": True,
        },
    }
    merged = _deep_merge_defaults(defaults, raw)
    w = merged.get("weights") or {}
    if isinstance(w, dict):
        s = sum(float(x) for x in w.values() if isinstance(x, (int, float)))
        if s > 0 and abs(s - 1.0) > 0.05:
            merged["weights"] = {k: float(v) / s for k, v in w.items() if isinstance(v, (int, float))}
    return merged


def _candidate_id_expr() -> ColumnElement[Any]:
    return func.coalesce(
        CommunicationThread.linked_candidate_id,
        case((CommunicationThread.entity_type == "candidate", CommunicationThread.entity_id), else_=None),
    )


@dataclass
class RiskMetricBundle:
    first_attempt: dict[str, datetime]
    first_outbound_msg: dict[str, datetime]
    thread_rollups: dict[str, dict[str, datetime | None]]
    msg_count_7d: dict[str, int]
    reminders_by_cand: dict[str, list[tuple[str, datetime, datetime | None]]]
    history_by_cand: dict[str, list[tuple[str | None, str, datetime]]]
    reopen_30d: dict[str, int]
    cutoff_7d: datetime


def _chunks(xs: Sequence[str], n: int) -> List[List[str]]:
    return [list(xs[i : i + n]) for i in range(0, len(xs), n)]


async def _batch_candidate_assignees(
    db: AsyncSession,
    tenant_id: str,
    candidate_ids: list[str],
) -> dict[str, str | None]:
    """Map candidate id → recruiter_id or manager (for risk automation assignee)."""
    out: dict[str, str | None] = {}
    if not candidate_ids:
        return out
    for batch in _chunks(candidate_ids, 400):
        r = await db.execute(
            select(Candidate.id, Candidate.manager, Candidate.recruiter_id).where(
                Candidate.tenant_id == tenant_id,
                Candidate.deleted_at.is_(None),
                Candidate.id.in_(batch),
            )
        )
        for cid, manager, recruiter_id in r.all():
            owner = recruiter_id or manager
            out[str(cid)] = str(owner).strip() if owner else None
    return out


async def _load_risk_metric_bundle(
    db: AsyncSession,
    tenant_id: str,
    candidate_ids: list[str],
    now_utc: datetime,
) -> RiskMetricBundle:
    """Batch-load inputs for risk_model_v1 for a fixed candidate id set (tenant-scoped)."""
    first_attempt: dict[str, datetime] = {}
    first_outbound_msg: dict[str, datetime] = {}
    thread_rollups: dict[str, dict[str, datetime | None]] = {}
    msg_count_7d: dict[str, int] = {}
    cutoff_7d = now_utc - timedelta(days=7)
    cutoff_30d = now_utc - timedelta(days=30)
    cid_expr = _candidate_id_expr()

    for batch in _chunks(candidate_ids, 400):
        ar = (
            await db.execute(
                select(ContactAttempt.candidate_id, func.min(ContactAttempt.attempted_at))
                .join(Candidate, ContactAttempt.candidate_id == Candidate.id)
                .where(
                    Candidate.tenant_id == tenant_id,
                    Candidate.deleted_at.is_(None),
                    ContactAttempt.candidate_id.in_(batch),
                )
                .group_by(ContactAttempt.candidate_id)
            )
        ).all()
        for cid, ts in ar:
            if cid and ts:
                tsu = _utc(ts)
                if tsu:
                    first_attempt[str(cid)] = tsu

        thread_clause = or_(
            CommunicationThread.linked_candidate_id.in_(batch),
            and_(CommunicationThread.entity_type == "candidate", CommunicationThread.entity_id.in_(batch)),
        )
        tr = (
            await db.execute(
                select(
                    cid_expr,
                    func.max(CommunicationThread.last_outbound_at),
                    func.max(CommunicationThread.last_inbound_at),
                    func.max(CommunicationThread.last_message_at),
                )
                .where(CommunicationThread.tenant_id == tenant_id, thread_clause, cid_expr.isnot(None))
                .group_by(cid_expr)
            )
        ).all()
        for cid, lo, li, lm in tr:
            if not cid:
                continue
            key = str(cid)
            prev = thread_rollups.get(key) or {}
            thread_rollups[key] = {
                "last_out": max_dt(prev.get("last_out"), _utc(lo)),
                "last_in": max_dt(prev.get("last_in"), _utc(li)),
                "last_msg": max_dt(prev.get("last_msg"), _utc(lm)),
            }

        fo = (
            await db.execute(
                select(
                    cid_expr,
                    func.min(CommunicationMessage.created_at),
                )
                .select_from(CommunicationMessage)
                .join(CommunicationThread, CommunicationMessage.thread_id == CommunicationThread.id)
                .where(
                    CommunicationMessage.tenant_id == tenant_id,
                    thread_clause,
                    cid_expr.isnot(None),
                    CommunicationMessage.direction == "outbound",
                    CommunicationMessage.is_internal_note.is_(False),
                )
                .group_by(cid_expr)
            )
        ).all()
        for cid, ts in fo:
            if cid and ts:
                tsu = _utc(ts)
                if tsu:
                    cur = first_outbound_msg.get(str(cid))
                    if cur is None or tsu < cur:
                        first_outbound_msg[str(cid)] = tsu

        mc = (
            await db.execute(
                select(cid_expr, func.count())
                .select_from(CommunicationMessage)
                .join(CommunicationThread, CommunicationMessage.thread_id == CommunicationThread.id)
                .where(
                    CommunicationMessage.tenant_id == tenant_id,
                    thread_clause,
                    cid_expr.isnot(None),
                    CommunicationMessage.created_at >= cutoff_7d,
                    CommunicationMessage.is_internal_note.is_(False),
                )
                .group_by(cid_expr)
            )
        ).all()
        for cid, cnt in mc:
            if cid:
                msg_count_7d[str(cid)] = int(cnt or 0)

    reminders_by_cand: dict[str, list[tuple[str, datetime, datetime | None]]] = {}
    for batch in _chunks(candidate_ids, 400):
        rr = (
            await db.execute(
                select(Reminder.entity_id, Reminder.status, Reminder.due_at, Reminder.completed_at)
                .where(
                    Reminder.tenant_id == tenant_id,
                    Reminder.entity_type == "candidate",
                    Reminder.entity_id.in_(batch),
                )
            )
        ).all()
        for eid, st, due, completed in rr:
            if not eid:
                continue
            reminders_by_cand.setdefault(str(eid), []).append(
                (str(st), _utc(due) or now_utc, _utc(completed))
            )

    history_rows: list[tuple[str, str | None, str, datetime]] = []
    for batch in _chunks(candidate_ids, 400):
        hr = (
            await db.execute(
                select(CandidateStageHistory.candidate_id, CandidateStageHistory.from_code, CandidateStageHistory.to_code, CandidateStageHistory.at)
                .where(
                    CandidateStageHistory.tenant_id == tenant_id,
                    CandidateStageHistory.candidate_id.in_(batch),
                    CandidateStageHistory.at >= now_utc - timedelta(days=400),
                )
                .order_by(CandidateStageHistory.at.asc())
            )
        ).all()
        for cid, fc, tc, at in hr:
            if cid and tc and at:
                history_rows.append((str(cid), str(fc) if fc is not None else None, str(tc), _utc(at) or now_utc))

    history_by_cand: dict[str, list[tuple[str | None, str, datetime]]] = {}
    for cid, fc, tc, at in history_rows:
        history_by_cand.setdefault(cid, []).append((fc, tc, at))

    reopen_30d: dict[str, int] = {cid: 0 for cid in candidate_ids}
    for cid, events in history_by_cand.items():
        for fc, tc, at in events:
            if at < cutoff_30d:
                continue
            if fc and _stage_index(fc) > _stage_index(tc):
                reopen_30d[cid] = reopen_30d.get(cid, 0) + 1

    return RiskMetricBundle(
        first_attempt=first_attempt,
        first_outbound_msg=first_outbound_msg,
        thread_rollups=thread_rollups,
        msg_count_7d=msg_count_7d,
        reminders_by_cand=reminders_by_cand,
        history_by_cand=history_by_cand,
        reopen_30d=reopen_30d,
        cutoff_7d=cutoff_7d,
    )


def _evaluate_candidate_risk_row(
    cand: tuple[str, str | None, datetime | None, datetime | None],
    bundle: RiskMetricBundle,
    cfg: dict[str, Any],
    now_utc: datetime,
) -> dict[str, Any]:
    """Per-candidate risk_model_v1 score + driver components (shared list/detail/shadow)."""
    w_resp = float(cfg["weights"]["response"])
    w_stag = float(cfg["weights"]["stagnation"])
    w_act = float(cfg["weights"]["action"])
    w_ctx = float(cfg["weights"]["context"])
    hl_resp_h = float(cfg["half_lives_hours"]["candidate_first_response"])
    hl_inb_h = float(cfg["half_lives_hours"]["inbound_unanswered"])
    hl_stag_d = float(cfg["half_lives_days"]["stage_stagnation"])
    default_base_d = float(cfg["default_stage_baseline_days"])
    stage_base: dict[str, float] = {}
    if isinstance(cfg.get("stage_baseline_days"), dict):
        stage_base = {str(k): float(v) for k, v in cfg["stage_baseline_days"].items() if isinstance(v, (int, float))}
    ctx_cfg = cfg.get("context") or {}
    low_msg_thr = int(ctx_cfg.get("low_interaction_messages_7d") or 2)
    low_msg_risk = float(ctx_cfg.get("low_interaction_risk") or 45.0)

    cid, stage, created_at, _updated = cand
    created = _utc(created_at) or now_utc
    stage_code = stage or ""
    if stage_code in PIPELINE_COMPLETED_STAGE_CODES:
        return {
            "score": 0.0,
            "band": "low",
            "drivers": [],
            "response_component": 0.0,
            "stagnation_risk": 0.0,
            "action_risk": 0.0,
            "context_risk": 0.0,
            "fr_bucket": None,
        }
    terminal = stage_code in TERMINAL_STATUSES
    cutoff_7d = bundle.cutoff_7d

    def stage_entered_at(current_stage: str | None) -> datetime | None:
        if not current_stage:
            return None
        evs = bundle.history_by_cand.get(cid) or []
        entered: datetime | None = None
        for _fc, tc, at in evs:
            if tc == current_stage:
                entered = at
        return entered

    touch_times: list[datetime] = []
    if cid in bundle.first_attempt:
        touch_times.append(bundle.first_attempt[cid])
    if cid in bundle.first_outbound_msg:
        touch_times.append(bundle.first_outbound_msg[cid])
    first_touch = min(touch_times) if touch_times else None

    fr_bucket: str | None
    if first_touch:
        fr_h = max(0.0, (first_touch - created).total_seconds() / 3600.0)
        if fr_h <= 24:
            fr_bucket = "0_24h"
        elif fr_h <= 48:
            fr_bucket = "24_48h"
        elif fr_h <= 72:
            fr_bucket = "48_72h"
        else:
            fr_bucket = "72h_plus"
    else:
        fr_bucket = "no_touch" if not terminal else None

    delay_first_h = max(0.0, (now_utc - created).total_seconds() / 3600.0) if first_touch is None else 0.0
    if first_touch is not None:
        delay_first_h = max(0.0, (first_touch - created).total_seconds() / 3600.0)
        delay_first_h = max(0.0, delay_first_h - 2.0)

    response_risk = risk_from_delay_hours(delay_first_h, hl_resp_h) if not terminal else 0.0

    tr = bundle.thread_rollups.get(cid) or {}
    last_out = tr.get("last_out")
    last_in = tr.get("last_in")
    inbound_unanswered_h = 0.0
    if last_in and (last_out is None or last_in > last_out):
        inbound_unanswered_h = max(0.0, (now_utc - last_in).total_seconds() / 3600.0)
    inbound_risk = risk_from_delay_hours(inbound_unanswered_h, hl_inb_h)

    response_component = max(response_risk, inbound_risk)

    entered = stage_entered_at(stage) or created
    days_in_stage = max(0.0, (now_utc - entered).total_seconds() / 86400.0)
    raw_b = stage_base.get(stage_code, default_base_d)
    try:
        baseline_d = float(raw_b)
    except (TypeError, ValueError):
        baseline_d = default_base_d
    if baseline_d <= 0:
        baseline_d = default_base_d
    over_d = max(0.0, days_in_stage - baseline_d)
    stagnation_risk = 0.0 if terminal else risk_from_delay_hours(over_d * 24.0, hl_stag_d * 24.0)
    sr = bundle.reopen_30d.get(cid, 0)
    if sr:
        stagnation_risk = min(100.0, stagnation_risk + min(40.0, sr * 12.0))

    rems = bundle.reminders_by_cand.get(cid) or []
    active = [r for r in rems if r[0] in ACTIVE_REMINDER_STATUSES]
    has_next = len(active) > 0
    overdue_h = 0.0
    for st, due, _comp in active:
        if due < now_utc:
            overdue_h = max(overdue_h, (now_utc - due).total_seconds() / 3600.0)
    action_risk = 0.0
    if not has_next and not terminal:
        action_risk = max(action_risk, risk_from_delay_hours(24.0, 36.0))
    if overdue_h > 0:
        action_risk = max(action_risk, risk_from_delay_hours(overdue_h, 18.0))

    overdue_done_7d = 0
    for st, due, comp in rems:
        if comp and comp >= cutoff_7d and due < comp and st in (ReminderStatus.done, "done"):
            overdue_done_7d += 1
    if overdue_done_7d:
        action_risk = min(100.0, action_risk + min(30.0, overdue_done_7d * 8.0))

    interaction_n = int(bundle.msg_count_7d.get(cid, 0))
    context_risk = 0.0
    if not terminal and interaction_n < low_msg_thr:
        factor = 1.0 - (interaction_n / max(1, low_msg_thr))
        context_risk = min(100.0, low_msg_risk * factor)

    score = (
        w_resp * response_component
        + w_stag * stagnation_risk
        + w_act * action_risk
        + w_ctx * context_risk
    )
    score = max(0.0, min(100.0, round(score, 2)))
    band = band_from_score(score)
    drivers = drivers_from_components(response_component, stagnation_risk, action_risk, context_risk)

    return {
        "score": score,
        "band": band,
        "drivers": drivers,
        "response_component": response_component,
        "stagnation_risk": stagnation_risk,
        "action_risk": action_risk,
        "context_risk": context_risk,
        "fr_bucket": fr_bucket,
    }


async def _fetch_tenant_settings(db: AsyncSession, tenant_id: str) -> dict[str, Any] | None:
    row = await db.execute(select(Tenant.settings).where(Tenant.id == tenant_id).limit(1))
    settings = row.scalar_one_or_none()
    return settings if isinstance(settings, dict) else {}


async def compute_candidate_risk_baseline(
    db: AsyncSession,
    tenant_id: str,
    scope_clause: ColumnElement[bool],
    *,
    now: datetime | None = None,
    limit: int = 5000,
    collect_shadow_rows: bool = False,
) -> dict[str, Any]:
    """
    Aggregate risk scores for visible candidates (scope_clause applied).
    When collect_shadow_rows=True, includes high/critical per-candidate rows for shadow persistence (Phase B).
    """
    now_utc = _utc(now) or datetime.now(timezone.utc)
    settings = await _fetch_tenant_settings(db, tenant_id)
    cfg = resolve_risk_config(settings)

    cand_rows = (
        await db.execute(
            select(Candidate.id, Candidate.stage, Candidate.created_at, Candidate.updated_at)
            .where(and_(Candidate.tenant_id == tenant_id, Candidate.deleted_at.is_(None), scope_clause))
            .order_by(Candidate.updated_at.desc())
            .limit(limit)
        )
    ).all()

    candidates: list[tuple[str, str | None, datetime | None, datetime | None]] = []
    for cid, stage, created_at, updated_at in cand_rows:
        candidates.append((str(cid), str(stage) if stage is not None else None, created_at, updated_at))

    # Завершённые отказы не входят в операционную аналитику риска.
    candidates = [c for c in candidates if (c[1] or "") not in PIPELINE_COMPLETED_STAGE_CODES]
    candidate_ids = [c[0] for c in candidates]
    if not candidate_ids:
        return _empty_baseline(now_utc, resolve_risk_config(settings))

    bundle = await _load_risk_metric_bundle(db, tenant_id, candidate_ids, now_utc)

    band_counts: MutableMapping[RiskBand, int] = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    by_stage: dict[str, dict[str, Any]] = {}
    fr_buckets = {"0_24h": 0, "24_48h": 0, "48_72h": 0, "72h_plus": 0, "no_touch": 0}
    scores: list[float] = []
    high_risk = 0
    shadow_rows: list[dict[str, Any]] = []

    for cand in candidates:
        ev = _evaluate_candidate_risk_row(cand, bundle, cfg, now_utc)
        score = float(ev["score"])
        band = ev["band"]
        frb = ev.get("fr_bucket")
        if isinstance(frb, str) and frb in fr_buckets:
            fr_buckets[frb] += 1

        band_counts[band] += 1
        scores.append(score)
        if band in ("high", "critical"):
            high_risk += 1

        cid, stage, _ca, _ua = cand
        stage_code = stage or ""
        st_key = stage_code or "unknown"
        if st_key not in by_stage:
            by_stage[st_key] = {"count": 0, "sum_score": 0.0, "band_high_plus": 0}
        by_stage[st_key]["count"] += 1
        by_stage[st_key]["sum_score"] += score
        if band in ("high", "critical"):
            by_stage[st_key]["band_high_plus"] += 1

        if collect_shadow_rows and band in ("high", "critical"):
            shadow_rows.append(
                {
                    "candidate_id": cid,
                    "score": score,
                    "band": band,
                    "stage_at_score": stage_code or None,
                    "drivers": ev["drivers"],
                }
            )

    out: dict[str, Any] = {
        "generated_at": now_utc,
        "risk_version": "risk_model_v1",
        "effective_weights": {k: float(v) for k, v in (cfg.get("weights") or {}).items()},
        "candidates_evaluated": len(candidate_ids),
        "band_distribution": dict(band_counts),
        "high_risk_volume": high_risk,
        "avg_risk_score": round(sum(scores) / max(1, len(scores)), 2),
        "risk_distribution_by_stage": {
            k: {
                "count": int(v["count"]),
                "avg_risk_score": round(v["sum_score"] / max(1, v["count"]), 2),
                "high_plus_count": int(v["band_high_plus"]),
            }
            for k, v in sorted(by_stage.items(), key=lambda x: (-x[1]["count"], x[0]))
        },
        "first_response_hours_histogram": fr_buckets,
    }
    if collect_shadow_rows:
        out["shadow_rows"] = shadow_rows
    return out


async def compute_candidate_risk_map_for_ids(
    db: AsyncSession,
    tenant_id: str,
    candidate_ids: Sequence[str],
    *,
    now: datetime | None = None,
) -> dict[str, dict[str, Any]]:
    """On-demand risk_model_v1 scores for explicit candidate ids (list rows, detail)."""
    now_utc = _utc(now) or datetime.now(timezone.utc)
    settings = await _fetch_tenant_settings(db, tenant_id)
    cfg = resolve_risk_config(settings)
    deduped: list[str] = []
    seen: set[str] = set()
    for x in candidate_ids:
        s = str(x).strip()
        if not s or s in seen:
            continue
        seen.add(s)
        deduped.append(s)
    if not deduped:
        return {}

    candidates: list[tuple[str, str | None, datetime | None, datetime | None]] = []
    for batch in _chunks(deduped, 400):
        cand_rows = (
            await db.execute(
                select(Candidate.id, Candidate.stage, Candidate.created_at, Candidate.updated_at).where(
                    and_(
                        Candidate.tenant_id == tenant_id,
                        Candidate.deleted_at.is_(None),
                        Candidate.id.in_(batch),
                    )
                )
            )
        ).all()
        for cid, stage, created_at, updated_at in cand_rows:
            candidates.append((str(cid), str(stage) if stage is not None else None, created_at, updated_at))

    cand_ids_found = [c[0] for c in candidates]
    if not cand_ids_found:
        return {}

    bundle = await _load_risk_metric_bundle(db, tenant_id, cand_ids_found, now_utc)
    out: dict[str, dict[str, Any]] = {}
    for cand in candidates:
        ev = _evaluate_candidate_risk_row(cand, bundle, cfg, now_utc)
        cid = cand[0]
        out[cid] = {
            "risk_score": int(round(float(ev["score"]))),
            "risk_band": str(ev["band"]),
            "risk_drivers": list(ev["drivers"]),
            "risk_updated_at": now_utc,
            "risk_version": "risk_model_v1",
        }
    return out


def max_dt(a: datetime | None, b: datetime | None) -> datetime | None:
    if a is None:
        return b
    if b is None:
        return a
    return a if a >= b else b


async def persist_risk_intel_hourly_and_shadow(
    db: AsyncSession,
    tenant_id: str,
    bucket_start: datetime,
    baseline: dict[str, Any],
    shadow_rows: list[dict[str, Any]],
    *,
    scored_at: datetime,
    prune_shadow_older_than_days: int = 90,
) -> None:
    """Replace aggregate for this hour; append shadow rows; prune old shadow."""
    cutoff = scored_at - timedelta(days=max(7, prune_shadow_older_than_days))
    await db.execute(
        delete(RiskIntelEntityShadow).where(
            RiskIntelEntityShadow.tenant_id == tenant_id,
            RiskIntelEntityShadow.scored_at < cutoff,
        )
    )
    await db.execute(
        delete(RiskIntelTenantHourly).where(
            RiskIntelTenantHourly.tenant_id == tenant_id,
            RiskIntelTenantHourly.bucket_start == bucket_start,
        )
    )
    bd = baseline.get("band_distribution") or {}
    hr = RiskIntelTenantHourly(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        bucket_start=_utc(bucket_start) or bucket_start,
        risk_version=str(baseline.get("risk_version") or "risk_model_v1"),
        generated_at=_utc(scored_at) or scored_at,
        candidates_evaluated=int(baseline.get("candidates_evaluated") or 0),
        avg_risk_score=float(baseline.get("avg_risk_score") or 0.0),
        high_risk_volume=int(baseline.get("high_risk_volume") or 0),
        band_low=int(bd.get("low") or 0),
        band_medium=int(bd.get("medium") or 0),
        band_high=int(bd.get("high") or 0),
        band_critical=int(bd.get("critical") or 0),
        first_response_histogram=dict(baseline.get("first_response_hours_histogram") or {}),
        effective_weights=dict(baseline.get("effective_weights") or {}),
    )
    db.add(hr)
    rv = str(baseline.get("risk_version") or "risk_model_v1")
    bs = _utc(bucket_start) or bucket_start
    st = _utc(scored_at) or scored_at
    for s in shadow_rows:
        db.add(
            RiskIntelEntityShadow(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                entity_type="candidate",
                entity_id=str(s.get("candidate_id") or ""),
                scored_at=st,
                bucket_start=bs,
                risk_version=rv,
                score=float(s.get("score") or 0.0),
                band=str(s.get("band") or "high"),
                stage_at_score=s.get("stage_at_score"),
                drivers=list(s.get("drivers") or []),
            )
        )


async def run_risk_intel_hourly_job(db: AsyncSession, tenant: Tenant, now: datetime | None = None) -> dict[str, Any]:
    """Scheduler entry: compute scoped baseline, persist hourly + shadow rows."""
    from backend.app.api.v1.candidates.repo import _candidate_scope_clause as repo_scope_clause
    from backend.app.services.handoff import is_client_tenant_for_list
    from backend.app.services.tenant_visibility import get_tenant_visibility

    tenant_id = str(tenant.id)
    now_utc = _utc(now) or datetime.now(timezone.utc)
    bucket = hour_bucket_start(now_utc)
    settings = tenant.settings if isinstance(getattr(tenant, "settings", None), dict) else {}
    cfg = settings.get("risk_model_v1") or {}
    if cfg.get("hourly_job_enabled") is False:
        return {"skipped": True, "reason": "hourly_job_disabled"}

    _job_t0 = time.perf_counter()
    visibility = get_tenant_visibility(db, tenant_id)
    is_client = await is_client_tenant_for_list(db, tenant_id)
    scope = repo_scope_clause(tenant_id, visibility, is_client_tenant=is_client)
    lim = int(cfg.get("hourly_candidate_limit") or 5000)
    baseline = await compute_candidate_risk_baseline(
        db,
        tenant_id,
        scope,
        now=now_utc,
        limit=lim,
        collect_shadow_rows=True,
    )
    shadow_rows = list(baseline.get("shadow_rows") or [])
    prune_days = int(cfg.get("shadow_retention_days") or 90)
    await persist_risk_intel_hourly_and_shadow(
        db,
        tenant_id,
        bucket,
        baseline,
        shadow_rows,
        scored_at=now_utc,
        prune_shadow_older_than_days=prune_days,
    )

    automation_stats: dict[str, int] = {}
    auto_cfg = cfg.get("automations")
    if isinstance(auto_cfg, dict) and auto_cfg.get("enabled") is True and shadow_rows:
        from backend.app.services.automation_rules import run_candidate_risk_band_rules

        shadow_ids = [str(s.get("candidate_id") or "") for s in shadow_rows if s.get("candidate_id")]
        assignee_map = await _batch_candidate_assignees(db, tenant_id, shadow_ids)
        automation_stats = await run_candidate_risk_band_rules(
            db,
            tenant_id=tenant_id,
            shadow_rows=shadow_rows,
            assignee_by_candidate_id=assignee_map,
            dedupe_hours=int(auto_cfg.get("dedupe_hours") or 24),
            min_band=str(auto_cfg.get("min_band") or "high"),
        )

    out: dict[str, Any] = {
        "ok": True,
        "bucket_start": bucket.isoformat(),
        "shadow_rows": len(shadow_rows),
        "candidates_evaluated": baseline.get("candidates_evaluated"),
    }
    if automation_stats:
        out["risk_automation"] = automation_stats

    from backend.app.services.risk_intel_digest_email import maybe_send_risk_shadow_digest_email

    out["digest_email"] = await maybe_send_risk_shadow_digest_email(
        db,
        tenant_id=tenant_id,
        tenant_settings=settings,
        bucket_start=bucket,
    )
    _elapsed_ms = round((time.perf_counter() - _job_t0) * 1000.0, 1)
    logger.info(
        "risk_intel.hourly_job tenant=%s duration_ms=%s shadow_rows=%s candidates_evaluated=%s "
        "risk_automation=%s",
        tenant_id,
        _elapsed_ms,
        len(shadow_rows),
        baseline.get("candidates_evaluated"),
        bool(automation_stats),
    )
    return out


def _stage_index_strict(code: str | None) -> int | None:
    if not code:
        return None
    try:
        return STAGE_ORDER.index(code)
    except ValueError:
        return None


def _forward_validation_progress(prev_stage: str | None, cur_stage: str | None) -> bool:
    if not cur_stage:
        return False
    if cur_stage in ("rejected", "declined"):
        return False
    pi = _stage_index_strict(prev_stage)
    ci = _stage_index_strict(cur_stage)
    if ci is None:
        return False
    if pi is None:
        return False
    return ci > pi


async def list_risk_intel_hourly_trends(
    db: AsyncSession,
    tenant_id: str,
    *,
    days: int = 30,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    now_utc = _utc(now) or datetime.now(timezone.utc)
    d = max(1, min(int(days), 90))
    since = now_utc - timedelta(days=d)
    result = await db.execute(
        select(RiskIntelTenantHourly)
        .where(RiskIntelTenantHourly.tenant_id == tenant_id, RiskIntelTenantHourly.bucket_start >= since)
        .order_by(RiskIntelTenantHourly.bucket_start.asc())
    )
    rows = result.scalars().all()
    out: list[dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "bucket_start": r.bucket_start.isoformat() if r.bucket_start else None,
                "avg_risk_score": float(r.avg_risk_score or 0.0),
                "high_risk_volume": int(r.high_risk_volume or 0),
                "candidates_evaluated": int(r.candidates_evaluated or 0),
                "band_low": int(r.band_low or 0),
                "band_medium": int(r.band_medium or 0),
                "band_high": int(r.band_high or 0),
                "band_critical": int(r.band_critical or 0),
            }
        )
    return out


def _shadow_bands_at_least(min_band: str) -> list[str]:
    mr = RISK_BAND_ORDER.get(str(min_band).strip().lower(), 2)
    return [k for k, v in RISK_BAND_ORDER.items() if v >= mr]


def parse_shadow_bucket_iso(bucket_start_iso: str) -> datetime | None:
    """Normalize client-provided bucket timestamp to UTC hour start (matches persist)."""
    try:
        raw = str(bucket_start_iso).strip().replace("Z", "+00:00")
        return hour_bucket_start(datetime.fromisoformat(raw))
    except (ValueError, TypeError):
        return None


async def _shadow_snapshot_at_bucket(
    db: AsyncSession,
    tenant_id: str,
    *,
    bucket_dt: datetime,
    limit: int,
    min_band: str,
) -> dict[str, Any]:
    """Single hourly bucket: high+ (or min_band+) shadow rows, top by score."""
    lim = max(1, min(int(limit), 200))
    eligible_bands = _shadow_bands_at_least(min_band)
    if not eligible_bands:
        eligible_bands = ["high", "critical"]
    mb = hour_bucket_start(bucket_dt)

    cnt_row = await db.execute(
        select(func.count())
        .select_from(RiskIntelEntityShadow)
        .where(
            RiskIntelEntityShadow.tenant_id == tenant_id,
            RiskIntelEntityShadow.bucket_start == mb,
            RiskIntelEntityShadow.entity_type == "candidate",
            RiskIntelEntityShadow.band.in_(eligible_bands),
        )
    )
    total_matching = int(cnt_row.scalar_one() or 0)

    result = await db.execute(
        select(RiskIntelEntityShadow)
        .where(
            RiskIntelEntityShadow.tenant_id == tenant_id,
            RiskIntelEntityShadow.bucket_start == mb,
            RiskIntelEntityShadow.entity_type == "candidate",
            RiskIntelEntityShadow.band.in_(eligible_bands),
        )
        .order_by(RiskIntelEntityShadow.score.desc())
        .limit(lim)
    )
    top = list(result.scalars().all())
    if not top:
        return {
            "bucket_start": mb.isoformat(),
            "scored_at": None,
            "risk_version": "risk_model_v1",
            "min_band": str(min_band).strip().lower(),
            "total_matching": total_matching,
            "items": [],
            "note": None,
        }

    ids = [str(r.entity_id) for r in top]
    display: dict[str, dict[str, Any]] = {}
    for i in range(0, len(ids), 100):
        batch = ids[i : i + 100]
        cr = await db.execute(
            select(
                Candidate.id,
                Candidate.first_name,
                Candidate.last_name,
                Candidate.short_id,
                Candidate.recruiter_id,
            ).where(
                Candidate.tenant_id == tenant_id,
                Candidate.id.in_(batch),
                Candidate.deleted_at.is_(None),
            )
        )
        for cid, fn, ln, sid, rid in cr.all():
            rid_s = str(rid).strip() if rid is not None and str(rid).strip() else None
            display[str(cid)] = {
                "first_name": fn,
                "last_name": ln,
                "short_id": sid,
                "recruiter_id": rid_s,
            }

    max_scored: datetime | None = None
    items: list[dict[str, Any]] = []
    for r in top:
        st = _utc(r.scored_at)
        if st and (max_scored is None or st > max_scored):
            max_scored = st
        d = display.get(str(r.entity_id)) or {}
        fn, ln = d.get("first_name"), d.get("last_name")
        name_parts = [x for x in [fn, ln] if x]
        items.append(
            {
                "entity_id": str(r.entity_id),
                "score": float(r.score or 0.0),
                "band": str(r.band or ""),
                "stage_at_score": r.stage_at_score,
                "drivers": list(r.drivers or []),
                "scored_at": st.isoformat() if st else None,
                "short_id": d.get("short_id"),
                "display_name": " ".join(name_parts) if name_parts else None,
                "recruiter_id": d.get("recruiter_id"),
            }
        )

    return {
        "bucket_start": mb.isoformat(),
        "scored_at": max_scored.isoformat() if max_scored else None,
        "risk_version": str(top[0].risk_version or "risk_model_v1"),
        "min_band": str(min_band).strip().lower(),
        "total_matching": total_matching,
        "items": items,
        "note": None,
    }


async def list_shadow_snapshot_for_bucket_iso(
    db: AsyncSession,
    tenant_id: str,
    *,
    bucket_start_iso: str,
    limit: int = 40,
    min_band: str = "high",
) -> dict[str, Any]:
    """Shadow cohort for a specific hourly bucket (validates tenant has rows for that bucket)."""
    mb = parse_shadow_bucket_iso(bucket_start_iso)
    if mb is None:
        return {
            "bucket_start": None,
            "scored_at": None,
            "risk_version": "risk_model_v1",
            "min_band": str(min_band).strip().lower(),
            "total_matching": 0,
            "items": [],
            "note": "Invalid bucket_start (expected ISO-8601 hour bucket).",
        }
    chk = await db.execute(
        select(func.count())
        .select_from(RiskIntelEntityShadow)
        .where(
            RiskIntelEntityShadow.tenant_id == tenant_id,
            RiskIntelEntityShadow.entity_type == "candidate",
            RiskIntelEntityShadow.bucket_start == mb,
        )
    )
    if int(chk.scalar_one() or 0) == 0:
        return {
            "bucket_start": None,
            "scored_at": None,
            "risk_version": "risk_model_v1",
            "min_band": str(min_band).strip().lower(),
            "total_matching": 0,
            "items": [],
            "note": "Unknown bucket for this tenant.",
        }
    return await _shadow_snapshot_at_bucket(db, tenant_id, bucket_dt=mb, limit=limit, min_band=min_band)


async def list_shadow_digest_bucket_summaries(
    db: AsyncSession,
    tenant_id: str,
    *,
    min_band: str = "high",
    limit_buckets: int = 14,
) -> list[dict[str, Any]]:
    """Recent hourly buckets with high+ (or min_band+) row counts — in-app manager digest queue."""
    eligible_bands = _shadow_bands_at_least(min_band)
    if not eligible_bands:
        eligible_bands = ["high", "critical"]
    lim = max(1, min(int(limit_buckets), 168))
    stmt = (
        select(
            RiskIntelEntityShadow.bucket_start,
            func.count().label("cnt"),
            func.max(RiskIntelEntityShadow.scored_at).label("max_scored"),
        )
        .where(
            RiskIntelEntityShadow.tenant_id == tenant_id,
            RiskIntelEntityShadow.entity_type == "candidate",
            RiskIntelEntityShadow.band.in_(eligible_bands),
        )
        .group_by(RiskIntelEntityShadow.bucket_start)
        .order_by(RiskIntelEntityShadow.bucket_start.desc())
        .limit(lim)
    )
    rows = (await db.execute(stmt)).all()
    out: list[dict[str, Any]] = []
    for bs, cnt, max_scored in rows:
        if bs is None:
            continue
        st = _utc(max_scored)
        out.append(
            {
                "bucket_start": bs.isoformat(),
                "total_matching": int(cnt or 0),
                "scored_at": st.isoformat() if st else None,
            }
        )
    return out


async def list_latest_shadow_snapshot(
    db: AsyncSession,
    tenant_id: str,
    *,
    limit: int = 40,
    min_band: str = "high",
) -> dict[str, Any]:
    """
    Ops digest: latest persisted hourly bucket — high+ (or min_band+) shadow rows, top by score.
    """
    lim = max(1, min(int(limit), 200))
    eligible_bands = _shadow_bands_at_least(min_band)
    if not eligible_bands:
        eligible_bands = ["high", "critical"]

    mb_row = await db.execute(
        select(func.max(RiskIntelEntityShadow.bucket_start)).where(
            RiskIntelEntityShadow.tenant_id == tenant_id,
            RiskIntelEntityShadow.entity_type == "candidate",
        )
    )
    mb = mb_row.scalar_one_or_none()
    if mb is None:
        return {
            "bucket_start": None,
            "scored_at": None,
            "risk_version": "risk_model_v1",
            "min_band": str(min_band).strip().lower(),
            "total_matching": 0,
            "items": [],
            "note": "No hourly shadow data yet (apply migration + run communications scheduler).",
        }

    return await _shadow_snapshot_at_bucket(db, tenant_id, bucket_dt=mb, limit=lim, min_band=min_band)


async def shadow_validation_summary(
    db: AsyncSession,
    tenant_id: str,
    *,
    cohort_days: int = 14,
    lag_days: int = 7,
    now: datetime | None = None,
) -> dict[str, Any]:
    now_utc = _utc(now) or datetime.now(timezone.utc)
    lag = max(1, min(int(lag_days), 60))
    cohort = max(lag + 1, min(int(cohort_days), 120))
    win_start = now_utc - timedelta(days=cohort)
    win_end = now_utc - timedelta(days=lag)
    result = await db.execute(
        select(RiskIntelEntityShadow)
        .where(
            RiskIntelEntityShadow.tenant_id == tenant_id,
            RiskIntelEntityShadow.entity_type == "candidate",
            RiskIntelEntityShadow.scored_at >= win_start,
            RiskIntelEntityShadow.scored_at < win_end,
            RiskIntelEntityShadow.band.in_(("high", "critical")),
        )
        .order_by(RiskIntelEntityShadow.scored_at.desc())
    )
    rows = result.scalars().all()
    latest_by_cand: dict[str, Any] = {}
    for r in rows:
        eid = str(r.entity_id or "")
        if eid and eid not in latest_by_cand:
            latest_by_cand[eid] = r
    if not latest_by_cand:
        return {
            "generated_at": now_utc.isoformat(),
            "cohort_window": {"from": win_start.isoformat(), "to": win_end.isoformat()},
            "lag_days_after_cohort": lag,
            "samples": 0,
            "forward_stage_progression_count": 0,
            "forward_stage_progression_rate": None,
            "interpretation": None,
            "note": "No shadow rows in cohort window (enable hourly job + migration).",
        }

    ids = list(latest_by_cand.keys())
    stage_map: dict[str, str | None] = {}
    for i in range(0, len(ids), 400):
        batch = ids[i : i + 400]
        cr = await db.execute(
            select(Candidate.id, Candidate.stage).where(
                Candidate.tenant_id == tenant_id,
                Candidate.id.in_(batch),
                Candidate.deleted_at.is_(None),
            )
        )
        for cid, st in cr.all():
            stage_map[str(cid)] = str(st) if st is not None else None

    progressed = 0
    total = 0
    for cid, row in latest_by_cand.items():
        total += 1
        if _forward_validation_progress(row.stage_at_score, stage_map.get(cid)):
            progressed += 1

    rate = round(100.0 * progressed / max(1, total), 2)
    return {
        "generated_at": now_utc.isoformat(),
        "cohort_window": {"from": win_start.isoformat(), "to": win_end.isoformat()},
        "lag_days_after_cohort": lag,
        "samples": total,
        "forward_stage_progression_count": progressed,
        "forward_stage_progression_rate": rate,
        "interpretation": "Among latest high/critical shadow rows per candidate in the cohort window, "
        "percentage where pipeline stage advanced vs stage_at_score (excludes rejected/declined).",
        "note": None,
    }


def _empty_baseline(now_utc: datetime, cfg: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": now_utc,
        "risk_version": "risk_model_v1",
        "effective_weights": {k: float(v) for k, v in (cfg.get("weights") or {}).items()},
        "candidates_evaluated": 0,
        "band_distribution": {"low": 0, "medium": 0, "high": 0, "critical": 0},
        "high_risk_volume": 0,
        "avg_risk_score": 0.0,
        "risk_distribution_by_stage": {},
        "first_response_hours_histogram": {
            "0_24h": 0,
            "24_48h": 0,
            "48_72h": 0,
            "72h_plus": 0,
            "no_touch": 0,
        },
    }


def score_single_candidate(
    *,
    created_at: datetime,
    now: datetime,
    stage: str | None,
    first_touch_at: datetime | None,
    last_outbound_at: datetime | None,
    last_inbound_at: datetime | None,
    has_next_action: bool,
    next_action_overdue_hours: float,
    interaction_count_7d: int,
    stage_entered_at: datetime | None,
    stage_reopen_30d: int,
    overdue_completed_reminders_7d: int,
    tenant_settings: Mapping[str, Any] | None = None,
) -> tuple[float, RiskBand, list[str]]:
    """Pure helper for unit tests and future list/card payloads."""
    cfg = resolve_risk_config(dict(tenant_settings) if tenant_settings else None)
    w_resp = float(cfg["weights"]["response"])
    w_stag = float(cfg["weights"]["stagnation"])
    w_act = float(cfg["weights"]["action"])
    w_ctx = float(cfg["weights"]["context"])
    hl_resp_h = float(cfg["half_lives_hours"]["candidate_first_response"])
    hl_inb_h = float(cfg["half_lives_hours"]["inbound_unanswered"])
    hl_stag_d = float(cfg["half_lives_days"]["stage_stagnation"])
    default_base_d = float(cfg["default_stage_baseline_days"])
    stage_base = cfg.get("stage_baseline_days") or {}
    ctx_cfg = cfg.get("context") or {}
    low_msg_thr = int(ctx_cfg.get("low_interaction_messages_7d") or 2)
    low_msg_risk = float(ctx_cfg.get("low_interaction_risk") or 45.0)

    created = _utc(created_at) or now
    now_utc = _utc(now) or now
    stage_code = stage or ""
    if stage_code in PIPELINE_COMPLETED_STAGE_CODES:
        return 0.0, "low", []

    terminal = stage_code in TERMINAL_STATUSES

    first_touch = _utc(first_touch_at)
    if first_touch is None:
        delay_first_h = max(0.0, (now_utc - created).total_seconds() / 3600.0)
    else:
        delay_first_h = max(0.0, (first_touch - created).total_seconds() / 3600.0 - 2.0)

    response_risk = risk_from_delay_hours(delay_first_h, hl_resp_h) if not terminal else 0.0
    li = _utc(last_inbound_at)
    lo = _utc(last_outbound_at)
    inbound_unanswered_h = 0.0
    if li and (lo is None or li > lo):
        inbound_unanswered_h = max(0.0, (now_utc - li).total_seconds() / 3600.0)
    inbound_risk = risk_from_delay_hours(inbound_unanswered_h, hl_inb_h)
    response_component = max(response_risk, inbound_risk)

    entered = _utc(stage_entered_at) or created
    days_in_stage = max(0.0, (now_utc - entered).total_seconds() / 86400.0)
    baseline_d = float(stage_base.get(stage_code, default_base_d)) if isinstance(stage_base, dict) else default_base_d
    if baseline_d <= 0:
        baseline_d = default_base_d
    over_d = max(0.0, days_in_stage - baseline_d)
    stagnation_risk = 0.0 if terminal else risk_from_delay_hours(over_d * 24.0, hl_stag_d * 24.0)
    if stage_reopen_30d:
        stagnation_risk = min(100.0, stagnation_risk + min(40.0, stage_reopen_30d * 12.0))

    action_risk = 0.0
    if not has_next_action and not terminal:
        action_risk = max(action_risk, risk_from_delay_hours(24.0, 36.0))
    if next_action_overdue_hours > 0:
        action_risk = max(action_risk, risk_from_delay_hours(next_action_overdue_hours, 18.0))
    if overdue_completed_reminders_7d:
        action_risk = min(100.0, action_risk + min(30.0, overdue_completed_reminders_7d * 8.0))

    context_risk = 0.0
    if not terminal and interaction_count_7d < low_msg_thr:
        factor = 1.0 - (interaction_count_7d / max(1, low_msg_thr))
        context_risk = min(100.0, low_msg_risk * factor)

    score = (
        w_resp * response_component
        + w_stag * stagnation_risk
        + w_act * action_risk
        + w_ctx * context_risk
    )
    score = max(0.0, min(100.0, round(score, 2)))
    band = band_from_score(score)
    labels = drivers_from_components(response_component, stagnation_risk, action_risk, context_risk)
    return score, band, labels
