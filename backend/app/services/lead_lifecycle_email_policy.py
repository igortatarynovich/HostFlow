"""ADR-033 — resolve lead lifecycle email policy (Vacancy → Company → Tenant preset)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.company_module_settings import CompanyModuleSettings
from backend.app.models.tenant import Tenant
from backend.app.models.vacancy import Vacancy
from backend.app.services.lead_communication_settings import (
    lead_communication_settings_from_tenant_dict,
)
from backend.app.services.lead_rodo_settings import lead_rodo_settings_from_tenant_dict

PURPOSE_GDPR_NOTICE = "gdpr_notice"
PURPOSE_SUBMISSION_ACK = "submission_acknowledgement"
PURPOSE_INTAKE_REJECTION = "intake_rejection_notice"
PURPOSE_MOVING_FORWARD = "moving_forward_notice"

LIFECYCLE_PURPOSES: frozenset[str] = frozenset(
    {
        PURPOSE_GDPR_NOTICE,
        PURPOSE_SUBMISSION_ACK,
        PURPOSE_INTAKE_REJECTION,
        PURPOSE_MOVING_FORWARD,
    }
)

OPS_PURPOSE_TO_KEY: dict[str, str] = {
    PURPOSE_SUBMISSION_ACK: "application_received",
    PURPOSE_INTAKE_REJECTION: "rejection",
    PURPOSE_MOVING_FORWARD: "moving_forward",
}

SourceLayer = Literal["vacancy", "company", "tenant_preset", "none"]
BlockCode = Optional[
    Literal[
        "disabled",
        "policy_template_missing",
        "policy_misconfigured",
        "unknown_purpose",
        "missing_company",
    ]
]


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    purpose: str
    send: bool
    template_ref: Optional[str]
    source_layer: SourceLayer
    block_code: BlockCode
    send_mode: Optional[str] = None  # RODO only
    enabled: bool = False
    reason: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "purpose": self.purpose,
            "send": self.send,
            "template_ref": self.template_ref,
            "source_layer": self.source_layer,
            "block_code": self.block_code,
            "send_mode": self.send_mode,
            "enabled": self.enabled,
            "reason": self.reason,
        }


def _trim(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    s = str(raw).strip()
    return s or None


def _as_dict(raw: Any) -> dict[str, Any]:
    return raw if isinstance(raw, dict) else {}


def _vacancy_override_block(settings_json: Any) -> dict[str, Any]:
    root = _as_dict(settings_json)
    return _as_dict(root.get("lead_lifecycle_email_override_v1"))


def _company_policy_block(settings_json: Any) -> dict[str, Any]:
    root = _as_dict(settings_json)
    return _as_dict(root.get("lead_lifecycle_email_v1"))


def tenant_preset_to_company_policy(tenant_settings: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Map tenant JSON preset → lead_lifecycle_email_v1 shape (cutover / fallback)."""
    rodo = lead_rodo_settings_from_tenant_dict(tenant_settings)
    ops = lead_communication_settings_from_tenant_dict(tenant_settings)
    return {
        "version": 1,
        "rodo_send_mode": rodo.send_mode,
        "rodo_template_ref": rodo.message_template_id or rodo.template_id,
        "ops_enabled": ops.enabled,
        "application_received": {
            "enabled": bool(ops.enabled and ops.send_application_received),
            "template_ref": ops.application_received_template_id,
        },
        "rejection": {
            "enabled": bool(ops.enabled and ops.send_rejection_notice),
            "template_ref": ops.rejection_notice_template_id,
        },
        "moving_forward": {
            "enabled": bool(ops.enabled and ops.send_moving_forward_notice),
            "template_ref": ops.moving_forward_template_id,
        },
        "channels": list(rodo.channels) if rodo.channels else ["email"],
    }


def _merge_layers(
    *,
    vacancy_ov: dict[str, Any],
    company: dict[str, Any],
    tenant: dict[str, Any],
    purpose: str,
) -> tuple[bool, Optional[str], SourceLayer, Optional[str]]:
    """Return enabled, template_ref, layer, send_mode(for rodo)."""
    if purpose == PURPOSE_GDPR_NOTICE:
        # Vacancy may override template_ref / enabled (enabled=false turns off auto send)
        v = _as_dict(vacancy_ov.get(PURPOSE_GDPR_NOTICE) or vacancy_ov.get("gdpr_notice"))
        if v:
            enabled = True if "enabled" not in v else bool(v.get("enabled"))
            tmpl = _trim(v.get("template_ref"))
            mode = _trim(v.get("send_mode")) or _trim(company.get("rodo_send_mode")) or _trim(
                tenant.get("rodo_send_mode")
            ) or "manual"
            if tmpl is None:
                tmpl = _trim(company.get("rodo_template_ref")) or _trim(tenant.get("rodo_template_ref"))
                layer: SourceLayer = "vacancy" if _trim(v.get("template_ref")) else (
                    "company" if _trim(company.get("rodo_template_ref")) else "tenant_preset"
                )
            else:
                layer = "vacancy"
            # send_mode always from company/tenant unless vacancy provided
            if not _trim(v.get("send_mode")):
                if _trim(company.get("rodo_send_mode")):
                    mode = _trim(company.get("rodo_send_mode")) or mode
                    if layer == "vacancy" and not _trim(v.get("template_ref")):
                        pass
                elif _trim(tenant.get("rodo_send_mode")):
                    mode = _trim(tenant.get("rodo_send_mode")) or mode
            return enabled, tmpl, layer, mode

        if company:
            mode = _trim(company.get("rodo_send_mode")) or "manual"
            tmpl = _trim(company.get("rodo_template_ref"))
            if tmpl or mode:
                return True, tmpl, "company", mode
        mode = _trim(tenant.get("rodo_send_mode")) or "manual"
        tmpl = _trim(tenant.get("rodo_template_ref"))
        return True, tmpl, "tenant_preset" if tenant else "none", mode

    key = OPS_PURPOSE_TO_KEY.get(purpose)
    if not key:
        return False, None, "none", None

    v = _as_dict(vacancy_ov.get(purpose) or vacancy_ov.get(key))
    if v:
        enabled = bool(v.get("enabled")) if "enabled" in v else False
        tmpl = _trim(v.get("template_ref"))
        if tmpl is None:
            c = _as_dict(company.get(key))
            t = _as_dict(tenant.get(key))
            ops_on = bool(company.get("ops_enabled")) if company else bool(tenant.get("ops_enabled"))
            if "enabled" not in v:
                enabled = ops_on and bool(c.get("enabled") if c else t.get("enabled"))
            tmpl = _trim(c.get("template_ref")) or _trim(t.get("template_ref"))
            layer = "vacancy"
            if _trim(v.get("template_ref")) is None:
                layer = "company" if _trim(c.get("template_ref")) else "tenant_preset"
        else:
            layer = "vacancy"
        return enabled, tmpl, layer, None

    if company:
        ops_on = bool(company.get("ops_enabled"))
        c = _as_dict(company.get(key))
        enabled = ops_on and bool(c.get("enabled"))
        tmpl = _trim(c.get("template_ref"))
        return enabled, tmpl, "company", None

    ops_on = bool(tenant.get("ops_enabled"))
    t = _as_dict(tenant.get(key))
    enabled = ops_on and bool(t.get("enabled"))
    tmpl = _trim(t.get("template_ref"))
    return enabled, tmpl, "tenant_preset" if tenant else "none", None


def decide_from_layers(
    *,
    purpose: str,
    vacancy_ov: dict[str, Any],
    company: dict[str, Any],
    tenant: dict[str, Any],
    company_id: Optional[str],
) -> PolicyDecision:
    purpose = str(purpose or "").strip()
    if purpose not in LIFECYCLE_PURPOSES:
        return PolicyDecision(
            purpose=purpose,
            send=False,
            template_ref=None,
            source_layer="none",
            block_code="unknown_purpose",
            enabled=False,
            reason="Unknown lifecycle purpose.",
        )
    if not company_id:
        return PolicyDecision(
            purpose=purpose,
            send=False,
            template_ref=None,
            source_layer="none",
            block_code="missing_company",
            enabled=False,
            reason="Lead has no company_id; lifecycle email policy requires a client company.",
        )

    enabled, tmpl, layer, mode = _merge_layers(
        vacancy_ov=vacancy_ov, company=company, tenant=tenant, purpose=purpose
    )

    if purpose == PURPOSE_GDPR_NOTICE:
        # RODO always "enabled" for gate purposes; send depends on mode + template when auto
        if mode == "manual":
            # Manual: no auto-send; template optional until operator sends
            if not tmpl:
                return PolicyDecision(
                    purpose=purpose,
                    send=False,
                    template_ref=None,
                    source_layer=layer,
                    block_code="policy_template_missing",
                    send_mode=mode,
                    enabled=True,
                    reason="RODO template_ref is missing; configure in Lead lifecycle email Control Center.",
                )
            return PolicyDecision(
                purpose=purpose,
                send=False,
                template_ref=tmpl,
                source_layer=layer,
                block_code=None,
                send_mode=mode,
                enabled=True,
                reason=None,
            )
        # auto modes require template to send
        if not enabled:
            return PolicyDecision(
                purpose=purpose,
                send=False,
                template_ref=tmpl,
                source_layer=layer,
                block_code="disabled",
                send_mode=mode,
                enabled=False,
                reason="RODO outbound disabled by vacancy override.",
            )
        if not tmpl:
            return PolicyDecision(
                purpose=purpose,
                send=False,
                template_ref=None,
                source_layer=layer,
                block_code="policy_template_missing",
                send_mode=mode,
                enabled=True,
                reason="RODO auto-send enabled but template_ref is missing.",
            )
        return PolicyDecision(
            purpose=purpose,
            send=True,
            template_ref=tmpl,
            source_layer=layer,
            block_code=None,
            send_mode=mode,
            enabled=True,
            reason=None,
        )

    # Ops purposes
    if not enabled:
        return PolicyDecision(
            purpose=purpose,
            send=False,
            template_ref=tmpl,
            source_layer=layer,
            block_code="disabled",
            enabled=False,
            reason=None,
        )
    if not tmpl:
        return PolicyDecision(
            purpose=purpose,
            send=False,
            template_ref=None,
            source_layer=layer,
            block_code="policy_template_missing",
            enabled=True,
            reason="Purpose enabled but template_ref is missing.",
        )
    return PolicyDecision(
        purpose=purpose,
        send=True,
        template_ref=tmpl,
        source_layer=layer,
        block_code=None,
        enabled=True,
        reason=None,
    )


OPS_EVENT_TO_PURPOSE: dict[str, str] = {
    "application_received": PURPOSE_SUBMISSION_ACK,
    "lead_rejected": PURPOSE_INTAKE_REJECTION,
    "moving_forward": PURPOSE_MOVING_FORWARD,
}

SAFE_DEFAULT_COMPANY_POLICY: dict[str, Any] = {
    "version": 1,
    "rodo_send_mode": "manual",
    "rodo_template_ref": None,
    "ops_enabled": False,
    "application_received": {"enabled": False, "template_ref": None},
    "rejection": {"enabled": False, "template_ref": None},
    "moving_forward": {"enabled": False, "template_ref": None},
    "channels": ["email"],
}

CUTOVER_SETTINGS_KEY = "lead_lifecycle_email_cutover_v1"


def cutover_completed(tenant_settings: Optional[dict[str, Any]]) -> bool:
    if not isinstance(tenant_settings, dict):
        return False
    block = tenant_settings.get(CUTOVER_SETTINGS_KEY)
    if not isinstance(block, dict):
        return False
    return bool(str(block.get("completed_at") or "").strip())


def mark_cutover_completed(tenant_settings: dict[str, Any], *, at_iso: str) -> dict[str, Any]:
    out = dict(tenant_settings)
    out[CUTOVER_SETTINGS_KEY] = {"completed_at": at_iso, "version": 1}
    return out


async def resolve_lifecycle_email_policy(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: Optional[str],
    vacancy_id: Optional[str],
    purpose: str,
) -> PolicyDecision:
    tenant = await db.get(Tenant, str(tenant_id))
    tenant_settings = tenant.settings if tenant is not None and isinstance(tenant.settings, dict) else {}
    tenant_policy = tenant_preset_to_company_policy(tenant_settings)

    company_policy: dict[str, Any] = {}
    if company_id:
        row = (
            await db.execute(
                select(CompanyModuleSettings).where(
                    CompanyModuleSettings.tenant_id == str(tenant_id),
                    CompanyModuleSettings.company_id == str(company_id),
                    CompanyModuleSettings.module_key == "recruitment",
                )
            )
        ).scalar_one_or_none()
        if row is not None:
            company_policy = _company_policy_block(row.settings_json)

    # After cutover, net-new companies without a company block must not inherit live tenant ops.
    if not company_policy and cutover_completed(tenant_settings):
        tenant_policy = dict(SAFE_DEFAULT_COMPANY_POLICY)

    vacancy_ov: dict[str, Any] = {}
    if vacancy_id:
        vac = await db.get(Vacancy, str(vacancy_id))
        if vac is not None and str(getattr(vac, "tenant_id", "") or "") == str(tenant_id):
            vacancy_ov = _vacancy_override_block(getattr(vac, "settings_json", None))

    return decide_from_layers(
        purpose=purpose,
        vacancy_ov=vacancy_ov,
        company=company_policy,
        tenant=tenant_policy,
        company_id=str(company_id).strip() if company_id else None,
    )


async def resolve_lifecycle_email_policy_for_lead(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Any,
    purpose: str,
) -> PolicyDecision:
    company_id = getattr(lead, "company_id", None)
    vacancy_id = getattr(lead, "vacancy_id", None)
    return await resolve_lifecycle_email_policy(
        db,
        tenant_id=str(tenant_id),
        company_id=str(company_id).strip() if company_id else None,
        vacancy_id=str(vacancy_id).strip() if vacancy_id else None,
        purpose=purpose,
    )


__all__ = [
    "BlockCode",
    "CUTOVER_SETTINGS_KEY",
    "LIFECYCLE_PURPOSES",
    "OPS_EVENT_TO_PURPOSE",
    "OPS_PURPOSE_TO_KEY",
    "PURPOSE_GDPR_NOTICE",
    "PURPOSE_INTAKE_REJECTION",
    "PURPOSE_MOVING_FORWARD",
    "PURPOSE_SUBMISSION_ACK",
    "PolicyDecision",
    "SAFE_DEFAULT_COMPANY_POLICY",
    "cutover_completed",
    "decide_from_layers",
    "mark_cutover_completed",
    "resolve_lifecycle_email_policy",
    "resolve_lifecycle_email_policy_for_lead",
    "tenant_preset_to_company_policy",
]
