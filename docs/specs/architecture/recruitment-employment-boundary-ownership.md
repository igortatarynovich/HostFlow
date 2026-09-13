# Recruitment → Employment Boundary Ownership

**Status:** **Proposed** (L2 decision — open for Accept; inventory only until Accepted)  
**Date:** 2026-09-13  
**Trusted base:** `integration/release-product-a-b`  
**Related:** [`ready-for-employment-contract.md`](ready-for-employment-contract.md) (`ready_for_employment.v1`) · [`employment-accept-policy.md`](employment-accept-policy.md) (`employment_accept_policy.v1`) · [`handoff-contract.md`](handoff-contract.md) · [`../../analysis/recruitment-employment-handoff-reality-audit.md`](../../analysis/recruitment-employment-handoff-reality-audit.md) · [`../tasks/recruitment-spine-orchestrator-v1.md`](../tasks/recruitment-spine-orchestrator-v1.md) · [`../tasks/employment-spine-orchestrator-v1.md`](../tasks/employment-spine-orchestrator-v1.md) · [`../tasks/employment-start-allowed-hr-host-binding.md`](../tasks/employment-start-allowed-hr-host-binding.md)

**L0 checklist:** No new P-rule; no Passport/Manifest **shape** change; no Architecture RFC. Applies **P-02** (Recruitment owns emit; Employment owns accept/employ) and the three RSO/ESO acceptance gates. Does not rewrite L0. Does not mint Employee from Recruitment. Does not open RSO-2 / Slice 4 / Full Spine by itself.

> **SoT for fact ownership at Transfer.**  
> Complements package **shape** (`ready_for_employment.v1`) and accept **policy** (`employment_accept_policy.v1`).  
> Does **not** redesign Document Hub; does **not** invent a second handoff entity.  
> Runtime cutover implication (after Accept of this decision): RSO-2 = cutover existing `CandidateHandoff` from legacy snapshot → `ready_for_employment.v1` + Employment auto-init — **not** a new handoff product.

---

## Operator question (one)

When Recruitment presses **Передать на трудоустройство**, **which facts must be frozen in the package**, which may pass **only if already known**, and which Employment alone may collect after Transfer — so Employment continues the **same person** without re-running Recruitment and without a ritual Accept?

No second question. Legalization pathway depth, Formalize, `start_allowed` Slice 4, and Started remain later Employment work.

---

## Master rule

Recruitment does **not** transfer everything Employment will ever need.  
Recruitment transfers **everything it already knows and is entitled to be authority for**, plus **provenance/evidence refs**.  
Employment collects **only new facts that arise after the Recruitment boundary**.

**Hard corollary — known ≠ required to know before Transfer:**

- Recruitment **must not** ask for a fact solely to pad a handoff package if that fact was **not** required for the Recruitment decision (e.g. citizenship not needed for Fits).  
- If the fact is **already known and canonicalized**, Employment **must not** re-ask it without a documented conflict / expiry / applicability reason.

---

## Ownership categories

Every Transfer-relevant fact falls into exactly one category:

| Category | Meaning |
|----------|---------|
| **REQUIRED_AT_TRANSFER** | Must be present and frozen on a valid `ready_for_employment.v1` before Transfer completes |
| **PASS_IF_KNOWN** | If Recruitment already holds a canonical value → freeze and transfer; if unknown → omit; Employment may resolve only as **genuinely missing** or **conflicting** |
| **EMPLOYMENT_OWNED** | Not Recruitment’s job to invent for Transfer; Employment missing / lifecycle after boundary |

### Evidence rule (cross-cutting)

> Evidence used by Recruitment **MUST** transfer by **reference + provenance**.  
> Evidence is **never copied**.  
> Downstream **legal applicability** / admit-to-work sufficiency remains **Employment-owned**.

---

## Fact matrix (v1)

| Data | Category | On Transfer | Ownership after Transfer |
|------|----------|-------------|--------------------------|
| Person identity | REQUIRED_AT_TRANSFER | Frozen | **reuse** |
| Contacts | REQUIRED_AT_TRANSFER | Frozen | **reuse**; update only as a **fact change** (not ritual re-entry) |
| Citizenship | PASS_IF_KNOWN | Frozen **if known** | Employment resolves only if genuinely missing / conflicting |
| Employer | REQUIRED_AT_TRANSFER | Required | **target context** — do not re-pick |
| Vacancy | REQUIRED_AT_TRANSFER | Required | **target context** |
| Position / role | REQUIRED_AT_TRANSFER if defined in Recruitment context | Required when Recruitment context defined it | Employment may refine **employment-specific** attributes only |
| Fits decision | REQUIRED_AT_TRANSFER | Required | **immutable** Recruitment decision |
| Fits reason | REQUIRED_AT_TRANSFER | Required | **immutable** |
| Ready / Transfer actor + time | REQUIRED_AT_TRANSFER | Required | **audit** |
| Recruitment requirements verdicts | REQUIRED_AT_TRANSFER | Required | **reuse** |
| Known residence / work facts | PASS_IF_KNOWN | Frozen if Recruitment knows them | Employment adds only Employment / legalization missing |
| Evidence / document refs (used) | REQUIRED_AT_TRANSFER | Refs for evidence used for Fits / Transfer | Same Document Hub authority |
| Source / provenance refs | REQUIRED_AT_TRANSFER | Required | audit / reasoning |
| Planned start | PASS_IF_KNOWN | Only if **already authoritatively agreed** | Otherwise **EMPLOYMENT_OWNED** missing |
| Contract basis / type | PASS_IF_KNOWN | Only if Recruitment already has **authoritative agreement** | Otherwise **EMPLOYMENT_OWNED** |
| BHP / Medical | PASS_IF_KNOWN (refs) | Pass **evidence refs** if already held | Applicability / admit decision = **Employment** (`start_allowed` etc.) |
| ZUS / Insurance | EMPLOYMENT_OWNED | Do not transfer as Recruitment package duty | Employment lifecycle |
| A1 / delegation | EMPLOYMENT_OWNED | Not for PEM-1 Transfer package | Other context / policy |

---

## Transfer semantics (frozen intent)

```text
Before Transfer     Recruitment Ready (Fits + package valid)
Atomic Transfer     freeze ready_for_employment.v1
                    → Recruitment completed audit
                    → create/init Employment handoff (keep CandidateHandoff as transport)
                    → employment_accept_policy.v1 evaluates automatically
After Transfer      HR opens: Person + Target work + Why Ready
                    + Known facts + Evidence + first Employment-only missing/action
```

**Forbidden after Transfer when gates pass:** ritual **Take into HR review** as the default path.

**Transport entity:** existing `CandidateHandoff` may remain. Change **payload + initialization semantics**, not necessarily the whole model. Legacy snapshot is not the package SoT.

---

## Accept policy ≠ Accept button

Keep **`employment_accept_policy.v1`** as system authority (ESO-1 lock):

| Policy outcome | Operator |
|----------------|----------|
| Package valid → auto-init Employment | No Accept ritual |
| Real blocker | Show blocker |
| Policy requires human **business** decision | Human decides **then** — not a default pickup chore |

Do **not** delete Accept Policy. Delete the **operator ritual** when policy returns auto-accept.

---

## HR verification (keep, split)

| Forbidden | Allowed |
|-----------|---------|
| Re-confirm a **known canonical Recruitment fact** merely because HR started | Verify a **new Employment requirement** |
| Re-ask package facts without `conflict_reason` | Resolve **evidence conflict**, expired document, applicability to **this post / conditions** |
| Treat Transfer as “re-collect the person” | Legally required verification that Employment owns |

Avoid both extremes: “HR re-checks everything” and “Recruitment wrote UA once → eternal truth without conflict/expiry rules.”

---

## Implications for schedule (after this decision is Accepted)

| Open next | Do not open yet |
|-----------|-----------------|
| Product Accept of this L2 | RSO-2 implementation before Accept |
| Then RSO-2 as **cutover**: `CandidateHandoff` + legacy snapshot → emit/consume `ready_for_employment.v1` + auto-init + HR host consumption | New parallel handoff product |
| Slice 4 only **after** that cutover proves Employment starts from package facts | Full Spine; auto-pull planned_start / contract basis into Recruitment without PASS_IF_KNOWN proof |

Slice 1–3 `start_allowed` remain valid downstream mechanics; they do not substitute this boundary.

---

## Non-goals

- Runtime emit / cutover code (RSO-2).  
- Changing Document Hub ownership.  
- Expanding Formalize or PEM-1 medical/BHP authorities.  
- Declaring Slice 4 or Full Spine open.  
- Forcing Recruitment to collect Employment lifecycle facts “just in case.”

---

## Accept criteria (for promoting Status → Accepted)

- [ ] Three categories + evidence rule accepted as SoT for Transfer ownership  
- [ ] Transfer semantics (atomic package → auto accept-policy eval; no ritual Accept as default) accepted  
- [ ] HR verification split (forbidden vs allowed) accepted  
- [ ] RSO-2 interpreted as **cutover**, not new handoff construction  
- [ ] Slice 4 gated **after** cutover, not after Slice 3 alone  

No machine gate in this Proposed open. Gate/tests attach when Accepted and RSO-2 opens.
