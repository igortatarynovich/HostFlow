"""C1.2 — UpdateThreadWorkflow: ops / SLA policy meta mutations."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.communications._helpers.escalation import (
    _emit_manual_thread_escalation_bridge,
)
from backend.app.api.v1.communications._helpers.sla import _resolve_thread_sla_alerts
from backend.app.api.v1.communications._helpers.tenant_settings import (
    _tenant_comm_allowed_roles,
    _tenant_sla_escalation_targets,
)
from backend.app.api.v1.communications._helpers.utils import (
    _as_dict,
    _deep_merge_dict,
    _now_utc as now_utc,
)
from backend.app.models.communication import CommunicationThread
from backend.app.models.user import User


def _wf_error(detail: dict[str, Any]) -> Exception:
    from backend.app.communications.workspace_commands import WorkspaceCommandError

    return WorkspaceCommandError(
        str(detail.get("code") or "workflow_invalid"),
        str(detail.get("message") or "Invalid workflow update"),
        {k: v for k, v in detail.items() if k not in ("code", "message")},
    )


async def apply_thread_workflow_meta(
    db: AsyncSession,
    *,
    tenant_id: str,
    tenant: Any,
    thread: CommunicationThread,
    actor_user_id: str | None,
    meta_patch: dict[str, Any],
) -> list[dict[str, Any]]:
    """Merge thread_meta patch with SLA/ops side-effects. Mutates thread in-session."""
    actions: list[dict[str, Any]] = [{"field": "thread_meta", "op": "merge"}]
    meta_before_merge = _as_dict(thread.thread_meta)
    merged_meta = _deep_merge_dict(meta_before_merge, _as_dict(meta_patch))
    merged_sla_policy = _as_dict(merged_meta.get("sla_policy"))
    merged_ops = _as_dict(merged_meta.get("ops"))
    now = now_utc()
    muted = bool(merged_sla_policy.get("muted") or merged_meta.get("sla_muted"))
    merged_sla_policy["muted"] = muted
    merged_meta["sla_muted"] = muted
    if muted and not merged_sla_policy.get("muted_at"):
        merged_sla_policy["muted_at"] = now.isoformat()
    if not muted:
        merged_sla_policy.pop("muted_at", None)
    no_reply_needed = bool(merged_sla_policy.get("no_reply_needed") or merged_meta.get("no_reply_needed"))
    merged_sla_policy["no_reply_needed"] = no_reply_needed
    merged_meta["no_reply_needed"] = no_reply_needed
    if muted:
        await _resolve_thread_sla_alerts(
            db,
            tenant_id=tenant_id,
            thread_id=str(thread.id),
            close_mode="cancelled",
        )
    if no_reply_needed:
        thread.sla_due_at = None
        if not merged_sla_policy.get("no_reply_needed_at"):
            merged_sla_policy["no_reply_needed_at"] = now.isoformat()
        merged_sla_policy.pop("snoozed_until", None)
        await _resolve_thread_sla_alerts(
            db,
            tenant_id=tenant_id,
            thread_id=str(thread.id),
            close_mode="cancelled",
        )
    else:
        merged_sla_policy.pop("no_reply_needed_at", None)
        snoozed_until_raw = str(merged_sla_policy.get("snoozed_until") or "").strip()
        if snoozed_until_raw:
            snoozed_until = None
            try:
                snoozed_until = datetime.fromisoformat(snoozed_until_raw.replace("Z", "+00:00"))
            except Exception:
                snoozed_until = None
            if snoozed_until is not None and snoozed_until.tzinfo is None:
                snoozed_until = snoozed_until.replace(tzinfo=timezone.utc)
            if snoozed_until is not None and snoozed_until > now:
                thread.sla_due_at = snoozed_until
                merged_sla_policy["snoozed_until"] = snoozed_until.isoformat()
                await _resolve_thread_sla_alerts(
                    db,
                    tenant_id=tenant_id,
                    thread_id=str(thread.id),
                    close_mode="cancelled",
                )
            else:
                merged_sla_policy.pop("snoozed_until", None)

    ops_mode = str(merged_ops.get("mode") or "").strip().lower()
    if ops_mode == "escalated":
        escalation = _as_dict(merged_ops.get("escalation"))
        prev_esc = _as_dict(_as_dict(meta_before_merge.get("ops")).get("escalation"))
        prev_target = _as_dict(prev_esc.get("target"))
        target = _as_dict(escalation.get("target"))
        reason = str(escalation.get("reason") or "").strip()
        has_target = any(
            str(target.get(k) or "").strip()
            for k in ("queue", "role", "user_id")
        )
        prev_reason = str(prev_esc.get("reason") or "").strip()
        has_prev_target = any(
            str(prev_target.get(k) or "").strip()
            for k in ("queue", "role", "user_id")
        )
        if (not reason and prev_reason) or (not has_target and has_prev_target):
            escalation = {**prev_esc, **escalation}
            escalation["target"] = {**prev_target, **_as_dict(escalation.get("target"))}
            merged_ops["escalation"] = escalation
            reason = str(escalation.get("reason") or "").strip()
            target = _as_dict(escalation.get("target"))
            has_target = any(
                str(target.get(k) or "").strip()
                for k in ("queue", "role", "user_id")
            )
        if not reason:
            raise _wf_error({
                    "code": "ops_escalation_reason_required",
                    "message": "Escalation reason is required for escalated mode",
                })
        if not has_target:
            raise _wf_error({
                    "code": "ops_escalation_target_required",
                    "message": "Escalation target is required for escalated mode",
                })
        queue_target = str(target.get("queue") or "").strip()
        if queue_target:
            allowed_targets = _tenant_sla_escalation_targets(tenant)
            if allowed_targets and queue_target not in allowed_targets:
                raise _wf_error({
                        "code": "ops_escalation_target_unknown_queue",
                        "message": "Escalation queue target is not allowed by tenant SLA settings",
                        "allowed_targets": sorted(allowed_targets),
                    })
        role_target = str(target.get("role") or "").strip().lower()
        if role_target:
            if not re.match(r"^[a-z][a-z0-9_-]{1,63}$", role_target):
                raise _wf_error({
                        "code": "ops_escalation_target_invalid_role",
                        "message": "Escalation role target has invalid format",
                        "role": role_target,
                    })
            allowed_roles = _tenant_comm_allowed_roles(tenant)
            if allowed_roles and role_target not in allowed_roles:
                raise _wf_error({
                        "code": "ops_escalation_target_unknown_role",
                        "message": "Escalation role target is not allowed by tenant communications access settings",
                        "allowed_roles": sorted(allowed_roles),
                    })
            target["role"] = role_target
        user_target = str(target.get("user_id") or "").strip()
        if user_target:
            try:
                UUID(user_target)
            except Exception:
                raise _wf_error({
                        "code": "ops_escalation_target_invalid_user_id",
                        "message": "Escalation user target must be a valid UUID",
                        "user_id": user_target,
                    })
            user_row = (
                await db.execute(
                    sa.select(User.id)
                    .where(
                        User.id == user_target,
                        User.tenant_id == tenant_id,
                        User.is_active.is_(True),
                    )
                    .limit(1)
                )
            ).scalar_one_or_none()
            if user_row is None:
                raise _wf_error({
                        "code": "ops_escalation_target_unknown_user",
                        "message": "Escalation user target does not belong to current tenant or is inactive",
                        "user_id": user_target,
                    })
        escalation["reason"] = reason
        escalation["target"] = target
        escalation["escalated_at"] = str(escalation.get("escalated_at") or now.isoformat())
        merged_ops["escalation"] = escalation
        prev_ops_before = _as_dict(meta_before_merge.get("ops"))
        prev_mode_before = str(prev_ops_before.get("mode") or "").strip().lower()
        if prev_mode_before != "escalated":
            await _emit_manual_thread_escalation_bridge(
                db,
                tenant_id=tenant_id,
                thread=thread,
                escalation=dict(escalation),
                actor_user_id=actor_user_id,
            )
        if str(thread.priority or "").strip().lower() != "high":
            thread.priority = "high"

    if ops_mode in ("later", "paused"):
        paused_until_raw = str(merged_ops.get("paused_until") or "").strip()
        paused_until = None
        if paused_until_raw:
            try:
                paused_until = datetime.fromisoformat(paused_until_raw.replace("Z", "+00:00"))
            except Exception:
                paused_until = None
        if paused_until is not None and paused_until.tzinfo is None:
            paused_until = paused_until.replace(tzinfo=timezone.utc)
        if paused_until is not None and paused_until > now:
            merged_ops["mode"] = "later"
            merged_ops["paused_until"] = paused_until.isoformat()
            merged_sla_policy["no_reply_needed"] = False
            merged_meta["no_reply_needed"] = False
            merged_sla_policy["snoozed_until"] = paused_until.isoformat()
            thread.sla_due_at = paused_until
            await _resolve_thread_sla_alerts(
                db,
                tenant_id=tenant_id,
                thread_id=str(thread.id),
                close_mode="cancelled",
            )
        else:
            merged_ops["mode"] = "in_work"
            merged_ops.pop("paused_until", None)
            merged_sla_policy.pop("snoozed_until", None)
    else:
        merged_ops.pop("paused_until", None)

    merged_meta["ops"] = merged_ops
    merged_meta["sla_policy"] = merged_sla_policy
    thread.thread_meta = merged_meta

    return actions
