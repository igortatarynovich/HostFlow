"""ADR-033 — resolve lead lifecycle email policy (Vacancy → Client → OwnCompany → Tenant)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.company_module_settings import CompanyModuleSettings
from backend.app.models.own_company import OwnCompany
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

SourceLayer = Literal["vacancy", "client", "own_company", "tenant_preset", "none"]
BlockCode = Optional[
    Literal[
        "disabled",
        "policy_template_missing",
        "policy_misconfigured",
        "unknown_purpose",
        "missing_own_company",
        "missing_company",  # legacy alias — prefer missing_own_company
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


def _own_company_policy_block(extra: Any) -> dict[str, Any]:
    root = _as_dict(extra)
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


def compose_own_and_client_policy(
    own: dict[str, Any],
    client: dict[str, Any],
) -> tuple[dict[str, Any], SourceLayer]:
    """
    Overlay optional client policy onto own-company SoT.

    ``rodo_send_mode`` is never taken from the client overlay (one firm RODO).
    Client may still overlay ``rodo_template_ref`` and ops purposes.

    Returns (merged_policy, base_layer) where base_layer is ``client`` if any
    client field contributed, else ``own_company`` when own is non-empty,
    else ``tenant_preset`` (caller still merges tenant).
    """
    if not client:
        if own:
            return dict(own), "own_company"
        return {}, "tenant_preset"

    if not own:
        # Client may overlay copy/ops, never RODO send_mode (firm / tenant SoT).
        stripped = dict(client)
        stripped.pop("rodo_send_mode", None)
        return stripped, "client"

    out = dict(own)
    layer: SourceLayer = "own_company"

    for key in ("version", "rodo_template_ref", "ops_enabled", "channels"):
        if key not in client:
            continue
        val = client[key]
        if key == "ops_enabled":
            out[key] = bool(val)
            layer = "client"
        elif key == "channels":
            if isinstance(val, (list, tuple)) and val:
                out[key] = list(val)
                layer = "client"
        elif key == "rodo_template_ref":
            if _trim(val) is not None:
                out[key] = _trim(val)
                layer = "client"
        elif val is not None:
            out[key] = val
            layer = "client"

    for pk in ("application_received", "rejection", "moving_forward"):
        if pk not in client or not isinstance(client[pk], dict):
            continue
        base_p = dict(out.get(pk) or {}) if isinstance(out.get(pk), dict) else {}
        ov = client[pk]
        if "enabled" in ov:
            base_p["enabled"] = bool(ov.get("enabled"))
            layer = "client"
        if "template_ref" in ov and _trim(ov.get("template_ref")) is not None:
            base_p["template_ref"] = _trim(ov.get("template_ref"))
            layer = "client"
        out[pk] = base_p

    return out, layer


def _merge_layers(
    *,
    vacancy_ov: dict[str, Any],
    company: dict[str, Any],
    tenant: dict[str, Any],
    purpose: str,
    company_layer: SourceLayer = "own_company",
) -> tuple[bool, Optional[str], SourceLayer, Optional[str]]:
    """Return enabled, template_ref, layer, send_mode(for rodo).

    ``company`` is the composed own(+client) policy. When the merge attributes
    the win to company, map to ``company_layer`` (``own_company`` or ``client``).
    """
    if purpose == PURPOSE_GDPR_NOTICE:
        # One firm RODO: send_mode is OwnCompany then tenant preset. Vacancy/client
        # cannot disable the notice or change auto vs manual (template_ref only).
        mode = _trim(company.get("rodo_send_mode")) or _trim(tenant.get("rodo_send_mode")) or "manual"
        v = _as_dict(vacancy_ov.get(PURPOSE_GDPR_NOTICE) or vacancy_ov.get("gdpr_notice"))
        tmpl = _trim(v.get("template_ref")) if v else None
        if tmpl:
            return True, tmpl, "vacancy", mode
        tmpl = _trim(company.get("rodo_template_ref"))
        if tmpl or _trim(company.get("rodo_send_mode")):
            return True, tmpl, company_layer, mode
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
                layer = company_layer if _trim(c.get("template_ref")) else "tenant_preset"
        else:
            layer = "vacancy"
        return enabled, tmpl, layer, None

    if company:
        ops_on = bool(company.get("ops_enabled"))
        c = _as_dict(company.get(key))
        enabled = ops_on and bool(c.get("enabled"))
        tmpl = _trim(c.get("template_ref"))
        return enabled, tmpl, company_layer, None

    ops_on = bool(tenant.get("ops_enabled"))
    t = _as_dict(tenant.get(key))
    enabled = ops_on and bool(t.get("enabled"))
    tmpl = _trim(t.get("template_ref"))
    return enabled, tmpl, "tenant_preset" if tenant else "none", None


def decide_from_layers(
    *,
    purpose: str,
    vacancy_ov: dict[str, Any],
    tenant: dict[str, Any],
    own_company: Optional[dict[str, Any]] = None,
    own_company_id: Optional[str] = None,
    client_override: Optional[dict[str, Any]] = None,
    # Backward-compat kw for older unit tests / callers
    company: Optional[dict[str, Any]] = None,
    company_id: Optional[str] = None,
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

    # Compat: old signature used company= / company_id= as the firm SoT layer
    if not own_company and company is not None:
        own_company = company
    own_company = _as_dict(own_company)
    resolved_own_id = _trim(own_company_id) or _trim(company_id)
    if not resolved_own_id:
        return PolicyDecision(
            purpose=purpose,
            send=False,
            template_ref=None,
            source_layer="none",
            block_code="missing_own_company",
            enabled=False,
            reason="Lead has no own_company_id; lifecycle email policy requires an operating firm.",
        )

    composed, base_layer = compose_own_and_client_policy(
        _as_dict(own_company),
        _as_dict(client_override),
    )

    enabled, tmpl, layer, mode = _merge_layers(
        vacancy_ov=vacancy_ov,
        company=composed,
        tenant=tenant,
        purpose=purpose,
        company_layer=base_layer if base_layer in ("own_company", "client") else "own_company",
    )

    if purpose == PURPOSE_GDPR_NOTICE:
        if mode == "manual":
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
        if not enabled:
            return PolicyDecision(
                purpose=purpose,
                send=False,
                template_ref=tmpl,
                source_layer=layer,
                block_code="disabled",
                send_mode=mode,
                enabled=False,
                reason="RODO outbound disabled by firm policy.",
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
OWN_COMPANY_CUTOVER_SETTINGS_KEY = "lead_lifecycle_email_own_company_cutover_v1"


def cutover_completed(tenant_settings: Optional[dict[str, Any]]) -> bool:
    """Legacy client-company cutover marker (P4)."""
    if not isinstance(tenant_settings, dict):
        return False
    block = tenant_settings.get(CUTOVER_SETTINGS_KEY)
    if not isinstance(block, dict):
        return False
    return bool(str(block.get("completed_at") or "").strip())


def own_company_cutover_completed(tenant_settings: Optional[dict[str, Any]]) -> bool:
    if not isinstance(tenant_settings, dict):
        return False
    block = tenant_settings.get(OWN_COMPANY_CUTOVER_SETTINGS_KEY)
    if not isinstance(block, dict):
        return False
    return bool(str(block.get("completed_at") or "").strip())


def mark_cutover_completed(tenant_settings: dict[str, Any], *, at_iso: str) -> dict[str, Any]:
    out = dict(tenant_settings)
    out[CUTOVER_SETTINGS_KEY] = {"completed_at": at_iso, "version": 1}
    return out


def mark_own_company_cutover_completed(tenant_settings: dict[str, Any], *, at_iso: str) -> dict[str, Any]:
    out = dict(tenant_settings)
    out[OWN_COMPANY_CUTOVER_SETTINGS_KEY] = {"completed_at": at_iso, "version": 1}
    return out


def set_own_company_lifecycle_policy(own: OwnCompany, policy: dict[str, Any]) -> None:
    """Persist lead_lifecycle_email_v1 onto OwnCompany.extra."""
    extra = dict(own.extra or {}) if isinstance(own.extra, dict) else {}
    extra["lead_lifecycle_email_v1"] = dict(policy)
    own.extra = extra


async def resolve_lifecycle_email_policy(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: Optional[str] = None,
    company_id: Optional[str] = None,
    vacancy_id: Optional[str] = None,
    purpose: str,
) -> PolicyDecision:
    """
    Resolve effective lifecycle email policy.

    ``own_company_id`` is required for a successful decision. ``company_id`` is an
    optional client overlay.
    """
    tenant = await db.get(Tenant, str(tenant_id))
    tenant_settings = tenant.settings if tenant is not None and isinstance(tenant.settings, dict) else {}
    tenant_policy = tenant_preset_to_company_policy(tenant_settings)

    own_id = _trim(own_company_id)
    own_policy: dict[str, Any] = {}
    if own_id:
        own_row = await db.get(OwnCompany, own_id)
        if own_row is not None and str(getattr(own_row, "tenant_id", "") or "") == str(tenant_id):
            own_policy = _own_company_policy_block(getattr(own_row, "extra", None))

    client_policy: dict[str, Any] = {}
    cid = _trim(company_id)
    if cid:
        row = (
            await db.execute(
                select(CompanyModuleSettings).where(
                    CompanyModuleSettings.tenant_id == str(tenant_id),
                    CompanyModuleSettings.company_id == cid,
                    CompanyModuleSettings.module_key == "recruitment",
                )
            )
        ).scalar_one_or_none()
        if row is not None:
            client_policy = _company_policy_block(row.settings_json)

    # After own-company cutover (or legacy client cutover), empty own blob must not
    # inherit live tenant ops — use safe defaults as the tenant fallback layer.
    if not own_policy and (
        own_company_cutover_completed(tenant_settings) or cutover_completed(tenant_settings)
    ):
        tenant_policy = dict(SAFE_DEFAULT_COMPANY_POLICY)

    vacancy_ov: dict[str, Any] = {}
    if vacancy_id:
        vac = await db.get(Vacancy, str(vacancy_id))
        if vac is not None and str(getattr(vac, "tenant_id", "") or "") == str(tenant_id):
            vacancy_ov = _vacancy_override_block(getattr(vac, "settings_json", None))

    return decide_from_layers(
        purpose=purpose,
        vacancy_ov=vacancy_ov,
        own_company=own_policy,
        client_override=client_policy,
        tenant=tenant_policy,
        own_company_id=own_id,
    )


async def resolve_lifecycle_email_policy_for_lead(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Any,
    purpose: str,
) -> PolicyDecision:
    own_company_id = getattr(lead, "own_company_id", None)
    company_id = getattr(lead, "company_id", None)
    vacancy_id = getattr(lead, "vacancy_id", None)
    return await resolve_lifecycle_email_policy(
        db,
        tenant_id=str(tenant_id),
        own_company_id=str(own_company_id).strip() if own_company_id else None,
        company_id=str(company_id).strip() if company_id else None,
        vacancy_id=str(vacancy_id).strip() if vacancy_id else None,
        purpose=purpose,
    )


__all__ = [
    "BlockCode",
    "CUTOVER_SETTINGS_KEY",
    "OWN_COMPANY_CUTOVER_SETTINGS_KEY",
    "LIFECYCLE_PURPOSES",
    "OPS_EVENT_TO_PURPOSE",
    "OPS_PURPOSE_TO_KEY",
    "PURPOSE_GDPR_NOTICE",
    "PURPOSE_INTAKE_REJECTION",
    "PURPOSE_MOVING_FORWARD",
    "PURPOSE_SUBMISSION_ACK",
    "PolicyDecision",
    "SAFE_DEFAULT_COMPANY_POLICY",
    "compose_own_and_client_policy",
    "cutover_completed",
    "decide_from_layers",
    "mark_cutover_completed",
    "mark_own_company_cutover_completed",
    "own_company_cutover_completed",
    "resolve_lifecycle_email_policy",
    "resolve_lifecycle_email_policy_for_lead",
    "set_own_company_lifecycle_policy",
    "tenant_preset_to_company_policy",
]
