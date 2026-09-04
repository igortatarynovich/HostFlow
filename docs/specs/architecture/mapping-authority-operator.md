# Mapping Authority Operator Surface

**Status:** **Accepted** (L2 UX contract — Mapping Operator Gate **not PASS**; feat may be opened)  
**Date:** 2026-09-04  
**Trusted base:** `integration/release-product-a-b` @ `3a4297b0` ([#348](https://github.com/igortatarynovich/HostFlow/pull/348))  
**Related:** [`mapping-authority-contract.md`](mapping-authority-contract.md) (`mapping_authority.v1`) · [`mapping-authority-resolution.md`](mapping-authority-resolution.md) (`resolve_mapping_authority`) · [`../tasks/mapping-authority.md`](../tasks/mapping-authority.md) · [`ADR-021`](ADR-021-unified-intake-resolution-model.md)

**L0 checklist:** No new P-rule; no Passport/Manifest **shape** change; no Architecture RFC. Applies **P-02** (one owner of this write), **INV-01** (one SoT for the operator question), **INV-16** (contract before a second editor). Does not rewrite L0. Does not mint a fourth mapping store or a Field Registry fork.

> This file is the **SoT** for MA-3 product surface: one editor, many entry points, schema-first, human-language health.  
> This merge **Accepts** the UX contract. It does **not** PASS Mapping Operator Gate. A later feat closes the remaining product gap. MA-4 / External Intake / Forms Publish / Hiring are not that feat.  
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

Flow:

1. Pick a source (Meta form, HostFlow Form, import source, …).
2. HostFlow shows **schema** — real questions and options. Sample / latest lead may sit beside a row as an example (`Последний пример: «Более 8 месяцев»`). Sample is never the structure SoT.
3. Each question has a simple destination: HostFlow field + status (`Mapped` / `Ignored` / `Unmapped`).
4. Choice destinations open **option map in-row**. Type is inherited from Field Registry; the operator cannot change it here.

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

A person who was never trained on Mapping connects a source, sees its schema, understands where each answer will land, brings the mapping to **ready**, and can explain what the next submission will write — **without** switching between several Settings / admin screens.

This untrained-operator criterion is the **acceptance statement** of MA-3. An editor that exists is not enough.

“Next submission will write …” is a **projection** produced from the saved Mapping contract + Field Registry metadata. It must use the same resolver/transform contract as ingestion and must not become a separate preview evaluator.

The three questions the surface must answer without a manual:

1. What arrived?
2. Where will HostFlow put it?
3. Is it working now?

If answering those requires Diagnostics + Meta Settings + Marketing Mapping, MA-3 has failed even if the backend is correct.

---

## Remaining product gap (not this merge)

This contract is **Accepted**. Mapping Operator Gate is **not PASS**. Do not fit this file to the current UI.

A later feat must close, at least:

- projection must not use a raw-text fallback;
- incomplete option map must not produce Ready;
- Meta Settings and other leftover surfaces must cease to be writers;
- schema-first mapping must work without a sample;
- preview must use the same resolution/transform contract as ingestion, not a private evaluator.

Schema + no sample + no binding → “Needs a check — 1 question to set” is the required no-sample semantics. It is not Operator Gate PASS.

MA-4 vocabulary cutover, External Intake, Forms Publish, and Hiring E2E are **not** that feat.

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

1. **Source identity** — name, provider, schema identity/version or deterministic schema fingerprint, depending on provider capability. Not “mapping rules admin”.
2. **Human summary** — Ready projection, or “N questions to set”, or a specific drift sentence from the taxonomy above.
3. **Question rows** — source question · HostFlow field (human label) · binding. Sample value optional, secondary. Removed fields stay as historical rows until review.
4. **In-row option map** when destination is choice-typed. Incomplete option decisions keep the choice binding not Ready.
5. **Projection** after save (same resolver/transform contract as ingestion, not a second evaluator); **applied evidence** after a real submission (RS-3 stays the program proof).
6. **No-sample state** — full schema still listed; copy is “no example answers yet”.
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

Reject: a fourth editor; renaming C-5 as “the authority” while Meta admin still writes independently; leftover screens remaining competing product surfaces; treating sample as schema SoT; using schema as a runtime transform input; blocking mapping until a lead exists; generic “Needs review” as the only drift copy; shipping only “new field” as drift; silently dropping removed-field bindings; implicit Ignore for a missing destination; incomplete option-map marked Ready; unknown runtime option passing through as raw text; a separate preview evaluator; showing `qualified_code` / JSON / storage paths as the working UI; letting the operator change Field Registry type; absorbing Sales convert / OCR / CL6; collapsing binding and contract health into one scale, or minting Ready as a third status vocabulary; treating mapping uncertainty as candidate `no_fit`; implementing Forms Publish / ADR-022 as MA-3 work; a second Import Mapping runtime outside Shared Intake / ingestion; starting External Intake / Hiring E2E / min HR; Foundation ✅; MA-4 vocabulary cutover in this feat.

---

## Consequences

- Mapping Operator Gate **PASS** only when a later feat ships this surface and the product criterion above is true on a real source. This Accepted contract is not that PASS.  
- Remaining writable screens must cease to be editors (deep-link/redirect or separately owned read-only diagnostics).  
- MA-4 still owns vocabulary cutover (`qualified_code` only). This file does not open MA-4.

---

## History

- 2026-09-04: UX contract **Accepted** (PASS_WITH_SMALL_CORRECTIONS). Mapping Operator Gate **not PASS**. MA-3 feat may be opened to close the remaining product gap. Not MA-4 / External Intake / Forms Publish / Hiring.
- 2026-09-04: **PASS_WITH_SMALL_CORRECTIONS** — split configuration-time schema from submission-time answers; Ready as projection; complete option-map / unknown-option semantics; drift taxonomy + historical removed fields; explicit Ignore; Shared Intake / ingestion as the one runtime caller; leftover screens cease to be editors. Mapping Operator Gate not PASS.
- 2026-09-04: Feat `feat/mapping-authority-ma3-operator-surface` opened. Mapping Operator Gate not PASS.
- 2026-09-04: UX contract accepted from measurement after [#348](https://github.com/igortatarynovich/HostFlow/pull/348). Feat locked. Mapping Operator Gate not PASS.
