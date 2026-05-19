# HR Data & Document Verification Workspace (PR10–PR11)

**Status:** Accepted (implemented).  
**Related:** [Employment Case Workspace](hr-employment-case-workspace.md), [Verified Fields](hr-verified-fields-model.md), [Document verification (PR3)](hr-review-task-priority-v1.md#pr-3--document-verification-cards-), [Handoff snapshot](../architecture/hr-inbox-queue-api.md).

---

## Goal

One **primary HR work surface** for pre-approve review:

- HR **confirms or corrects** recruiter-provided values against documents.
- HR does **not** re-enter data from scratch when values already exist at handoff.
- Documents are linked **per field row**, not as three competing full-page lists.

---

## BFF: unified read-model

On `HrReviewPanelOut` (employee + handoff `GET …/hr-review`):

| Field | Purpose |
|-------|---------|
| `data_verification_items[]` | One row per `field_code` (deduped across document cards) |
| `data_verification_summary` | Counts: verified / pending / missing / critical / identity status |

Built by `hr_data_verification.py` after document enrichment + verified-fields attach.

### Item shape (`HrDataVerificationItemOut`)

| Field | Meaning |
|-------|---------|
| `field_code`, `label` | Canonical field |
| `recruiter_value` | Primary display value (prefers `handoff.*` profile keys) |
| `recruiter_profile_values` | All non-empty sources (`handoff.candidate.citizenship`, `snapshot.*`, …) |
| `current_verified_value` | SoT after document verify / override |
| `source_document_type`, `source_document_label`, `document_open_url` | Primary linked doc |
| `status` | `pending` \| `verified` \| `overridden` \| `conflict` \| `missing` |
| `required_for_approval` | Critical field gate |
| `can_confirm`, `can_correct`, `can_request_info` | Row actions |

### Derived checklist

`identity_verified` is auto-satisfied when all **critical** verification rows are verified/overridden (`sync_checklist_from_data_verification`). Manual checklist remains for HR decision + eligibility; document cards still drive per-doc checklist keys via PR3 sync.

---

## Recruiter value sources (PR11)

Priority order in `FIELD_SPECS.profile_keys`:

1. **`handoff.candidate.*`** — immutable `candidate_handoff_snapshots.payload` at transfer (`hr_handoff_profile_context.py`)
2. `employee.*`, `eligibility.*`
3. `snapshot.*` — `workforce_employees.candidate_snapshot`
4. `document.*`, `context.*` — file / HR context metadata

Handoff namespace (v1 snapshot + live candidate at panel read):

- `handoff.candidate.*` — name, citizenship, email, phone from immutable snapshot
- `handoff.transport.*` — merged at `GET …/hr-review` from:
  - snapshot `documents[]` (`expires_at` per type)
  - live `Candidate.extra` / `personal_data` (`license_number`, `license_categories`, optional `code95_*` / `tacho_*`)

Transport field codes (no OCR):

| Field | Document key |
|-------|----------------|
| `driver_license_number`, `driver_license_categories`, `document_expiry` (license) | Driver license |
| `code95_number`, `code95_expiry` | Code95 |
| `tacho_card_number`, `tacho_card_expiry` | Tacho card |

---

## Document keys (approval + verification)

| `document_key` | Context types (HR bundle) | Typical fields |
|----------------|---------------------------|----------------|
| Legal stay | legal_stay, residence_permit, visa | full_name, citizenship, document_expiry |
| Work permit | work_permit, work_permit_application | full_name, work_country, permit_type |
| Red paper | red_paper, red_paper_certificate | full_name, pesel |
| Medical | medical, medical_certificate | full_name, exam_valid_until |
| Psychological | psychological, psychological_certificate | full_name, exam_valid_until |
| **Driver license** | driver_license, driver_license_code95 | number, categories, expiry |
| **Code95** | code95, driver_license_code95 | number, expiry |
| **Tacho card** | tacho_card, tachograph_card | number, expiry |

Catalog: `hr_verified_field_catalog.py` (`FIELD_SPECS`, `FIELD_CATALOG`).

---

## UI (review case layout)

**Main column (order):**

1. Hero  
2. `HrCurrentTaskPanel` — primary task; anchor **`#hr-data-verification`**  
3. **`HrDataVerificationWorkspace`** — unified table + compact identity strip  
4. `HrReviewPanelCard` — checklist + approve / return / reject only (`hideDocuments`)  
5. Supporting (collapsed): work eligibility, recruitment handoff summary  

**Removed as primary surfaces (review mode):**

- Separate `HrDocumentsForApproval` list  
- Separate `HrVerifiedFieldsPanel` table  
- Full `HrEmploymentIdentitySummary` grid (replaced by compact strip inside workspace)

**Right rail:** summary only — one blocker, data verification progress, identity status (no full blocker list).

---

## Write path (unchanged)

Row actions call existing APIs:

- Confirm / correct → `POST …/document-verifications/{key}/reviewed`
- Document verify / reject → collapsed **Document sign-off** section (PR3 cards)
- SoT override → `POST …/verified-fields/{field_code}/override`

No second persistence layer for verification items.

---

## Out of scope

- OCR / auto-fill from document PDF
- Finalization (send / sign / ePUAP)
- Contract preview UI (PR9 backend only until separate frontend PR)
