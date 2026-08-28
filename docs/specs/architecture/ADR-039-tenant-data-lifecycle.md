# ADR-039: Tenant Data Lifecycle (provision → import → export → erase → retain)

**Status:** Proposed (acceptance is the [Launch Ownership Gate](../tasks/operate-and-launch.md) in OL-1)
**Date:** 2026-08-28
**Trusted base:** `integration/release-product-a-b`
**Related:** [`ADR-003`](ADR-003-tenant-company-module-data-boundaries.md) (tenant / company / module data boundaries) · [`ADR-009`](ADR-009-document-hub-platform-layer.md) (documents are a platform layer) · [`ADR-026`](ADR-026-capability-ownership.md) (capability ownership) · [`multi_tenant_model.md`](multi_tenant_model.md) · [`../../security/security-ssot.md`](../../security/security-ssot.md) §2 data classification · [`../gates/release-readiness-gate.md`](../gates/release-readiness-gate.md) RR4 / RR5 · [`../tasks/operate-and-launch.md`](../tasks/operate-and-launch.md) (consumer program)

**L0 checklist:** No new L0 P-rule and no Passport/Manifest shape change. (1) Owner = Platform Tenant capability, Security co-signs. (2) No existing capability claims this — searched for tenant export / erasure / retention owners; only fragments exist. (3) Delivery via a **Stable** platform adapter with module participants; modules keep their internals (Rule 2). (4) Does not extend any module’s Owns into the System Layer — participants declare, platform orchestrates (Rule 6). (5) No settings duplication: retention policy becomes one platform policy, module TTLs become participants. (6) SoT unchanged per entity; the lifecycle capability never becomes a second SoT for module data. (7) Events: lifecycle operations emit canonical security events (`emit_security_event_v1`), no new taxonomy family invented here. (8) Requires: RLS tenant binding, object storage, documents platform. (9) No new licence. (10) Public contract change is **additive** (new platform endpoints + participant registry).

---

## Context

The product is multi-tenant with `tenant_id` on every row and Postgres RLS, and it can already **create** a tenant through product surfaces. Everything after creation is unowned:

- **Import** exists only for leads (`backend/app/services/imports/leads.py`) and an HR org-unit JSON tree. A customer arriving with an existing candidate base cannot be onboarded.
- **Export** exists as per-entity fragments: per-candidate document bundles, client-side list CSVs, an analytics CSV, an invoice PDF, an org-unit JSON. Nothing aggregates a tenant, and nothing aggregates a natural person.
- **Erasure** is a soft flag. `delete_candidate_full` sets `deleted_at`; documents, communications and audit rows survive. `TenantStatus` has no `deleted` value and there is no tenant delete endpoint — offboarding is `scripts/purge_test_tenants.sql`. No `anonymize` / `pseudonymize` code exists in the backend, yet the customer-facing FAQ states that data is anonymised.
- **Retention** exists once, locally, for notifications (`services/notification_retention.py`, 30 days) with no platform policy above it.

Two consequences make this an architecture decision rather than a backlog item. First, the [Release Readiness Gate](../gates/release-readiness-gate.md) RR4/RR5 cannot be answered while these verbs have no owner — and it currently tolerates a purge script as evidence, which is a bar the product cannot ship on. Second, without a contract each module will grow its own export and its own delete, producing exactly the pattern Rule 6 forbids: business modules re-implementing a cross-module platform obligation, inconsistently, with legal exposure attached.

---

## Decision

### 1. Tenant Data Lifecycle is one platform capability with five verbs

| Verb | Meaning | Owner |
|------|---------|-------|
| **Provision** | Create tenant + license + first administrator + the minimum configuration needed to be usable | Platform (exists today) |
| **Import** | Load a customer’s pre-existing data into a tenant through a product surface | Platform orchestration; per-entity participants |
| **Export** | Produce a complete, machine-readable copy — for a **tenant** and for a **data subject** | Platform orchestration; per-entity participants |
| **Erase** | Destroy data irreversibly — for a **tenant** and for a **data subject** | Platform orchestration; per-entity participants |
| **Retain** | Time-based expiry / minimisation policy over tenant-scoped data | Platform policy; participants execute |

No module may expose its own tenant-wide export or its own subject-erasure endpoint. Per-entity operator exports (a candidate’s documents, a list CSV) remain module features and are explicitly **not** this capability.

### 2. Modules participate, they do not implement

Each module registers a **lifecycle participant** declaring, for the data it owns: which tenant-scoped tables and storage objects it holds, how they are exported, how they are erased, and what must survive erasure for legal reasons (for example financial records). The platform orchestrates order and atomicity; it never reaches into module internals (Rule 2), and modules never learn about each other’s tables.

### 3. Three deletion concepts are distinct and must not be conflated

| Concept | Meaning | May be called “erasure”? |
|---------|---------|--------------------------|
| **Soft delete** (`deleted_at`, `is_archived`) | Operational hide; data intact and restorable | **No** |
| **Subject erasure** | A natural person’s personal data destroyed or irreversibly pseudonymised across every participant | Yes |
| **Tenant offboarding** | The whole tenant’s data destroyed, storage objects included | Yes |

Any surface, document, or marketing claim that presents soft delete as erasure is a defect. The FAQ anonymisation claim is one, and is corrected by whichever slice ships the capability — not by weakening the definition.

### 4. Retention is one policy, not per-module constants

Retention windows become platform policy with participants executing them. Existing local windows (notification retention) are migrated to participants rather than duplicated. Class-based defaults follow the data classification in [`security-ssot.md`](../../security/security-ssot.md) §2.

### 5. Claims discipline

No customer-facing artifact (FAQ, legal document, DPA, sales material) may promise a lifecycle capability that has no registered participant implementation. This is the ADR’s hardest rule, because the current violation was found in the product, not in the plan.

### 6. Enforcement (Rule 7 — no boundary without enforcement)

| Requirement | Enforcement |
|-------------|-------------|
| Every tenant-scoped table is claimed by exactly one participant | Guard scan over tables carrying `tenant_id`, mirroring the RLS allowlist migration `202511261201_enable_rls_for_all_tables` |
| Export completeness | Contract test: an exported tenant archive covers every claiming participant |
| Erasure completeness | Contract test: after tenant erasure no row and no storage object remains for that `tenant_id`, except legally retained records that a participant declared |
| Lifecycle auditability | Every operation emits a canonical security event with actor, tenant, scope and reason |
| No module-owned tenant export / subject erasure | Import-boundary / route scan in the security gates workflow |

---

## Consequences

**Positive.** RR4 and RR5 become answerable with evidence instead of intent. Offboarding stops depending on a SQL script. New modules inherit the obligation through the participant contract rather than discovering it during a legal review. A DPA can describe real mechanics.

**Negative / cost.** Every existing module that owns tenant data must write a participant — this is real work, sized in [Operate & Launch](../tasks/operate-and-launch.md) OL-6. Erasure that is genuinely irreversible needs care where financial and audit records must legally survive; the participant contract must express that instead of quietly keeping everything.

**Security perimeter.** This ADR touches erasure, export and superadmin-initiated operations, so PRs implementing it fall inside the security perimeter and require the [security review checklist](../../security/security-review-checklist.md).

**Not decided here.** The archive format, whether export is synchronous or job-based, storage of produced archives and their own retention, DSAR intake workflow, and the migration importer’s file formats. Those are OL-6 implementation decisions and must not silently become a second ADR.

---

## Alternatives considered

| Alternative | Rejected because |
|-------------|------------------|
| Leave export/erasure to each module | Produces N inconsistent implementations of a legal obligation; violates Rule 6 and Rule 4 (the requirement is platform-mandatory, not module-local) |
| Keep the SQL purge script as the offboarding answer | Fails RR4 by definition; unauditable; unavailable to a non-developer operator; the gate’s own evidence bar rejects it |
| One “GDPR module” owning the data of others | Would need cross-module internals; violates Rule 2 |
| Defer the whole topic past v1 | Offboarding and data export are contractual for a first paying customer, not a later feature |

---

## Ownership card (Rule 3)

| Field | Value |
|-------|-------|
| **Domain** | Tenant Data Lifecycle |
| **Owner** | Platform Tenant capability owner; Security owner co-signs erasure / export semantics |
| **Source of truth** | This ADR for the contract; per-entity SoT unchanged for the data itself |
| **Consumers** | Superadmin / operator surfaces, Release Readiness Gate RR4 / RR5, acceptance suite RS-10 / RS-11, DPA |
| **Delivery contract** | Platform lifecycle adapter (Stable) + module participant registration |
| **Versioning** | Participant contract is versioned; adding a participant is additive; changing erasure semantics requires an ADR amendment |
| **Override policy** | Legally retained data only, declared by the participant with the legal basis named |
| **Enforcement** | See § 6 |

---

## History

- 2026-08-28: Proposed. Opened while briefing [Operate & Launch](../tasks/operate-and-launch.md) (v1 blocker 6) after an inventory found tenant export, subject erasure, tenant offboarding and retention without an owner, and a customer-facing anonymisation claim with no implementation.
