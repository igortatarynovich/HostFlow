# Relationships — contract inventory (confirmed slice)

**Hierarchy:** L2 — RelationshipKind contract + confirmed-slice rows; **not** a full CRM graph SoT  
**Decision record:** [`ADR-042`](../architecture/ADR-042-relationships.md)  
**Parent model:** [`ADR-038`](../architecture/ADR-038-platform-standardization-model.md) · [`platform-standardization-model.md`](platform-standardization-model.md) (area `relationships`)  
**Related:** [`object-kind-catalog.md`](object-kind-catalog.md) · [`ADR-009`](../architecture/ADR-009-document-hub-platform-layer.md) · [`ADR-012`](../architecture/ADR-012-activity-notification-operating-layer.md) · activity-notification operating layer  
**Owner:** Platform architecture + Architecture canon  
**Slice:** Documents / Object Kind links + proven handoff / assignment / Activity binding / Communications C1 opaque result

---

## 1. Row contract

| Field | Meaning |
|-------|---------|
| `relationship_kind` | Flat `stable_code` (vocabulary — not a table name) |
| `source_kind` | Source object / entity kind |
| `target_kind` | Target object / entity kind or opaque-ref kind |
| `cardinality` | Association cardinality (descriptive) |
| `ownership` | Who owns the relationship SoT |
| `requiredness` | Mandatory vs optional for ends |
| `lifecycle_dependency` | Tie to source/target lifecycle |
| `deletion_policy` | Intended delete behaviour |
| `visibility` | Who may see the edge |
| `writers` | Who may mutate the edge |
| `status` | `confirmed` \| `fragment` |
| `sot_refs` | Evidence paths (implementation may differ from kind code) |
| `notes` | Naming drift, MVP limits, forbidden mixes |

---

## 2. Rules summary (from ADR-042)

1. RelationshipKind is **vocabulary**, not a FK/table description.
2. Fill all contract fields; do not invent kinds without evidence.
3. Relationship ≠ Field/DataType ≠ Permission ≠ Activity pointer alone ≠ Process lifecycle state.
4. `thread_opaque_result` targets an **OpaqueResultRef**, not a new domain entity.
5. Unconfirmed edges stay **`fragment` / out_of_slice** — do not complete the CRM graph here.
6. No runtime migration in this PR.

---

## 3. Confirmed slice (`status=confirmed`)

| relationship_kind | source_kind | target_kind | cardinality | ownership | requiredness | lifecycle_dependency | deletion_policy | visibility | writers | sot_refs | notes |
|-------------------|-------------|-------------|-------------|-----------|--------------|----------------------|-----------------|------------|---------|----------|-------|
| `document_reused_for_hr` | `document` | `workforce_employee` | 1:N (doc→many links; unique per tenant/doc/type/id/relation) | Document Hub | optional | follows document; link removed if document deleted (FK CASCADE observed) | cascade with document | tenant / HR operational context consumers | Workforce / HR operational context writers (MVP) | `document_entity_links`, `workforce_hr_operational_context.py`, ADR-009 | Live MVP often stores `relation_type=reused_for_hr`; ADR-009 target wording `reused_for_employment` — naming drift, not a second kind |
| `document_primary_owner` | `document` | owner entity (`candidate` / … per Hub) | 1:1 semantic (primary) | Document Hub | required for Hub passport semantics | follows document | cascade with document | tenant / owning module | Document Hub writers | ADR-009 Document Link; `document_data_contract.py` (`relation_type` e.g. `primary`) | Confirmed as Hub contract; full generic links CRUD may be incomplete |
| `document_dossier_share` | `document` | `user` (share grant) | 1:N | Documents / Hub share model | optional | follows document / grant revoke | revoke/delete grant row | grant principals + admins | Documents share APIs | `document_dossier_share` model | Access **grant** typed as visibility relationship — not a Permission catalog entry |
| `activity_related_to` | `activity` | closed entity set (candidate, lead, company, vacancy, document, …) | N:1 (activity→one related) | Activity / Notifications (ADR-012) | required on Activity | independent of target delete (soft ref — orphan risk) | soft / retain pointer | role-scoped activity consumers | producing modules via Activity API | `activity.related_entity_type/id`, ADR-012, activity-notification operating layer §2.5 | **Binding kind** for work items; does not replace typed Document Link kinds |
| `candidate_assigned_to_vacancy` | `candidate` | `vacancy` | N:M | Recruitment | optional (process-dependent) | assignment row has own status dimension | restrict/archive per assignment rules | recruitment roles | Recruitment assignment writers | `assignment` / `candidate_vacancy` model | Confirmed assignment edge; status values are **not** this kind |
| `candidate_handoff_to_destination` | `candidate` | destination (`company` / client / HR context per handoff contract) | 1:N over time | Recruitment / handoff | process-required when handoff fires | edge participates in handoff workflow; lifecycle state separate | retain for audit | agency/client visibility per handoff | Handoff writers | `candidate_handoff`, handoff-contract.md | Kind = transfer association; PE/handoff **states** stay in States / Process |
| `thread_origin_entity` | `communication_thread` | origin entity (polymorphic) | 1:N (multi-link allowed) | Communications | optional / product-required per flow | follows thread | cascade/restrict per Comms policy | thread participants | Communications | `communication_thread_entity_link` | Origin binding for G13 — not opaque result |
| `thread_opaque_result` | `communication_thread` | **OpaqueResultRef** (`module_owner` + `result_type` + `result_id`; optional ledger provenance) | 1:1 per thread (unique tenant+thread) | Communications (C1) | optional until confirmed | independent of domain ORM rows (no FK to Application / SalesInquiry) | retain / unresolved status on link | thread participants / owning module | Communications C1 writers | `communication_thread_result_links`, model docstring | **Not a domain entity.** Target is an opaque external/result handle only; `unresolved`/`confirmed` are link statuses, not ObjectKinds |

---

## 4. Fragment / out_of_slice (do not invent)

Listed for awareness only — **no full contract rows** in this PR:

| Evidence | Why not confirmed here |
|----------|------------------------|
| `tenant_links` (agency↔client) | Tenancy topology; may become `agency_client_tenant_link` later — needs ownership card clarity |
| `calendar_items.linked_entity_*` / provider sync links | Soft calendar binding + sync plumbing; not Object Kind Documents slice |
| Embedded FKs (`candidate.vacancy_id`, etc.) | Ownership refs — usually not first-class RelationshipKinds |
| Notification `related_entity_*` | Parallel soft pointer to Activity; fold under Activity/Notification operating layer first |
| Pack / requirement “links” to DocumentType codes | Reference composition, not instance relationships |
| Field `reference_code` → reference domain | DataType / Field Registry (ADR-041), not RelationshipKind |

---

## 5. Forbidden mixes (quick check)

| If you are about to… | Use instead |
|----------------------|-------------|
| Add a new `field_type` for “link to X” | Field + `reference_code` / DataType, or register a RelationshipKind for instance edges |
| Store cross-module file copies | Document Link kinds (`document_*`) — ADR-009 no-copy |
| Treat handoff status as a relationship_kind | State dimension / ProcessRule |
| Promote OpaqueResultRef to Application entity | Keep `thread_opaque_result`; resolve via owning module |

---

## 6. History

- 2026-08-13: Initial L2 RelationshipKind contract inventory under ADR-042; confirmed Documents + handoff/assignment/Activity/Comms C1 slice; CRM graph deferred; area `relationships` → exists.
