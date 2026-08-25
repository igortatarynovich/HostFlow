# Communication Context — C3 Module-owned Policy Ports

**Status:** **COMPLETE** (implementation)  
**Parent gate:** [`intake-communication-context-c1-c6-gate.md`](intake-communication-context-c1-c6-gate.md)  
**Prerequisite:** C2 Communication Context Resolver **COMPLETE** (`#72`)  
**Unlocks:** C4 Template Metadata Enforcement  

---

## Question C3 answers

> Is this `communication_purpose` allowed for this module-owned result context?

```text
CommunicationContext
→ published communication policy contract
→ module-owned policy adapter
→ allow / deny
```

---

## Ownership

| Layer | Owns | Does not own |
|-------|------|--------------|
| Shared communications | contract shape, gate, fail-closed, decision id | purpose lists, module business rules, templates |
| Recruitment adapter | Recruitment purposes | Sales policy / Sales ORM |
| Sales adapter | Sales purposes | Recruitment policy / Recruitment ORM |

### Example purposes (module-owned)

| Recruitment | Sales |
|-------------|-------|
| `submission_acknowledgement` | `submission_acknowledgement` |
| `additional_information_request` | `qualification_questionnaire_request` |
| `interview_invitation` | `meeting_invitation` |
| `document_request` | `proposal_follow_up` |

---

## Contract

**Request:** `module_owner` · `result_type` · `result_id` (opaque) · `communication_domain` · `communication_purpose` · `channel` · `locale` · optional `actor_context` · `resolver_version`

**Decision:** `allowed` · `reason_code` · `policy_owner` · `policy_version` · `decision_id`

---

## Rules

- No adapter → deny (no Recruitment fallback)  
- Unknown purpose → deny  
- Incompatible module/purpose → deny  
- Unknown channel → deny  
- Shared layer has **no** hardcoded Recruitment/Sales purpose lists  
- Modules do not import each other's policy  

---

## Acceptance

`sales` + `sales_inquiry` + `qualification_questionnaire_request` → **allow**  
Same context + `recruitment_submission_acknowledgement` → **deny** (any form/locale/UI/Lead/path)

---

## History

- 2026-07-19: C3 implemented after C2 `#72`.
