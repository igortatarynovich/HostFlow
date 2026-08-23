# ADR-038: Shell Observability Access and Collect Diagnostics

**Status:** Accepted (canon sealed; runtime not started)  
**Date:** 2026-08-23  
**Trusted base:** `integration/release-product-a-b`  
**Related:** [`platform-capability-catalog.md`](platform-capability-catalog.md) · [`../platform/observability.md`](../platform/observability.md) · [`capability-settings-manifest.md`](capability-settings-manifest.md) · [`ADR-023`](ADR-023-recruitment-sales-module-separation.md) · [`ADR-026`](ADR-026-capability-ownership.md) · [`ADR-036`](ADR-036-four-trust-roles-rbac.md) · [`../../security/runtime-roadmap.md`](../../security/runtime-roadmap.md)

**L0 checklist:** No new P-rule; no Passport/Manifest **shape** change; no Architecture RFC. Applies **P-01** (Observability Adapter), **P-02** (one owner per boundary), **P-03** (Shell Diagnostics composes Observability), **P-04/P-05** (Manifest knobs on the owner). **INV-01** (one SoT), **INV-04** (Business does not own Infrastructure), **INV-07** (do not fork diagnostics per module), **INV-16** (decision priority). Adding Catalog Index rows + Passports is L1 application of L0, not a constitution rewrite.

**Does not supersede:** ADR-010 (Resource List Shell), ADR-011 (UI Standard), ADR-012 (Activity / Notifications), ADR-023 (Application Shell as deploy host), domain diagnostics (C0.3 Delivery Diagnostics, Acquisition Source Diagnostics, Marketing Diagnostics). Amends *who may expose operator log/trace access*.

---

## Context

HostFlow already emits structured logs, request correlation, and Sentry spans (`backend/app/core/observability.py`, `hostflow-frontend/src/lib/observability.ts`). Catalog has **Activity** (operational history) and **Search** (entity query). It does **not** name who owns logs/traces/errors, or who may give a human a diagnostic bundle.

Without an owner, the next module will add a «Скачать лог» button. That forks observability the same way a second Form Builder forks Forms.

Two questions must stay separate:

1. Who **produces** telemetry?
2. Who **provides access** to it for an operator?

---

## Decision

### 1. Split emit from access

```text
service / module  →  emit logs + spans
Platform          →  collect, correlate, store, search, redact, RBAC
Application Shell →  operator surface: Logs / Traces / Errors / Collect diagnostics
```

**Shell must be able to obtain and present diagnostic data ≠ Shell must generate and store all logs.**

### 2. Which Shell

This ADR means the **Application / Platform Shell** (`hostflow.cc`, ADR-023): the shared operator host, not a business module workspace.

| Surface | This ADR? |
|---------|-----------|
| Application / Platform Shell (`hostflow.cc`) | **Yes** — operator access to observability |
| Resource List Shell (ADR-010) | No |
| Settings Shell (P-05 admin IA) | No — may later *compose* Observability Manifest knobs |
| Entity Workspace chrome | No |

Shell must not accumulate business workspaces (ADR-023). Diagnostics is a **platform** surface on the shell host, not a Recruitment/HR/CRM screen.

### 3. Two Catalog capabilities (P-02)

One Passport cannot own both the log store and the operator button.

| Capability | Kind | Owner | Owns |
|------------|------|-------|------|
| **Observability** | Infrastructure | Platform observability | Structured log/trace/error pipelines; `trace_id` / `request_id` propagation; storage / export; search of Logs / Traces / Errors; redaction of secrets / PII in telemetry |
| **Shell Diagnostics** | Platform | Application Shell | Operator UI (Diagnostics); **Collect diagnostics**; **Download diagnostic bundle** |

Business modules (Recruitment, HR, Sales, SMS/Communications, Automations, …) **emit** their own structured logs and spans. They do **not** own a log store, a trace search, or a download-log capability.

### 4. Ownership matrix

| Responsibility | Owner |
|----------------|-------|
| Emit logs | Concrete service / module |
| Emit spans | Concrete service / module |
| `trace_id` / `request_id` propagation | Platform (Observability) |
| Storage / export | Observability infrastructure |
| Search Logs / Traces / Errors | Observability |
| Collect diagnostics | Shell Diagnostics |
| Download diagnostic bundle | Shell Diagnostics |
| RBAC of access | Platform (ADR-036 + Observability / Shell Diagnostics gates) |
| Redaction of secrets / PII | Platform (Observability implements; Security canon is policy) |

Emit of logs/spans is a **platform duty of every runtime**, like structured logging — not a Catalog `Consumes` edge and not a `Requires` on business passports. Modules must not own a second store.

### 5. Collect diagnostics (not «download log»)

Shell Diagnostics exposes **Collect diagnostics**, not a raw file dump.

A **diagnostic bundle** is assembled for a **specific operation** (preferred: `trace_id` / `request_id`) or a **bounded time window**, and may include:

- correlation metadata (`trace_id`, `request_id`, `tenant_id`, `company_id`, module, entity type/id)
- frontend logs / client errors in that scope
- backend logs in that scope
- errors
- traces / spans

**Before issue:** Observability **must** redact secrets, tokens, credentials, and sensitive / PII fields. Unredacted bundles are forbidden.

The Diagnostics UI shows correlation context and from there opens the trace, related logs, or Collect diagnostics. It does not become a second Activity Timeline (ADR-012) or a second Search (entity index).

### 6. Domain diagnostics stay module-owned

Existing **domain / operational** diagnostics remain with their owners:

- Communications C0.3 Delivery Diagnostics
- Acquisition Source Diagnostics
- Marketing Diagnostics

They may **display** correlation ids and **deep-link** into Shell Diagnostics. They must not become a log store, a trace backend, or a tenant-wide «download logs» path.

Activity (ADR-012) remains operational history for humans in the product. Observability remains machine telemetry. Do not merge the two SoTs.

### 7. Correlation context (minimum)

Every request / span / structured log that participates in Collect diagnostics SHOULD bind:

`trace_id` · `request_id` · `tenant_id` · `company_id` (when known) · `module` · `entity_type` / `entity_id` (when known)

Platform owns propagation. Modules fill domain fields they already know; they do not invent a parallel correlation scheme.

### 8. Delivery sequence (Rule 5)

```text
Ownership (this ADR + Passports)
  → Reference (Catalog / Manifest outline)
  → Public Contract (Observability Adapter + Collect diagnostics ops)
  → Enforcement (guards: no module-local log download)
  → Runtime (UI last)
```

This ADR does **not** start runtime. It does **not** cut in front of the locked Product / Engineering tracks (CL0 / R1). Public Contract, threat model, and adapter land in a later scheduled slice.

UI must not define the architecture ([`capability-contract.md`](capability-contract.md)).

---

## Consequences

1. Collect Diagnostics / Logs / Traces is a **Platform Shell** capability. It is **not** a Recruitment, HR, CRM, Communications, or Automations capability.
2. New module-local «download log» / «our traces» / «support dump» implementations are an **architecture violation** (P-02, INV-07) unless they are domain diagnostics as in §6.
3. Observability.md is the L2 operating canon for pipelines, retention, and metrics; **ownership** lives in this ADR + Catalog Passports.
4. Runtime Collect diagnostics is a **security-perimeter export**. Before Adapter/UI: threat model, `security-review-checklist.md`, `emit_security_event_v1` on collect/download/deny, redaction tests. Unredacted export is STOP.
5. Enforcement (Rule 7) is required before the capability is «implemented»: contract tests + a guard against module-local log-download APIs. Until then this ADR is canon, not runtime.
6. Catalog Index grows by two rows. L0 constitution / Passport **shape** is unchanged.

---

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Observability owns Collect + Download; Shell is only UI chrome | Conflicts with the access/emit split: operator collect is a Shell capability; storage/search stay Observability. One Passport would hide two owners. |
| One «Application Shell» Catalog capability that owns nav, launcher, and diagnostics | Over-scope. ADR-023 already defines the shell **host**. This ADR mints only the diagnostics **access** capability. |
| Each module ships its own diagnostics bundle | INV-07 / P-02 failure: observability fragments; redaction and RBAC drift. |
| Put log download on Resource List Shell | Wrong Shell (ADR-010 is list chrome). |
| Merge Observability into Activity | Activity is operational product history, not traces/logs. |

---

## Cross-references (updated in this slice)

- [`platform-capability-catalog.md`](platform-capability-catalog.md) — Observability + Shell Diagnostics Passports
- [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md) — §0 / §0.1
- [`../platform/observability.md`](../platform/observability.md) — emit vs access
- [`capability-settings-manifest.md`](capability-settings-manifest.md) — Manifest outlines
- [`ADR-026`](ADR-026-capability-ownership.md) — ownership examples
- [`platform-architecture-principles.md`](platform-architecture-principles.md) — shared capabilities §6

---

## История

- 2026-08-23: Accepted — emit vs access; Observability (Infrastructure) vs Shell Diagnostics (Platform); Collect diagnostics; runtime not started.
