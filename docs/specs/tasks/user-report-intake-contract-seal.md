# User Report Intake — Contract Seal

**Status:** **ACTIVE** (docs-only seal; runtime not started)  
**Phase class:** platform  
**Date:** 2026-09-03  
**Trusted base:** `integration/release-product-a-b`  
**Parents:** [`ADR-040`](../architecture/ADR-040-user-report-intake.md) · [`ADR-038`](../architecture/ADR-038-shell-observability-diagnostics.md) · Catalog [User Report Intake](../architecture/platform-capability-catalog.md#user-report-intake) · ownership [`../../modules/user-report-intake/module_ownership_card.md`](../../modules/user-report-intake/module_ownership_card.md) · [Operate & Launch](operate-and-launch.md) OL-7 · [Hierarchy of Truth](../../governance/hierarchy-of-truth.md) · [Architecture review checklist](../architecture/architecture-review-checklist.md)

> Architecture seal only. Does **not** consume Active Product (RPM-1) or Active Launch-ops (OL-2). Unlock ≠ schedule. Not a v1 Release Goal blocker.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
Without a named owner, the next PR will invent a second support SoT — module-local «багтикет», Communications thread as feedback, Activity task as incident, Forms as ticket registry, or OL-7 email writing rows into a premature `reports` table “because HostFlow is SoT”. Telemetry, human report, service incident, and engineering work will collapse into one hidden state machine.

**Completion proof (named consumer):**  
This seal is **complete** when:

1. [`ADR-040`](../architecture/ADR-040-user-report-intake.md) is Accepted with four objects, refs ≠ status, INV-UR-01, Architecture SoT ≠ runtime, severity exclusion, best-effort correlation, observational entity, optional title;
2. Catalog Passport + Manifest outline + ownership card + module-catalog inbound refs exist;
3. OL-7 note states Intake is optional evidence/input **when runtime exists**, and does **not** own incidents;
4. Threat model outline exists; runtime STOP without it.

**False close (reject):** green in-app inbox; OL-7 email as “ADR-040 done”; table created to honor Architecture SoT before Public Contract; severity on report contract; `linked` as status.

---

## Locked principle

```text
Telemetry Event     → Observability (ADR-038)
User Report         → User Report Intake (ADR-040) — architecture SoT when runtime exists
Service Incident    → Operate & Launch / RB-10
Engineering Work    → GitHub

refs only; INV-UR-01; runtime not started
```

---

## In / Out

**In (this seal):** ADR + Passport + ownership card + Manifest outline + OL-7 consumer wording + frontend error_handling pointer + threat model outline.

**Out:** Alembic, API, widget, GitHub App, Collect diagnostics runtime, OL-7 execution, sequential-queue amendment, fifth trust role, severity on report.

---

## Acceptance

- [x] ADR-040 Accepted, runtime not started  
- [x] Ownership card with explicit non-ownership (incidents, telemetry, GitHub, Activity, severity)  
- [x] Catalog Index + Passport + Business Forbidden updated  
- [x] Manifest outline without severity knobs  
- [x] OL-7 wording: evidence/input when exists; ADR-040 does not mint incidents  
- [x] Threat model file linked from ADR and threat-models index  
- [x] `make docs-lint` green in the seal PR  

---

## History

- 2026-09-03: Brief opened with the seal; docs-only; Product/Launch-ops queues unchanged.
