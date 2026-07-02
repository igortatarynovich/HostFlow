# Lead intake → Candidate conversion — implementation audit (snapshot)

**Purpose:** map **actual code + UI** to the domain doctrine ([recruitment-domain-model.md](../architecture/recruitment-domain-model.md), [lead-intake-resolution-and-activity-continuity.md](lead-intake-resolution-and-activity-continuity.md)) — what is stable, what diverges, what not to touch yet, recommended slices.

**Scope:** backend HostFlow + CRM lead/candidate UI; **not** a Person/AI/merge design.

**Out of scope for fixes here:** Person layer, fuzzy merge, Application Kanban, rehire engine, intelligence.

**Phase context:** semantic foundation is largely in place; the active push is **operational consolidation** (Intake Resolution MVP and contradictions in this audit) — not new core entities or intelligence-first work until intake is operationally stable.

---

## 1. What is already stable (aligned with doctrine)

| Area | Evidence / behaviour |
|------|----------------------|
| **Conversion boundary (Meta/high-volume)** | `create_candidate_from_lead_conversion` → `create_candidate_full`; audit `candidate_created` + `conversion_contract_version`; idempotent return if `lead.candidate_id` already live. |
| **Duplicate tiers + HR/workforce gate** | `duplicate_resolution`: exact / probable / `duplicate_review`; workforce → review; intake trail on exact attach. |
| **Duplicate decisions** | `attach_existing` / `create_new` / `ignore` + audit; Application after attach/process per MVP rules. |
| **Application intent layer** | `ensure_recruitment_application_for_lead_intent`: **no row** in `duplicate_review`; **no row** without vacancy unless **explicit pool** (`funnel_id` or `normalized.recruitment_pool_intent_v1`); idempotent per `(tenant, candidate, lead)` when `lead_id` set. |
| **Dual-write** | Sets `Candidate.vacancy_id` when effective vacancy known. |
| **Idempotent Meta replay** | Lead lookup by `tenant_id + source + external_id`; early exit for processed/duplicated without duplicating work. |
| **Services tenant path** | `business_type == "services"`: processed lead **without** Candidate — no fake Application row. |
| **GET Applications + UI block** | Read-only candidate card; masked/new hidden. |
| **Lead “lost” + reason codes** | CRM `stage=lost` + `lost_reason_code` / note (partial **reject** signal — funnel-level, not full intake taxonomy). |
| **Lead-stage RODO (art. 14)** | `Tenant.settings.lead_rodo_v1`; `normalized.rodo`; ingest `apply_lead_rodo_on_ingest`; gates via `ensure_lead_rodo_allows_action` / `LEAD_RODO_REQUIRED`; manual + auto modes; idempotent Meta replay; merge-safe rodo block. Spec: [lead-intake-resolution-and-activity-continuity.md](lead-intake-resolution-and-activity-continuity.md) §8.0.1. |

---

## 2. Semantic / UX gaps & legacy

### 2.1 Intake channels ≠ single “Lead-first” model

| Channel | Lead row | Candidate | Application | Notes |
|---------|----------|-----------|-------------|--------|
| **Meta webhook** | Yes | Via `process_normalized_lead` | When vacancy or explicit pool | Canonical path. |
| **POST import / bulk / generic JSON** | Yes | Same pipeline | Same | Uses `process_normalized_lead`. |
| **Manual reroute** | Yes | `create_candidate_from_lead_conversion` | `ensure_recruitment_application_for_converted_lead` | Strong path. |
| **Public intake (`candidate`)** | **Usually no** until flow-specific side-effects | **Draft Candidate first** (`create_public_intake` / reuse) | **Not** created from Lead conversion (no `lead_id` on that journey) | **Divergence:** domain doc says “Lead always records entry”; **public candidate intake is Candidate-centric**, Lead only for **`client`** kind on submit (`public-intake:{candidate_id}`). |
| **Telegram bootstrap** | Unclear / side paths | Service-based dossier | Tied to Telegram intake, not Meta lead pipeline | Parallel intake rail — continuity with Lead-based flow is **not** unified in one screen. |

**Implication:** doctrine is **true for CRM Meta/import/reroute**; **public/Telegram** need explicit sub-flow documentation or future alignment (optional Lead stub, or accepted exception).

### 2.2 Vacancy: UI vs canonical routing

- **Gap (doctrine P1):** vacancy can appear in UI / payload / `lead.vacancy_id` while **routing/fit/process** still behave as if unresolved — recruiter-facing **contradiction**. No dedicated **“Confirm vacancy”** commit in product UI spec implemented as first-class action yet (doctrine only).

### 2.3 Intake resolution vs “Process only”

- Backend encodes **status** (`needs_routing`, `duplicate_review`, `processed`, `duplicated`, `failed`) and **stage** (funnel CRM).
- **Doctrine** wants a compact **resolution action strip** (qualify / reject / pool / request docs / confirm vacancy). Today much of that is **implicit** in Process + settings, not a dedicated intake resolution UX.

### 2.4 Reject / intake taxonomy

- **Partial:** `lost` + `lost_reason_code` on Lead **stage** (CRM loss), not the full **intake reject taxonomy** from [lead-intake-resolution-and-activity-continuity.md](lead-intake-resolution-and-activity-continuity.md) §5.
- **Gap:** structured **intake-level** reject (pre-candidate) + analytics hooks **not** fully implemented.

### 2.5 Activity continuity

- **Doctrine:** no duplicate first-call / SLA on Candidate after Lead work.
- **Reality (2026-07-02):** Slice 4 Guard 1 suppresses default UOS `Call candidate` when lead shows prior touch; marker `lead_to_candidate.first_contact_suppressed`. Tenant automation rules may still fire independently — audit per config if needed.

### 2.6 Lead UI (CRM)

- **Recruitment agency (2026-07-02):** `LeadDetailPage` + list inbox use **intake-first** layout — sticky header, `LeadIntakeDecisionRail`, qualification collapsed, CRM chrome under **More**. Services tenant retains legacy hero + `LeadIntakeResolutionPanel`.
- **Gap (services / legacy paths):** services tenant detail still mixes ingest mode, stage, qualification panels prominently.

### 2.8 Operational communication (not RODO)

- **Lead-stage RODO** covers **legal art. 14** only. Product emails such as “application received”, “moving forward”, “rejected” are **`lead_communication_v1`** (see `lead-intake-resolution-and-activity-continuity.md` §8.0.2) — separate from RODO gates; status portal / in-app / Telegram remain later.

### 2.7 Processed lead early return

- Re-hitting pipeline when lead already `processed`/`duplicated` returns **without** re-running `ensure` — correct for idempotency; **legacy** leads processed **before** Applications existed may **lack** rows until backfill or manual replay — acceptable per MVP.

---

## 3. Architectural debt (summary)

1. **Multi-channel intake semantics** (public/Telegram vs Lead-first CRM).  
2. **Vacancy confirmation** product gap vs routing.  
3. **Lead UI density** — operational chrome before intake resolution.  
4. **Intake reject taxonomy** vs CRM `lost` only.  
5. **Automation + activity dedup** across Lead→Candidate (continuity not proven globally).  
6. **Handoff readiness** — covered by separate contracts; not re-audited here.

---

## 4. Recommended implementation slices (ordered)

**Architectural program:** **Canonical Intake Resolution Layer** — boundary между intake world и recruitment operations (vacancy/routing, actions, qualification, reject, continuity, handoff readiness, UI demotion).

**Practical MVP name:** **Intake Resolution MVP** — шесть срезов ниже; **не** синоним «Lead UI cleanup» (cleanup — срез **6**, после семантики и guards). После стабилизации MVP: Activities spine, Rehire, Person, intelligence.

Align with [lead-intake-resolution-and-activity-continuity.md](lead-intake-resolution-and-activity-continuity.md) §8:

1. **Manual vacancy confirmation** (backend commit + UI) — убирает главное противоречие UI vs routing.  
2. **Intake resolution actions** — явные qualify / reject / pool / docs / duplicate / assign.  
3. **Reject reasons + intake taxonomy** (или мост из `lost_reason`) — foundation analytics & automation.  
4. **Qualification summary** — компактный блок данных для решения по intake (отдельно от финальной чистки layout).  
5. **Activity continuity guards** — audit automation; подавить дублирующие intents / fake work после convert.  
6. **Lead workspace cleanup** — intake decision first; demote candidate-style chrome.  
7. **Activities operational spine** — после стабилизации MVP.  
8. **Rehire spec** — later.  
9. **Person** — last.

**Parallel decision (architecture):** competing **Lead-first** vs **Candidate-first** public paths — [ADR-013-public-intake-strategy.md](../architecture/ADR-013-public-intake-strategy.md) (**Proposed**); **canonical ingestion governance:** не расширять канал без записанного contract (conversion boundary, duplicate, intake resolution, ownership) — см. ADR-013.

---

## 5. Guardrails — do not violate while refactoring

From doctrine + domain model:

- **Lead ≠ Candidate**; **Candidate ≠ Application**.  
- **Application only with** vacancy **or** explicit **pool** intent — not “every lead row”.  
- **duplicate_review** → **no** Application until resolved.  
- **assignment ≠ stage**; do not merge in UI.  
- **Semantics before automation before AI.**  
- **No fake work** — duplicate tasks/SLAs for same human intent.  
- **Do not** remove `candidate.vacancy_id` dual-write until Application reads are trusted everywhere.  
- **Do not** collapse or extend public intake without recording the chosen model — see [ADR-013-public-intake-strategy.md](../architecture/ADR-013-public-intake-strategy.md).  
- **New or materially changed ingestion source:** complete [ingestion-contract-template.md](ingestion-contract-template.md) before merge (contract-review checkpoint).

---

## 6. Answer: “Candidate-centric ATS again?”

**Partially.** Applications + duplicate + pool intent **pull** the model toward the right separation. **Residual ATS feel** comes from: **Lead UI** still surfacing candidate-like ops; **public intake** still **Candidate-first**; **vacancy** mismatch; **automation** possibly duplicating work. **Stabilising Intake Resolution MVP (slices 1–6)** above reduces regression into a single overloaded Candidate card.

---

*This audit is a point-in-time snapshot; re-run after major lead/UI or automation changes.*
