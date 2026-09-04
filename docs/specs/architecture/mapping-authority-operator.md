# Mapping Authority Operator Surface

**Status:** **Accepted** (L2 UX contract — Mapping Operator Gate **not PASS**; feat open)  
**Date:** 2026-09-04  
**Trusted base:** `integration/release-product-a-b` @ `4073f3a7` ([#350](https://github.com/igortatarynovich/HostFlow/pull/350))  
**Related:** [`mapping-authority-contract.md`](mapping-authority-contract.md) (`mapping_authority.v1`) · [`mapping-authority-resolution.md`](mapping-authority-resolution.md) (`resolve_mapping_authority`) · [`../tasks/mapping-authority.md`](../tasks/mapping-authority.md) · [`ADR-021`](ADR-021-unified-intake-resolution-model.md)

**L0 checklist:** No new P-rule; no Passport/Manifest **shape** change; no Architecture RFC. Applies **P-02** (one owner of this write), **INV-01** (one SoT for the operator question), **INV-16** (contract before a second editor). Does not rewrite L0. Does not mint a fourth mapping store or a Field Registry fork.

> This file is the **SoT** for MA-3 product surface: one editor, many entry points, human-language health. Schema remains SoT; sample is not. For Meta, the primary operator setup is Form → test/latest lead → Mapping.  
> UX contract **Accepted** on [#350](https://github.com/igortatarynovich/HostFlow/pull/350). Feat `feat/mapping-authority-ma3-operator-gate` is **open**. Mapping Operator Gate stays **not PASS** until the close path below is proven. A page that exists is not that proof. MA-4 / External Intake / Forms Publish / Hiring are not this feat.  
> Binding / option map / evaluator isolation remain [MA-1](mapping-authority-contract.md). One resolver remains [MA-2](mapping-authority-resolution.md).

---

## Process boundary (universal)

Mapping is configured from source schema before submissions may exist. At submission runtime, source answers are resolved through the saved Mapping contract into canonical facts before any business evaluation.

Schema participates in **configuration**. It must not become an extra input to runtime transformation. Runtime reads **source answers + the saved Mapping contract**.

```text
Configuration time:
  source schema → mapping contract

Submission time:
  source answers + saved mapping contract
    → canonical HostFlow facts (qualified_code + canonical option)
    → business logic
    → user object
```

| Source | Path |
|--------|------|
| Meta | form / question / option → Intake Source Profile → Mapping Authority → `qualified_code` + canonical option → Lead / Application facts → Requirement / qualification / routing → Recruiter workspace |
| HostFlow Form | Form schema → Submission → Mapping Authority → canonical facts → Decision / Outcome → Candidate / Inquiry / other business object |

This HostFlow Form path is the **target consumption boundary**. MA-3 does not implement Forms Publish or [ADR-022](ADR-022-intake-form-purpose-and-submission-policy-model.md) submission lifecycle.

Forbidden order: Meta label (`Более 8 месяцев`) → Recruitment evaluator. Required order: Mapping → `document_validity = GT_8_MONTHS` → evaluator.

This rule is the same for every intake source. A later source does not get a private mapping path. A later CSV import that uses the same Shared Intake / ingestion boundary uses this Mapping path. It must not mint a second “Import Mapping runtime.”

---

## Who asks Mapping vs who consumes facts

**Direct runtime caller (one boundary):** Shared Intake / ingestion runtime. It is the only layer allowed to ask Mapping Authority “how does this source answer become a canonical field/value?”

Business modules never call Mapping Authority directly.

**Indirect consumers** (canonical facts only — they must not know Meta vs Form vs CSV vs API):

- Recruitment
- Hiring / qualification
- Requirement Policy
- External Intake / Forms Publish
- routing / Decision Layer where the decision depends on canonical facts
- later intake consumers

Recruitment sees `driving_license_category = CE`, `code95 = true`, `eu_experience_months = 24` — not questionnaire answers.

**Not this write** (do not absorb into the MA-3 editor):

| Adjacent | Why out |
|----------|---------|
| Sales `convert_mapping_v1` | SalesInquiry → ClientAccount — different pair |
| Documents OCR mapping | later; different pair |
| CL6 Flight map | already gated; consume, do not fork |
| Telegram intake bootstrap | leftover with owner + expiry |
| `lead_criteria_v1` | not a Mapping write |

---

## UX object

The operator object is **the source**, not a table of mapping rules and not “Mapping Authority configuration”.

The operator thinks: “Here is my Meta form. What will HostFlow do with its questions?”

**Schema ≠ sample stays [MA-1](mapping-authority-contract.md).** Schema is the structure SoT. Sample is never the structure SoT. Mapping remains configurable with no lead yet (no-sample is not a dead end).

**Meta operator setup (primary path):** Form → test or latest lead → Mapping. Schema still lists every question so an incomplete sample cannot hide a field.

```text
Connect Meta → select Page / Form
  → load form schema (Graph questions)
  → request or use a test / latest lead
  → show schema + sample values in one workspace
  → map fields / options → Ready
  → canonical projection
  → another test / real lead → applied evidence
```

Zapier’s Facebook Lead Ads setup is the UX reference for that Meta path ([sample lead via Facebook testing tool](https://help.zapier.com/hc/en-us/articles/8496061345805-Use-the-Facebook-Lead-Ads-testing-tool-to-create-sample-leads)): Page + Form → test record (`fields` + values) → map. Zapier can show generic placeholders when a new form has no submissions; it recommends a sample lead for real mapping. HostFlow must not copy Zapier’s “test record is the schema.” HostFlow uses **schema + sample together**: eight questions on the form and seven filled in the sample still show the eighth row.

Flow:

1. Pick a source (Meta form, HostFlow Form, import source, …).
2. For **Meta**, HostFlow asks for a test or latest application so the operator sees real answers (`Получим пример заявки, чтобы настроить поля`). Schema still loads even if that example is missing.
3. The workspace shows **source question · example answer · HostFlow field**. Sample sits beside the row (`Последний пример: «Более 8 месяцев»`). Canonical option codes (`GT_8_MONTHS`) are not operator vocabulary.
4. Each question has a simple destination: HostFlow field + status (`Mapped` / `Ignored` / `Unmapped`).
5. Choice destinations open **option map in-row**. Type is inherited from Field Registry; the operator cannot change it here.

**Ignored** is always an explicit operator decision. Absence of a destination is `Unmapped`, never implicit Ignore. A new provider question must not appear as unused.

A choice binding is not Ready while any currently known source option lacks either a canonical option binding or an explicit ignore decision. An unknown option observed at runtime does not silently pass through as raw text.

The operator must not see `qualified_code`, JSON, or storage paths as the working vocabulary.

---

## One editor, many entry points

**Invariant:** one editing surface; many entry points. Meta Connect, a form, diagnostics, or “1 field is not configured” may **open** Mapping. Editing always lands in the **same** workspace.

Existing writable surfaces must **cease to be editors**. They may only deep-link/redirect into this workspace or expose narrowly scoped read-only diagnostics where separately owned. A leftover “view” that still edits is a competing product surface, not a fold.

A second writable mapping screen is a false close — even if it writes the same store.

---

## Two scales, one human summary

Architecture keeps both [MA-1](mapping-authority-contract.md) scales:

| Scale | Values |
|-------|--------|
| Binding | `Mapped` \| `Ignored` \| `Unmapped` |
| Contract health | `Valid` \| `Needs review` \| `Invalid` |

The main screen speaks human language, not two technical columns:

- “All set — 8 of 8 questions”
- “Needs a check — 1 new question appeared on the form”
- Inside the row: “EU experience — Unmapped”
- On option drift: “The form changed. Check 2 answers before automatic evaluation continues.”

Generic “Contract Health: Needs review” as the only signal is leftover C-5 vocabulary, not this contract.

---

## Ready (projection, not a third status)

**Ready** is a projection, not a third status vocabulary. A source is Ready when:

- current schema is known;
- contract health is `Valid`;
- every current source field is explicitly `Mapped` or `Ignored`;
- every choice binding has complete option decisions for the known schema;
- every mapped destination still exists in Field Registry;
- no blocking drift remains unreviewed.

Human copy such as “All set — 8 of 8 questions” is this projection. The UI must not invent a fourth health enum named `ready`.

---

## Drift taxonomy (minimum)

Human-language copy must name a specific class. Minimum set:

- source field added;
- source field removed;
- source option added;
- source option removed;
- source field type changed;
- existing binding destination no longer valid.

Removed source fields remain visible as historical bindings until operator review; they do not disappear silently from the saved contract.

A feat that only surfaces “new field” has not shipped this taxonomy.

---

## Product criterion (Mapping Operator Gate)

A person who was never trained on Mapping connects a Meta source, sees its questions **with example answers**, understands where each answer will land, brings the mapping to **ready**, and can explain what the next submission will write — **without** switching between several Settings / admin screens.

This untrained-operator criterion is the **acceptance statement** of MA-3. An editor that exists is not enough.

**Close path (must be proven on a real Meta source):**

```text
Connect Meta → select Page/Form → load form schema
  → request/use test or latest lead → show schema + sample values
  → map fields/options → Ready → canonical projection
  → another test/real lead → applied evidence
```

plus retirement of write access on leftover mapping surfaces.

Until that path is proven, Mapping Operator Gate is **not PASS** — even if parts of the UI already work.

The shorter line `source → schema → bindings → Ready → projection → submission → applied evidence` is still the architecture. For Meta, “schema” in that line is not “map with no example.” The operator’s primary path includes a test or latest lead as the way to see answers. Schema still guarantees completeness and drift.

“Next submission will write …” is a **projection** produced from the saved Mapping contract + Field Registry metadata. It must use the same resolver/transform contract as ingestion and must not become a separate preview evaluator.

The three questions the surface must answer without a manual:

1. What arrived?
2. Where will HostFlow put it?
3. Is it working now?

If answering those requires Diagnostics + Meta Settings + Marketing Mapping, MA-3 has failed even if the backend is correct.

---

## Remaining product gap (this feat)

UX contract is **Accepted**. Mapping Operator Gate is **not PASS**. Do not fit this file to the current UI. Do not close MA-3 because a mapping page exists.

This feat must close:

```text
Connect Meta → select Page/Form → load form schema
  → request/use test or latest lead → show schema + sample values
  → map fields/options → Ready → canonical projection
  → another test/real lead → applied evidence
```

and leftover mapping surfaces must cease to be writers.

Until then, at least these remain open:

- projection must not use a raw-text fallback;
- incomplete option map must not produce Ready;
- Meta Settings and other leftover surfaces must cease to be writers;
- schema-first mapping must still work without a sample (architecture / no-sample semantics); that is not the primary Meta operator setup;
- preview must use the same resolution/transform contract as ingestion, not a private evaluator.

Schema + no sample + no binding → “Needs a check — 1 question to set” is required no-sample semantics. It is not Operator Gate PASS. For Meta, Operator Gate PASS uses the test/latest-lead close path above.

### Meta test-lead capability (capability check — not Gate PASS)

HostFlow **cannot** mint a Facebook test lead inside the product (no Graph POST to the Lead Ads testing tool). Zapier cannot either: the operator fills the form in [Facebook’s testing tool](https://developers.facebook.com/tools/lead-ads-testing/), then the integration **pulls** the record.

HostFlow **can** already:

| Need | What exists |
|-------|-------------|
| Form schema | Graph `GET /{form_id}?fields=questions` (`fetch_leadgen_form`) |
| Latest Graph lead `field_data` | `GET /{form_id}/leads?fields=id,created_time,field_data,ad_id,form_id` (`fetch_leadgen_form_latest_lead`) |
| Specific lead `field_data` | Graph `GET /{leadgen_id}?fields=field_data,ad_id,form_id` (webhook enrichment + preview) |
| Wait for the next webhook lead | Mapping workspace capture-next (C-4 leftover still exists) |
| Stored HostFlow sample | latest Lead / `last_sample_lead_id` |

`field_data` is Meta’s `[{ "name": "<key>", "values": ["…"] }]`. Graph `questions` carry `key` / `label` (and options when present). Preview already **merges** questions + latest `field_data`, so a missing sample value does not delete a schema question.

Mapping workspace uses this as evidence: Get latest example pulls Graph `field_data` or the latest HostFlow lead; Wait for next application arms capture-next. HostFlow still cannot mint a Facebook test lead. C-4 Test lead remains a leftover diagnostic, not a second mapping authority. This is not Operator Gate PASS.

MA-4 vocabulary cutover, External Intake, Forms Publish, and Hiring E2E are **not** this feat.

---

## Measurement (2026-09-04 — current surfaces)

Measured on `3a4297b0` after Mapping Resolution Gate PASS. This is the gap the feat must close; it is not today’s product.

### 1. Where does the operator enter Mapping?

| Entry | Path today | Lands in |
|-------|------------|----------|
| Marketing Sources row | `/app/marketing/sources` → Mapping | C-5 `MarketingSourceMappingPage` |
| Test lead | `/app/marketing/sources/:id/test-lead` | link to C-5 |
| Diagnostics | `/app/marketing/diagnostics` → Open mapping | C-5 (read-only health + fingerprint drift on the diagnostics page) |
| Meta Settings | `/app/settings/integrations/meta` tab Field mapping | **second editor** (`MetaLeadsAdminPage`) |
| Intake form admin | `/app/settings/intake-forms/:id` | **third editor** (`IntakeFormMappingEditor`) |
| Connect Source | `/app/marketing/campaigns/:id/connect` | **campaign**, not Mapping |

Connect Source does not open Mapping after bind. Meta Settings and Intake form admin write overlapping rules from different screens. Entries do **not** yet share one workspace.

### 2. When does Mapping first appear?

Ideal: as soon as the source schema exists, before the first lead.

Today: Connect returns to the campaign. C-5 rows are `mapping_rules ∪ sample.fields`. Graph/form questions are not the C-5 table SoT. Mapping is easy to miss until a sample or a Settings tab.

### 3. What happens without a sample?

MA-1: missing sample is “no sample yet”; it must not block binding.

Today:

- C-5 with no rules and no sample → empty table (dead end for schema-first mapping).
- Meta admin can show Graph questions with italic “no sample”.
- Intake form editor can add rows by hand, but structure comes from pasted JSON / a fictional `DEFAULT_SAMPLE`, not the form schema.

### 4. How is drift shown?

Required: the minimum drift taxonomy (field/option added or removed, type changed, destination no longer valid) — not a generic error.

Today: `compute_mapping_health` is `ready` / `needs_review` / `broken` from connection status, rule count, and last error. Diagnostics drift is a fingerprint boolean. C-5 “Needs review” still mixes “new field or sample changed.” Option-map drift is not a first-class sentence.

### 5. How does the operator see impact?

Required: after save, a projection through the same resolver as ingestion (“the next application will write Code 95 = Yes”), not a second evaluator. After a submission, applied result / evidence.

Today: C-5 save toast + routing preview (destination / queue / duplicate — not canonical facts). Intake editor has preview / test-ingest over operator-pasted JSON. Applied-rule evidence lives in diagnostics (`mapping_applied_v1`), not on the editor.

### UX sources in MA-3 vs consume-only

**In the editor:** source types represented by an Intake Source Profile. MA-3 target coverage includes Meta Lead Form, HostFlow Form / public intake and import sources **where that profile binding exists**.

MA-3 does not take on missing profile bootstrap for import or forms. That is a later slice if the binding is absent.

**Consume facts only (no Mapping screen of their own):** Recruitment, Hiring, Requirement Policy, External Intake publish, Decision Layer.

**Out of the editor:** Sales convert, OCR, CL6, Telegram leftover, `lead_criteria_v1`.

---

## Screen contract (feat must ship)

Minimum workspace:

1. **Source identity** — form name, provider, schema identity/version or deterministic schema fingerprint, and sample evidence in the same workspace (`N questions · example received …`). Not “mapping rules admin”. Not a C-4 transplant.
2. **Human summary** — Ready projection, or “N questions to set”, or a specific drift sentence from the taxonomy above.
3. **Question rows** — source question · example answer (when a test/latest lead exists) · HostFlow field (human label) · binding. Sample is never schema SoT. 8 schema questions + 7 filled sample values remain 8 rows. Removed fields stay as historical rows until review.
4. **In-row option map** when destination is choice-typed. Incomplete option decisions keep the choice binding not Ready.
5. **Projection** after save (same resolver/transform contract as ingestion, not a second evaluator); **applied evidence** after a real submission (RS-3 stays the program proof).
6. **No-sample state** — full schema still listed; copy is “no example yet”. Actions in this workspace: Get latest example / Wait for next application. For Meta this is a pause to get a test/latest lead, not a dead end and not a licence to treat placeholders as schema. C-4 Test lead is leftover diagnostic, not a second mapping authority.
7. Entry CTAs from Connect, form, diagnostics, and “1 field is not configured” — all `open` the same editor.

C-5, Meta Field mapping, and Intake form mapping must **cease to be editors**. They may only deep-link/redirect into this workspace or expose narrowly scoped read-only diagnostics where separately owned.

Out: themes, analytics, bulk rule import, Zapier-style conditions, a type picker, a fourth store.

---

## Architecture review (L0 — ten questions)

| # | Answer |
|---|--------|
| 1 | **Owner:** Mapping Authority. Field Registry owns destination identity and type. Acquisition C-5 / Meta admin / Intake form editor are leftover writers to fold. |
| 2 | Not a new capability. One editor over the MA-1 write + MA-2 resolver. |
| 3 | No new adapter. Shared Intake / ingestion runtime remains the only direct Mapping caller. Business modules never call Mapping Authority directly. |
| 4 | CL6 stays CL6. Sales convert stays Sales. OCR stays later. No Field Registry fork. No Zapier product. |
| 5 | Meta Settings field mapping and Intake form mapping must not stay a second/third writable overlay. |
| 6 | SoT for the operator surface = this file. MA-1 remains SoT for the operator question and write. MA-2 remains SoT for which rules apply. |
| 7 | No new event family. `mapping_applied_v1` stays applied-rule evidence. |
| 8 | **Requires:** MA-1 contract, MA-2 resolver, source schema (Graph / form schema / import headers). **Optional:** sample / latest lead as example. |
| 9 | No new licence. |
| 10 | Public contract **additive**: one operator surface. No breaking Hub/Passport change. |

**INV-01:** one SoT for “which answer writes which canonical field?”. **INV-16:** this UX contract before a second mapping editor.

---

## False close

Reject: a fourth editor; renaming C-5 as “the authority” while Meta admin still writes independently; leftover screens remaining competing product surfaces; treating sample as schema SoT; using schema as a runtime transform input; blocking mapping until a lead exists; generic “Needs review” as the only drift copy; shipping only “new field” as drift; silently dropping removed-field bindings; implicit Ignore for a missing destination; incomplete option-map marked Ready; unknown runtime option passing through as raw text; a separate preview evaluator; showing `qualified_code` / JSON / storage paths as the working UI; letting the operator change Field Registry type; absorbing Sales convert / OCR / CL6; collapsing binding and contract health into one scale, or minting Ready as a third status vocabulary; treating mapping uncertainty as candidate `no_fit`; implementing Forms Publish / ADR-022 as MA-3 work; a second Import Mapping runtime outside Shared Intake / ingestion; starting External Intake / Hiring E2E / min HR; Foundation ✅; MA-4 vocabulary cutover in this feat; declaring Mapping Operator Gate PASS because a mapping page exists or because parts of the UI already work.

---

## Consequences

- Mapping Operator Gate **PASS** only when this feat proves the close path on a real source and leftover mapping surfaces have ceased to be writers. An existing page is not that PASS.  
- Remaining writable screens must cease to be editors (deep-link/redirect or separately owned read-only diagnostics).  
- MA-4 still owns vocabulary cutover (`qualified_code` only). This file does not open MA-4.

---

## History

- 2026-09-04: Mapping workspace shows test/latest-lead evidence in the same scenario (form name · N questions · example received; Get latest example / Wait for next application). Schema remains SoT; sample does not add/drop rows. C-4 is leftover diagnostic, not a second mapping authority. Mapping Operator Gate **not PASS**. Close-path proof remains: map → Ready → projection → second submission → applied evidence. Not MA-4 / External Intake / Forms Publish / Hiring.
- 2026-09-04: Meta operator setup corrected: Schema remains SoT; sample remains non-authoritative; Meta primary path is Form → test/latest lead → Mapping (schema for completeness/drift). Close path includes test/latest lead + a second lead for applied evidence. HostFlow cannot mint a Facebook test lead; it can pull Graph `questions` + `field_data` and arm capture-next. Mapping Operator Gate **not PASS**. Not MA-1/MA-2 rewrite. Not MA-4 / External Intake / Forms Publish / Hiring.
- 2026-09-04: Mapping workspace shows source schema identity (native id when the provider has one, otherwise a deterministic schema fingerprint). This is not `mapping_applied_v1` applied-stale and not mapping readiness. Mapping Operator Gate **not PASS**. Close-path proof remains. Not MA-4 / External Intake / Forms Publish / Hiring.
- 2026-09-04: Sources / Diagnostics / Test lead open the Mapping workspace with a human CTA from the same assessment (`1 field is not configured` / Check Mapping / Open Mapping). Connect bind already lands in that workspace. Mapping Operator Gate **not PASS**. Not schema identity / close-path proof. Not MA-4 / External Intake / Forms Publish / Hiring.
- 2026-09-04: Sources / Diagnostics / Test lead read the canonical mapping assessment (questions to set, named drift, or Ready). Leftover `ready` / `broken` mapping chips are gone; connection / last-error / routing waiting stay operational health, not mapping readiness. Mapping Operator Gate **not PASS**. Not MA-4 / External Intake / Forms Publish / Hiring.
- 2026-09-04: Meta form mapping PUT and tenant `field_mapping` PATCH return 410; leftover Meta stores stay read-through. Legacy SPA write clients removed. Intake leftover PUT returns 410. Intake leftover preview over pasted `mapping_rules` is rejected (second algorithm); preview over the saved contract remains a read-only diagnostic. Routing preview is off the operator workspace. Mapping Operator Gate **not PASS**. Leftover writers are not retired as a product claim. Not MA-4 / External Intake / Forms Publish / Hiring.
- 2026-09-04: Feat `feat/mapping-authority-ma3-operator-gate` opened from `4073f3a7` ([#350](https://github.com/igortatarynovich/HostFlow/pull/350)). Close path = source → schema → explicit bindings/options → Ready → projection → real submission → applied evidence, plus leftover writer retirement. Mapping Operator Gate **not PASS**. Not MA-4 / External Intake / Forms Publish / Hiring.
- 2026-09-04: **PASS_WITH_SMALL_CORRECTIONS** — split configuration-time schema from submission-time answers; Ready as projection; complete option-map / unknown-option semantics; drift taxonomy + historical removed fields; explicit Ignore; Shared Intake / ingestion as the one runtime caller; leftover screens cease to be editors. Mapping Operator Gate not PASS.
- 2026-09-04: Feat `feat/mapping-authority-ma3-operator-surface` opened. Mapping Operator Gate not PASS.
- 2026-09-04: UX contract accepted from measurement after [#348](https://github.com/igortatarynovich/HostFlow/pull/348). Feat locked. Mapping Operator Gate not PASS.
