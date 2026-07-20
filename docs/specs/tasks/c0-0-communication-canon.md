# C0.0 — Communication Canon & Contracts

**Status:** NORMATIVE (docs + contracts only; no production writers in this slice)  
**Date:** 2026-07-20  
**Parents:** [Sequential queue](sales-to-comms-sequential-queue.md) · [Epic C0](epic-c0-communication-integrity.md) · [C0.1 platform outbound](c0-1-platform-outbound.md) · [Epic C2](epic-c2-communication-campaigns.md)

> Short design gate before expanding the outbound foundation.  
> Fixes Source of Truth and boundaries so C0.1 does not become another module-specific questionnaire sender.  
> **Not** months of design: contracts only. Production alignment of C0.1 to this canon is a **separate** follow-up slice.

---

## 1. Scope and boundaries

### Communication is a platform capability

Communication owns:

- manual send  
- automatic send  
- templates  
- signatures  
- sender selection  
- links and public actions  
- threads and messages  
- deliveries / outbox  
- consents and communication limits  
- audit  
- mass / campaign communications  

### Product modules do not send

Sales, Recruitment, HR, and Services **must not** form or send email/SMS/WhatsApp themselves.  
They only express intent:

```text
Send a message to this object, in this business context, for this purpose.
```

Modules may:

- raise domain events  
- request a manual action (UI “Write”)  
- pass origin entity, purpose, recipient role, template key, link intents  

Modules must not:

- mint public URLs  
- call provider transport directly  
- maintain parallel “questionnaire / RODO / stage email” engines  
- embed template composition or channel policy in module code or frontend  

### In scope of this document

Contracts and ownership only:

1. Entity ownership  
2. Template model  
3. Communication command  
4. Link intent model  
5. Capability resolver  
6. Thread resolution  
7. Automation rule  
8. Consent / compliance  
9. Message snapshot  
10. Idempotency and transaction boundaries  

### Out of scope (later slices)

| Slice | Owns |
|-------|------|
| C0.1 (vertical + align-to-canon) | First writers through universal contracts |
| C0.2 | Inbound resolver |
| C0.3 | Delivery diagnostics |
| C1 | Inbox UX |
| C2 | Templates catalog UX, automations product, campaigns |
| Legal review | Exact RODO bases, retention periods, notice texts |

---

## 2. Entity ownership

| Entity / concept | Owner | Notes |
|------------------|-------|--------|
| `CommunicationThread` | Communication | Work-context primary; not address-primary |
| `CommunicationMessage` | Communication | Immutable snapshot after send |
| `CommunicationDelivery` | Communication | Provider/outbox state |
| `communication_thread_entity_link` (G13) | Communication | Durable `thread ↔ entity`; origin required when origin known |
| `CommunicationTemplate` (+ versions) | Communication | Registry; no baked public URLs |
| `LinkIntent` / public action tokens | Communication (`PublicActionLinkService`) | Created at prepare-send time |
| `CommunicationActionPolicy` | Communication (+ domain stage keys) | What actions/intents are allowed on a stage |
| `CommunicationAutomationRule` | Communication | Evaluates domain events; emits commands |
| Channel accounts / mailboxes | Communication | Provider config, limits |
| Signatures | Communication | Selection by tenant/company/mailbox/user/module/locale |
| Tenant communication settings | Communication | Locale, quiet hours, retention, branding |
| Compliance / consent evidence | Communication (permission layer) | Purpose-scoped; not a boolean on contact |
| Pipeline stages | Owning domain module | Know *what* should happen; not message text |
| Domain events | Owning domain module | Trigger input only |
| Questionnaire / form definitions | Forms / owning module | Link service chooses form; template does not hardcode URL |

**G13 rule:** convert may **add** a ClientAccount link; it must not erase the SalesInquiry (or other origin) link needed for history.

---

## 3. CommunicationCommand

Unified application entry for manual and automatic outbound:

```text
prepare_and_send_communication(command) → SendResult
```

Logical command fields:

| Field | Role |
|-------|------|
| `origin_entity_type` / `origin_entity_id` | Work context (mandatory when known) |
| `related_entities[]` | Extra G13 links (e.g. lead facade + inquiry) |
| `recipient` | Resolved person/address or role (`primary_contact`, …) |
| `channel` | `email` \| `sms` \| `whatsapp` \| … |
| `purpose` | `transaction` \| `workflow` \| `marketing` \| … |
| `template_key` **or** manual `content` | Exactly one composition path |
| `locale` | Rendering locale |
| `requested_link_intents[]` | Logical links to mint |
| `actor` **or** `automation_identity` | Who/what initiated |
| `idempotency_key` | Deduplicate retries |
| `correlation` / `source_event_id` | Trace to domain event / UI action |
| `channel_account_id` / sender preference | Optional override within policy |

**Pipeline inside the platform (normative order):**

1. Authorization  
2. Capability resolution  
3. Recipient resolution  
4. Policy / consent check  
5. Template version resolution (or accept manual content)  
6. Variable validation  
7. Public link generation (`PublicActionLinkService`)  
8. Signature resolution  
9. Thread resolution  
10. G13 linkage  
11. `CommunicationMessage` snapshot  
12. Delivery / outbox creation  
13. Audit  

Transport may run after the atomic unit (async worker); durable message + delivery + G13 must exist before “accepted”.

**Relation to PR #100 `send_communication`:** that API is a **vertical slice** approximating this command (origin, recipients, channel, content, G13, message, delivery). Aligning field names, consent, template/link/signature steps to this contract is a **follow-up C0.1 align slice**, not “foundation complete”.

---

## 4. CommunicationTemplate

Single registry. A template is a **contract**, not a pasted marketing email.

| Field | Purpose |
|-------|---------|
| `tenant_id` | Owner |
| `key` | Stable machine key |
| `name` | Operator-facing title |
| `channel` | email / SMS / WhatsApp |
| `purpose` | transaction / workflow / marketing |
| `subject_template` | Email subject (channel-dependent) |
| `body_template` | Body with variables |
| `supported_entity_types` | Where it may be applied |
| `required_variables` | Must be supplied |
| `optional_variables` | May be supplied |
| `link_intents` | Allowed logical links (not URLs) |
| `locale` | Language |
| `version` | Monotonic version |
| `status` | `draft` / `active` / `archived` |
| `created_by` | Author |
| `compliance_profile_id` | Consents / mandatory notices |

**Key principle:** templates **must not** store finished public URLs.  
They store intents, e.g.:

- `candidate_questionnaire`  
- `document_upload`  
- `application_continue`  
- `meeting_booking`  
- `offer_review`  
- `privacy_notice`  
- `unsubscribe`  
- `proposal_review`  
- `sales_questionnaire`  
- `client_onboarding`  

Concrete URLs exist only in the message snapshot after `PublicActionLinkService` runs.

---

## 5. LinkIntent

Logical name of a public action the message may include.

Contract properties (logical):

| Field | Purpose |
|-------|---------|
| `intent` | Stable key (see examples above) |
| `target_entity_type` / id | What the link acts on |
| `auth_mode` | anonymous token / login / etc. |
| `reuse_policy` | single-use / multi-use / reuse-if-valid |
| `ttl` | Expiry policy |
| `locale` | Optional |
| `constraints` | Stage/policy gates evaluated before mint |

Templates reference intents; stages/policies authorize intents; the link service mints tokens.

---

## 6. PublicActionLinkService

Sole owner of public URL creation.

**Input:**

- tenant  
- entity  
- link intent  
- actor or automation  
- expiry  
- locale  
- required authorization  
- single-use / multi-use  

**Output:**

- token  
- public URL  
- `expires_at`  
- target entity  
- purpose / intent  
- audit record  

**Prepare-send sequence for a link variable:**

1. Check action policy allows intent on current stage/context  
2. Resolve target form/resource  
3. Create or reuse an allowed public token  
4. Substitute URL into message snapshot only  
5. Record which link was sent, to whom, and why  

Forbids: string-concat URLs in templates, modules, or frontend.

---

## 7. CommunicationActionPolicy

Business-process rules: **which action / link intent is allowed on which stage**.  
Not template text. Not automation timing.

Example rows:

| Module | Entity | Stage | Action | Link intent |
|--------|--------|-------|--------|-------------|
| Recruitment | CandidateApplication | new | Request questionnaire | `candidate_questionnaire` |
| Recruitment | CandidateApplication | documents_pending | Request documents | `document_upload` |
| Recruitment | CandidateApplication | interview | Invite to meeting | `meeting_booking` |
| Sales | SalesInquiry | qualified | Send proposal | `proposal_review` |
| Sales | SalesInquiry | awaiting_details | Request company data | `sales_questionnaire` |
| Client | ClientAccount | onboarding | Complete data | `client_onboarding` |

**Separation of concerns:**

| Layer | Knows |
|-------|--------|
| Pipeline stage | What should happen |
| Automation rule | When to emit a command |
| Template | How to phrase the message |
| Link service | Which safe URL to create |
| Communication platform | How to send and bind history |

Stages **must not** store message body copy as the SoT for outbound content.

---

## 8. `resolve_communication_capabilities`

Platform resolver (not per-frontend hardcoding):

```text
resolve_communication_capabilities(entity_type, entity_id, actor) → Capabilities
```

Returns:

- possible recipients  
- known emails / phones  
- allowed channels  
- available senders / channel accounts  
- matching templates  
- restrictions / quiet hours / consent blocks  
- existing thread(s) for origin  
- reason a channel is unavailable  

Illustrative capability matrix (normative intent; exact rows live in registry data):

| Entity | Email | SMS | WhatsApp | Bulk |
|--------|-------|-----|----------|------|
| Candidate | yes | yes | yes | yes |
| CandidateApplication | yes | yes | yes | yes |
| SalesInquiry | yes | yes | yes | limited |
| ClientAccount | yes | yes | yes | yes |
| ContactPerson | yes | yes | yes | yes |
| Employee | yes | yes | yes | HR rules |
| ServiceOrder | via contact | via contact | via contact | no |
| Lead facade | temporary | temporary | temporary | no |

“Write” buttons across modules only call this resolver + command; they do not invent channel rules.

---

## 9. Thread resolution

| Rule | Contract |
|------|----------|
| Primary key | Work context / **origin entity**, not recipient address alone |
| One person | May have many threads (candidate vs client vs inquiry) |
| Re-send | Same origin reuses the resolved origin thread when policy says so |
| G13 | Origin link mandatory when origin known; related links optional |
| Address-only | Allowed only when no HostFlow origin exists (e.g. pure inbound unresolved) |
| Convert | Add links; do not drop prior origin links needed for history |

Inbound preference order is **C0.2** (reply headers → provider ids → contact → active inquiry/application → client/candidate → unresolved). This canon only requires outbound to be origin-linked.

---

## 10. Message snapshot

After send, `CommunicationMessage` **must not** depend on live template edits.

Persist at least:

- template id + version (if templated)  
- rendered subject / body  
- resolved variables  
- created public links (intent, token id, URL, expiry)  
- chosen signature  
- sender identity  
- recipient identity  
- purpose  
- compliance decision (allow/deny basis summary)  
- automation rule id (if any)  
- origin entity (+ related entity ids)  
- command idempotency / correlation ids  

Yesterday’s email stays exactly as sent if the template changes tomorrow.

---

## 11. Consent / RODO contract

RODO is **not** `consent=true` on a contact.

`CommunicationPermission` / `ConsentEvidence` (logical model) stores:

- subject / contact  
- purpose  
- channel  
- legal / compliance basis category  
- source  
- notice text or notice version  
- recorded_at  
- scope  
- status  
- withdrawal  
- expiry (if applicable)  
- evidence payload  
- related submission / form / document  

Before send, policy engine answers:

- is this communication allowed?  
- for which purpose?  
- on which channel?  
- is consent required?  
- which mandatory footer / notice?  
- is unsubscribe link required?  
- may this contact join a bulk audience?  

**Do not mix** purposes: application workflow ≠ client ops ≠ employee notice ≠ marketing.  
Same email address ≠ same permission for all purposes.

Exact legal bases, retention, and copy require separate legal review; architecture must already store evidence and apply distinct policies.

---

## 12. Automation contract

`CommunicationAutomationRule` fields (logical):

- `module`, `entity_type`  
- `trigger`  
- `stage_from` / `stage_to`  
- `conditions`  
- `delay`  
- `channel_strategy`  
- `template_key`  
- `recipient_role`  
- `link_intents`  
- `deduplication_key`  
- `retry_policy`  
- `quiet_hours`  
- `requires_consent`  
- `enabled`  

Example triggers: entity created, entered stage, remained in stage, field changed, document missing, task overdue, form not completed, manual action requested.

**Mandatory chain:**

```text
Stage transition → DomainEvent → Automation evaluation → CommunicationCommand → Message + links + outbox
```

Stage / RODO handlers **must not** call transport or `prepare_and_send` synchronously inside the domain write transaction in a way that couples pipeline commit to provider latency. Emit event → evaluate → command (with idempotency).

Product UX for authoring rules is **Epic C2**; C0 only requires the contract and that new writers follow the chain.

---

## 13. Settings ownership

Do **not** pile everything into one tenant JSON blob.

| Bucket | Contents |
|--------|----------|
| Tenant communication settings | default locale/timezone, quiet hours, reply handling, allowed channels, default sender policies, branding, retention |
| Channel accounts | email mailbox, SMS sender, WhatsApp account, provider config, inbound addresses, sending limits |
| Signatures | selection by tenant / company / mailbox / user / module / locale; priority e.g. user+mailbox → company+mailbox → tenant default |
| Templates | versioned catalog (Communication ownership) |
| Automation rules | separate section bound to pipelines / domain events |
| Compliance policies | purposes, consents, mandatory inserts, prohibitions |

Legacy JSON keys (e.g. `lead_communication_v1`, `lead_rodo_v1`) are migration debt — read adapters only until retired.

---

## 14. Idempotency

| Key | Scope |
|-----|--------|
| Command `idempotency_key` | Same logical send → same message/delivery (no duplicates) |
| Automation `deduplication_key` | Same rule+entity+window → one command |
| G13 ensure | Idempotent upsert of `(thread, entity_type, entity_id)` |
| Public link reuse | Per intent reuse policy; do not mint unbounded duplicates |
| Provider retry | Safe against duplicate outbox rows via delivery/message keys |

Unknown delivery result is allowed; duplicate successful business send for the same idempotency key is not.

---

## 15. Transaction boundaries

**Atomic unit (same DB transaction / UoW):**

1. Thread resolve/create for origin  
2. G13 origin (+ related) links  
3. Message snapshot  
4. Delivery / outbox row(s)  
5. Audit of accept  

**After commit (async OK):**

- provider transport  
- webhook status updates  
- non-critical notifications  

**Forbidden:** commit domain stage change that has already talked to SMTP/SMS inside the same request without an outbox; or create Message without G13 when origin is known.

---

## 16. Migration path for existing writers

Target: every outbound path becomes a caller of `prepare_and_send_communication` (or thin adapter → command).

| Current path | Migration |
|--------------|-----------|
| Questionnaire invite → `send_communication` (PR #100) | First vertical caller; align to full command (template intents, PublicActionLink, consent, snapshot fields) in C0.1-align |
| `lead_communications` / auto lead ops | Adapter → command; retire direct `send_email_for_tenant` for product mail |
| `lead_rodo` / ingest auto-send | DomainEvent → automation/command; stop sync send in ingest handler |
| `candidate_notifications` / stage Telegram-or-email | DomainEvent → command; shared engine |
| Inbox `create_thread_message` + dispatch | Gate already G13-aware; compose path must resolve capabilities + command |
| Hardcoded `/public/apply/{token}` | Replace with `LinkIntent` + `PublicActionLinkService` |
| Seed `CommunicationTemplate` dataclass / C4 metadata | Evolve into durable registry matching §4 |
| Tenant JSON communication settings | Split into settings buckets (§13) |

**Order:** C0.0 (this doc) → finish/align C0.1 vertical under contracts → C0.2 / C0.3 → C2 for catalog/automation/campaign product surfaces. Do not add new module-specific senders during migration.

---

## 17. Anti-patterns (forbidden)

| Anti-pattern | Why |
|--------------|-----|
| **Hardcoded public URLs** in templates, modules, or frontend | Stale tokens after stage/form/vacancy change; no audit of intent |
| **Module-specific senders** (questionnaire / recruitment / sales / RODO / bulk each composing differently) | Divergent G13, snapshot, consent, idempotency |
| **Sync send from stage or RODO handlers** inside domain transactions | Couples pipeline to provider; double-sends; weak audit |
| **Template / channel logic inside frontend or domain modules** | Capability matrix and policies drift per screen |
| Treating **`ensure_thread_entity_link` alone** as completed Communication foundation | Linkage is necessary but not templates, links, consent, automation, or one engine |
| **Address-primary threading** when origin is known | Collapses distinct work contexts into one person-thread |
| **One consent boolean** for all purposes | Violates purpose separation / RODO evidence needs |
| **Campaign = N× Write in the browser** | Must be server-side campaign orchestration (C2) on the same command |

---

## 18. Relationship to PR #100 and follow-up slices

| Artifact | Role under this canon |
|----------|------------------------|
| PR #100 | **Vertical slice only:** `send_communication`, G13 writer/gate, questionnaire first caller, entity_links API/UI. **Not** completed Communication foundation. |
| C0.1 align (next code slice after this doc) | Questionnaire (and shared command) through: policy → template → link intent → thread → G13 → message snapshot → outbox |
| C0.2 / C0.3 | Inbound + delivery diagnostics |
| C2 | Templates product, automations product, campaigns — all on the same command |

---

## 19. Acceptance for C0.0 itself

- [x] This document exists and is linked from the sequential queue and Epic C0  
- [x] C2 scope states templates + automations + campaigns  
- [x] PR #100 described as vertical slice, not foundation complete  
- [ ] No production code required for C0.0 merge/land  
- [ ] Subsequent C0.1 code changes cite this canon and do not introduce anti-patterns in §17  
