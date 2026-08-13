# Platform Standardization Model — area index

**Status:** Accepted (L2 operating canon — platform layer)  
**Hierarchy:** L2 — map of standardization areas; **not** a data SoT  
**Decision record:** [`ADR-038`](../architecture/ADR-038-platform-standardization-model.md)  
**Owner:** Architecture canon + platform core team

**Related:** [`ADR-037`](../architecture/ADR-037-platform-object-kind-catalog.md) · [`object-kind-catalog.md`](object-kind-catalog.md) · [`../architecture/platform-capability-catalog.md`](../architecture/platform-capability-catalog.md) · [`../architecture/ADR-011-hostflow-ui-platform-standard.md`](../architecture/ADR-011-hostflow-ui-platform-standard.md) · [`../architecture/ADR-043-ui-component-composition-canon.md`](../architecture/ADR-043-ui-component-composition-canon.md) · [`../architecture/ADR-046-analytics-visualization-canon.md`](../architecture/ADR-046-analytics-visualization-canon.md) · [`../architecture/ADR-036-four-trust-roles-rbac.md`](../architecture/ADR-036-four-trust-roles-rbac.md) · [`../architecture/architecture-review-checklist.md`](../architecture/architecture-review-checklist.md) · [`../architecture/platform-extraction-phase.md`](../architecture/platform-extraction-phase.md)

---

## 1. Purpose

Index of the **fourteen platform standardization areas** under ADR-038:

- which group each area belongs to;
- who owns it;
- maturity `status`: `exists` | `next` | `gap`;
- where today’s canon lives;
- which enforcement hooks already apply.

This file does **not** invent datatype lists, state vocabularies, relationship inventories, or design tokens. Those are follow-on canons.

**Platform-first / Reuse-first** (ADR-038): check the matching area catalog before any local entity, field, datatype, relationship, state, action, event, rule, library, capability, API contract, or UI pattern.

---

## 2. Groups

| Group | Areas |
|-------|-------|
| Vocabulary | Object Kind, Roles & Permissions, Fields, Data Types, Relationships, States & Transitions, Actions, Events, Naming & Identifiers |
| Policy & Reuse | Rules, Libraries, Capabilities |
| Runtime Contracts | Runtime / API Contracts |
| Experience | Design & Interaction |
| Governance | Architecture Enforcement (**mechanism**, not area #15) |

---

## 3. Area index

Row contract: `area_code` · `group` · `owner` · `status` · `canonical_refs` · `notes` · `enforcement_hooks`.

| # | area_code | group | owner | status | canonical_refs | notes | enforcement_hooks |
|---|-----------|-------|-------|--------|----------------|-------|-------------------|
| 1 | `object_kind` | Vocabulary | Architecture / platform core | **exists** | [`ADR-037`](../architecture/ADR-037-platform-object-kind-catalog.md), [`object-kind-catalog.md`](object-kind-catalog.md) | ObjectKind / RuleKind / LibraryKind; Documents–Automation slice indexed | architecture-review-checklist; docs-lint inbound refs |
| 2 | `roles_permissions` | Vocabulary | Users / Roles / Permissions (Catalog) | **exists** | [`ADR-036`](../architecture/ADR-036-four-trust-roles-rbac.md), [`rbac_matrix.md`](../architecture/rbac_matrix.md) | Four trust roles; presets ≠ roles; `access_context` | `make rbac-role-lint` / security-gates |
| 3 | `fields` | Vocabulary | Platform Field Registry | **exists** | [`field-registry-card-configuration.md`](field-registry-card-configuration.md), Field Registry manifests | Canonical field codes + layouts; profile JSON remains fallback | Field Registry seed / closure tests |
| 4 | `data_types` | Vocabulary | Platform Reference (target) + Architecture | **exists** | [`ADR-041`](../architecture/ADR-041-data-types.md), [`data-types.md`](data-types.md) | Semantic DataType canon; Field **uses** DataType. **Runtime `field_type` adoption still deferred** | docs-lint inbound; future Field/Forms adoption PR |
| 5 | `relationships` | Vocabulary | Platform architecture | **exists** | [`ADR-042`](../architecture/ADR-042-relationships.md), [`relationships.md`](relationships.md) | RelationshipKind **contract** + confirmed Documents/handoff/Activity/Comms slice. **Full CRM graph deferred**; fragments listed only | docs-lint inbound |
| 6 | `states_transitions` | Vocabulary | Architecture canon | **exists** | [`ADR-039`](../architecture/ADR-039-state-lifecycle-inventory.md), [`state-lifecycle-inventory.md`](state-lifecycle-inventory.md) | Inventory of dimensions + owners for Object Kind slice. **Shared value vocabulary still deferred** (no platform-wide status enum) | docs-lint inbound; checklist via ADR-039 |
| 7 | `rules` | Policy & Reuse | Architecture + domain policy owners | **exists** | ADR-037 RuleKind; [`object-kind-catalog.md`](object-kind-catalog.md) §5 | DomainPolicy / ProcessRule / AutomationReaction / PresentationRule | checklist dual-classification bans |
| 8 | `libraries` | Policy & Reuse | Forms / Field Registry / Communications / Documents | **exists** | ADR-037 LibraryKind; object-kind-catalog §6 | FormComponent, FieldDefinition, templates; checklist ≠ gate | Forms catalog tests; ADR-011 drift policy for UI libs |
| 9 | `actions` | Vocabulary | Platform Automations (ADR-019) + Architecture | **exists** | [`ADR-047`](../architecture/ADR-047-actions.md), [`actions.md`](actions.md) | Action contract + confirmed Documents/Activity/PE slice. **3A-3 runtime registry deferred**; CRM public actions remain fragment | docs-lint inbound; ADR-019 3A-3 for runtime |
| 10 | `events` | Vocabulary | Platform events / Communications / modules | **gap** | Outbox 3A-1 (`domain_event_outbox`), scattered activity/security event lists | Need Event Canon registry contract: producer, schema owner, payload version, subject, actor, correlation/causation, consumers, classification (domain fact / audit / integration) | outbox tests (partial) |
| 11 | `capabilities` | Policy & Reuse | Platform architecture | **exists** | [`platform-capability-catalog.md`](../architecture/platform-capability-catalog.md), [`ADR-026`](../architecture/ADR-026-capability-ownership.md) | Passport / Owns / Exposes / Consumes | architecture-review-checklist; Catalog gate |
| 12 | `runtime_api_contracts` | Runtime Contracts | Platform + capability owners | **exists** | [`capability-contract.md`](../architecture/capability-contract.md), Forms public contract, [`reference_delivery_contract_standard.md`](../reference_delivery_contract_standard.md) | **Sub-gaps:** unified Error, Pagination, Filtering contracts not closed — do not invent a second status enum | capability contract tests; Forms sprint gates |
| 13 | `design_interaction` | Experience | Frontend platform | **exists** | [`ADR-011`](../architecture/ADR-011-hostflow-ui-platform-standard.md), [`ADR-043`](../architecture/ADR-043-ui-component-composition-canon.md), [`ADR-044`](../architecture/ADR-044-list-workspace-data-presentation-canon.md), [`ADR-046`](../architecture/ADR-046-analytics-visualization-canon.md), [`ui-component-canon.md`](ui-component-canon.md), [`ui-list-workspace-canon.md`](ui-list-workspace-canon.md), [`ui-analytics-canon.md`](ui-analytics-canon.md), ADR-010 List Shell | Composition: React kit public API; CSS implementation. Lists: one `ListWorkspace` + `DataTable` (rule; runtime = [Platform Extraction](../architecture/platform-extraction-phase.md)). Analytics: four layers; Recruitment reference. **Sub-gaps:** layouts/templates (ADR-045, deferred); remaining dashboard migrations; ListWorkspace/EntityWorkspace runtime extract; persisted Analytics View | ADR-011 §12; ADR-043 migrate-on-touch; kit CI ratchet |
| 14 | `naming_identifiers` | Vocabulary | Architecture canon | **exists** | [`ADR-040`](../architecture/ADR-040-naming-identifiers.md), [`naming-identifiers.md`](naming-identifiers.md) | Identifier kinds + namespaces + alias policy; DocumentType split inventoried. **Runtime code alignment still deferred** (`integrity=split` until dedicated PR) | docs-lint inbound; future naming lint / registry CI |

---

## 4. Governance mechanism (not area #15)

| Mechanism | role | refs | notes |
|-----------|------|------|-------|
| Architecture Enforcement | Forces the fourteen areas to bind | [`architecture-review-checklist.md`](../architecture/architecture-review-checklist.md), `make docs-lint`, REF-4 / boundary gates, ADR-011 §12 | Not a subject canon; does not own domain vocabulary |

---

## 5. Status legend

| status | Meaning |
|--------|---------|
| `exists` | Canonical docs and/or runtime SoT are in place for the area’s core job |
| `next` | Next dedicated standardization PR (explicitly queued) |
| `gap` | Needed; no closed area canon yet (fragments may exist) |

Sub-gaps under an `exists` area are recorded in **notes** only (e.g. Error/Pagination under Runtime/API; Semantic Visual Language under Design).

---

## 6. How a developer uses this map

1. Find the area for the change (entity → Object Kind / Naming; color → Design; gate → Rules / States; webhook payload → Events; …).
2. Open `canonical_refs`. If an equivalent exists — **reuse**.
3. If missing and `status` is `gap` or `next` — extend that area’s canon in a dedicated PR **before** module adoption (Platform-first).
4. Do not invent a parallel local catalog.

---

## 7. Explicit follow-on sequence

Vocabulary Canon **closed** (ADR-037…047). Do not write further docs-only ADRs to fill map cells.

1. ~~**States & Transitions**~~ **Done (ADR-039 inventory).** Shared value vocabulary still deferred.  
2. ~~**Naming & Identifiers**~~ **Done (ADR-040).** DocumentType runtime alignment remains a separate PR (Documents E).  
3. ~~**Data Types**~~ **Done (ADR-041 inventory).** Runtime Field/Forms `data_type` adoption deferred (Forms C).  
4. ~~**Relationships**~~ **Done (ADR-042).** Full CRM graph deferred.  
5. ~~**Design composition / ListWorkspace rule / Analytics / Actions**~~ **Done as rules** (ADR-043 / 044 / 046 / 047).  
6. **Platform Extraction** (active) — [phase](../architecture/platform-extraction-phase.md) · [Core Platform Kit](../tasks/ui-platform-composition-epic.md): `DataTable` + `ListWorkspace` runtime; Analytics public composition; minimal `EntityWorkspace` chrome.  
7. **Events runtime** — ADR-019 3A-1 when a real consumer exists; **not** an inventory ADR now.  
8. **ADR-045** page templates — only when a second real template consumer exists.

---

## 8. History

- 2026-08-13: Vocabulary Canon closed; follow-on = [Platform Extraction](../architecture/platform-extraction-phase.md) (not Events/ADR-045 docs).  
- 2026-08-13: Area `design_interaction` ListWorkspace / DataTable via ADR-044 (rule; runtime extract P1–P2).
- 2026-08-13: Area `design_interaction` analytics + reporting language via ADR-046 (Recruitment efficiency = reference; other dashboards migrate-on-touch).
- 2026-08-13: Area `design_interaction` composition rule via ADR-043 (React kit public API).
- 2026-08-13: Area `actions` → `exists` via ADR-047 (confirmed slice; 3A-3 runtime deferred).
- 2026-08-13: Area `relationships` → `exists` via ADR-042 (confirmed slice; CRM graph deferred).
- 2026-08-13: Area `data_types` → `exists` via ADR-041 (runtime Field/Forms adoption deferred).
- 2026-08-13: Area `naming_identifiers` → `exists` via ADR-040 (runtime DocumentType alignment deferred).
- 2026-08-13: Area `states_transitions` → `exists` via ADR-039 inventory (shared enums deferred).
- 2026-08-13: Initial area index under ADR-038; ADR-037 retained as Object Kind / Rules / Libraries vocabulary.
