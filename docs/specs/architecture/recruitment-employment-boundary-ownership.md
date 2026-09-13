# Recruitment → Employment Boundary Ownership

**Status:** **Accepted** (L2 decision — dual-axis model)  
**Accepted:** 2026-09-13  
**Trusted base:** `integration/release-product-a-b`  
**Related:** [`ready-for-employment-contract.md`](ready-for-employment-contract.md) (`ready_for_employment.v1`) · [`employment-accept-policy.md`](employment-accept-policy.md) (`employment_accept_policy.v1`) · [`handoff-contract.md`](handoff-contract.md) · [`../../analysis/recruitment-employment-handoff-reality-audit.md`](../../analysis/recruitment-employment-handoff-reality-audit.md) · [`../tasks/recruitment-employment-handoff-rso2-cutover.md`](../tasks/recruitment-employment-handoff-rso2-cutover.md) · [`../tasks/recruitment-spine-orchestrator-v1.md`](../tasks/recruitment-spine-orchestrator-v1.md) · [`../tasks/employment-spine-orchestrator-v1.md`](../tasks/employment-spine-orchestrator-v1.md) · [`../tasks/employment-start-allowed-hr-host-binding.md`](../tasks/employment-start-allowed-hr-host-binding.md)

**L0 checklist:** No new P-rule; no Passport/Manifest **shape** change; no Architecture RFC. Applies **P-02** (Recruitment owns emit; Employment owns accept/employ) and the three RSO/ESO acceptance gates. Does not rewrite L0. Does not mint Employee from Recruitment.

> **SoT for Transfer boundary: lifecycle ownership × representation.**  
> Complements package **shape** (`ready_for_employment.v1`) and accept **policy** (`employment_accept_policy.v1`).  
> **Does not** invent a second HR dossier. **Does not** treat the package as live SoT for person/evidence.  
> **RSO-2** (opened separately): cutover `CandidateHandoff` — legacy snapshot → immutable manifest + access/write transition + Employment auto-init from **live authorities** + manifest decisions. Slice 4 remains closed.

---

## Operator question (one)

When Recruitment presses **Передать на трудоустройство**, for each fact: **who was authority before Transfer**, **what freezes in the boundary manifest**, **what stays live shared**, and **who may write after Transfer** — so Employment continues the **same person** without dossier copy and without a ritual Accept?

No second question. Formalize depth, Slice 4, Started remain later Employment work.

---

## Key locks

1. **`ready_for_employment.v1` fixes the boundary state and decision basis; it does not own live person/evidence data.**  
   Manifest = historical proof of the boundary; live authorities = current operational truth.
2. **Permission handoff ≠ domain authority.** Transfer may grant HR read/write *capabilities* for its stage without making HR owner of Person / Documents / Vacancy.
3. **Manifest records refs to fact versions, not silent copies.** If citizenship later changes UA → other, current HR sees the live fact; the manifest still proves: *at Transfer, Recruitment knew UA, version X, source Y*.
4. **known ≠ required to know before Transfer.** Do not collect facts only to pad the package. If already canonical, do not re-ask without conflict / expiry / applicability reason.
5. **Evidence used by Recruitment transfers by reference + provenance only.** Never copy files or invent `hr_*` SoT duplicates. Downstream **legal applicability** (e.g. enough for `start_allowed`) remains Employment-owned.
6. **No downstream runtime may use the manifest as the preferred current-value read when a live authority exists.**  
   Manifest citizenship answers “what was known at Transfer”; HR operational UI **defaults** to current canonical citizenship. Historical values appear only as audit / as-of context.
7. **Scope transition ≠ new permission subsystem.** RSO-2 must first inventory existing tenant/entity/handoff access rules and **reuse** them when HR access already arises via handoff/linkage. Do not mint a parallel ACL engine solely because this decision mentions scope transition.

---

## Dual axes

### Axis A — Lifecycle ownership

| Category | Meaning |
|----------|---------|
| **REQUIRED_AT_TRANSFER** | Must be decided/present for a valid Transfer (as value, ref, and/or decision). Applies to the **minimum** required for that row — not a full profile dump. |
| **PASS_IF_KNOWN** | Include only if already **authoritative canonical** in Recruitment/shared scope; omit if unknown; Employment may fill only as genuinely missing / conflicting. **Not** recruiter notes, preferences, or raw form answers. |
| **EMPLOYMENT_OWNED** | Arises after / belongs after the Recruitment boundary; not Recruitment’s job to invent for Transfer |

### Axis B — Representation

| Category | Meaning |
|----------|---------|
| **FROZEN_IN_MANIFEST** | Immutable historical record in `ready_for_employment.v1` only (decision, as-of value/ref+version/provenance, actor/time). No live SoT for that fact. |
| **LIVE_SHARED_AUTHORITY** | Same canonical entity/fact after Transfer; HR workspace reads the live SoT. (Use alone only when the manifest does **not** need an as-of freeze.) |
| **BOTH** | Manifest stores immutable as-of value/ref-set for audit; **operational SoT remains live**. Default for Person facts and Documents/Evidence that Transfer must prove *and* continue using. |

**Anti-pattern this freezes out:** snapshot quietly becoming a new source of truth  
(`Candidate snapshot → handoff snapshot → Employee snapshot → HR verification copy`).

---

## Four questions (every fact)

| # | Question | Example answers |
|---|----------|-----------------|
| 1 | Who is authority **before** Transfer? | Recruitment / shared Person / Documents Hub |
| 2 | What **freezes** in the manifest? | known value/ref + provenance / fact-version as-of-Transfer |
| 3 | What stays **live**? | canonical Person fact / Document / Vacancy entity |
| 4 | Who may **write** after Transfer? | limited Recruitment / Employment / shared fact authority |

---

## Master transfer rule

Recruitment does **not** transfer everything Employment will ever need.  
Recruitment freezes a **boundary manifest** and transitions **access/write scopes** (reusing existing access primitives where possible).  
Employment reads **live shared authorities** + **immutable Recruitment decisions**, then collects only **Employment-owned missing**.

Target runtime shape (RSO-2):

```text
Recruitment closes
  → immutable ready_for_employment.v1 manifest emitted
  → access / write scopes transition (inventory-first; no new ACL product by default)
  → Employment auto-initializes from live authorities + manifest decisions
  → only Employment-owned missing remains
```

Not:

```text
Candidate copied → handoff copied → Employee copied → HR verifies copies
```

---

## Fact matrix (dual-axis — Accepted)

| Data | Lifecycle (A) | Representation (B) | Before-Transfer authority | Freezes in manifest | Stays live | Write after Transfer |
|------|---------------|--------------------|---------------------------|---------------------|------------|----------------------|
| Person **identity minimum** (enough to identify the person) | REQUIRED_AT_TRANSFER | BOTH | shared Person / Candidate | identity minimum + version/provenance as-of | same Person facts | shared Person authority; no `hr_identity` copy |
| Contacts **operational minimum** (enough to reach the person for handoff ops) | REQUIRED_AT_TRANSFER | BOTH | shared Person | contact minimum as-of | same contacts | shared; update = fact change |
| Other person profile facts | PASS_IF_KNOWN | BOTH | shared Person | only if authoritative known | same facts | shared / conflict flows |
| Citizenship / other canonical person facts | PASS_IF_KNOWN | BOTH | shared Person (+ Recruitment write in its scope) | value + fact/version/provenance **if authoritative known** | same citizenship fact | change via **canonical fact authority**; no `hr_citizenship` |
| Documents | used → REQUIRED refs; else PASS_IF_KNOWN | **BOTH** | Document Hub | **immutable ref-set** of evidence used for Recruitment verdict (as-of) | same Document objects | Hub rules; Employment checks / applicability — not a second file SoT |
| Evidence | used → REQUIRED refs | **BOTH** | Evidence / Hub | immutable ref-set + provenance used for Fits/Transfer | same Evidence | Employment applicability; no metadata clone as HR SoT |
| Employer | REQUIRED_AT_TRANSFER | BOTH | Employer / company entity | canonical **ref** + optional label/version as-of | same Employer | target context — do not re-pick; Transfer does not transfer entity ownership |
| Vacancy | REQUIRED_AT_TRANSFER | BOTH | Vacancy entity | canonical **ref** + optional title/version as-of | same Vacancy | same |
| Target role / position | REQUIRED_AT_TRANSFER **when it exists as part of Recruitment target-work context** | BOTH | Vacancy / Recruitment target context | Freeze **target role ref/context** when distinct; if Vacancy alone is sufficient target-work authority, **do not duplicate** a separate role | live vacancy / role attrs | Employment may add **employment-specific** attributes only — must not reconstruct target role from thin labels |
| Fits decision + reason | REQUIRED_AT_TRANSFER | FROZEN_IN_MANIFEST | Recruitment | full immutable decision | *(none — historical)* | immutable |
| Requirements verdicts at Transfer | REQUIRED_AT_TRANSFER | FROZEN_IN_MANIFEST | Recruitment | immutable verdict set as-of | *(none as Recruitment SoT)* | Employment may run **new** Employment requirements; must not replace Recruitment verdict history |
| Evidence refs used for decision | REQUIRED_AT_TRANSFER | BOTH (frozen ref-set + live objects) | Documents/Evidence | frozen ref-set | live objects | see Documents/Evidence |
| Source / provenance / Transfer actor+time | REQUIRED_AT_TRANSFER | FROZEN_IN_MANIFEST | Recruitment audit | actor, time, source refs | audit trail | append-only audit |
| Known residence / work facts | PASS_IF_KNOWN | BOTH | shared / Recruitment | as-of if **authoritative** known | live facts | Employment adds legalization/employability missing only |
| Planned start | PASS_IF_KNOWN else EMPLOYMENT_OWNED | BOTH **only if authoritative known**; else Employment | agreement / Employment | Freeze **only** authoritative established agreement — **not** recruiter note / preference / raw form answer | live Employment start fact if any | otherwise Employment-owned missing |
| Contract basis / type | PASS_IF_KNOWN else EMPLOYMENT_OWNED | BOTH **only if authoritative known**; else Employment | agreement / Formalize | Freeze **only** authoritative agreement — **not** note / preference / raw form | Formalize / Employment | otherwise Employment-owned |
| Medical / BHP **document** | PASS_IF_KNOWN (refs) | BOTH | Documents | refs if already held | same docs | **applicability / admit** = EMPLOYMENT_OWNED |
| Medical / BHP **applicability to admit** | EMPLOYMENT_OWNED | — (Employment decision) | — | do not pretend Recruitment decided sufficiency | Employment decision SoT | Employment only |
| HR employability / pathway | EMPLOYMENT_OWNED | — | — | not in Recruitment package as decision | Employment | Employment |
| ZUS / Insurance | EMPLOYMENT_OWNED | — | — | no | Employment lifecycle | Employment |
| A1 / delegation | EMPLOYMENT_OWNED | — | — | not for PEM-1 Transfer | other policy | other context |

---

## Permission handoff vs domain authority

| Transfer may grant | Transfer must not imply |
|--------------------|-------------------------|
| HR **read** of Person / Documents / Vacancy / Application needed for the case | HR **owns** those entities |
| Employment **write** capabilities for Employment-owned facts and allowed verifications | Exclusive ownership of Person or Document Hub |
| Recruitment **read-only** or **limited write** after Transfer | Recruitment loses all visibility of the person |

Inventory existing handoff/linkage access first (lock 7). Complexity stays in the system: one person, Recruitment → HR; internals change scopes, not copy entities.

---

## Transfer semantics (Accepted intent)

```text
Before Transfer     Recruitment Ready (Fits + package valid under this dual model)
Atomic Transfer     emit immutable ready_for_employment.v1 (boundary manifest)
                    → Recruitment completed audit
                    → create/init Employment case on CandidateHandoff transport
                    → access/write scopes transition (reuse existing access)
                    → employment_accept_policy.v1 evaluates automatically
After Transfer      HR opens workspace composed from:
                    live Person + Target work + Why Ready (manifest decisions)
                    + live Documents/Evidence + first Employment-owned missing/action
                    (manifest values only as as-of/audit — lock 6)
```

**Forbidden as default:** ritual **Take into HR review** that re-collects the person from copies.

**Transport:** keep `CandidateHandoff`. Change payload (manifest) + initialization (access + auto-init). Legacy multi-snapshot chain is not SoT.

---

## Accept policy ≠ Accept button

Keep **`employment_accept_policy.v1`** (ESO-1):

| Policy outcome | Operator |
|----------------|----------|
| Package valid → auto-init | No Accept ritual |
| Real blocker | Show blocker |
| Human business decision required | Human decides then — not default pickup chore |

---

## HR verification (keep, split)

| Forbidden | Allowed |
|-----------|---------|
| Re-confirm known canonical fact merely because HR started | New Employment requirement |
| Prefer manifest current-value over live authority (lock 6) | Evidence conflict, expiry, applicability to **this post/conditions** |
| Mint `hr_*` copies of Person/Documents | Legally required Employment verification bound to live authorities |
| Treat weak notes/form answers as PASS_IF_KNOWN established facts | Use authoritative canonical facts only |

---

## Schedule

| Open now | Still closed |
|----------|--------------|
| This L2 **Accepted** | Slice 4 / Full Spine |
| [`recruitment-employment-handoff-rso2-cutover.md`](../tasks/recruitment-employment-handoff-rso2-cutover.md) — inventory + cutover brief | New permission subsystem by default |
| RSO-2 implementation only after cutover inventory | Auto-pull planned_start/contract into Recruitment without authoritative PASS_IF_KNOWN proof |

Slice 1–3 `start_allowed` remain valid downstream; they do not replace this boundary.

---

## Non-goals

- Implementing RSO-2 in this decision.  
- Redesigning Document Hub ownership.  
- Expanding Formalize / PEM-1 medical-BHP decision authorities into Recruitment.  
- Opening Slice 4 or Full Spine.  
- Collecting Employment lifecycle facts “just in case.”  
- Building a greenfield ACL engine without access inventory.

---

## Accept record

Accepted 2026-09-13 with pre-Accept refinements:

- Documents/Evidence representation = **BOTH**  
- Person identity / contacts = **minimum** REQUIRED; other person facts PASS_IF_KNOWN  
- Target role required when part of target-work context; no duplicate if Vacancy suffices  
- Planned start / contract = PASS_IF_KNOWN only for **authoritative** known  
- Locks 6–7 (manifest not preferred live read; scope transition inventory-first)
