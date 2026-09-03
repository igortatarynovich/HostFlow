# User Report Intake Ownership Card

Status: baseline-established  
Date: 2026-09-03

Program: Architecture Rule 3 (ownership before domain) · seal brief [`user-report-intake-contract-seal.md`](../../specs/tasks/user-report-intake-contract-seal.md)  
Canon: [`ADR-040`](../../specs/architecture/ADR-040-user-report-intake.md) · Catalog [User Report Intake](../../specs/architecture/platform-capability-catalog.md#user-report-intake)

## Module

Name: `User Report Intake`  
Owner: `Platform / Application Shell` (platform capability owner)

Layer: **platform capability** — peer of Shell Diagnostics / Forms / Observability access surfaces. **Not** an ADR-004 licensed product module. **Not** Operate & Launch / RB-10.

## Module-Owned Capabilities

1. Explicit human submission object (`User Report`) and its **lifecycle status**;
2. Platform-owned `kind` set: `defect` | `data_wrong` | `idea` | `question`;
3. Orthogonal reference arrays: `telemetry_refs[]`, `incident_refs[]`, `work_refs[]`;
4. Architecture SoT for report lifecycle **when runtime exists**;
5. Later: authenticated submit API, tenant-visible own reports, platform inbox (superadmin + elevated reason).

## Source-of-Truth Areas

| Zone | Owner | Note |
|------|-------|------|
| Report lifecycle (`status`) | User Report Intake | Runtime **not started** — no table/API yet |
| Report `kind` | User Report Intake | Platform-owned small set (Rule 1) |
| Refs arrays | User Report Intake | Links only; INV-UR-01 |
| Telemetry store / search | Observability (ADR-038) | Report may reference; does not store |
| Service incident lifecycle | Operate & Launch / RB-10 | ADR-040 does not mint incidents |
| Engineering work state | GitHub | Report may expose `work_refs`; never owns work |
| Entity business history | Activity (ADR-012) + owning modules | Entity on report is observational only |

## Explicit Non-Ownership Boundaries

User Report Intake does **not** own:

1. Telemetry pipelines, Sentry, log/trace storage, Collect diagnostics / diagnostic bundles (ADR-038);
2. Service incident severity, escalation, rollback window, or customer-communication ownership (RB-10 / OL-7);
3. GitHub issue/PR state or engineering backlog SoT;
4. Activity / Task / Reminder SoT (ADR-012);
5. Communications threads (candidate/client messaging);
6. Forms publication / Field Catalog / business intake (Forms may later be submit UI only);
7. Module-local ticket inboxes or «support dump» downloads;
8. Severity on the public report contract (ops/incident assessment only);
9. Authority for entity existence, state, or business history (opaque entity ref is observational).

## Critical Invariants

1. **INV-UR-01** — Linking telemetry / incident / work **MUST NOT** auto-mutate `report.status` unless an explicit Intake-owned transition policy says so.
2. **Architecture SoT ≠ runtime** — HostFlow is Architecture SoT only when runtime exists; OL-7 email before runtime is **not** ADR-040 implementation and **not** a second product SoT.
3. Correlation (`request_id`, `trace_id`, `sentry_event_id`, `route`, `build_sha`) is **reference-only, best-effort** — absence does not invalidate a report.
4. `linked` is **not** a status; refs are orthogonal arrays.
5. No fifth trust role for support agents without Architecture RFC (ADR-036).

## Current Boundary State

1. **Runtime not started** — no persistence, public contract, or UI.
2. Frontend error boundaries say «contact support» with **no channel** ([`error_handling.md`](../../specs/frontend/error_handling.md)).
3. OL-7 / RB-10 remain **queued / MISSING**; when written, they may use Intake as evidence/input **if** runtime exists — they do not invent report rows to satisfy Architecture SoT.
4. This card records ownership for the seal; certification (contract map / dependency audit / test boundary) is later and not claimed here.
