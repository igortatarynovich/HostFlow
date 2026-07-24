# Acquisition UI Cutover — Connect Source picker enrichment

**Status:** IMPLEMENTED (local SoT + Graph hydrate for names)  
**Date:** 2026-07-24  
**Canon:** [acquisition-ui-cutover.md](acquisition-ui-cutover.md)  
**Parents:** C-3 (#160) · C-3.1 Sources list columns · Campaign Detail Source cards (PR2)  
**Not:** C-4 test-lead · C-5 mapping · FlightAdBinding Ad-ID UI  

> Connect Source Meta picker must show **human form / page / ad labels**, not only IDs.  
> Root cause #1: different endpoint than Sources list (C-3.1).  
> Root cause #2: SoT had no `form_name` / page name — hydrate from Meta Graph + cache `form_name`.

---

## 1. Why

| Surface | Endpoint / compose | Enrichment |
|---------|-------------------|------------|
| Marketing → Sources list | `list_marketing_source_summaries` (`sources_read.py`) | C-3.1 — `page_id`, `provider_form`, `destination` via **`campaign_source_cards`** |
| Campaign Detail Source cards | `_campaign_out` + `enrich_intake_source_card` | PR2 — `lead_form_name`, `page_id`, … |
| **Connect Source picker** | `GET /platform/campaigns/intake-source-options` (`campaigns.py`) | **None** — `name=str(r.name or r.code or r.id)` only |

Operators choose a Meta form **here**. Raw `Meta form {id}` blocks self-serve setup even when Form IDs already match Ads Manager.

**Non-cause:** Meta Form ID sync failure (Ad `120249…` → form `135224…` already verified in prod leads).

---

## 2. Product job

On Connect Source → Meta Lead Ads, each option shows enough to pick without opening Ads Manager side-by-side:

- human form title when known (`lead_form_name` / `display_title`) — from mapping **or Graph hydrate**
- **Form ID** (always)
- **Page** — name from Graph when token available; else page ID
- recent **Ads** with Graph / `meta_ads_map.note` / vacancy labels when available
- optional: last submission timestamp

---

## 3. Donor (do not re-invent)

**Primary donor:** `backend/app/acquisition/campaign_source_cards.py`

Reuse (already imported by `campaigns.py` for Detail cards):

- `enrich_intake_source_card`
- `load_meta_form_mappings_by_form_id`
- `parse_meta_form_id` / `parse_meta_page_id` (via enrich)
- `humanize_meta_profile_name` (via enrich)
- `load_last_submission_by_endpoint` + `intake_source_endpoint_id`

**Pattern reference:** C-3.1 compose in `sources_read.py` (same helpers, list shape).

**Forbidden:** new local name dictionary; inventing page/form names without Graph or operator SoT.

**Allowed Graph (this slice):** page token → form `name`, page `name`, sample ad `name`; cache form name on `meta_lead_form_mappings` only (do not wipe `mapping_rules`).

---

## 4. API shape (additive)

`IntakeSourceOptionOut` keeps `id`, `name`, `provider`, `code`, `is_active` (compat).

Add optional:

| Field | Source |
|-------|--------|
| `display_title` | `enrich_intake_source_card.display_title` |
| `lead_form_name` | enrich / `meta_map.form_name` |
| `meta_form_id` | enrich |
| `page_id` | enrich |
| `page_name` | enrich (usually `null`) |
| `last_submission_at` | activity endpoint map |
| `sample_ad_ids` | top recent distinct `leads.ad_id` for this `form_id` (cap 3) — recognition aid when name empty |

---

## 5. UI

`MarketingConnectSourcePage` Meta cards:

- primary line: `lead_form_name` or «Lead Form»
- secondary: Form ID · Page · sample Ad IDs · last lead (if present)
- do not show only `name` / `code` when enrichment exists

---

## 6. Out of scope

- Binding Ad ID → Flight UI (API exists; separate slice)
- Writing `form_name` / page name from Graph
- Changing attach/connect write contracts
- Reopening C-3 / C-3.1

---

## 7. Acceptance

- [ ] `GET .../intake-source-options?provider=meta` returns enrichment fields for Meta profiles with bindings
- [ ] Connect Source UI shows Form ID + Page (and sample ads when leads exist) — not sole `Meta form {id}` line
- [ ] No new donor module; compose calls `campaign_source_cards`
- [ ] Existing intake-source-options company filter tests still pass
