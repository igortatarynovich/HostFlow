# REF-UI-000 — COMPONENT_REGISTRY (Prefill)

Source: frontend code inventory (`src/pages`, `src/components`)  
Scope: audit sprint 1 (component-first)  
Last updated: 2026-05-29

Notes:
- This is inventory only, not canonical approval.
- `status` follows registry lifecycle (`Candidate/Canonical/Legacy/Deprecated`).
- `audit_state` tracks review progress (`Not Audited/Audited/Validated`).

| component_id | component_type | variant | pages | usage_count | module_coverage | owner | dependency_links | criticality | business_criticality | replacement_cost | status | audit_state | notes |
|---|---|---|---|---:|---|---|---|---|---|---|---|---|---|

## 1. Tables (P0)

| component_id | component_type | variant | pages | usage_count | module_coverage | owner | dependency_links | criticality | business_criticality | replacement_cost | status | audit_state | notes |
|---|---|---|---|---:|---|---|---|---|---|---|---|---|---|
| table_candidates_main_v7 | Table | Entity List Table | `/app/candidates` | 1 | Recruitment | Recruitment | candidates hooks + saved views + DnD columns | high | P0 | high | Candidate | Audited | Baseline candidate for `TABLE_V1`; audit artifact: `REF-UI-000-table_candidates_main_v7.audit.md`; final canon lock blocked pending cross-table comparison |
| table_vacancies_list | Table | Entity List Table | `/app/vacancies` | 1 | Recruitment | Recruitment | vacancies list state | high | P0 | medium | Candidate | Audited | Comparative audit: `REF-UI-000-table_vacancies_main.audit.md`; benchmark delta vs candidates: -4 |
| table_companies_list | Table | Entity List Table | `/app/clients/directory`, `/app/clients/:id` | 1 | Recruitment | Recruitment | Companies page local state | high | P1 | high | Candidate | Audited | Comparative audit: `REF-UI-000-table_companies_main.audit.md`; benchmark delta vs candidates: -18 |
| table_leads_workspace | Table | Entity List Table | `/app/leads` | 1 | Recruitment | Recruitment | leads workspace modes | high | P1 | high | Candidate | Audited | Comparative audit: `REF-UI-000-table_leads_main.audit.md`; benchmark delta vs candidates: -10 |
| table_hr_employees | Table | Entity List Table | `/app/hr/employees` | 1 | HR | HR Operations | hr workspace state | high | P1 | medium | Candidate | Audited | Comparative audit: `REF-UI-000-table_employees_main.audit.md`; benchmark delta vs candidates: -11 |
| table_documents_registry | Table | Reference Table | `/app/documents` | 1 | Documents | Document Operations | documents registry state | medium | P1 | medium | Candidate | Not Audited | Registry style table |
| table_audit_log_admin | Table | Audit Table | `/app/settings/audit` | 1 | Admin | Platform Admin | audit log query | medium | P2 | low | Candidate | Not Audited | Audit/history canonical candidate |
| table_automation_log | Table | Audit Table | `/app/automation-log` | 1 | Operations | Operations | automation log query | medium | P2 | low | Candidate | Not Audited | Similar intent to audit table |
| table_users_admin | Table | Reference Table | `/app/settings/users` | 1 | Admin | Platform Admin | `UserTable` component | medium | P2 | medium | Candidate | Not Audited | Shared component in admin domain |
| table_services_orders | Table | Workspace Table | `/app/services`, `/app/orders` | 1 | FinanceOps | Finance Operations | services workspace tabs | medium | P1 | high | Candidate | Not Audited | Multiple table blocks in one page |
| table_invoices_main | Table | Workspace Table | `/app/invoices` | 1 | FinanceOps | Finance Operations | invoices state | medium | P1 | medium | Candidate | Not Audited | Candidate for finance list standard |
| table_do_procesowania | Table | Workspace Table | `/app/procesowani` | 1 | Recruitment | Recruitment | advanced filters + bulk actions | high | P1 | high | Candidate | Not Audited | Heavy operations table with local persistence |
| table_hr_zus_workspace | Table | Workspace Table | `/app/hr/zus-workspace` | 1 | HR | HR Operations | zus workspace | high | P1 | medium | Candidate | Not Audited | Operational dense table |
| table_meta_leads_admin_group | Table | Reference Table | `/app/settings/integrations/meta` | 6 | Admin | Platform Admin | one page, many table variants | medium | P2 | high | Candidate | Not Audited | High risk of table proliferation inside one page |

## 2. Detail Cards (P0)

| component_id | component_type | variant | pages | usage_count | module_coverage | owner | dependency_links | criticality | business_criticality | replacement_cost | status | audit_state | notes |
|---|---|---|---|---:|---|---|---|---|---|---|---|---|---|
| detail_candidate_card | Detail Card | Entity Card | `/app/candidates/:id`, `/app/candidates/:id/:tab` | 1 | Recruitment | Recruitment | large page + nested sections | high | P0 | high | Candidate | Audited | Primary UX Benchmark for Sprint 2; audit artifact: `detail_candidate_card.audit.md`; recommendation: Adapt |
| detail_vacancy_card | Detail Card | Entity Card | `/app/vacancies/:id`, `/app/vacancies/:id/:tab` | 1 | Recruitment | Recruitment | `VacancyDetailRoute` + `VacancyDetail` | high | P0 | high | Candidate | Not Audited | Must be diffed against candidate card |
| detail_company_card | Detail Card | Entity Card | `/app/clients/:id`, `/app/clients/:id/:tab` | 1 | Recruitment | Recruitment | Companies mixed list/detail page | high | P1 | high | Candidate | Not Audited | High complexity with role-specific sections |
| detail_employee_card | Detail Card | Entity Card | `/app/hr/employees/:employeeId` | 1 | HR | HR Operations | HR review + docs panels | high | P1 | high | Candidate | Not Audited | HR-specific detail variation |
| detail_lead_card | Detail Card | Entity Card | `/app/leads/:leadId` | 1 | Recruitment | Recruitment | lead intake/review modes | high | P1 | high | Candidate | Not Audited | Separate detail paradigm to compare |

## 3. Filter Bars (P0)

| component_id | component_type | variant | pages | usage_count | module_coverage | owner | dependency_links | criticality | business_criticality | replacement_cost | status | audit_state | notes |
|---|---|---|---|---:|---|---|---|---|---|---|---|---|---|
| filterbar_candidates_workspace | Filter Bar | Multi-filter + saved view | `/app/candidates` | 1 | Recruitment | Recruitment | saved views + table layout | high | P0 | high | Candidate | Not Audited | Prime candidate for `FILTER_BAR_V1` |
| filterbar_do_procesowania | Filter Bar | Header + column filter menus | `/app/procesowani` | 1 | Recruitment | Recruitment | URL + local storage table state | high | P1 | high | Candidate | Not Audited | Different pattern: column filter menus |
| filterbar_leads_workspace | Filter Bar | Workspace filters | `/app/leads` | 1 | Recruitment | Recruitment | table/kanban dual mode | high | P1 | medium | Candidate | Not Audited | Needs behavior mapping |
| filterbar_dashboard | Filter Bar | Dashboard filters | `/app/overview` | 1 | Overview | Product | dashboard widgets | medium | P2 | medium | Candidate | Not Audited | Analytics-style filter bar |
| filterbar_hr_documents | Filter Bar | Queue filters | `/app/hr/documents*` | 1 | HR | HR Operations | hub mode tabs + filters | medium | P1 | medium | Candidate | Not Audited | HR document queue behavior |

## 4. Status Badges

| component_id | component_type | variant | pages | usage_count | module_coverage | owner | dependency_links | criticality | business_criticality | replacement_cost | status | audit_state | notes |
|---|---|---|---|---:|---|---|---|---|---|---|---|---|---|
| badge_candidate_stage | Status Badge | Pipeline stage badge | candidates + candidate card | 2 | Recruitment | Recruitment | stage label helpers | high | P0 | medium | Candidate | Not Audited | Must align with pipeline color semantics |
| badge_lead_stage | Status Badge | Lead stage/status badge | leads + lead detail | 2 | Recruitment | Recruitment | lead pipeline utils | high | P1 | medium | Candidate | Not Audited | Candidate for shared stage badge rules |
| badge_document_status | Status Badge | Document state badge | documents + hr docs | 2 | Documents, HR | Document Operations | doc policy + verification | medium | P1 | medium | Candidate | Not Audited | Cross-module consistency risk |

## 5. Tabs

| component_id | component_type | variant | pages | usage_count | module_coverage | owner | dependency_links | criticality | business_criticality | replacement_cost | status | audit_state | notes |
|---|---|---|---|---:|---|---|---|---|---|---|---|---|---|
| tabs_candidate_card_main | Tabs | Entity detail tabs | `/app/candidates/:id/:tab` | 1 | Recruitment | Recruitment | candidate card sections | high | P0 | medium | Candidate | Not Audited | Anchor for detail tab behavior |
| tabs_vacancy_card_main | Tabs | Entity detail tabs | `/app/vacancies/:id/:tab` | 1 | Recruitment | Recruitment | vacancy detail tabs | high | P0 | medium | Candidate | Not Audited | Compare with candidate tabs |
| tabs_work_context | Tabs | Workspace tabs | `/app/work/*` | 1 | Operations | Operations | WorkAreaLayout + redirects | medium | P1 | low | Candidate | Not Audited | Shared workspace tab pattern |
| tabs_hr_workspace | Tabs | Workspace tabs | `/app/hr/*` | 1 | HR | HR Operations | HrWorkspaceLayout | medium | P1 | low | Candidate | Not Audited | HR workspace tab semantics |

## 6. Forms

| component_id | component_type | variant | pages | usage_count | module_coverage | owner | dependency_links | criticality | business_criticality | replacement_cost | status | audit_state | notes |
|---|---|---|---|---:|---|---|---|---|---|---|---|---|---|
| form_candidate_detail_sections | Form | Entity form sections | candidate card | 1 | Recruitment | Recruitment | section-level save patterns | high | P0 | high | Candidate | Not Audited | Baseline for entity edit behaviors |
| form_company_detail_sections | Form | Entity form sections | companies detail | 1 | Recruitment | Recruitment | large mixed form model | high | P1 | high | Candidate | Not Audited | High schema complexity |
| form_vacancy_detail_sections | Form | Entity form sections | vacancy detail | 1 | Recruitment | Recruitment | vacancy profile integration | high | P1 | medium | Candidate | Not Audited | Candidate for shared entity form contract |
| form_invoice_create | Form | Transaction form | `/app/invoices/new`, `/app/invoices/:id/edit` | 1 | FinanceOps | Finance Operations | invoice create/update flows | medium | P1 | medium | Candidate | Not Audited | Distinct business form family |

## 7. Modals

| component_id | component_type | variant | pages | usage_count | module_coverage | owner | dependency_links | criticality | business_criticality | replacement_cost | status | audit_state | notes |
|---|---|---|---|---:|---|---|---|---|---|---|---|---|---|
| modal_candidate_change_log | Modal | Entity history modal | candidate card | 1 | Recruitment | Recruitment | change log API | medium | P1 | low | Candidate | Not Audited | Candidate for `Modal L` |
| modal_bulk_actions_confirm | Modal | Confirm modal | candidates, procesowani, leads | 3 | Recruitment | Recruitment | bulk action handlers | high | P1 | medium | Candidate | Not Audited | Must standardize confirm UX |
| modal_calendar_event_detail | Modal | Detail modal | `/app/calendar` | 1 | Operations | Operations | calendar event state | medium | P2 | medium | Candidate | Not Audited | Example of domain detail modal |
| modal_services_order_ops | Modal | Edit/confirm modal | `/app/services` | 1 | FinanceOps | Finance Operations | service order workflow | medium | P1 | medium | Candidate | Not Audited | Domain-specific modal family |

## Sprint 1 Working Rules

1. No canonical approval during prefill.
2. First audit pass must complete `Tables`, `Detail Cards`, `Filter Bars`.
3. For each table in pass 1, fill explicit fields in notes:
   - columns
   - filters
   - sorting
   - bulk actions
   - pagination
   - deviation from Candidates List
4. `audit_state` progression only: `Not Audited -> Audited -> Validated`.
