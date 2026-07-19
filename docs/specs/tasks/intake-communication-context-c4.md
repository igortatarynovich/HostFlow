# Communication Context — C4 Template Metadata Enforcement

**Status:** **COMPLETE** (implementation)  
**Parent gate:** [`intake-communication-context-c1-c6-gate.md`](intake-communication-context-c1-c6-gate.md)  
**Prerequisite:** C3 Policy Ports **COMPLETE** (`#73`)  
**Unlocks:** C5 Send-path migration  

---

## Role

Backend enforcement only:

```text
CommunicationContext + Template metadata → allow | deny + reason_code
```

**Template never defines context. Context defines template eligibility.**

C4 does **not**: find · pick · fallback · substitute locale/purpose/module · touch destination ORM.

---

## Metadata SoT (`CommunicationTemplateMetadata`)

| Field | Role |
|-------|------|
| `template_id` · `template_version` | identity |
| `module_owner` · `communication_domain` · `communication_purpose` | eligibility |
| `supported_channels` · `supported_locales` | channel/locale gates |
| `lifecycle_status` | `active` only |
| `policy_version` | policy stamp |

Not SoT: template name · catalog folder · UI label.

---

## Mandatory checks

Match all of: `module_owner` · `communication_domain` · `communication_purpose` · `channel` · `lifecycle_status` · optional `template_version` · locale when provided.

Any mismatch → fail-closed. No Recruitment / candidate / “similar purpose” fallback.

---

## Acceptance

| Case | Result |
|------|--------|
| SalesInquiry + sales + `qualification_questionnaire_request` + Sales template | allow |
| Recruitment template for SalesInquiry | deny |
| Candidate acknowledgement for Sales | deny |
| Sales template for Application | deny |
| Purpose mismatch | deny |
| Archived / disabled | deny |
| Missing/unknown template | deny |
| Other `module_owner` | deny |
| Incompatible channel | deny |

---

## History

- 2026-07-19: C4 implemented after C3 `#73`.
