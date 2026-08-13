# Platform Standardization Model — area index

**Status:** Accepted (L2 operating canon — platform layer)  
**Hierarchy:** L2 — map of standardization areas; **not** a data SoT  
**Decision record:** [`ADR-038`](../architecture/ADR-038-platform-standardization-model.md)  
**Owner:** Architecture canon + platform core team

**Related:** [`ADR-037`](../architecture/ADR-037-platform-object-kind-catalog.md) · [`object-kind-catalog.md`](object-kind-catalog.md) · [`../architecture/platform-capability-catalog.md`](../architecture/platform-capability-catalog.md) · [`../architecture/ADR-011-hostflow-ui-platform-standard.md`](../architecture/ADR-011-hostflow-ui-platform-standard.md) · [`../architecture/ADR-036-four-trust-roles-rbac.md`](../architecture/ADR-036-four-trust-roles-rbac.md) · [`../architecture/architecture-review-checklist.md`](../architecture/architecture-review-checklist.md)

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
| 4 | `data_types` | Vocabulary | Platform Reference (target) | **gap** | Field `field_type` fragments only | Need semantic DataType canon (`phone`, `money`, `country`, `date`) separate from Fields; Field **uses** DataType | — |
| 5 | `relationships` | Vocabulary | Platform architecture (target) | **gap** | `document_entity_links`, Activity `related_entity_type` (runtime fragments) | Need Relationship Canon **contract**: source/target kind, cardinality, ownership, requiredness, lifecycle dependency, deletion policy, visibility, writers | — |
| 6 | `states_transitions` | Vocabulary | Architecture canon | **exists** | [`ADR-039`](../architecture/ADR-039-state-lifecycle-inventory.md), [`state-lifecycle-inventory.md`](state-lifecycle-inventory.md) | Inventory of dimensions + owners for Object Kind slice. **Shared value vocabulary still deferred** (no platform-wide status enum) | docs-lint inbound; checklist via ADR-039 |
| 7 | `rules` | Policy & Reuse | Architecture + domain policy owners | **exists** | ADR-037 RuleKind; [`object-kind-catalog.md`](object-kind-catalog.md) §5 | DomainPolicy / ProcessRule / AutomationReaction / PresentationRule | checklist dual-classification bans |
| 8 | `libraries` | Policy & Reuse | Forms / Field Registry / Communications / Documents | **exists** | ADR-037 LibraryKind; object-kind-catalog §6 | FormComponent, FieldDefinition, templates; checklist ≠ gate | Forms catalog tests; ADR-011 drift policy for UI libs |
| 9 | `actions` | Vocabulary | Platform Automations (ADR-019) | **gap** | ADR-019 Action Registry planned (3A-3) | Action semantics ≠ Permission ≠ Capability | future Action Registry + contract tests |
| 10 | `events` | Vocabulary | Platform events / Communications / modules | **gap** | Outbox 3A-1 (`domain_event_outbox`), scattered activity/security event lists | Need Event Canon registry contract: producer, schema owner, payload version, subject, actor, correlation/causation, consumers, classification (domain fact / audit / integration) | outbox tests (partial) |
| 11 | `capabilities` | Policy & Reuse | Platform architecture | **exists** | [`platform-capability-catalog.md`](../architecture/platform-capability-catalog.md), [`ADR-026`](../architecture/ADR-026-capability-ownership.md) | Passport / Owns / Exposes / Consumes | architecture-review-checklist; Catalog gate |
| 12 | `runtime_api_contracts` | Runtime Contracts | Platform + capability owners | **exists** | [`capability-contract.md`](../architecture/capability-contract.md), Forms public contract, [`reference_delivery_contract_standard.md`](../reference_delivery_contract_standard.md) | **Sub-gaps:** unified Error, Pagination, Filtering contracts not closed — do not invent a second status enum | capability contract tests; Forms sprint gates |
| 13 | `design_interaction` | Experience | Frontend platform | **exists** | [`ADR-011`](../architecture/ADR-011-hostflow-ui-platform-standard.md), ADR-010 List Shell | Prohibitions: no local semantic colors; no primitive clones; no unregistered interaction patterns. **Sub-gap:** Semantic Visual Language (meaning → token → treatment) | ADR-011 §12; eslint / `qa:static` tasks |
| 14 | `naming_identifiers` | Vocabulary | Architecture / platform core (target) | **gap** | Conflict evidence: `id_card` vs `national_identity_card` vs OCR codes | Rules for canonical codes, entity ids, field codes, actions, events, permissions, namespaces — naming standard for all other catalogs | future naming lint / registry CI |

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

1. ~~**States & Transitions** (`next`) — inventory on Object Kind Catalog rows.~~ **Done (ADR-039 inventory).** Shared value vocabulary still deferred.  
2. **Naming & Identifiers** — unblocks DocumentType `integrity=split`.  
3. **Data Types** + Fields linkage.  
4. **Relationships** contract.  
5. **Actions** / **Events** (ADR-019 3A-*).  
6. **Design** Semantic Visual Language on ADR-011.

---

## 8. History

- 2026-08-13: Area `states_transitions` → `exists` via ADR-039 inventory (shared enums deferred).
- 2026-08-13: Initial area index under ADR-038; ADR-037 retained as Object Kind / Rules / Libraries vocabulary.
