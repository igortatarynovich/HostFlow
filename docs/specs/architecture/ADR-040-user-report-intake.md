# ADR-040: User Report Intake

**Status:** Accepted (canon sealed; runtime not started)  
**Date:** 2026-09-03  
**Trusted base:** `integration/release-product-a-b`  
**Related:** [`platform-capability-catalog.md`](platform-capability-catalog.md) · [`capability-settings-manifest.md`](capability-settings-manifest.md) · [`ADR-038`](ADR-038-shell-observability-diagnostics.md) · [`ADR-012`](ADR-012-activity-notification-operating-layer.md) · [`ADR-023`](ADR-023-recruitment-sales-module-separation.md) · [`ADR-036`](ADR-036-four-trust-roles-rbac.md) · [`../tasks/operate-and-launch.md`](../tasks/operate-and-launch.md) · [`../frontend/error_handling.md`](../frontend/error_handling.md) · [`../../security/threat-models/user-report-intake.md`](../../security/threat-models/user-report-intake.md) · ownership [`../../modules/user-report-intake/module_ownership_card.md`](../../modules/user-report-intake/module_ownership_card.md)

**L0 checklist:** No new P-rule; no Passport/Manifest **shape** change; no Architecture RFC. Applies **P-01** (Adapter later), **P-02** (one owner per boundary), **P-03** (compose Observability optionally; do not fork), **P-04/P-05** (Manifest knobs on Intake owner). **INV-01** (one SoT per object), **INV-04** (Business does not own Infrastructure), **INV-07** (do not fork diagnostics / support dump per module), **INV-16** (decision priority). Adding Catalog Index row + Passport is L1 application of L0, not a constitution rewrite.

**Does not supersede:** ADR-038 (Observability / Shell Diagnostics), ADR-012 (Activity / Notifications), Operate & Launch RB-10 (service incidents), Forms (ADR-007), Communications. Amends *who owns explicit human problem/feedback submission*.

---

## Context

HostFlow already has:

- **Machine telemetry** — optional Sentry + structured logs / `request_id` ([`../platform/observability.md`](../platform/observability.md), ADR-038).
- **Frontend error UX** — toast / banner / boundaries ([`../frontend/error_handling.md`](../frontend/error_handling.md)). `AppErrorBoundary` tells the user to contact support, but **no intake channel exists**.
- **Operator diagnostics** — Shell Diagnostics Collect bundle (ADR-038; runtime not started).
- **Service incident path** — OL-7 / RB-10 queued under Operate & Launch; **MISSING** today. Answers “the customer’s service is down”, not “user filed a report row”.

Without an owner, the next module will add «Сообщить о баге» into Communications, Activity, Forms, or a local Jira dump. That forks support the same way a second Form Builder forks Forms.

Four questions must stay separate:

1. What did the **machine** observe?
2. What did a **human** explicitly submit?
3. How does **ops** respond to service degradation?
4. What **engineering work** will change the product?

---

## Decision

### 1. Four objects, four lifecycle owners

| Object | Meaning | Lifecycle owner |
|--------|---------|-----------------|
| **Telemetry Event** | Machine evidence (logs, spans, Sentry) | Observability ([ADR-038](ADR-038-shell-observability-diagnostics.md)) |
| **User Report** | Explicit human submission (`defect` \| `data_wrong` \| `idea` \| `question`) | **User Report Intake** (this ADR) |
| **Service Incident** | Operational response to service degradation | Operate & Launch / RB-10 |
| **Engineering Work** | What engineers decide to change | GitHub (external work SoT) |

One Catalog capability owns User Report. Defect and feedback are **`kind` values on one object**, not two capabilities.

ADR-040 **does not mint or own** Service Incidents. ADR-040 **does not own** telemetry stores or GitHub issue state.

### 2. Directed references only — no shared lifecycle

```text
User Report  ──may reference──►  Telemetry
Incident     ──may reference──►  User Report(s) + Telemetry
GitHub Work  ──may reference──►  Report(s) / Incident
Report       ──may expose──────►  work reference (never owns work state)
```

Incident **never lives inside** a report row. Report **never owns** work state.

### 3. INV-UR-01 — Correlation does not imply lifecycle coupling

Linking a report to telemetry, an incident, or engineering work **MUST NOT** mutate `report.status` automatically unless an explicit **Intake-owned** transition policy says so.

Closing a GitHub issue **≠** auto-`closed` customer report. Mitigating an incident **≠** auto-`resolved` report. Attaching `request_id` **≠** status change.

### 4. Architecture SoT vs runtime (mandatory split)

Three statements that must not collapse:

| Statement | Meaning |
|-----------|---------|
| **Architecture SoT** | When runtime exists, User Report Intake owns user-report lifecycle |
| **Runtime state** | **not started** — no persistence, API, or inbox. HostFlow is **not** currently a runtime SoT for user reports |
| **OL-7 operational channel before runtime** | Procedure / email intake under Operate & Launch. **Not** an implementation of ADR-040 and **not** a second product SoT |

**Forbidden reading:** «HostFlow = Architecture SoT ⇒ OL-7 email must write `reports` rows». Email before runtime **must not** invent a table to “close” SoT.

OL-7 may consume User Report Intake as an **evidence/input channel when that capability exists**; incident lifecycle remains owned by RB-10 / Operate & Launch.

### 5. Lifecycle status ≠ refs

`linked` is **not** a `report.status`. Links are orthogonal arrays (may be empty). A report may be `triaged` and linked, `waiting_on_reporter` and linked, or `resolved` and linked at once.

**status (Intake-owned):**

`received` | `triaged` | `waiting_on_reporter` | `resolved` | `closed`

**refs (orthogonal):**

| Field | Contents |
|-------|----------|
| `telemetry_refs[]` | Best-effort refs: `request_id`, `trace_id`, `sentry_event_id`, … |
| `incident_refs[]` | RB-10 / ops incident ids when that procedure exists |
| `work_refs[]` | GitHub issue/PR later; adding a ref **does not** change status |

Status and `kind` are a **platform-owned** small set (Architecture Rule 1 — no module-local dictionaries).

### 6. Severity is not on User Report

The reporter says “it broke”; they do **not** assign severity. **Severity belongs to incident / ops assessment** (RB-10 runbook).

- This seal: **no** severity on the report Passport / future `user_report.public_contract.v1`.
- Later: optional Intake-owned `priority` / `impact` may exist as a **different authority**, never a copy of RB-10 severity into the public report contract.

### 7. Correlation — reference-only, best-effort

Optional observational fields: `request_id`, `trace_id`, `sentry_event_id`, `route`, `build_sha`.

**Invariant:** Absence of telemetry correlation **MUST NOT** block intake and **MUST NOT** make a report invalid. Crash-path, email intake, and failures before Observability init must still be able to produce a valid report.

Crash-path UI (`AppErrorBoundary`) must not depend on the full app provider tree; correlation remains best-effort.

### 8. Entity context — observational, not ownership

Intake **may** retain an **opaque** `entity_type` / `entity_id` for navigation/correlation when already known on screen.

Intake **MUST NOT** become authority for entity existence, state, or business history. Activity (ADR-012) remains the SoT for operational entity history. Modules do not own reports; they may pass observational context only.

### 9. Title optional / system-derived

Contract minimum for content: **`body` (required)**. `title` is a display aid — optional on submit, may be system-derived. Do not canonize “title + body” as required UX fields.

Passport shape (not schema / code): `id`, `tenant_id`, `reporter_user_id` (nullable for crash/email later), `kind`, `status`, `body`, optional `title`, `telemetry_refs[]`, `incident_refs[]`, `work_refs[]`, optional opaque entity ref, timestamps.

### 10. Which Shell / host

Application / Platform Shell (`hostflow.cc`, ADR-023) hosts later operator surfaces (platform inbox). Not Resource List Shell, not Entity Workspace chrome, not a business module workspace.

Platform inbox later = `superadmin` + elevated reason (ADR-036). **No fifth trust role** «support agent» without Architecture RFC (reject by default).

### 11. Delivery sequence (Rule 5)

```text
Ownership (this ADR + Passport + ownership card)
  → Reference (Catalog / Manifest outline)
  → Public Contract (`user_report.public_contract.v1`, Experimental until sealed)
  → Enforcement (guards: no module-local ticket inbox / support dump)
  → Threat model + security taxonomy (before runtime)
  → Runtime (persistence / API / UI last)
```

This ADR does **not** start runtime. It does **not** cut in front of Active Product (RPM-1) or Active Launch-ops (OL-2). Unlock ≠ schedule.

UI must not define the architecture ([`capability-contract.md`](capability-contract.md)).

### 12. Forbidden (when runtime eventually starts)

- Unredacted screenshot / DOM dump as default attachment
- Module-local download-log / support dump (ADR-038)
- Ticket as Communications thread SoT
- Ticket as Activity / Task SoT
- Forms Builder as ticket SoT (Forms may later be *submit UI* only; owner remains Intake)
- Auto-close from GitHub / incident without Intake-owned policy (INV-UR-01)
- Required telemetry for submit
- `linked` as status
- Severity on report public contract
- New canonical trust role for support agents

---

## Consequences

1. User Report Intake is a **Platform** Catalog capability (Always Available). It is **not** a sixth ADR-004 product module.
2. OL-7 / RB-10 remains the incident procedure owner. ADR-040 is not an “incident layer”.
3. Runtime Collect diagnostics stays ADR-038. Reports may later *cite* correlation ids; they do not replace Collect.
4. Security perimeter: free text, later attachments, cross-tenant superadmin inbox, rate limits — threat model prerequisite; taxonomy PR before runtime producers.
5. Enforcement (Rule 7) is required before the capability is «implemented». Until then this ADR is canon, not runtime.
6. Catalog Index grows by one row. L0 constitution / Passport **shape** unchanged.

---

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Put user reports in Communications threads | Wrong SoT; candidate/client messaging ≠ product feedback |
| Put user reports in Activity / Tasks | Activity is entity operational history (ADR-012), not support intake |
| Forms as ticket SoT | Forms is business intake; would fork support and Field Catalog |
| Status includes `linked` | Forces backward transitions or a hidden second state machine |
| Severity on report | Reporter is not ops; couples RB-10 into public contract |
| Require `request_id` / Sentry for valid report | Blocks crash-path and pre-observability failures |
| OL-7 email writes `reports` to “honor SoT” | Collapses Architecture SoT with runtime; invents product before Public Contract |
| Fifth trust role `support` | ADR-036 invariant; use elevated superadmin + reason |

---

## Cross-references (updated in this slice)

- [`platform-capability-catalog.md`](platform-capability-catalog.md) — User Report Intake Passport
- [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md) — §0 / §0.1
- [`capability-settings-manifest.md`](capability-settings-manifest.md) — Manifest outline (no severity knobs)
- [`../tasks/operate-and-launch.md`](../tasks/operate-and-launch.md) — OL-7 consumer note
- [`../frontend/error_handling.md`](../frontend/error_handling.md) — contact-support CTA later
- [`../tasks/user-report-intake-contract-seal.md`](../tasks/user-report-intake-contract-seal.md) — seal brief
- [`../../security/threat-models/user-report-intake.md`](../../security/threat-models/user-report-intake.md)

---

## History

- 2026-09-03: Accepted — four objects; refs ≠ status; INV-UR-01; Architecture SoT ≠ runtime; severity excluded; correlation best-effort; entity observational; title optional; runtime not started.
