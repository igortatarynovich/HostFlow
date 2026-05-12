# Person — identity layer (deferred architecture guardrail)

**Purpose:** This document is **not** an implementation task. It is a **guardrail** so HostFlow does not introduce a full **Person** entity prematurely, and so duplicate / recruitment work stays operationally coherent until the right prerequisites exist.

**Related:** [Lead → Candidate operating model](../workflows/lead-to-candidate-operating-model.md) (§8 duplicate MVP, §12–§13), [Applications operating model](applications-operating-model.md) (intent layer **before** Person).

---

## One-line policy

**Person identity layer is intentionally deferred.** The current MVP uses **Candidate** as the operational identity anchor. **Person** may be introduced later after **Applications**, **Rehire flows**, and the **ownership model** are stable.

---

## What Person is (conceptually)

**Person** is the canonical **identity** entity for a human: *“who is this?”*

It is **not**:

- a recruitment object;
- an HR / workforce object;
- an intake or lead object.

---

## What belongs in Person (when it exists)

Only **identity** data, for example:

- normalized names;
- aliases / transliterations;
- phones, emails;
- date of birth, citizenship (if policy allows);
- identity confidence;
- document references (pointers, not full operational workflow);
- canonical matching keys for deduplication.

---

## What must not live in Person

Anything that is **operational state**, for example:

- pipeline stage, vacancy, recruiter assignment;
- SLA, tasks, queues;
- handoff status, HR status;
- recruitment or employment lifecycle.

Those stay on **Lead**, **Application**, **Candidate**, **Handoff**, or **WorkforceEmployee** (as appropriate).

---

## Why Person is not implemented now

- Large migration and model split;
- slows delivery while operational value is still low for the current product surface;
- **Candidate** temporarily combines *identity anchor* and *recruitment entity*, which is acceptable for MVP if duplicate and intake trails are disciplined.

---

## Problems Person will solve later

Without Person, **Candidate = person + recruitment context** breaks down when you need:

- repeat hire / multiple recruitment cycles for the same human;
- multiple applications over time with clean analytics;
- shared access, multi-agency, or cross-company identity reuse;
- reactivation and historical workforce tied to one identity;
- strict separation of “who” vs “which recruitment cycle”.

**Example:** someone employed in 2025, leaves, reapplies in 2026. Reusing one Candidate record pollutes pipeline history; creating a second loses identity continuity. **Person** (plus **Application** / cycle boundaries) fixes that split.

---

## Phases that should come before Person

Recommended sequence (operational, not calendar):

1. **Stabilize duplicate resolution** — decision API, audit, intake history, review UX; overrides must survive re-process (e.g. `duplicate_override_v1` preserved on re-normalization).
2. **Applications** — explicit “applied to this vacancy / campaign / cycle” instead of overloading Candidate alone — see [applications-operating-model.md](applications-operating-model.md).
3. **Rehire flow** — new recruitment cycle for an existing person record (today: existing Candidate), without pretending it is the same pipeline row as the old cycle.
4. **Handoff / ownership formalization** — recruitment vs HR vs employer vs shared; ownership ≠ stage ≠ visibility.
5. **Only then — Person** — thin identity layer on top of stable boundaries above.

---

## Signals that it may be time to introduce Person

Consider Person when several of these are true:

- heavy rehire and multi-cycle recruitment on the same humans;
- multiple concurrent applications per human with reporting that must not double-count identity;
- multi-agency or shared identity across companies;
- frequent identity conflicts and audit requirements that exceed “Candidate + duplicate override”;
- workforce history and recruitment history must be joined under one stable identity key.

Until then, **defer**.

---

## What not to build now (explicit non-goals)

To protect the roadmap, **do not** start now:

- graph-style identity resolution across arbitrary entities;
- automatic merge engines for candidates or leads;
- heavy fuzzy / ML duplicate matching as a product requirement;
- treating **Candidate** as a long-term global person registry without Applications / cycles.

Duplicate MVP should remain: exact / probable, HR protection, manual decision, audit trail, minimal UI.

---

## Current MVP stance (summary)

| Layer | MVP role |
|--------|-----------|
| **Lead** | Intake signal |
| **Candidate** | Recruitment entity **and** temporary identity anchor |
| **WorkforceEmployee** | Employment / HR entity |
| **Person** | **Not implemented** — architectural future layer only |

This keeps velocity high while preserving a clear path to a **thin** Person layer once boundaries above are stable.
