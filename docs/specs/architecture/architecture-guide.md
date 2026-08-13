# Architecture Guide (platform canon)

## Phase 0 complete · L0 FROZEN

[`L0-platform-architecture.md`](L0-platform-architecture.md) · [`architecture-invariants.md`](architecture-invariants.md) · [`ADR-030`](ADR-030-l0-platform-architecture-closure.md) · product sequencing: [`platform-completion-roadmap.md`](platform-completion-roadmap.md) · active stage: [`platform-extraction-phase.md`](platform-extraction-phase.md)

```text
Phase 0 Constitution (done) → Phase 1 Platform (L1) → Phase 2 Business (L2) → Phase 3 Implementation (L3)
```

Организационные правила (спор → L0; не раздувать конституцию; ADR ссылается на P-rules; Catalog ежедневно; модуль только по шаблону) — в L0 § Organizational rules.

## Phase 1 lock (2026-07-18 · updated after Forms Sprint 1)

1. **Acquisition Stage 3D / Epic P:** ✅ **COMPLETE** ([`../tasks/acquisition-epic-p-stage-3d.md`](../tasks/acquisition-epic-p-stage-3d.md)).
2. **Forms Sprint 1:** ✅ **COMPLETE** ([`../tasks/forms-sprint-1.md`](../tasks/forms-sprint-1.md) · PR #36 · `37b652af`).
3. **Forms Sprint 2:** ✅ **COMPLETE** ([`../tasks/forms-sprint-2.md`](../tasks/forms-sprint-2.md) · PR #37 · `ec5fcd86`).
4. **Forms Sprint 3:** ✅ **COMPLETE** ([`../tasks/forms-sprint-3.md`](../tasks/forms-sprint-3.md) · PR #38 · `f5771df6`).
5. **Forms Sprint 4:** ✅ **COMPLETE** ([`../tasks/forms-sprint-4.md`](../tasks/forms-sprint-4.md) · PR #39 · `779cffd3`).
6. **Forms Sprint 5:** ✅ **COMPLETE** ([`../tasks/forms-sprint-5.md`](../tasks/forms-sprint-5.md) · PR #40 · `a6df02f0`).
7. **Forms Sprint 6:** ✅ **COMPLETE** ([`../tasks/forms-sprint-6.md`](../tasks/forms-sprint-6.md) · PR #41 · `7e259f22`) — backend platform contour closed.
8. **Forms Product Layer P1:** ✅ **CLOSED** (`97aac4e3` / #54 · status #55) — Catalog v1 **FROZEN**.
9. **P2 Builder MVP:** ✅ **COMPLETE** (P2.1–P2.5). P3–P5 **LOCKED**.  
10. **P2.5 UI gate:** ✅ **COMPLETE** (minimal Builder UI delivered).  
11. **Intake Canonical Input Matrix:** ✅ **ACCEPTED / FROZEN** — [`intake-canonical-input-matrix.md`](intake-canonical-input-matrix.md); **Runtime Split** R1–R4 + **R3.5 Flights dispatch** ✅ ([`../tasks/intake-runtime-split-v1.md`](../tasks/intake-runtime-split-v1.md) · [`../tasks/intake-r35-flights-dispatch-boundary.md`](../tasks/intake-r35-flights-dispatch-boundary.md)); **Communication Context V1** [`READY`](../tasks/intake-domain-separation-communication-context-v1.md); Forms P3–P5 **LOCKED**.  
12. **Decision Priority (INV-16):** [`decision-priority-rule.md`](decision-priority-rule.md) — L0 → ownership → contracts → only then convenience.  
13. **Outbound Communication (INV-17):** sole entry is the Communication Pipeline ([`../tasks/intake-communication-context-c5.md`](../tasks/intake-communication-context-c5.md)).
13. **Каждая новая L1 capability** идёт только по [`capability-contract.md`](capability-contract.md).  
14. Integration base-known CI failures: [`../tasks/acquisition-epic-p-base-known-ci-failures.md`](../tasks/acquisition-epic-p-base-known-ci-failures.md).

## Ежедневный путь проектирования (L1)

1. [`platform-capability-catalog.md`](platform-capability-catalog.md) — Owner + Passport  
2. Settings Manifest keys  
3. **Public Capability Contract** ([`capability-contract.md`](capability-contract.md))  
4. Adapter (P-01)  
5. Contract Tests  
6. Checklist + Invariants  
7. UI / L3 runtime  

```text
Passport → Manifest → Public Contract → Adapter → Contract Tests → UI
```

UI **не** определяет архитектуру.

## Артефакты

| Doc | Role |
|-----|------|
| L0 constitution | Freeze + org rules + phases |
| Catalog | **Рабочий справочник** |
| Settings Manifest | P-05 ops schema |
| **Capability Contract** | Публичный boundary surface до Adapter |
| **Platform Standardization Model** | Карта 14 областей стандартизации + Platform-first ([`ADR-038`](ADR-038-platform-standardization-model.md) · [`../platform/platform-standardization-model.md`](../platform/platform-standardization-model.md)) |
| **Object Kind Catalog** | Meta-canon классов объектов ([`ADR-037`](ADR-037-platform-object-kind-catalog.md) · [`../platform/object-kind-catalog.md`](../platform/object-kind-catalog.md)) — индекс SoT, не SoT данных; область ADR-038 Vocabulary / Policy & Reuse |
| **State / Lifecycle Inventory** | Dimensions + owners for Object Kind slice ([`ADR-039`](ADR-039-state-lifecycle-inventory.md) · [`../platform/state-lifecycle-inventory.md`](../platform/state-lifecycle-inventory.md)) — не общий enum статусов |
| **Naming & Identifiers** | Identifier kinds + namespaces + alias policy ([`ADR-040`](ADR-040-naming-identifiers.md) · [`../platform/naming-identifiers.md`](../platform/naming-identifiers.md)) — не runtime alignment DocumentType |
| **Data Types** | Semantic value types; Field **uses** DataType ([`ADR-041`](ADR-041-data-types.md) · [`../platform/data-types.md`](../platform/data-types.md)) — не миграция `field_type` |
| **Relationships** | RelationshipKind contract + confirmed slice ([`ADR-042`](ADR-042-relationships.md) · [`../platform/relationships.md`](../platform/relationships.md)) — не полный CRM-граф |
| **UI Component Canon** | Composition rule: React kit public API; pages assemble catalogued controls ([`ADR-043`](ADR-043-ui-component-composition-canon.md) · [`../platform/ui-component-canon.md`](../platform/ui-component-canon.md)) — не restyle |
| **List Workspace Canon** | One `ListWorkspace` + one `DataTable`; modules pass `ListDefinition` ([`ADR-044`](ADR-044-list-workspace-data-presentation-canon.md) · [`../platform/ui-list-workspace-canon.md`](../platform/ui-list-workspace-canon.md)) — runtime = [Platform Extraction](platform-extraction-phase.md) |
| **Analytics, Visualization & Reporting Canon** | Operational analytics language: meaning→family, story composition, screenshot-ready Analytics View ([`ADR-046`](ADR-046-analytics-visualization-canon.md) · [`../platform/ui-analytics-canon.md`](../platform/ui-analytics-canon.md)); Recruitment efficiency = reference |
| **Actions** | Operation semantics; Action ≠ Permission ≠ Capability ([`ADR-047`](ADR-047-actions.md) · [`../platform/actions.md`](../platform/actions.md)) — не runtime 3A-3 registry |
| **Platform Extraction** | Vocabulary Canon closed; Core Platform Kit before Phase B ([`platform-extraction-phase.md`](platform-extraction-phase.md) · [`../tasks/ui-platform-composition-epic.md`](../tasks/ui-platform-composition-epic.md)) |
| Invariants | INV-01…15 |
| Checklist | Обязателен перед ADR/PR |
| Epic P (3D) | Закрытие Acquisition V1 vertical |

## История

- 2026-08-13: **Platform Extraction** — Vocabulary Canon closed; next stage is Core Platform Kit before Phase B ([`platform-extraction-phase.md`](platform-extraction-phase.md)).
- 2026-08-13: **ADR-044** List Workspace & Data Presentation Canon Accepted — one `ListWorkspace` + `DataTable`; L2 [`../platform/ui-list-workspace-canon.md`](../platform/ui-list-workspace-canon.md); runtime extract = epic P1–P2.
- 2026-08-13: **ADR-046** Analytics, Visualization & Reporting Canon Accepted — four layers (semantics, grammar, composition, presentation/sharing); Recruitment efficiency reference; L2 [`../platform/ui-analytics-canon.md`](../platform/ui-analytics-canon.md).
- 2026-08-13: **ADR-043** UI Component & Composition Canon Accepted — React kit public API; CSS implementation; L2 [`../platform/ui-component-canon.md`](../platform/ui-component-canon.md).
- 2026-08-13: **ADR-047** Actions Accepted — Action contract + confirmed Documents/Activity/PE slice; L2 [`../platform/actions.md`](../platform/actions.md); 3A-3 runtime deferred.
- 2026-08-13: **ADR-042** Relationships Accepted — RelationshipKind contract + confirmed Documents/handoff/Activity/Comms slice; L2 [`../platform/relationships.md`](../platform/relationships.md); CRM graph deferred.
- 2026-08-13: **ADR-041** Data Types Accepted — Field ≠ DataType; L2 [`../platform/data-types.md`](../platform/data-types.md); runtime Field/Forms adoption deferred.
- 2026-08-13: **ADR-040** Naming & Identifiers Accepted — kinds / namespaces / alias policy; L2 [`../platform/naming-identifiers.md`](../platform/naming-identifiers.md); DocumentType runtime alignment deferred.
- 2026-08-13: **ADR-039** State / Lifecycle Inventory Accepted — dimensions + owners for Object Kind slice; L2 [`../platform/state-lifecycle-inventory.md`](../platform/state-lifecycle-inventory.md); shared status enum deferred.
- 2026-08-13: **ADR-038** Platform Standardization Model Accepted — 5 groups · 14 areas · Platform-first; L2 [`../platform/platform-standardization-model.md`](../platform/platform-standardization-model.md); State inventory = next.
- 2026-08-13: **ADR-037** Object Kind Catalog Accepted — meta-index for Documents / Requirements / Automation / Templates; prerequisite for state-dimension canon.
- 2026-07-18: L0 FROZEN; Phase 0 complete; switch to Phase 1.  
- 2026-07-18: Phase 1 lock — Epic P first; Capability Contract sequence; Forms Sprint 1 after V1.  
- 2026-07-18: Epic P COMPLETE — Forms Sprint 1 unlocked; Builder locked.
- 2026-07-18: Forms Sprint 1 infra started (Public Contract + Adapter).
- 2026-07-18: Forms Sprint 6 COMPLETE — submission envelope; Forms backend platform contour closed; Builder remains LOCKED.
- 2026-07-18: Forms Product Layer epic OPEN — Field Catalog SoT; Builder must not invent types; P1 next.
- 2026-07-18: Product Layer ACTIVE (`29f4057f`); P1 designed as component registry.
- 2026-07-18: P1 implementation plan P1.1 Registry → P1.2 Descriptors → P1.3 Stdlib → P1.4 Extension API.
- 2026-07-18: P1 decomposition ACTIVE (`51063d1c`); P1.1 READY FOR IMPLEMENTATION; Builder LOCKED until P1.3.
- 2026-07-18: P1.1 Registry COMPLETE (`644b102a`); P1.2 Descriptors READY; Builder LOCKED.
- 2026-07-18: P1.2 Design ACTIVE; Descriptor Contract READY FOR IMPLEMENTATION; declarative-only descriptors rule.
- 2026-07-18: P1.2 Descriptors COMPLETE (`1f7b4aba`); P1.3 Standard Library READY FOR IMPLEMENTATION; Builder LOCKED.
- 2026-07-18: P1.3 Standard Library implementation — Basic pack via public Catalog APIs; Builder UNLOCKED; P1.4 READY.
- 2026-07-19: P1.3 COMPLETE (`0cf7fc00`); P1.4 Extension API READY FOR IMPLEMENTATION.
- 2026-07-19: P1.4 Extension API + Field Catalog v1 freeze; P1 foundation COMPLETE; P2 Builder READY.
- 2026-07-19: P1.4 COMPLETE (`97aac4e3`); P2 Builder boundary fixed (Catalog client only).
- 2026-07-19: P2 Design ACTIVE (`a142bd0c`); P2.1–P2.5 decomposition; P2.1 READY; P3–P5 LOCKED.
- 2026-07-19: P2.1 Builder Read Model COMPLETE; P2.2 Composition READY.
- 2026-07-19: P2.1 merge #57; P2.2 Composition COMPLETE; P2.3 Commands READY.
- 2026-07-19: P2.3 Composition Commands COMPLETE; P2.4 Persistence READY.
- 2026-07-19: P2.4 Draft Persistence COMPLETE; P2.5 UI gate OPEN.
- 2026-07-19: P2.5 Minimal Builder UI COMPLETE — Builder MVP closed.  
- 2026-07-19: Intake Canonical Input Matrix ACTIVE / READY (docs-only; before routing runtime).
- 2026-07-19: Matrix ACCEPTED / FROZEN; Intake Runtime Split V1 READY; Flights / Intake Routing runtime UNLOCKED.
