# Billing legal exhibits (SSOT §2.16 checklist)

Canonical **English draft HTML** for tenant-scoped `legal_documents` rows lives in:

- `backend/app/legal/billing_terms_templates_v1.py` (`default_billing_template_items()`)

Types: `trial_terms`, `downgrade_cancellation`, `overage_autodebit`, `data_retention`, `automation_disclaimer`, `mapping_disclaimer`.

**Admin:** Settings → Legal documents → *Billing & subscription exhibits*, or `GET /api/v1/legal-documents/default-templates/billing-v1` (authenticated admin).

Drafts are **not** legal advice; replace with counsel-approved text and your locale.
