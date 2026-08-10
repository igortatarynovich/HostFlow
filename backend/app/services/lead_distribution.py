"""Lead auto-distribution snapshot + settings (Tenant.settings.lead_distribution_v1)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Set, Tuple
from uuid import UUID

from sqlalchemy import func, select, exists, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from backend.app.models import Lead, Reminder, Tenant, User
from backend.app.services.working_hours_window import is_within_working_hours, schedule_applies
from backend.app.models.reminder import ReminderStatus
from backend.app.models.user import Role
from backend.app.services.plan_feature_gates import (
    plan_allows_team_tier_features,
    resolve_tenant_plan_code,
)

DIST_KEY = "lead_distribution_v1"

DEFAULTS: Dict[str, Any] = {
    "mode": "manual",
    "strategy": "smart",
    "criteria_order": ["working_hours", "workload", "language"],
    "max_leads_per_person": 10,
    "only_active_employees": True,
    "preview_language": "pl",
    # Explicit language → user ids (priority = list order). Falls back to profile languages if empty / no match.
    "language_routing_v1": {},
    # Last user_id chosen under strategy=round_robin; advances circularly in team order (§2.3).
    "round_robin_last_user_id": None,
}

ACTIVE_REMINDER = (ReminderStatus.pending, ReminderStatus.new, ReminderStatus.overdue)


def roles_for_pipeline_owner_role(raw: Optional[str]) -> Optional[Set[Role]]:
    """
    Map free-text FunnelStage.stage_contract_v1.owner_role to tenant User.role values.
    Multiple tokens: comma, pipe, slash, or whitespace. Unknown tokens are ignored; if nothing
    maps, returns None (caller skips filtering).
    """
    if raw is None or not str(raw).strip():
        return None
    tokens = [t for t in re.split(r"[,|/\s]+", str(raw).strip().lower()) if t]
    out: Set[Role] = set()
    for t in tokens:
        if t in ("recruiter", "rec"):
            out.add(Role.employee)
        elif t in ("supervisor", "manager", "mgr"):
            out.add(Role.employee)
        elif t in ("administrator", "admin", "owner"):
            out.add(Role.administrator)
    return out or None


def filter_team_by_pipeline_owner_roles(
    team: List[Dict[str, Any]],
    allowed_roles: Optional[Set[Role]],
) -> List[Dict[str, Any]]:
    """Narrow distribution pool to roles; if that would empty the list, keep the original team."""
    if not allowed_roles:
        return team
    allowed_vals = {r.value for r in allowed_roles}
    filtered = [m for m in team if m.get("role") in allowed_vals]
    return filtered if filtered else team


def _is_uuid_str(value: str) -> bool:
    try:
        UUID(str(value).strip())
        return True
    except Exception:
        return False


def _sanitize_language_routing_v1(raw: object) -> Dict[str, List[str]]:
    """Lang code → ordered user ids (tenant-validated separately on PATCH)."""
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, List[str]] = {}
    for k, v in raw.items():
        lang = str(k).strip().lower()[:16]
        if not lang or not lang[0].isalpha():
            continue
        if not lang.replace("_", "").isalnum():
            continue
        if not isinstance(v, list):
            continue
        ids: List[str] = []
        for item in v[:40]:
            s = str(item).strip()
            if s and _is_uuid_str(s) and s not in ids:
                ids.append(s)
        if ids:
            out[lang] = ids
    return out


def _merge_settings(raw: object) -> Dict[str, Any]:
    base = dict(DEFAULTS)
    if isinstance(raw, dict):
        for k, v in raw.items():
            if k == "language_routing_v1":
                base[k] = _sanitize_language_routing_v1(v)
            elif k in DEFAULTS or k == "preview_language":
                base[k] = v
    return base


def _display_name(u: User) -> str:
    fn = (getattr(u, "full_name", None) or "").strip()
    if fn:
        return fn
    return (u.email or "").split("@")[0] or str(u.id)[:8]


def _user_languages(prefs: object, extra: object) -> List[str]:
    out: List[str] = []
    if isinstance(prefs, dict):
        langs = prefs.get("languages") or prefs.get("spoken_languages")
        if isinstance(langs, list):
            out.extend(str(x).strip().lower() for x in langs if str(x).strip())
        elif isinstance(langs, str) and langs.strip():
            out.append(langs.strip().lower())
    if isinstance(extra, dict):
        langs = extra.get("languages")
        if isinstance(langs, list):
            out.extend(str(x).strip().lower() for x in langs if str(x).strip())
    if not out:
        out = ["en"]
    # normalize short codes
    norm: List[str] = []
    for x in out:
        if x in ("polish", "polski", "pl"):
            norm.append("pl")
        elif x in ("english", "en"):
            norm.append("en")
        else:
            norm.append(x[:2] if len(x) > 2 else x)
    return list(dict.fromkeys(norm))


def _lang_match(user_langs: List[str], want: str) -> bool:
    w = (want or "").strip().lower()
    if w in ("polish", "polski"):
        w = "pl"
    if w in ("english",):
        w = "en"
    return w in user_langs or any(w in ul for ul in user_langs)


async def _plan_allows_auto(db: AsyncSession, tenant_id: str) -> Tuple[bool, str]:
    plan = await resolve_tenant_plan_code(db, tenant_id)
    return plan_allows_team_tier_features(plan, tenant_id=tenant_id), plan


def language_route_user_ids(cfg: Dict[str, Any], preview_lang: str) -> List[str]:
    """Ordered user ids for explicit routing for this language code (may be empty)."""
    lr = cfg.get("language_routing_v1")
    if not isinstance(lr, dict) or not lr:
        return []
    lang = str(preview_lang or "pl").strip().lower()
    candidates = [lang]
    if len(lang) > 2:
        candidates.append(lang[:2])
    for ck in candidates:
        raw = lr.get(ck)
        if isinstance(raw, list) and raw:
            return [str(x).strip() for x in raw if str(x).strip() and _is_uuid_str(str(x).strip())]
    for lk, ids in lr.items():
        if str(lk).strip().lower() == lang:
            if isinstance(ids, list):
                return [str(x).strip() for x in ids if str(x).strip() and _is_uuid_str(str(x).strip())]
    return []


def language_from_lead_normalized(normalized: Optional[Dict[str, Any]]) -> Optional[str]:
    """Best-effort language hint from lead normalized payload (ingest / Meta)."""
    if not isinstance(normalized, dict):
        return None
    for key in ("language", "locale", "preferred_language", "lead_language", "interface_language"):
        v = normalized.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


async def _build_distribution_team(
    db: AsyncSession,
    *,
    tenant_id: str,
    cfg: Dict[str, Any],
) -> List[Dict[str, Any]]:
    users_rows = (
        await db.execute(
            select(User)
            .where(
                User.tenant_id == tenant_id,
                User.is_active.is_(True),
                User.deleted_at.is_(None),
                or_(
                    User.role == Role.administrator,
                    User.role == Role.employee,
                ),
            )
            .order_by(User.created_at.asc())
        )
    ).scalars().all()

    team: List[Dict[str, Any]] = []
    max_l = int(cfg.get("max_leads_per_person") or 10)
    wh_order = "working_hours" in (cfg.get("criteria_order") or [])
    now_utc = datetime.now(timezone.utc)
    for u in users_rows:
        cnt_row = await db.execute(
            select(func.count())
            .select_from(Reminder)
            .where(
                Reminder.tenant_id == tenant_id,
                Reminder.entity_type == "lead",
                Reminder.assignee_id == str(u.id),
                Reminder.status.in_(ACTIVE_REMINDER),
            )
        )
        load = int(cnt_row.scalar_one() or 0)
        langs = _user_languages(u.preferences, u.extra)
        if load >= max_l * 12 // 10:
            status: Literal["available", "busy", "offline"] = "offline"
        elif load >= max_l * 7 // 10:
            status = "busy"
        else:
            status = "available"
        wh_configured = schedule_applies(u.extra)
        wh_inside = is_within_working_hours(u.extra, now_utc)
        if status != "offline" and wh_order and wh_configured and not wh_inside:
            status = "offline"
        team.append(
            {
                "user_id": str(u.id),
                "display_name": _display_name(u),
                "role": u.role.value,
                "status": status,
                "lead_load": load,
                "languages": [x.upper() if len(x) == 2 else x for x in langs],
                "working_hours_configured": wh_configured,
                "within_working_hours": wh_inside,
            }
        )
    return team


def _eligible_pool_after_cap(team: List[Dict[str, Any]], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    max_l = int(cfg.get("max_leads_per_person") or 10)
    pool = [m for m in team if m["lead_load"] < max_l]
    if cfg.get("only_active_employees", True):
        pool = [m for m in pool if m["status"] != "offline"]
    return pool


def _lang_pool_for_distribution(
    pool: List[Dict[str, Any]],
    cfg: Dict[str, Any],
    preview_lang: str,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Returns eligible members for language step + meta for UI ('why').
    Explicit ``language_routing_v1`` wins when at least one mapped user is in the pool.
    """
    lang = str(preview_lang or "pl").lower()
    meta: Dict[str, Any] = {"explicit_route": False, "preference_fallback": False}
    route_ids = language_route_user_ids(cfg, preview_lang)
    if route_ids:
        pos = {uid: i for i, uid in enumerate(route_ids)}
        explicit = [m for m in pool if str(m["user_id"]) in pos]
        explicit.sort(key=lambda m: pos[str(m["user_id"])])
        if explicit:
            meta["explicit_route"] = True
            meta["route_order"] = route_ids
            return explicit, meta
        meta["preference_fallback"] = True
    lang_pool = [m for m in pool if _lang_match([x.lower() for x in m["languages"]], lang)] or pool
    return lang_pool, meta


def pick_assignee_member_from_team(
    team: List[Dict[str, Any]],
    cfg: Dict[str, Any],
    preview_lang: str,
    tenant_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Same selection logic as distribution UI preview: pool by cap + active filter,
    language match, then smart (lowest load) or round_robin.

    Round-robin uses ``cfg["round_robin_last_user_id"]`` and stable **team list order**
    (same as ``_build_distribution_team``): next assignee is the following eligible member,
    wrapping. Ingest persists ``round_robin_last_user_id`` after each automatic assignment.
    """
    _ = tenant_id  # reserved for logging / future tenant-scoped rules
    strategy = str(cfg.get("strategy") or "smart")
    pool = _eligible_pool_after_cap(team, cfg)
    lang_pool, pick_meta = _lang_pool_for_distribution(pool, cfg, preview_lang)
    if strategy == "round_robin" and lang_pool:
        eligible_ids = {str(m["user_id"]) for m in lang_pool}
        pool_ordered = [m for m in team if str(m["user_id"]) in eligible_ids]
        if not pool_ordered:
            return None
        raw_last = cfg.get("round_robin_last_user_id")
        last_uid = str(raw_last).strip() if raw_last else ""
        if not last_uid or not any(str(m["user_id"]) == last_uid for m in pool_ordered):
            return pool_ordered[0]
        idx = next(i for i, m in enumerate(pool_ordered) if str(m["user_id"]) == last_uid)
        return pool_ordered[(idx + 1) % len(pool_ordered)]
    if lang_pool:
        route_order = pick_meta.get("route_order")
        if isinstance(route_order, list) and route_order:
            pos = {str(uid): i for i, uid in enumerate(route_order)}
            return sorted(
                lang_pool,
                key=lambda x: (x["lead_load"], pos.get(str(x["user_id"]), 999), x["display_name"]),
            )[0]
        return sorted(lang_pool, key=lambda x: (x["lead_load"], x["display_name"]))[0]
    return None


async def _lead_pipeline_owner_roles_for_distribution(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
) -> Optional[Set[Role]]:
    """Resolve stage_contract.owner_role for this lead's CRM stage (lead funnel)."""
    from backend.app.modules.leads.lead_stage_contract import batch_lead_stage_contracts

    lead = await db.get(Lead, str(lead_id).strip())
    if lead is None or str(lead.tenant_id) != str(tenant_id):
        return None
    cmap = await batch_lead_stage_contracts(db, tenant_id=tenant_id, leads=[lead])
    c = cmap.get(str(lead.id))
    if c is None or not getattr(c, "owner_role", None):
        return None
    return roles_for_pipeline_owner_role(str(c.owner_role))


async def pick_assignee_user_id_for_ingest(
    db: AsyncSession,
    *,
    tenant_id: str,
    normalized: Optional[Dict[str, Any]] = None,
    lead_id: Optional[str] = None,
) -> Optional[str]:
    """
    When lead_distribution_v1.mode == automatic and plan is team/pro, pick assignee
    using the same rules as the distribution panel (workload, language from lead or preview_language).
    Returns None if manual mode, plan blocks auto, or no eligible user.
    """
    if lead_id:
        nrow = await db.execute(
            select(Lead.normalized).where(Lead.id == str(lead_id), Lead.tenant_id == tenant_id).limit(1)
        )
        norm = nrow.scalar_one_or_none()
        if isinstance(norm, dict):
            lock = norm.get("assignment_lock_v1")
            if isinstance(lock, dict) and lock.get("locked") is True:
                return None
    trow = await db.execute(select(Tenant).where(Tenant.id == tenant_id).limit(1))
    tenant = trow.scalar_one_or_none()
    if tenant is None:
        return None
    settings_all: Dict[str, Any] = dict(tenant.settings or {}) if isinstance(tenant.settings, dict) else {}
    cfg = _merge_settings(settings_all.get(DIST_KEY))
    auto_allowed, _ = await _plan_allows_auto(db, tenant_id)
    if cfg.get("mode") != "automatic" or not auto_allowed:
        return None
    lang_hint = language_from_lead_normalized(normalized)
    preview_lang = (lang_hint or str(cfg.get("preview_language") or "pl")).lower()
    team = await _build_distribution_team(db, tenant_id=tenant_id, cfg=cfg)
    if lead_id:
        allowed = await _lead_pipeline_owner_roles_for_distribution(
            db, tenant_id=tenant_id, lead_id=str(lead_id)
        )
        team = filter_team_by_pipeline_owner_roles(team, allowed)
    picked = pick_assignee_member_from_team(team, cfg, preview_lang, tenant_id)
    if not picked:
        return None
    uid = str(picked["user_id"])
    if str(cfg.get("strategy") or "smart") == "round_robin":
        merged = dict(cfg)
        merged["round_robin_last_user_id"] = uid
        settings_all[DIST_KEY] = merged
        tenant.settings = settings_all
        flag_modified(tenant, "settings")
        await db.flush()
    return uid


async def build_distribution_snapshot(db: AsyncSession, *, tenant_id: str) -> Dict[str, Any]:
    trow = await db.execute(select(Tenant).where(Tenant.id == tenant_id).limit(1))
    tenant = trow.scalar_one_or_none()
    settings_all: Dict[str, Any] = dict(tenant.settings or {}) if tenant and isinstance(tenant.settings, dict) else {}
    cfg = _merge_settings(settings_all.get(DIST_KEY))

    auto_allowed, plan_code = await _plan_allows_auto(db, tenant_id)
    if not auto_allowed and cfg.get("mode") == "automatic":
        cfg = dict(cfg)
        cfg["mode"] = "manual"

    team = await _build_distribution_team(db, tenant_id=tenant_id, cfg=cfg)

    preview_lang = str(cfg.get("preview_language") or "pl").lower()
    max_l = int(cfg.get("max_leads_per_person") or 10)
    co = list(cfg.get("criteria_order") or [])
    wh_in_criteria = "working_hours" in co

    pool = _eligible_pool_after_cap(team, cfg)
    _, lang_meta = _lang_pool_for_distribution(pool, cfg, preview_lang)

    picked = pick_assignee_member_from_team(team, cfg, preview_lang, tenant_id)
    strategy = str(cfg.get("strategy") or "smart")

    detail_lines: List[str] = []
    if wh_in_criteria:
        n_outside_wh = sum(
            1
            for m in team
            if m.get("working_hours_configured")
            and not m.get("within_working_hours")
            and int(m.get("lead_load") or 0) < max_l
        )
        if n_outside_wh:
            detail_lines.append(
                f"{n_outside_wh} teammate(s) have working hours configured but are outside the window now "
                f"(excluded from assignment when “only active” is on)."
            )
    if lang_meta.get("explicit_route"):
        detail_lines.append("Language: using explicit language → user map for this preview language.")
    elif lang_meta.get("preference_fallback") and language_route_user_ids(cfg, preview_lang):
        detail_lines.append(
            "Language: explicit map is set but no mapped user is eligible — using profile languages / full pool."
        )

    subtitle_parts: List[str] = []
    if picked:
        subtitle_parts.append("Lowest load among eligible" if strategy == "smart" else "Round-robin among eligible")
        if lang_meta.get("explicit_route"):
            subtitle_parts.append("explicit language route")
        elif "language" in co:
            subtitle_parts.append("profile language match")
        if wh_in_criteria and picked.get("working_hours_configured"):
            subtitle_parts.append(
                "inside working hours" if picked.get("within_working_hours") else "outside configured hours (see team cards)"
            )

    why: List[str] = []
    if picked:
        if wh_in_criteria:
            why.append("active_working_hours")
        if "workload" in co:
            why.append("lowest_workload")
        if "language" in co:
            why.append("language_match")

    rules_summary: List[str] = []
    if preview_lang:
        tail = f" → {picked['display_name']}" if picked else " — no eligible assignee"
        if language_route_user_ids(cfg, preview_lang):
            rules_summary.append(f"Language: explicit map for {preview_lang.upper()}{tail}")
        else:
            rules_summary.append(f"Language: preview {preview_lang.upper()}{tail}")
    rules_summary.append(
        "Workload: lowest first" if strategy == "smart" else "Round robin: next in rotation (saved between leads)"
    )
    if wh_in_criteria:
        rules_summary.append(
            "Working hours: teammates outside their calendar window are treated as offline (when enabled in criteria)."
        )
    else:
        rules_summary.append("Working hours: not prioritized in rule order (calendar still affects status if configured).")
    rules_summary.append("Only active employees" if cfg.get("only_active_employees", True) else "Offline teammates may still receive leads")

    flow = ["New lead", "Rules"]
    if picked:
        flow.append(picked["display_name"])
    else:
        flow.append("—")

    unassigned = int(
        (
            await db.execute(
                select(func.count())
                .select_from(Lead)
                .where(
                    Lead.tenant_id == tenant_id,
                    Lead.status == "processed",
                    ~exists().where(
                        and_(
                            Reminder.tenant_id == tenant_id,
                            Reminder.entity_type == "lead",
                            Reminder.entity_id == Lead.id,
                            Reminder.status.in_(ACTIVE_REMINDER),
                        )
                    ),
                )
            )
        ).scalar_one()
        or 0
    )

    alerts: List[Dict[str, Any]] = []
    if not pool:
        alerts.append({"severity": "warning", "code": "no_available", "message": "No available employees match current rules"})
    if unassigned > 0:
        alerts.append({"severity": "warning", "code": "unassigned", "message": f"{unassigned} leads not assigned"})
    for m in team:
        if m["lead_load"] >= max_l * 12 // 10 and m["lead_load"] > 0:
            alerts.append(
                {
                    "severity": "warning",
                    "code": "overloaded",
                    "message": f"{m['display_name']} overloaded ({m['lead_load']} leads)",
                }
            )

    return {
        "config": cfg,
        "team": team,
        "assignment_detail_lines": detail_lines,
        "next_preview": (
            {
                "user_id": picked["user_id"],
                "display_name": picked["display_name"],
                "reason_codes": why,
                "subtitle": "; ".join(subtitle_parts) if subtitle_parts else "",
                "detail_lines": detail_lines,
            }
            if picked
            else None
        ),
        "rules_summary_lines": rules_summary,
        "flow_steps": flow,
        "alerts": alerts,
        "stats": {"unassigned_processed_leads": unassigned},
        "feature_gate": {
            "automatic_allowed": auto_allowed,
            "advanced_rules_allowed": auto_allowed,
            "load_balance_pro": plan_code == "pro",
            "plan_code": plan_code,
        },
    }


async def patch_distribution_settings(
    db: AsyncSession,
    *,
    tenant_id: str,
    patch: Dict[str, Any],
) -> Dict[str, Any]:
    trow = await db.execute(select(Tenant).where(Tenant.id == tenant_id).limit(1))
    tenant = trow.scalar_one_or_none()
    if tenant is None:
        return DEFAULTS

    settings_all: Dict[str, Any] = dict(tenant.settings or {}) if isinstance(tenant.settings, dict) else {}
    cur = _merge_settings(settings_all.get(DIST_KEY))

    auto_allowed, _ = await _plan_allows_auto(db, tenant_id)
    if patch.get("mode") == "automatic" and not auto_allowed:
        patch = {k: v for k, v in patch.items() if k != "mode"}

    for key in ("mode", "strategy", "only_active_employees", "preview_language"):
        if key in patch and patch[key] is not None:
            cur[key] = patch[key]
    if "strategy" in patch and patch["strategy"] is not None and patch["strategy"] != "round_robin":
        cur["round_robin_last_user_id"] = None
    if patch.get("max_leads_per_person") is not None:
        try:
            v = int(patch["max_leads_per_person"])
            if 1 <= v <= 500:
                cur["max_leads_per_person"] = v
        except (TypeError, ValueError):
            pass
    if isinstance(patch.get("criteria_order"), list):
        allowed = {"working_hours", "workload", "language", "experience"}
        co = [str(x).strip() for x in patch["criteria_order"] if str(x).strip() in allowed]
        if co:
            cur["criteria_order"] = co

    if isinstance(patch.get("language_routing_v1"), dict):
        sanitized = _sanitize_language_routing_v1(patch["language_routing_v1"])
        res = await db.execute(
            select(User.id).where(
                User.tenant_id == tenant_id,
                User.is_active.is_(True),
                User.deleted_at.is_(None),
            )
        )
        allowed = {str(r[0]) for r in res.fetchall()}
        filtered: Dict[str, List[str]] = {}
        for lk, uids in sanitized.items():
            keep = [u for u in uids if u in allowed]
            if keep:
                filtered[lk] = keep
        cur["language_routing_v1"] = filtered

    settings_all[DIST_KEY] = cur
    tenant.settings = settings_all
    db.add(tenant)
    await db.flush()
    return cur
