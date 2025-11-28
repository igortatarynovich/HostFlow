# Restructure Documents Module (HostFlow)

## Objective
Unify and reorganize the “Documents” module so that all candidate and employer documents — including process-based ones (visa, work permit, residence card) — are handled through one consistent interface, without duplicating logic or creating separate candidate types.

---

## Core Principles
- Keep the **existing upload interface** and build logic around it.
- Introduce **document templates** (sets of required docs) selectable directly in the **Documents** module.
- Automatically generate checklist items for a candidate based on the selected template.
- Each document belongs to one of three categories: `driver`, `employer`, or `process`.
- Each document has clear lifecycle statuses and owner responsibilities.
- Use one unified model for all documents, processes, and validations.
- **Template selection (template choice) is performed inside the Documents module itself, not in the vacancy.**

---

## Data Model Changes

### documents table (extended)
| Field | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `candidate_id` | UUID | Link to candidate |
| `company_id` | UUID | Link to employer (if applicable) |
| `kind` | enum: `driver`, `employer`, `process` | Defines ownership and grouping |
| `doc_type` | text | Machine name of document type |
| `custom_name` | text, nullable | Optional free-text name when `doc_type` = `other` |
| `status` | enum: `missing`, `requested`, `in_progress`, `received`, `approved`, `rejected`, `expired` | Workflow status |
| `issue_date` | date | Issue date |
| `expire_date` | date | Expiry date |
| `remind_days_before` | int | Reminder threshold |
| `owner_id` | UUID | Responsible recruiter or supervisor |
| `requested_from` | enum: `driver`, `employer`, `agency` | Who must provide it |
| `process_type` | enum: `none`, `work_permit`, `visa`, `pobyt_card` | Used only for process-type documents |
| `workflow` | JSON | Step-based tracking for processes |
| `files` | JSON[] | Uploaded files metadata |
| `meta` | JSON | Extra fields, numbers, issuer, notes, etc. |

### document_templates table
| Field | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `name` | text | Template name, e.g. “Driver CE Poland” |
| `vacancy_type` | enum | driver_ce, warehouse, mechanic, etc. |
| `documents` | JSON[] | List of required document types |
| `created_by` | UUID | Creator |
| `is_active` | bool | Controls availability |

> **Note:** Template selection happens **inside the Documents module** (top of the screen, dropdown “Select template”) — not in Vacancy.  
> **Also:** PESEL is a mandatory document across **all** templates and is auto-included even if not listed explicitly.

---

## Categories

1. **Driver Documents**
   - Passport / ID
   - Driver license
   - Qualification (Code 95)
   - Tachograph card
   - Medical certificate
   - Criminal record
   - Insurance / A1
   - Photo
   - Bank account confirmation
   - PESEL / registration proof — **for all vacancies/templates**
   - Other (custom) — free-name document, use \'other\' doc_type with \'custom_name\' filled

2. **Employer Documents**
   - Contract / Offer
   - Work assignment / Order
   - Insurance confirmation
   - A1 / Świadectwo kwalifikacji
   - BHP instruction
   - Accommodation / housing declaration

3. **Process-based Documents**
   - Work permit (A/B/C)
   - Visa (C/D)
   - Residence card (Karta pobytu)
   - Other country-specific permit workflows

Each process includes a JSON workflow with steps like:
`application_submitted → under_review → approved → received`.

### Process Tracking Enhancements

Many documents are not static but **undergo a process** before completion (visa, tachograph, driver license exchange, residence card, work permit, świadectwo kierowcy, etc.).  
Each process has its own lifecycle with sub-stages stored in the `workflow` JSON field and displayed in the UI as a progress bar.

Example `workflow` structures:
- **Visa (`visa`)**  
  `{ "applied_at": date, "interview_at": date, "approved_at": date, "received_at": date }`
- **Work Permit (`work_permit`)**  
  `{ "ordered_at": date, "submitted_at": date, "approved_at": date, "delivered_at": date }`
- **Tachograph Card (`tachograph_card`)**  
  `{ "applied_at": date, "received_at": date }`
- **Driver License Exchange (`driver_license_exchange`)**  
  `{ "submitted_at": date, "approved_at": date, "received_at": date }`
- **Residence Card (`residence_card`)**  
  `{ "applied_at": date, "fingerprints_at": date, "approved_at": date, "received_at": date }`
- **Świadectwo Kierowcy (`swiadectwo_kierowcy`)**  
  `{ "ordered_at": date, "issued_at": date, "delivered_at": date }`

Rules:
- When any sub-step is filled, the document automatically moves to `in_progress`.
- Once the final step date is filled, the document becomes `received` or `approved` (depending on configuration).
- Recruiters see next expected actions (e.g., “awaiting fingerprints”, “awaiting approval”) in the right sidebar Tasks.
- Reminders can be attached to intermediate steps to ensure deadlines (visa appointments, document collection, etc.).

---

## Status Flow
- missing → requested → in_progress → received → approved / rejected → expired
- Automatic transitions:
  - upload → received
  - expire_date reached → expired
  - process step completed → next step

---

## UI/UX Plan
- Preserve current upload list and “required docs” tags.
- Group documents by category (Driver / Employer / Process).
- Add a dropdown at the top: **“Select Template”** → applies document set to candidate.
- Show counters: `Driver docs 5/9`, `Employer docs 3/4`, `Processes 1/2`.
- Add filters: missing / in progress / expired.
- Keep file upload and approval interface unchanged.
- Each document row displays:
  - type, name, status, last checked, uploaded by, validity dates, and actions (Approve / Reject / Replace).
- "Select Template" always includes PESEL by default; it cannot be removed from the checklist.
- Button "Add custom document" (type: Other) → modal with name field + category + requested_from; creates a checklist item with doc_type=other and custom_name.
- Right sidebar (future): “Tasks” — upcoming expirations and requested documents.

---

## Automation and Reminders
- Background job checks `expire_date` daily and marks expired docs.
- Reminder system notifies recruiters `remind_days_before` expiry.
- For process documents — workflow deadlines (`step_due_at`) trigger alerts.

---

## Implementation Roadmap

**Phase 1: Data & Cleanup**
- Migrate existing document types, remove duplicates.
- Add fields `kind`, `process_type`, `requested_from`.
- Create table `document_templates` and seed with:
  - `driver_ce_template`
  - `warehouse_template`
- Enforce PESEL as required in every template (seed + API guard).
- Introduce 'other' doc_type with free-name (custom_name) and UI support.

**Phase 2: UI Grouping**
- Add category sections (accordion or tabs).
- Introduce template selector dropdown in Documents page.

**Phase 3: Logic & Workflows**
- Implement auto-generation of checklist items per template.
- Enable automatic status updates and reminders.

**Phase 4: Review & Optimization**
- Ensure full parity with old upload system.
- Test with driver and warehouse templates.
- Add filters, counters, and reminder jobs.

---

## Deliverables Checklist
- [ ] Updated DB schema & Alembic migration  
- [ ] document_templates table seeded with 2–3 templates  
- [ ] Document grouping in UI  
- [ ] Template selector in UI  
- [ ] Auto-creation of document checklist  
- [ ] Reminders for expiry and requested docs  
- [ ] Cleanup of duplicates (28 → ~15 unique)  
- [ ] Updated API documentation  
- [ ] Unit tests for template application and document status changes  
- [ ] PESEL enforced across all templates  
- [ ] 'Other' (custom) document flow with free-name and upload

---

## Success Criteria
- One unified document flow for all candidate types.
- Recruiters see at a glance which documents are missing, requested, or expired.
- Different job roles (driver, warehouse, etc.) use different templates, selectable in UI.
- No duplicated document names or manual document setup.
