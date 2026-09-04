# Mapping Authority Operator Surface

**Status:** **Accepted** (L2 UX contract — Mapping Operator Gate not PASS; feat open)  
**Date:** 2026-09-04  
**Trusted base:** `integration/release-product-a-b` @ `3a4297b0` ([#348](https://github.com/igortatarynovich/HostFlow/pull/348))  
**Related:** [`mapping-authority-contract.md`](mapping-authority-contract.md) (`mapping_authority.v1`) · [`mapping-authority-resolution.md`](mapping-authority-resolution.md) (`resolve_mapping_authority`) · [`../tasks/mapping-authority.md`](../tasks/mapping-authority.md) · [`ADR-021`](ADR-021-unified-intake-resolution-model.md)

**L0 checklist:** No new P-rule; no Passport/Manifest **shape** change; no Architecture RFC. Applies **P-02** (one owner of this write), **INV-01** (one SoT for the operator question), **INV-16** (contract before a second editor). Does not rewrite L0. Does not mint a fourth mapping store or a Field Registry fork.

> This file is the **SoT** for MA-3 product surface: one editor, many entry points, schema-first, human-language health.  
> Feat `feat/mapping-authority-ma3-operator-surface` implements the editor. Mapping Operator Gate stays **not PASS** until the untrained-operator criterion holds on a real source.  
> Binding / option map / evaluator isolation remain [MA-1](mapping-authority-contract.md). One resolver remains [MA-2](mapping-authority-resolution.md).

---

## Process boundary (universal)

Mapping sits **after** the source schema or answers arrive and **before** any business evaluation of those answers.

```text
Source schema / answers
  → Mapping Authority
  → canonical HostFlow facts (qualified_code + canonical option)
  → business logic
  → user object
```

| Source | Path |
|--------|------|
| Meta | form / question / option → Intake Source Profile → Mapping Authority → `qualified_code` + canonical option → Lead / Application facts → Requirement / qualification / routing → Recruiter workspace |
| HostFlow Form | Form schema → Submission → Mapping Authority → canonical facts → Decision / Outcome → Candidate / Inquiry / other business object |

Forbidden order: Meta label (`Более 8 месяцев`) → Recruitment evaluator. Required order: Mapping → `document_validity = GT_8_MONTHS` → evaluator.

This rule is the same for every intake source. A later source does not get a private mapping path.

---

## Who asks Mapping vs who consumes facts

**Direct consumer (one):** Intake runtime. It is the only layer allowed to ask Mapping Authority “how does this source answer become a canonical field/value?”

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

The operator must not see `qualified_code`, JSON, or storage paths as the working vocabulary.

---

## One editor, many entry points

**Invariant:** one editing surface; many entry points. Meta Connect, a form, diagnostics, or “1 field is not configured” may **open** Mapping. Editing always lands in the **same** workspace.

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

## Product criterion (Mapping Operator Gate)

A person who was never trained on Mapping connects a source, sees its schema, understands where each answer will land, brings the mapping to **ready**, and can explain what the next submission will write — **without** switching between several Settings / admin screens.

The three questions the surface must answer without a manual:

1. What arrived?
2. Where will HostFlow put it?
3. Is it working now?

If answering those requires Diagnostics + Meta Settings + Marketing Mapping, MA-3 has failed even if the backend is correct.

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

Required: specific — new question, missing option, changed options — not a generic error.

Today: `compute_mapping_health` is `ready` / `needs_review` / `broken` from connection status, rule count, and last error. Diagnostics drift is a fingerprint boolean. C-5 “Needs review” still mixes “new field or sample changed.” Option-map drift is not a first-class sentence.

### 5. How does the operator see impact?

Required: after save, a real projection (“the next application will write Code 95 = Yes”). After a submission, applied result / evidence.

Today: C-5 save toast + routing preview (destination / queue / duplicate — not canonical facts). Intake editor has preview / test-ingest over operator-pasted JSON. Applied-rule evidence lives in diagnostics (`mapping_applied_v1`), not on the editor.

### UX sources in MA-3 vs consume-only

**In the editor:** intake sources that have an Intake Source Profile — Meta Lead Form, HostFlow Form / public intake, import source.

**Consume facts only (no Mapping screen of their own):** Recruitment, Hiring, Requirement Policy, External Intake publish, Decision Layer.

**Out of the editor:** Sales convert, OCR, CL6, Telegram leftover, `lead_criteria_v1`.

---

## Screen contract (feat must ship)

Minimum workspace:

1. **Source identity** — name, provider, schema version. Not “mapping rules admin”.
2. **Human summary** — ready count, or “N questions to set”, or a specific drift sentence.
3. **Question rows** — source question · HostFlow field (human label) · binding. Sample value optional, secondary.
4. **In-row option map** when destination is choice-typed.
5. **Projection** after save; **applied evidence** after a real submission (RS-3 stays the program proof).
6. **No-sample state** — full schema still listed; copy is “no example answers yet”.
7. Entry CTAs from Connect, form, diagnostics, and “1 field is not configured” — all `open` the same editor.

C-5, Meta Field mapping, and Intake form mapping become **views or redirects** into this workspace. They must not remain independent writers.

Out: themes, analytics, bulk rule import, Zapier-style conditions, a type picker, a fourth store.

---

## Architecture review (L0 — ten questions)

| # | Answer |
|---|--------|
| 1 | **Owner:** Mapping Authority. Field Registry owns destination identity and type. Acquisition C-5 / Meta admin / Intake form editor are leftover writers to fold. |
| 2 | Not a new capability. One editor over the MA-1 write + MA-2 resolver. |
| 3 | No new adapter. Intake runtime remains the only direct Mapping consumer. |
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

Reject: a fourth editor; renaming C-5 as “the authority” while Meta admin still writes independently; treating sample as schema SoT; blocking mapping until a lead exists; generic “Needs review” as the only drift copy; showing `qualified_code` / JSON / storage paths as the working UI; letting the operator change Field Registry type; absorbing Sales convert / OCR / CL6; collapsing binding and contract health into one scale; treating mapping uncertainty as candidate `no_fit`; starting External Intake / Hiring E2E / min HR; Foundation ✅; MA-4 vocabulary cutover in this feat.

---

## Consequences

- Mapping Operator Gate **PASS** only when the feat ships this surface and the product criterion above is true on a real source.  
- Remaining writable screens become views or redirects.  
- MA-4 still owns vocabulary cutover (`qualified_code` only). This file does not open MA-4.

---

## History

- 2026-09-04: Feat `feat/mapping-authority-ma3-operator-surface` opened. Mapping Operator Gate not PASS.
- 2026-09-04: UX contract accepted from measurement after [#348](https://github.com/igortatarynovich/HostFlow/pull/348). Feat locked. Mapping Operator Gate not PASS.
