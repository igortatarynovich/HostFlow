# Workspace Capability — legacy local forks inventory

**Status:** **INVENTORY** (feat; not a migration)  
**Parents:** [Workspace Capability Platform Completion](workspace-capability-platform-completion.md)  
**Canon replacement:** platform kit (data types → fields → primitives → widgets → tables) + Capability Host Contract

> Inventory ≠ migrate every row. Proof screen (next slice) must not add a **new** row.
> Consent-at-capture (ADR-007) is **not** a kit widget to absorb here.
> RODO/Notes forks are **rows**, not the scope of this inventory.

---

## Kit SoT (do not copy)

| Layer | Canon | Typed catalog |
|-------|-------|---------------|
| Data types | [Field Registry §4](../platform/field-registry-card-configuration.md) | `KIT_DATA_TYPE_IDS` |
| Fields | Field Registry + [Entity Profile](../platform/entity-profile-definition-registry.md) | pointer only |
| UI primitives | [PRIMITIVES_V1](../frontend/PRIMITIVES_V1.md) | `KIT_UI_PRIMITIVE_IDS` |
| Widgets | compositions of primitives + fields | `KIT_WIDGET_CLASS_IDS` |
| Tables | [TABLE_V1](../frontend/TABLE_V1.md) | `KIT_TABLE_FRAME_IDS` |
| Table instances (audit) | [COMPONENT_REGISTRY prefill](../frontend/REF-UI-000-COMPONENT_REGISTRY.prefill.md) | migrate-on-touch |

---

## Hosts in scope

| Host | Constitution | Runtime today |
|------|--------------|---------------|
| `entity_workspace` | §3.3 | `EntityWorkspaceShell` |
| `application_workspace` | §3.2 | `ApplicationWorkspace` |

---

## 1. Data types / fields

| Local fork | Consumer | Maps toward | Evidence |
|------------|----------|-------------|----------|
| `CandidateProfile.config.field_configs` | Candidate | Field Registry layout | field-registry canon § migration |
| `profileUtils.ts` hardcoded keys | Candidate | Field Registry `qualified_code` | frontend profile utils |
| `personal_data` / `extra` schemaless keys | Candidate | `storage.json_path` on canonical fields | `candidates` table |
| Module-local required-field matrices | Recruitment / HR | Field Requirement Registry | field-registry canon |

---

## 2. UI primitives

| Local fork | Consumer | Maps toward | Evidence |
|------------|----------|-------------|----------|
| Ad-hoc status `<span className=...>` | Recruitment Application header | `status_badge` (PRIMITIVES_V1) | `APPLICATION_STATUS_BADGE` in `applicationDisplay.ts` |
| Native unstyled `<select>` / `<input>` in rails | Recruitment Application | `select` / `input` | `ApplicationRecruitmentDetailPanel` vacancy/assignee controls |
| New primitive family in a module | any | forbidden; extend PRIMITIVES_V1 | constitution §11 |

---

## 3. Tables

| Local fork | Consumer | Maps toward | Evidence |
|------------|----------|-------------|----------|
| `table_candidates_main_v7` | Candidate list | TABLE_V1 reference | COMPONENT_REGISTRY |
| `table_vacancies_list` and other entity lists | Vacancy / Client / HR / … | TABLE_V1 migrate-on-touch | COMPONENT_REGISTRY §1 |
| Page-local table chrome | any new list | `table_v1_entity_list` | TABLE_V1 governance |

---

## 4. Widgets (including, not limited to, Notes/Consent)

| Local widget | Consumer | Host | Maps toward | Evidence |
|--------------|----------|------|-------------|----------|
| Hardcoded `CandidateCard` sections | Candidate | Entity | `field_row` + Field Registry layout | `CandidateCard.tsx` |
| `SalesInquiryCallNotesSection` | Sales Inquiry | Application | widget `notes` | `components/sales/SalesInquiryCallNotesSection.tsx` |
| `SalesInquiryRodoSection` | Sales Inquiry | Application | widget `consent` + policy `lead_rodo_v1` | `components/sales/SalesInquiryRodoSection.tsx` |
| `CandidateRodoSection` | Candidate | Entity | widget `consent` | `components/candidate/CandidateRodoSection.tsx` |
| ContextRail `vacancy` stuffing | Recruitment Application | Application | `recruitment.vacancy` | `ApplicationRecruitmentDetailPanel` `contextSlots.vacancy` |
| ContextRail `assignee` stuffing | Recruitment Application | Application | `recruitment.assignee` | `contextSlots.assignee` |
| Stage / decision JSX | Recruitment Application | Application | `recruitment.stage` / widget `decision_zone` | `resolveRecruitmentApplicationDecision` |
| Contacts chrome in rail | Recruitment Application | Application | widget `contacts` / `identity_header` | `contextSlots.contacts` |

---

## Named kit gaps (do not invent locally)

`filter_bar` · `modal` · `checkbox` · `radio` · `toggle` — listed in `KIT_WIDGET_GAP_IDS`. A module must not ship a private version while the gap is unnamed-unfilled.

---

## Proof screen must not add a row

G4 (next slice) binds Recruitment Application through the kit + contributions. If the page invents a local type, field, primitive, widget, or table — including “RODO here, comments there, stage below” in parent JSX — G4 fails.

This feat does **not** rewrite that panel.
