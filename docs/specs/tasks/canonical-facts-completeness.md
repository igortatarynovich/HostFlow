# Canonical Facts Completeness

**Status:** **Accepted** (L2 contract). Runtime occupancy cutover **not this slice**.  
**Phase class:** product  
**Module owner:** **Platform** (field registry / Mapping Authority write path) · **Recruitment** and **Employment** consume — they do not fork a second fact bag  
**Date:** 2026-09-11  
**Trusted base:** `feat/eso4-formalize`  
**Parents:** [Vacancy Recruitment Requirements SoT](vacancy-recruitment-requirements-sot.md) · [Mapping Authority](mapping-authority.md) · [Field Registry](../platform/field-registry-card-configuration.md) · [ADR-016](../architecture/ADR-016-requirement-evidence-document-separation.md) · [RPM-1](../architecture/requirement-policy-authority.md) · [Early employability](../architecture/early-employability.md) · [Ready for employment](../architecture/ready-for-employment-contract.md) · [ADR-042](../architecture/ADR-042-operator-host-boundary.md)  
**Research (L3, not SoT):** [Inventory](../../analysis/vacancy-requirements-facts-inventory.md) · [HRappka audit](../../analysis/hrappka-live-session-audit-brief.md)

**L0 checklist:** No new P-rule; no Passport/Manifest **shape** change; no Architecture RFC. Applies **INV-01** (one SoT per fact), **INV-16**, **P-02** (Recruitment vs Employment ownership of *decisions*, not duplicate fact stores). Does not open Vacancy Requirements evaluator runtime. Does not wait on HR UI. Does not claim Full Spine PASS. Unlock ≠ sequential-queue Active Product.

> Any fact used by Recruitment or Employment for a **deterministic decision** has **one canonical representation** and **one read path**, independent of source.  
> Inventory starts from **consumers**, not form fields.  
> Citizenship is the control example — not the whole program.

---

## Operator question (one)

For a fact that RSO, ESO, requirement rules, Overlay, or the future Vacancy Requirements evaluator needs: **where is the single canonical value**, who may write it, and which path must every consumer use — so Meta / Form / CSV / manual never become a parallel SoT?

No second question. Not vacancy Overlay write. Not RPM “must provide type X?”. Not Mapping operator UX. Not HR host.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
Deterministic consumers (`early_employability`, accept policy, readiness/slots, handoff package assembly, future Vacancy Requirements evaluator) still resolve the same business fact through **fallback chains** across `field_answers`, `lead.normalized`, `Candidate.extra`, `personal_data`, package `identity_facts`, and document lists. Building the Vacancy Requirements evaluator on that layer would mint another temporary SoT that later must be cut out.

**Completion proof (named consumer):**  
Occupancy matrix below accepted; every **decision-critical** row is REUSE or ADAPT with a named single read path. A minimal runtime cutover then makes at least the Driver CE decision set (citizenship, years CE, and evidence-backed qualification slots) occupy that path end-to-end:  
`source value → Mapping Authority → canonical field → persistence → consumer`.  
Vacancy Requirements evaluator is **forbidden** to start until that cutover holds for the facts it will evaluate. Citizenship alone green while years_ce / geo still read `lead.normalized` is a **false close**.

**False close (reject):** patching only citizenship; minting `canonical_facts_v2` / a new bag; copying the same fact into Recruitment and Employment stores “for convenience”; treating Hub documents as a parallel fact store; evaluator on `lead.normalized` / `field_answers` / Meta payload; growing `lead_criteria_v1` as fact SoT; auto-Transfer from fit; waiting on HR UI; claiming Full Spine PASS.

---

## Hard locks (four)

1. **`field_answers`, `lead.normalized`, Meta payload, CSV columns** = transport / source representation. Never SoT for a deterministic decision.  
2. **Do not create `canonical_facts_v2`** (or any new bag) if existing Person / Candidate / Application + field-registry storage can own the fact. Prefer REUSE / ADAPT.  
3. **Do not copy one fact into both Recruitment and Employment** for consumer convenience. Employment reads the Ready-for-employment package (projection) or the same Person/Candidate canonical path — not a second write.  
4. **Documents / evidence confirm a fact; they are not a parallel fact store** (ADR-016). Slot satisfaction ≠ inventing `has_code95: true` as a free-floating fact outside evidence + evaluator.

---

## Method: consumers first

Trace for each decision-critical fact:

```text
source value
  → Mapping Authority (qualified_field_code)
  → canonical field (field registry)
  → persistence (declared storage.path)
  → consumer (one read API / one payload key)
```

Do **not** start from form question inventory. Start from live decision consumers.

### Decision consumers in scope (Driver CE spine)

| Consumer | Decision | Facts / evidence it already touches |
|----------|----------|-------------------------------------|
| **ESO-2** `early_employability.v1` | Pathway / employable / blocked / insufficient_facts | `citizenship` (+ `nationality` fallback), package `identity_facts`, work-auth **evidence** |
| **ESO-1** accept policy | Auto-accept vs review | Package-authoritative codes include `citizenship` — must not re-ask |
| **ESO-3 / ESO-4** | Missing / formalize gates | `person.identity_facts` occupancy |
| **RSO package / handoff assembly** | Emit `ready_for_employment.v1` | Citizenship from `personal_data` **or** `extra` **or** `country_code` (leak) |
| **RPM / ADR-018 / slots / readiness_bridge** | Slot applicability + field_required | `platform.identity.citizenship`, `years_ce` / `experience_eu_years`, address, birth_date |
| **Vacancy Overlay / CL7** | Vacancy delta predicates | `recruitment.candidate.experience.years_ce` (ad-hoc `years_ce_min` → delta) |
| **Vacancy Requirements evaluator** (future) | fit / missing / not_fit | Overlay merge × **canonical facts only** — blocked until this cutover |
| **`lead_criteria_v1`** (leftover) | Routing / display “fit” on Application list | Reads **`lead.normalized`** — not a blessed consumer; RETIRE as SoT |

Out of scope for this matrix: payroll rates, ZUS post-hire journeys, HR inbox dump fields, calendar.

---

## Occupancy matrix (decision-critical)

| Canonical key | Owner | Persisted where (declared) | Writers (today) | Consumers (today) | Source mappings (today) | Current leak | Action |
|---------------|-------|----------------------------|-----------------|-------------------|-------------------------|--------------|--------|
| `platform.identity.citizenship` | Platform identity | `Candidate.personal_data.citizenship` | Mapping → conversion; manual card; often **none** | ESO-2 (multi-fallback); ESO-1 package; handoff assembly; slots/readiness; formalize identity | Mapping alias **`country`** in `intake_mapping.py`; also legacy `citizenship` on normalized | Value stays in `field_answers` / `normalized.country`; handoff also reads `extra.citizenship` / `country_code`; ESO accepts `nationality` as twin | **ADAPT** — one write to `personal_data.citizenship`; one read helper; retire `country` as citizenship alias; stop nationality-as-citizenship without explicit map |
| `platform.identity.birth_date` | Platform identity | `personal_data.birth_date` | Mapping / card | Field_required / layout; package identity | → `birth_date` | Milder than citizenship | **REUSE** — enforce occupancy on intake when mapped |
| `platform.identity.address` | Platform identity | `personal_data.address` | Mapping / card | Readiness / transition levels | → `address` | Mixed occupancy | **REUSE** |
| `recruitment.candidate.experience.years_ce` | Recruitment | `extra.experience.years_ce` (registry) | Mapping → often flat `experience_eu_years` on lead + candidate extra root | Overlay (`years_ce_min`); readiness_bridge (three keys); lead_criteria leftover | → `experience_eu_years` | Triple key: qualified / `years_ce` / `experience_eu_years` | **ADAPT** — single persistence path; consumers read qualified only; map Overlay predicate to that code |
| `recruitment.candidate.personal.in_poland` | Recruitment | `personal_data.in_poland` | Mapping | lead_criteria leftover; profile | → `in_poland` | Decision use still on `lead.normalized` | **ADAPT** if Overlay/Vacancy Requirements need it; else leave as profile field, **RETIRE** lead_criteria read |
| `recruitment.candidate.personal.driving_license_category` | Recruitment | conversion maps to `extra.driving_license_category`; **not** in `recruitment_candidate_fields()` list | Intake normalizer / conversion | Mostly leftover / normalized | → `driving_license_category` | Code exists in intake bridge without full registry field row | **ADAPT** — register field + storage, or **RETIRE** if CE category is evidence-only via Hub `driver_license` |
| Geo / location country (`geo_country`, `location_country`, …) | Undecided | No single `platform.identity.*` / recruitment field for “current country for fit” | Lead normalizer into `lead.normalized` | lead_criteria only | Multiple raw keys | Used as if citizenship/geo policy | **ADAPT** or **RETIRE** — pick one canonical “current location country” if Vacancy Requirements needs geo; do not keep three normalized geo keys as SoT |
| `nationality` (as distinct from citizenship) | Undecided | Often confused with citizenship in ESO helpers | Package / normalized | ESO-2 fallback chain | Mixed | Twin of citizenship without contract | **RETIRE** as citizenship alias **or** **ADAPT** as separate registry field with explicit semantics — pick one in cutover |
| Driver license / Code 95 / tachograph / legal stay / work auth | Document Hub + RPM slots | Hub document instances + evidence / slots | Upload / approve | Slots, transfer readiness, ESO evidence checks | N/A as fact codes | lead_criteria `requires_documents` on `normalized.documents[]` treats codes as facts | **REUSE** slots/Hub as evidence; **RETIRE** `normalized.documents[]` as decision SoT |
| Names / phone / email | Recruitment | Candidate columns | Process / Mapping | Fits person create; package | Qualified → flat | Usually occupied | **REUSE** |

**Control reading:** citizenship is **not** a one-off mapping bug. The same pattern (transport key ≠ registry path ≠ consumer fallback chain) appears on **years_ce**, **driving_license_category**, **geo**, and **documents-as-fact**. That is the symptom this brief names.

---

## Decision

### 1. One representation, one read path

For every **ADAPT** / **REUSE** row that a deterministic consumer needs:

- Canonical key = field-registry `qualified_code` (or Hub evidence + slot evaluator for document requirements).  
- Persistence = registry `storage.path` only.  
- One module-facing read (thin helper / projection into readiness payload / package) — no N-key OR chains in business logic.  
- Mapping Authority writes that path; consumers never read `field_answers` / Meta / CSV.

### 2. Package is a projection, not a second SoT

`ready_for_employment.v1` `person.identity_facts` **copies** canonical occupancy at Transfer for Employment gate 2. It does not become the Person SoT. Employment must not invent a parallel Employment-owned citizenship column for the same person while Candidate/Person already holds it.

### 3. Leftover SoTs classified

| Leftover | Role after this contract |
|----------|--------------------------|
| `lead.normalized` as evaluation input | Transport / display only; **RETIRE** as SoT for fit / pathway / Overlay |
| `lead_criteria_v1` / Candidate Requirements tab | Leftover Profiling layer ([Requirements SoT](vacancy-recruitment-requirements-sot.md)); fold or retire in that feat |
| `Candidate.extra` root aliases (`citizenship`, `experience_eu_years`) | Strangler; cut over to registry paths |
| ESO `nationality` fallback for citizenship | Document in cutover: RETIRE or separate field |
| `intake_mapping` `citizenship → country` | Defect; ADAPT |

### 4. Sequencing (locked)

```text
1. This contract + occupancy matrix (here)
2. Minimal runtime occupancy cutover (decision-critical Driver CE set)
3. Vacancy Requirements evaluator (Requirements SoT runtime)
4. Only then: Application shows requirements × facts → fit / missing / not_fit → one action
```

Do **not** invert steps 2 and 3.

---

## Architecture review (L0 — ten questions)

| # | Answer |
|---|--------|
| 1 | **Owner of fact write:** Mapping Authority + field-registry storage on Person/Candidate. Recruitment/Employment **consume**. Document Hub owns evidence instances. |
| 2 | Not a new Catalog capability. Closes occupancy of existing identity / recruitment fields. |
| 3 | No new adapter. Shared Intake remains Mapping runtime caller. |
| 4 | No `canonical_facts_v2`. No second pack. Overlay/RPM unchanged as write authorities. |
| 5 | No Settings JSON page as fact SoT. |
| 6 | SoT for the operator question = this file + matrix. Inventory is L3. |
| 7 | No new event family in this docs slice. |
| 8 | **Requires:** Mapping Authority contract/resolution; field registry; RSO package shape. **Blocks:** Vacancy Requirements evaluator runtime. |
| 9 | No new licence. |
| 10 | Additive public contract. Does not rewrite L0. |

---

## Non-goals

- Implementing occupancy cutover in this docs PR  
- Vacancy Requirements evaluator / Overlay vacancy UI runtime  
- Full field-registry census of non-decision fields  
- HR operator host / Full Spine operator PASS  
- Retiring every lead_criteria UI control in this slice  
- Minting Employment-local fact tables  

---

## Next

1. **This contract** — sealed.  
2. **Runtime occupancy cutover** (feat): Driver CE decision-critical ADAPT rows — especially citizenship + years_ce + evidence-vs-normalized.documents; one read path per consumer in the table.  
3. **Vacancy Requirements evaluator** — only after step 2 for the facts that evaluator will read.  
4. Broader geo / license-category ADAPT decisions resolved in the cutover PR description against this matrix (no silent new keys).
