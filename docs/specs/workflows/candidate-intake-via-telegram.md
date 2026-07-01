# Candidate Intake via Telegram (Meta -> WhatsApp -> Telegram -> CRM)

## Goal
Build a clear and scalable candidate flow where:
- Meta channels (`whatsapp`, `messenger`, `instagram`) are used for first contact only;
- full candidate intake (questions, agreements, documents) is completed in Telegram;
- CRM remains the single source of truth without duplicated fields between intake and candidate card.

## Channel Contract

### 1) Meta channels (entry)
Purpose:
- fast first response;
- qualification and routing;
- transfer interested lead to Telegram.

Allowed actions:
- short scripted communication;
- transfer CTA to Telegram;
- manager notes / tags.

Not allowed:
- full questionnaire in channel chat;
- document collection in channel chat.

### 2) Telegram (intake and document completion)
Purpose:
- complete candidate questionnaire;
- collect required agreements;
- upload/scan required documents;
- update candidate status in CRM in near real time.

### 3) CRM (single source of truth)
Purpose:
- storage of all final candidate data;
- manager operations (assignment, stage transitions, quality control);
- audit trail for all updates.

Rule:
- no business-critical field may have two independent entry points with equal priority.

## Data Ownership and Anti-Duplication Rule

For each field we must define:
- `field_code`: stable identifier;
- `owner`: `candidate` | `manager` | `system`;
- `source_of_truth`: `telegram_intake` | `manager_card` | `system`;
- `required_stage`: stage where field becomes mandatory;
- `editable_by`: who can edit after initial fill;
- `purpose`: why field exists.

If candidate already filled the field in Telegram:
- candidate card shows it as read/verified;
- manager can override only with explicit reason (audit event).

## Canonical Field Matrix (MVP)

### Identity and Contacts
| field_code | owner | source_of_truth | editable_by | required_stage | purpose |
|---|---|---|---|---|---|
| `first_name` | candidate | telegram_intake | candidate, manager | intake_started | identification |
| `last_name` | candidate | telegram_intake | candidate, manager | intake_started | identification |
| `phone` | candidate | telegram_intake | candidate, manager | intake_started | communication |
| `phone_country_code` | candidate | telegram_intake | candidate, manager | intake_started | dialing normalization |
| `email` | candidate | telegram_intake | candidate, manager | intake_started | status links, magic link, notices |
| `contacts.preferred_messenger` | candidate | telegram_intake | candidate, manager | intake_started | operator routing |

### Personal and Eligibility
| field_code | owner | source_of_truth | editable_by | required_stage | purpose |
|---|---|---|---|---|---|
| `personal.birth_date` | candidate | telegram_intake | candidate, manager | profile_data | legal checks |
| `personal.citizenship` | candidate | telegram_intake | candidate, manager | profile_data | document requirements |
| `personal.residency_status` | candidate | telegram_intake | candidate, manager | profile_data | legal routing |
| `personal.current_location` | candidate | telegram_intake | candidate, manager | profile_data | relocation logistics |
| `personal.in_poland` | candidate | telegram_intake | candidate, manager | profile_data | visa/workflow branching |

### Experience and Qualification
| field_code | owner | source_of_truth | editable_by | required_stage | purpose |
|---|---|---|---|---|---|
| `experience.years_ce` | candidate | telegram_intake | candidate, manager | profile_data | qualification |
| `experience.intl_experience` | candidate | telegram_intake | candidate, manager | profile_data | route fit |
| `experience.trailer_types[]` | candidate | telegram_intake | candidate, manager | profile_data | vacancy matching |
| `experience.route_types[]` | candidate | telegram_intake | candidate, manager | profile_data | vacancy matching |
| `personal.frigo_experience` | candidate | telegram_intake | candidate, manager | profile_data | specialization |
| `personal.has_adr` | candidate | telegram_intake | candidate, manager | profile_data | specialization |

### Employments (history)
| field_code | owner | source_of_truth | editable_by | required_stage | purpose |
|---|---|---|---|---|---|
| `employments[]` | candidate | telegram_intake | candidate, manager | profile_data | screening and verification |

### Agreements and Consents
| field_code | owner | source_of_truth | editable_by | required_stage | purpose |
|---|---|---|---|---|---|
| `agreements.general` | candidate | telegram_intake | candidate, manager (with reason) | before_submit | legal |
| `agreements.employer_share` | candidate | telegram_intake | candidate, manager (with reason) | before_submit | legal |
| `agreements.terms_acceptance` | candidate | telegram_intake | candidate, manager (with reason) | before_submit | legal |
| `agreements.cookies_accepted` | candidate | telegram_intake | candidate | optional | portal UX |

### Documents
| field_code | owner | source_of_truth | editable_by | required_stage | purpose |
|---|---|---|---|---|---|
| `documents.required_types[]` | system | system | system, manager | profile_data | policy enforcement |
| `documents.uploaded[]` | candidate | telegram_intake | candidate, manager | before_submit | candidate dossier |
| `documents.review_status` | manager | manager_card | manager | after_submit | QC/compliance |

### Operations (manager-only)
| field_code | owner | source_of_truth | editable_by | required_stage | purpose |
|---|---|---|---|---|---|
| `stage` | manager/system | manager_card/system | manager/system | any | process control |
| `assignee` | manager/system | manager_card/system | manager/system | any | workload/routing |
| `tags` | manager/system | manager_card | manager/system | any | triage/ops |
| `note` | manager | manager_card | manager | any | context |

## Telegram Intake Flow (Target)

### Entry paths
- `/start <token>` from CRM invitation;
- `/bind <email|phone>` for existing candidate link;
- transfer from WhatsApp script with one-click Telegram CTA.

### Guided flow
1. Resolve candidate link.
2. Compute missing required fields from profile/ruleset.
3. Ask only missing questions (skip completed).
4. Save each answer immediately to CRM.
5. Run document checklist and request missing files.
6. Open scanner via Telegram WebApp for required docs.
7. On completion: mark intake submitted and move candidate to next stage policy.

### Scanner in Telegram
- use existing public scanner web flow inside Telegram WebApp container;
- upload to current document storage pipeline;
- map uploaded files to required doc types;
- return progress to chat (remaining required docs count).

## WhatsApp/Messenger/Instagram Onboarding UX (3 languages)

Objective:
- every non-technical user must connect a channel without external help.

For each channel setup screen:
- Step 1: where to get each credential (with provider path).
- Step 2: where to paste it in CRM field.
- Step 3: click `Test` and read expected result.
- Step 4: copy `Webhook URL` + `Verify token` to provider console.

Mandatory UX rules:
- no ambiguous labels;
- inline examples near each field;
- localized help in `en`, `ru`, `pl`;
- explicit success/failure states with human-readable error and next action.

WhatsApp clarification (must be explicit in UI):
- `Phone number ID` is required (not human phone number like `+48...`).

## Required Backend/Frontend Changes

### A. Unified field catalog
- add tenant-aware catalog for intake/card fields (or use candidate profile config as canonical source);
- include ownership/source/edit rules per field;
- expose API consumed by both Telegram intake renderer and candidate card sections.

### B. Intake rendering
- render questionnaire dynamically from unified field catalog;
- field-level completion state and skip logic for already filled values;
- strict mapping from answer to canonical candidate field.

### C. Candidate card deduplication
- remove duplicate inputs for candidate-owned fields already collected in intake;
- keep manager override with mandatory reason and audit log entry.

### D. Telegram orchestration
- add step engine for question order and validation;
- integrate scanner launch + callback completion;
- add retry and resume from last incomplete step.

### E. Audit and observability
- for each field write: `who`, `source`, `old_value`, `new_value`, `reason`;
- metrics: completion rate, drop-off by step, duplicate override rate, document completion lead time.

## Acceptance Criteria

1. Candidate can be fully processed in Telegram:
- all required profile fields collected;
- all required consents captured;
- required docs uploaded via scanner;
- intake status becomes `submitted`.

2. No duplicated mandatory fields between Telegram intake and candidate card:
- manager sees candidate-filled values as read-only by default;
- override requires reason and is audited.

3. Channel onboarding clarity:
- WhatsApp/Messenger/Instagram setup wizard available and localized in `en/ru/pl`;
- user can complete setup by following in-product instructions only.

4. Business workflow:
- lead starts from Meta channel;
- interested lead is transferred to Telegram;
- further structured communication and data collection stay in Telegram + CRM.

## Rollout Plan

### Phase 1 (design lock, 1-2 days)
- finalize canonical field matrix and ownership;
- map current DB fields (`candidates`, `intake_state`, `documents`) to catalog.

### Phase 2 (foundation, 3-5 days)
- implement unified field catalog APIs;
- adapt candidate card to catalog-driven rendering and deduplication.

### Phase 3 (Telegram intake runtime, 4-7 days)
- step engine, answer persistence, resume logic;
- scanner handoff and document completion loop.

### Phase 4 (channel setup UX, 2-3 days)
- guided setup wizard for WhatsApp/Messenger/Instagram;
- full localization and actionable troubleshooting messages.

## Open Decisions
- Keep catalog in `candidate_profiles.config` vs dedicated `candidate_field_catalog` table.
- Level of manager override permissions by role.
- Automatic stage transition policy after intake/doc completion per tenant/profile.
