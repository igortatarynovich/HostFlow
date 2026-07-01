# Slice 3 — Qualification Summary: data sources audit

**Goal:** one **compact read/decision** block for recruiters (reject / request info / pool / process) — **no** new scoring engine, ML, or workflow statuses.

**Status:** inventory complete; UI consumes existing payloads only.

---

## 1. `lead.normalized` (canonical lead-side blob)

Written by **Meta normalizer** (`normalize_meta_payload` / `normalizer.py`), **CSV `_normalize_row`**, **reprocess merge** (`_merge_lead_normalized_fallback`), and **processing** (`process_normalized_lead`).

| Area | Typical keys | Notes |
|------|----------------|------|
| **Identity / contact** | `email`, `phone`, `phone_country_code`, `preferred_contact`, `first_name`, `last_name`, `full_name`, `raw_lead_id` | CSV always sets email/phone when row valid. |
| **Source / campaign context** | `ad_id`, `form_id`, `created_time`, **`utm`** (dict `utm_*` → first value each), `company_hints`, `company_name_hint`, `vacancy_id_hint`, `vacancy_hint` | Meta: `utm` object from field mapping; CSV: Meta-export overlay adds similar fields when `ad_id` column exists. |
| **Geo / stay** | `country`, `country_raw`, `geo_country`, `in_poland`, `poland_stay_basis`, `poland_stay_basis_raw` | Drives criteria + UI. |
| **Experience** | `experience_eu_years`, `driving_experience_in_europe` | EU years may be derived from driving-experience answer in normalizer. |
| **Eligibility (criteria inputs)** | `nationality`, `nationality_code`, `languages` (list), `language` (string), **`documents`** (list of declared codes) | Populated when form / mapping supplies them; **not** hard-coded in core normalizer for every field — often **custom field mapping**. |
| **Routing hints** | `vacancy_id`, `company_id`, `resolved_vacancy_id` (set during processing), `vacancy_routing_fallback_v1` | `resolved_vacancy_id` reflects pipeline resolution snapshot. |
| **Mode / flags** | `leads_processing_mode_v1`, `leads_auto_convert_on_fit_effective_v1`, **`lead_fit_evaluation_effective_v1`** (bool) | `lead_fit_evaluation_effective_v1` = whether vacancy criteria evaluation is “on” for fit (`lead_criteria_eval.lead_fit_evaluation_effective` on `Vacancy.extra`). |
| **Intake / pool** | `intake_resolution_v1`, `recruitment_pool_intent_v1`, `intake_vacancy_confirm_v1`, … | Slice 2; summary may show pool flag for context. |
| **Qualification artifacts** | **`lead_qualification_preview_v1`**, **`lead_qualification_rule_match_v1`** | See §2–3. |

---

## 2. `lead_qualification_preview_v1` (fit snapshot)

**Writer:** `_stamp_lead_qualification_preview_v1` in `service/_helpers.py`.

**Shape:**

- `suggested_vacancy_id`
- `fit_status` — `fit` | `no_fit` | `needs_info` | `no_criteria` (aligned with `evaluate_vacancy_for_lead` / `evaluate_lead_criteria_v1`)
- `fit_reasons` — string codes (often same family as `app.leads.qualification.reasons.*` on frontend)
- `blocked_auto_convert`
- `evaluated_at` (ISO)

**When stamped:** assisted/automatic branches in `process_normalized_lead` when routing stops at `needs_routing` or fit blocks auto-convert (`_processing.py`).

**UI today:** `LeadQualificationSuggestionPanel` reads this blob; Slice 3 summary **reuses** the same reader (`readLeadQualificationPreview`).

---

## 3. `lead_fit_evaluation_effective_v1`

**Writer:** `process_normalized_lead` sets `normalized["lead_fit_evaluation_effective_v1"]` from `lead_fit_evaluation_effective(vacancy.extra)` (`lead_criteria_eval.py`).

**Meaning:** “Does this vacancy run structured lead criteria?” — not the outcome of fit, but whether **criteria evaluation is active** (vs mapping-only / empty criteria).

---

## 4. `lead_qualification_rule_match_v1`

**Writer:** `pick_vacancy_via_qualification_rules` (`lead_qualification_rules.py`) when an automation rule with trigger `lead.qualification` matches.

**Use:** audit / transparency (“which rule pinned this vacancy attempt”); optional line in summary (`rule_id`, `note`).

---

## 5. Vacancy criteria (not duplicated on Lead row)

**Source of truth:** `Vacancy.extra.lead_criteria_v1` (evaluated by `evaluate_lead_criteria_v1` in `lead_criteria_eval.py`).

**On Lead:** only **results** surface as `fit_status` / `fit_reasons` in `lead_qualification_preview_v1` and pipeline errors (`LEAD_FIT_NO_MATCH`, `LEAD_FIT_NEEDS_INFO` on `lead.error`).  

**Slice 3 UI:** show **criteria text** only indirectly via translated **reason codes**; loading full vacancy criteria JSON on lead detail is **out of scope** for the compact card unless an existing API already embeds it.

---

## 6. Meta payload vs normalized

**Raw:** `lead.payload` — original webhook / ingest JSON.

**Normalized:** `lead.normalized` — operator-facing; summary should prefer **normalized**; payload remains for debugging (existing JSON blocks on detail page).

---

## 7. CSV import normalized fields

**Base row:** `services/imports/leads.py` `_normalize_row` — contact, names, `in_poland`, `poland_stay_basis`, company hints, `vacancy_id` / hint, optional `ad_id`, optional Meta-export overlay when CSV has `ad_id` column.

**Gap vs Meta:** fewer default keys unless columns / overlay populate them (e.g. `utm`, `form_id` may be absent on plain CRM CSV).

---

## 8. Implementation mapping (Slice 3 UI block)

| Summary section | Primary sources |
|-----------------|-----------------|
| Source / campaign / route | `lead.source`, `lead.ad_id`, `normalized.form_id`, `normalized.utm`, `normalized.created_time`, `normalized.company_hints` |
| Contact completeness | `normalized.email`, `normalized.phone` |
| Experience | `normalized.experience_eu_years`, `normalized.driving_experience_in_europe` |
| Documents | `normalized.documents` (list) |
| Citizenship / eligibility | `normalized.country`, `normalized.geo_country`, `normalized.nationality` / `nationality_code`, `normalized.in_poland`, `normalized.poland_stay_basis` |
| Language | `normalized.languages`, `normalized.language` |
| Vacancy / pool context | `lead.vacancy_id`, `lead.vacancy_title`, `lead.suggested_vacancy_id`, `normalized.resolved_vacancy_id`, `lead.funnel_id`, `normalized.recruitment_pool_intent_v1` |
| Fit + reasons | `lead_qualification_preview_v1`, `lead.error` (LEAD_FIT_*), `lead_fit_evaluation_effective_v1` |
| Rule hint | `lead_qualification_rule_match_v1` |

---

## 9. Out of scope (explicit)

- New scoring / ranking models, ML, or propensity scores.
- New lead workflow statuses.
- Persisting a second “summary” blob — **derive** from existing fields at render time.

---

## 10. References (code)

- `backend/app/modules/leads/normalizer.py` — Meta normalization.
- `backend/app/services/imports/leads.py` — CSV `_normalize_row`.
- `backend/app/modules/leads/service/_helpers.py` — `_stamp_lead_qualification_preview_v1`.
- `backend/app/modules/leads/service/_processing.py` — fit stamping, `lead_fit_evaluation_effective_v1`.
- `backend/app/modules/leads/lead_criteria_eval.py` — criteria schema + reason codes.
- `backend/app/modules/leads/lead_qualification_rules.py` — `lead_qualification_rule_match_v1`.
- `hostflow-frontend/src/utils/leadQualificationPreview.ts` — shared preview reader.
- `hostflow-frontend/src/components/leads/LeadQualificationSummaryCard.tsx` — compact summary UI.
