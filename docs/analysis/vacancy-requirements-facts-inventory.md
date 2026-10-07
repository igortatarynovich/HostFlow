# Vacancy Requirements / Facts inventory

**Status:** research draft  
**Date:** 2026-09-10  
**Trusted base:** `feat/eso4-formalize`  
**Parent:** [hrappka-live-session-audit-brief.md](hrappka-live-session-audit-brief.md)  
**Does not amend:** L0 · ADR-018 · RPM-1 authority · Vacancy Overlay Gate · Mapping Authority

> L3 inventory of **what already exists**. Requirements SoT: [`vacancy-recruitment-requirements-sot.md`](../specs/tasks/vacancy-recruitment-requirements-sot.md).  
> Does **not** wait on HR UI. Does **not** claim Full Spine PASS. Does **not** fold `lead_criteria_v1` into RPM.

---

## Target contract (from HRappka audit)

```text
Vacancy Recruitment Requirements
  × Canonical Candidate Facts
  → Fits / Not fits / Missing (+ explanation)
```

**Today this contract is not implemented as one product path.** Several stores already answer adjacent questions. The system result fit / missing / not_fit is **not** the Application verb **Подходит**. Relabeling «Создать кандидата» would not implement the contract.

---

## Verdict

HostFlow already has **document-requirement authority** (RPM / R5), **vacancy delta over a profile** (Overlay), **intake screening criteria** (`lead_criteria_v1`), **ADR-018 slots/graph**, and **canonical field codes** (field registry + Entity Profile). They are **not one SoT**.

**Подходит** is the human boundary into Candidates. It must stay that. The gap is a **system result** (fit / missing / not_fit + explanation) that chooses **one** next action — not three buttons, not a Create rename.

SoT brief: [`vacancy-recruitment-requirements-sot.md`](../specs/tasks/vacancy-recruitment-requirements-sot.md).

---

## 1. Vacancy Requirements — existing stores

Each row is a live answerer or leftover. **Question** is what the store actually answers today — not what the HRappka contract needs.

| # | Store | Question it answers today | Where | Operator surface | Feeds Fits? |
|---|-------|---------------------------|-------|------------------|-------------|
| A | **R5 pack + `tenant_delta`** | For this tenant/client/vacancy/profile/country, **must the candidate provide document type X?** | [`document-policy-platform-pack-v1.json`](../specs/platform/document-policy-platform-pack-v1.json) · `document_policy_merge.py` · [`requirement-policy-authority.md`](../specs/architecture/requirement-policy-authority.md) | RPM-2 overlay (`RequirementPolicyOverlayPage`) | **No** |
| B | **Vacancy Overlay + screening pack** | Vacancy-specific **delta** over Entity Profile / Screening Pack (presence / value / document / process). Contract: `entity_profile_vacancy_overlay.v1` | `entity_profile/vacancy_overlay_runtime.py` · [`entity-profile-vacancy-overlay-contract.md`](../specs/tasks/entity-profile-vacancy-overlay-contract.md) | **None** (explicitly not vacancy UI) | **No** (CL7 `evaluate` only) |
| C | **`lead_criteria_v1` in `Vacancy.extra`** | Does this **lead.normalized** match vacancy screening (years, docs list, geo, languages)? | `modules/leads/lead_criteria_eval.py` · `Vacancy.extra` JSON string | Vacancy **Candidate Requirements** tab (`CandidateRequirementsTab`) + tenant presets `/settings/team/vacancy-requirements-presets` | **Not the Application Fits verb.** Used by lead list/get display and `process_normalized_lead` routing when `lead_fit_evaluation_enabled_v1` is on |
| D | **ADR-018 requirement policy + slots** | Which **slots** apply for this profile/country/citizenship, and are they satisfied? | `requirement_rules/data/requirement_policy.recruitment.driver_ce.pl.v1.json` · `requirement_slots.v1.json` · slot evaluator | Candidate checklist / evidence, not vacancy create | **No** (handoff / stage readiness) |
| E | **Entity Profile + document pack codes** | Which field composition + named document pack this vacancy’s profile uses | `entity_profile/manifests/recruitment.py` · `Vacancy.candidate_profile_id` | Profile bind on vacancy, not a requirements editor | Indirect (pins profile; not Fits) |
| F | **`Vacancy.required_documents_template_id`** | Apply a document **template** when a candidate is assigned | `models/vacancy.py` | Vacancy field | **No** |
| G | **`Vacancy.description` (rich text)** | Free-text job copy (“C+E, Code 95…”) | column | Vacancy details | **No** — HRappka anti-pattern if this becomes the only requirements store |
| H | **Leftover / consume-only document lists** | Parallel “required types” still classified under RPM | Hub `DOCUMENT_PACK_DEFINITIONS`, `ref_packs`, `document_applicability_policy`, FE `candidateStageDocPolicy.ts`, seeded `candidate_profiles.config.document_configs` | Mixed | **No** |
| I | **A3 Requirements Workspace** | Recruiter checklist on **Candidate** (what to close), not vacancy policy | [`a3-requirements-workspace-backlog.md`](../specs/tasks/a3-requirements-workspace-backlog.md) · `/app/candidates/:id/requirements` leftover route | Candidate workspace | **No** |

RPM-1 freeze: **A is the write of “must provide type X?”**. Overlay (**B**) is a **different write-set**. Screening (**C**) is a **different question** and must not become a tenth RPM write.

Driver CE pack defaults (A): `driver_license`, `driver_qualification_card`, `tachograph_card`, `passport` (+ residency overrides). Slot catalog (D): `identity_document`, `legal_stay_confirmation`, `driver_license_with_code95`, `tachograph_card`, `work_authorization`, plus later slot additions (e.g. psych tests) in the cutover line — **not** the same list as A.

---

## 2. Canonical Facts — existing stores

Canonical **codes** exist. Canonical **runtime occupancy** is split.

### 2.1 Named canonical fields

| Qualified code | Registry | Declared storage | Occupied today? |
|----------------|----------|------------------|-----------------|
| `platform.identity.citizenship` | `field_registry/manifests/platform.py` | `personal_data.citizenship` | Often **not**. Intake mapping alias → lead `country`. Handoff still reads `personal.citizenship` **or** `extra.citizenship`. Live leak: value stays in form `field_answers` |
| `platform.identity.birth_date` | same | `personal_data.birth_date` | Column accessor on Candidate; more often present than citizenship |
| `platform.identity.address` | same | `personal_data.address` | Profile marks card_save / transition required; occupancy mixed |
| `recruitment.candidate.experience.years_ce` | `field_registry/manifests/recruitment.py` | `extra.experience.years_ce` | Aliases `years_ce`, `experience_eu_years`. Overlay / screening / lead criteria use **flat** `experience_eu_years` on `lead.normalized` |
| `recruitment.candidate.personal.in_poland` | same | `personal_data.in_poland` | Lead criteria also reads `normalized.in_poland` |
| `recruitment.candidate.contacts.*` / names | same | columns | Usually present (Fits/process needs a person) |
| `recruitment.candidate.experience.trailer_types[]` / `route_types[]` | same | `extra.experience.*` | Profile optional; not a Fits input |

Entity Profile `recruitment.candidate.driver_ce` **includes** `platform.identity.citizenship` as intake optional / card_save required — so the product already *named* citizenship as a fact. Completeness is occupancy + single read path, not inventing the field.

### 2.2 Runtime bags (not the registry)

| Bag | Typical keys | Consumers | Risk |
|-----|--------------|-----------|------|
| `lead.normalized` | flat: `experience_eu_years`, `country`, `nationality`, `geo_country`, `documents[]`, `languages[]`, `in_poland` | `evaluate_lead_criteria_v1` | **Evaluation input is this bag**, not qualified canonical codes |
| Form `field_answers` | source question ids | Mapping Authority → should become facts; Intake Readiness forbids hand-patching | Citizenship leak named in HRappka brief |
| `Candidate.extra` (JSON string) | `citizenship`, `experience_eu_years`, nested `experience.*` | readiness_bridge, handoff | Duplicate of personal_data |
| `Candidate.personal_data` | citizenship, birth_date, address, in_poland | field registry storage | Incomplete occupancy |
| `ready_for_employment.v1` `person.identity_facts` | `citizenship`, names, `nationality` | ESO-1…5 | Assembled at Transfer from leftover bags; not a person SoT |
| Mapping Authority applied evidence | source → qualified code | Shared Intake | Evaluators must not read provider payload |

`field_registry/intake_mapping.py` maps `platform.identity.citizenship` → **`country`**. That is a completeness defect: citizenship is not country.

---

## 3. What Fits actually does

`recruitment_fits_application` → existing `process` (create/find Candidate) → `record_fits_decision_on_lead`.

It does **not** call:

- `evaluate_lead_criteria_v1`
- RPM `r5_required_set`
- Overlay `merge` / CL7 `evaluate`
- ADR-018 slot evaluator

Lead-side “fit” (`fit` / `no_fit` / `needs_info`) is a **routing/display** result on `lead.normalized` vs `Vacancy.extra.lead_criteria_v1`, gated by `lead_fit_evaluation_enabled_v1`. It is **not** the Application **Подходит** verb after ADR-042.

HRappka anti-pattern already present in UI: vacancy **Candidate Requirements** tab is a **Profiling / matching parameters** editor (`min_experience_eu_years`, two document multi-selects, geo allow/block, preferred docs/languages, enable-fit checkbox). That is store **C**, not Requirements SoT.

---

## 4. Parallelism the next SoT must not add a tenth of

Do **not** create:

- another vacancy “matching parameters” table  
- a second document pack catalog  
- vacancy UI that writes RPM `tenant_delta` as if it were Overlay  
- Fits that reads Meta questions / `field_answers`  

Reuse:

| Keep | As |
|------|----|
| RPM-1 (A) | Document type X required? — already SoT |
| Overlay (B) | Vacancy **delta** over profile/pack — contract exists, **no operator write** yet |
| Field registry + Profile fields | Canonical fact **codes** |
| Mapping Authority | Source answer → canonical fact |
| ADR-018 slots | Satisfaction / alternatives for recruitment missing — consume requirements, do not own vacancy policy |
| Application **Подходит** | Human boundary into Candidate (ADR-042). Not the evaluator. Must not auto-Transfer |

**SoT (sealed):** [`vacancy-recruitment-requirements-sot.md`](../specs/tasks/vacancy-recruitment-requirements-sot.md) — operator writes Overlay + profile; evaluator reads canonical facts; store **C** leftover.

---

## 5. Completeness gaps (facts) — seed for the next brief

Priority leaks (do not patch in this inventory):

1. **Citizenship** — registry + profile field exist; intake alias `country`; extra vs personal_data; ESO pathway needs the fact.  
2. **Years CE** — three keys (`years_ce`, `experience_eu_years`, qualified code) plus Overlay ad-hoc `years_ce_min` mapped into delta.  
3. **Geo / in_poland / nationality** — live on `lead.normalized` and lead_criteria; not first-class `platform.identity` / recruitment fields for Fits.  
4. **Documents as facts vs evidence** — lead_criteria `requires_documents` on normalized lists vs Hub instances vs slots. ADR-016: documents are evidence, not a second fact bag.  
5. **Подходит (verb) vs lead_criteria fit status vs system result** — three different things; do not collapse them into a button rename.

---

## 6. Explicit non-goals of this file

- Implementing Requirements SoT or a vacancy create wizard  
- Implementing canonical-facts completeness runtime  
- HR operator host / Full Spine operator PASS  
- Folding rates, contract subtype, or permits into vacancy create  
- A tenth write of “must provide type X?”  
- Scheduling this as sequential-queue Active Product (unlock ≠ schedule)

---

## 7. Next

1. **Vacancy Recruitment Requirements SoT** — sealed: [`vacancy-recruitment-requirements-sot.md`](../specs/tasks/vacancy-recruitment-requirements-sot.md). Runtime not started.  
2. **Canonical Facts Completeness** — sealed: [`canonical-facts-completeness.md`](../specs/tasks/canonical-facts-completeness.md) (consumers-first occupancy matrix). Next: minimal runtime occupancy cutover, then Vacancy Requirements evaluator.  
3. Configuration runtime dependency audit remains **P1** (HRappka brief §5.3).
