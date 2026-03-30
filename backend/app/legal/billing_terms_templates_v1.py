"""Draft HTML exhibits for §2.16 billing/subscription checklist (trial, downgrade, overage, retention, disclaimers).

These are **not** legal advice. Tenants must have qualified counsel adapt text, language, and jurisdiction.
"""

from __future__ import annotations

ORDERED_BILLING_LEGAL_TYPES: tuple[str, ...] = (
    "trial_terms",
    "downgrade_cancellation",
    "overage_autodebit",
    "data_retention",
    "automation_disclaimer",
    "mapping_disclaimer",
)

BILLING_LEGAL_DOC_TYPES: frozenset[str] = frozenset(ORDERED_BILLING_LEGAL_TYPES)

CORE_LEGAL_DOC_TYPES: frozenset[str] = frozenset({"rodo_clause", "privacy_policy"})

ORDERED_LEGAL_DOC_TYPES: tuple[str, ...] = ("rodo_clause", "privacy_policy") + ORDERED_BILLING_LEGAL_TYPES

ALL_LEGAL_DOC_TYPES: frozenset[str] = frozenset(ORDERED_LEGAL_DOC_TYPES)

# Default version_id suggested when seeding from drafts.
_DRAFT_VERSION = "draft-ssot-v1"

# Short HTML bodies; tenants typically replace with hosted PDF URL via content_url instead.
_TRIAL_HTML = """<div class="hf-legal-draft">
<p><strong>DRAFT — NOT LEGAL ADVICE.</strong> Replace with counsel-approved text.</p>
<h1>Trial terms</h1>
<p>The trial period, eligible features, and limits are defined in your order summary and the applicable plan description. When the trial ends, continued use requires an active paid subscription unless otherwise agreed.</p>
<p>Usage during trial may be subject to technical, fair-use, or anti-abuse limits described in product documentation.</p>
</div>"""

_DOWNGRADE_HTML = """<div class="hf-legal-draft">
<p><strong>DRAFT — NOT LEGAL ADVICE.</strong> Replace with counsel-approved text.</p>
<h1>Plan changes, downgrade, and cancellation</h1>
<p><strong>Upgrade:</strong> may take effect according to the billing provider’s proration rules stated at checkout.</p>
<p><strong>Downgrade:</strong> typically applies from the next billing period unless your order states otherwise. After a downgrade, if your usage exceeds the new plan limits, the service may restrict creation of new records, integrations, or features until usage is within limits or the plan is upgraded.</p>
<p><strong>Cancellation:</strong> access generally continues until the end of the paid period unless stated otherwise. Export your data before closure if the product provides export tools.</p>
</div>"""

_OVERAGE_HTML = """<div class="hf-legal-draft">
<p><strong>DRAFT — NOT LEGAL ADVICE.</strong> Replace with counsel-approved text.</p>
<h1>Limits and automatic charges for usage (overage)</h1>
<p>Some usage types may be capped by plan. Where the product offers <strong>paid overage</strong> or add-on packs, charges may be applied only if you have <strong>explicitly consented</strong> to automatic billing for those items (e.g. at checkout or in billing settings).</p>
<p>Without such consent, exceeding a limit may result in soft warnings, hard blocks, or a requirement to upgrade — not unanticipated charges.</p>
</div>"""

_RETENTION_HTML = """<div class="hf-legal-draft">
<p><strong>DRAFT — NOT LEGAL ADVICE.</strong> Replace with counsel-approved text.</p>
<h1>Data retention after cancellation or archive</h1>
<p>Distinguish <strong>active</strong> records (in day-to-day recruiting workflows) from <strong>archived</strong> records where applicable. Archived data may be stored under separate limits described in your plan or data processing terms.</p>
<p>After subscription cancellation or account closure, data may be retained for a defined period for legal, security, or backup reasons, then deleted or anonymised as described in the main Terms / DPA. Align this section with your backup and subprocessors policy.</p>
</div>"""

_AUTOMATION_HTML = """<div class="hf-legal-draft">
<p><strong>DRAFT — NOT LEGAL ADVICE.</strong> Replace with counsel-approved text.</p>
<h1>Automation rules</h1>
<p>Automation executes according to <strong>rules configured by your organisation</strong>. You are responsible for designing, testing, and maintaining those rules (including assignment, messaging triggers, and integrations).</p>
<p>The platform provider does not guarantee outcomes of automation and is <strong>not liable</strong> for business or legal consequences arising from misconfigured rules, third-party API changes, or operator error.</p>
</div>"""

_MAPPING_HTML = """<div class="hf-legal-draft">
<p><strong>DRAFT — NOT LEGAL ADVICE.</strong> Replace with counsel-approved text.</p>
<h1>Lead sources, field mapping, and custom fields</h1>
<p>You are responsible for mapping fields from external sources (e.g. advertising forms, webhooks) to internal fields, and for the accuracy of custom field definitions used in filters and automation.</p>
<p>The platform does not warrant that mapped or normalised data is correct; validation and compliance with applicable law (including marketing consent and data minimisation) remain your responsibility.</p>
</div>"""


def default_billing_template_items() -> list[dict[str, str]]:
    """Static drafts for admin UI / API `GET …/default-templates/billing-v1`."""
    pairs: list[tuple[str, str]] = [
        ("trial_terms", _TRIAL_HTML),
        ("downgrade_cancellation", _DOWNGRADE_HTML),
        ("overage_autodebit", _OVERAGE_HTML),
        ("data_retention", _RETENTION_HTML),
        ("automation_disclaimer", _AUTOMATION_HTML),
        ("mapping_disclaimer", _MAPPING_HTML),
    ]
    return [
        {"type": t, "version_id": _DRAFT_VERSION, "content_html": html} for t, html in pairs
    ]
