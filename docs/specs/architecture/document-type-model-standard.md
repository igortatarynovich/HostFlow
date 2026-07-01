# Document Type Model Standard (HostFlow)

## Status
Proposed (normative standard for system `document_type` object).

## Problem
`Document type` cannot be a plain label field. In HostFlow it must be a rule-bearing system object used by Recruitment, HR, legal stay/work permit processing, payroll onboarding, driver compliance, fleet readiness, reminders, and analytics.

## Core Principle
A document type answers:
- what this document is,
- why it exists,
- where it applies,
- what data matters,
- what compliance/eligibility impact it has,
- which automation and verification rules it triggers.

Not just "how it is named".

## Canonical Structure (mandatory blocks)

### 1) Identity
- `code` (canonical system code)
- `public_name`
- `local_names` (i18n dictionary)
- `country_scope` (`global|country_specific|country_group`)
- `category`
- `subcategory`
- `status` (`draft|active|deprecated`)
- `origin` (`system|tenant_custom|requested`)

Example canonical codes:
- `passport`, `driver_license`, `work_permit`, `residence_card`, `zus_zua`, `employment_contract`, `medical_certificate`, `psychotest`, `tachograph_card`, `code_95`.

### 2) Category
Allowed top-level categories:
- `identity`
- `immigration`
- `work_authorization`
- `driver_qualification`
- `medical`
- `employment`
- `payroll`
- `tax`
- `social_security`
- `client_specific`
- `internal_hr`
- `fleet_compliance`
- `other`

### 3) Country Applicability
- `applicability_scope` (`global|country_specific|country_group`)
- `issuing_country_rules`
- `work_country_rules`
- `residence_country_rules`
- `country_codes[]` and/or `country_group_codes[]`

Examples:
- passport: global
- `zus_zua`: Poland-specific
- `code_95`: EU group + transport profile
- work permit: country-specific variants under shared category

### 4) Business Purpose
`business_purposes[]` (multi-value):
- `identification`
- `legal_stay`
- `right_to_work`
- `employment_formalization`
- `payroll_setup`
- `driver_compliance`
- `client_onboarding`
- `internal_record`
- `renewal_tracking`

### 5) Required Fields Schema
- versioned schema of extracted/verified fields
- field types, required flags, validation constraints

Examples:
- passport: number, first_name, last_name, birth_date, citizenship, issue_date, expiry_date, issuing_country
- driver license: number, categories, issue_date, expiry_date, issuing_country
- zus_zua: submission_date, registration_date, status, reference_number
- employment contract: contract_type, start_date, end_date, employer, rate, currency, work_regime

### 6) Expiry & Renewal Rules
- `has_expiry`
- `expiry_required`
- `reminder_days[]`
- `can_work_after_expiry`
- `blocks_candidate`
- `blocks_employee`
- `renewal_flow_required`

### 7) Compliance Criticality
- `criticality`: `informational|operational|required|compliance_critical|work_blocking`

UI must prioritize by criticality, not show flat equal list.

### 8) Entity Applicability
`entity_types[]`:
- `candidate`, `employee`, `client`, `vacancy`, `vehicle`, `company`, `assignment`, `contract`, `payroll_profile`

### 9) Stage Applicability
`stage_rules[]` for module lifecycles.

Recruitment examples:
- after interest
- before client submission
- before arrival
- before HR handoff

HR examples:
- before contract sign
- before work start
- before payroll activation
- before first trip
- periodic renewal

### 10) Role / Position Applicability
`position_profiles[]`:
- `driver`, `warehouse_worker`, `mechanic`, `dispatcher`, `office_worker`, `subcontractor`

### 11) Automation Flags
- `affects_eligibility`
- `affects_handoff`
- `affects_payroll`
- `affects_reminders`
- `affects_client_submission`
- `affects_fleet_readiness`
- `requires_manual_verification`
- `supports_ocr_extraction`
- `supports_e_signature`

### 12) Verification Profile
Defines the verification playbook (whole-document decision flow):
- `check_personal_data_match`
- `check_expiry_validity`
- `check_category_or_class`
- `check_issuing_country`
- `check_right_to_work`
- `check_vacancy_fit`
- `manual_review_required`
- `integration_verification_supported`

UX invariant:
- verifier opens document, checks key points, confirms/rejects document as one unit.

### 13) Versioning
- `document_type_version`
- `valid_from`
- `valid_to`
- `deprecation_reason`
- `replacement_document_type_code`

Historical instances keep their original type version context.

### 14) Tenant Overrides (limited)
Allowed:
- enable/disable
- mark required (within legal bounds)
- reminder tuning
- internal instructions
- client-specific addendum requirement
- responsible role mapping

Forbidden:
- semantic changes of system meaning
- changing compliance criticality class
- reclassifying custom doc into legal work permit/visa/passport equivalents
- creating canonical duplicates

### 15) Custom Document Policy
- default `strict`: no direct tenant creation, only requests
- optional `limited`: max 2 active custom types per tenant (platform-enabled)
- hard deny-list for legal/compliance-critical document families

## Instance Lifecycle (separate from type)
Type defines allowed state machine; instance executes it.

Baseline instance states:
- `requested`
- `uploaded`
- `extracted`
- `verification_required`
- `verified`
- `rejected`
- `expired`
- `renewal_required`
- `archived`

## Normative JSON Contract (v1)
```json
{
  "code": "work_permit",
  "public_name": "Work Permit",
  "local_names": {"en": "Work Permit", "pl": "Zezwolenie na pracę"},
  "status": "active",
  "origin": "system",
  "category": "work_authorization",
  "subcategory": "national_work_permit",
  "country_applicability": {
    "applicability_scope": "country_specific",
    "country_codes": ["PL"],
    "country_group_codes": []
  },
  "business_purposes": ["right_to_work", "renewal_tracking"],
  "required_fields_schema": {
    "version": "1.0.0",
    "required": ["permit_type", "issue_date", "expiry_date", "issuing_country"],
    "properties": {
      "permit_type": {"type": "string"},
      "issue_date": {"type": "string", "format": "date"},
      "expiry_date": {"type": "string", "format": "date"},
      "issuing_country": {"type": "string", "minLength": 2, "maxLength": 2}
    }
  },
  "expiry_rules": {
    "has_expiry": true,
    "expiry_required": true,
    "reminder_days": [60, 30, 7],
    "can_work_after_expiry": false,
    "blocks_candidate": true,
    "blocks_employee": true,
    "renewal_flow_required": true
  },
  "compliance_criticality": "work_blocking",
  "entity_applicability": ["candidate", "employee"],
  "stage_applicability": ["pre_handoff", "pre_contract", "pre_work_start"],
  "position_applicability": ["driver", "warehouse_worker"],
  "automation_flags": {
    "affects_eligibility": true,
    "affects_handoff": true,
    "affects_payroll": false,
    "affects_reminders": true,
    "affects_client_submission": true,
    "affects_fleet_readiness": false,
    "requires_manual_verification": true,
    "supports_ocr_extraction": true,
    "supports_e_signature": false
  },
  "verification_profile": {
    "check_personal_data_match": true,
    "check_expiry_validity": true,
    "check_category_or_class": false,
    "check_issuing_country": true,
    "check_right_to_work": true,
    "check_vacancy_fit": true,
    "manual_review_required": true,
    "integration_verification_supported": false
  },
  "versioning": {
    "document_type_version": "2026.1",
    "valid_from": "2026-01-01",
    "valid_to": null,
    "deprecation_reason": null,
    "replacement_document_type_code": null
  },
  "tenant_override_policy": {
    "allow_enable_disable": true,
    "allow_required_toggle": true,
    "allow_reminder_override": true,
    "allow_internal_instruction": true,
    "allow_change_semantics": false,
    "allow_change_criticality": false
  }
}
```

## Implementation Mapping (current -> target)
Current columns and structures to map into the standard:
- `document_types.code/name/kind/requested_from/process_type/is_active`
- `document_types.metadata_schema/required_files/expiry_rule`
- `document_types.duplicate_policy/orderable`
- `document policies/rulesets` and eligibility gates

Target:
- canonical `ref_document_type` + versioned profiles + pack applicability + tenant overrides.

## Acceptance Criteria
- No module treats document type as free string.
- All legal/compliance-critical documents are system-owned canonical types.
- Runtime checklist resolution uses this model plus context/packs.
- UI exposes task-oriented flow, not global raw dictionary browsing.

## Implementation Spec Link
- `docs/specs/architecture/document-type-model-sql-orm-target.md`
