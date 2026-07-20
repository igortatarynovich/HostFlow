# C0.0 — Communication Canon & Contracts

**Status:** NORMATIVE  
**Date:** 2026-07-20 (rev. Intent-first + PR #100 contract alignment)  
**Parents:** [Sequential queue](sales-to-comms-sequential-queue.md) · [Epic C0](epic-c0-communication-integrity.md) · [C0.1 platform outbound](c0-1-platform-outbound.md) · [Epic C2](epic-c2-communication-campaigns.md)

> Canon + **extension-point alignment** in the same iteration as PR #100.  
> Docs fix SoT; code in #100 is brought to those contracts **without** adding product features  
> (no template admin UI, automation engine, consent engine, campaigns, Inbox, full Public Link Service).

**Working rule:** do not hard-split “docs then code”. Iterate:

1. Fix the canon (this doc).  
2. Align existing PR #100 code to contracts (Command, Intent, resolvers).  
3. No new capabilities — only architectural seams.  
4. Then close PR #100 as the **first implementation of the approved Communication Canon**.

---

## 1. Scope and boundaries

### Communication is a platform capability

Communication owns:

- communication **intents** and intent policy  
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
They express a **Communication Intent** against an origin entity:

```text
Request Questionnaire for this SalesInquiry / CandidateApplication
```

not “compose and SMTP this email”.

Modules may:

- raise domain events  
- request a manual action (UI “Write” → intent)  
- pass origin entity, intent, recipient role  

Modules must not:

- mint public URLs  
- call provider transport directly  
- maintain parallel “questionnaire / RODO / stage email” engines  
- embed template composition or channel policy in module code or frontend  
- call `resolve_template` / hardcode apply URLs in callers  

### In scope of this document

1. **Communication Intent** (primary layer)  
2. Entity ownership  
3. CommunicationCommand  
4. Template model + TemplateResolver  
5. LinkIntent + LinkResolver / PublicActionLinkService  
6. CommunicationActionPolicy  
7. Capability resolver  
8. Thread resolution  
9. Automation rule  
10. Consent / compliance  
11. Message snapshot  
12. Idempotency and transaction boundaries  
13. Migration path + anti-patterns  

### Out of scope as product features (later)

| Slice | Owns |
|-------|------|
| C0.1 (this PR) | Canon seams + first durable outbound path |
| C0.2 | Inbound resolver |
| C0.3 | Delivery diagnostics |
| C1 | Inbox UX |
| C2 | Templates catalog UX, automations product, campaigns |
| Legal review | Exact RODO bases, retention periods, notice texts |

### Allowed in PR #100 (contract alignment only)

- `CommunicationIntent` + intent policy seed  
- `CommunicationCommand`  
- `CapabilityResolver` / `TemplateResolver` / `LinkResolver` seams (thin impls)  
- `prepare_and_send_communication` + `CommunicationSender` port  
- Questionnaire as first intent caller through those seams  
- G13 + message/delivery atomicity (already in slice)  

### Forbidden in PR #100

- Full template registry persistence / admin UI  
- Automation engine product  
- Consent evidence engine product  
- Campaigns / bulk  
- Inbox redesign  
- Full PublicActionLinkService (token store, reuse matrix, multi-intent catalog) — **interface + one impl only** |

---

## 2. Communication Intent (primary layer)

**Intent is first. `send_communication()` is the executor, not the business API.**

Every outbound starts as a named intent, for example:

| Intent | Meaning |
|--------|---------|
| `request_questionnaire` | Ask contact to fill a questionnaire |
| `request_documents` | Ask for documents |
| `invite_to_interview` | Meeting / interview invite |
| `send_offer` | Offer / proposal for review |
| `follow_up` | Generic follow-up |
| `marketing_campaign` | Marketing (consent-gated) |
| `gdpr_notice` | Privacy / RODO notice |
| `document_expiry_reminder` | Expiry reminder |
| `manual_outbound` | Escape hatch while callers migrate |

Intent policy determines:

- which templates are allowed  
- which channels are allowed  
- whether a public link is required and which **link intent**  
- whether consent is required  
- who may initiate (manual / automation flags)  
- whether automation may fire  

```text
UI / DomainEvent
  → CommunicationIntent (+ origin entity)
  → IntentPolicy + ActionPolicy + Capabilities
  → CommunicationCommand
  → TemplateResolver + LinkResolver (+ signature, consent)
  → prepare_and_send_communication
  → send_communication (thread + G13 + snapshot + outbox)
```

This layer prevents a year of `if stage == …` / `if module == recruitment` forks.  
Stages and modules select **intents**; they do not own send pipelines.

Code seams (PR #100): `backend/app/communications/intent.py`, `command.py`, `prepare_send.py`.

---

## 3. Entity ownership

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

## 4. CommunicationCommand

Unified application entry for manual and automatic outbound:

```text
prepare_and_send_communication(command) → SendResult
```

Logical command fields:

| Field | Role |
|-------|------|
| **`intent`** | Primary business key (see §2) |
| `origin_entity_type` / `origin_entity_id` | Work context (mandatory when known) |
| `related_entities[]` | Extra G13 links (e.g. lead facade + inquiry) |
| `recipient` | Resolved person/address or role (`primary_contact`, …) |
| `channel` | `email` \| `sms` \| `whatsapp` \| … |
| `purpose` | Derived from intent policy when omitted |
| `template_key` **or** manual `content` | Composition path after TemplateResolver |
| `locale` | Rendering locale |
| `requested_link_intents[]` | Logical links to mint via LinkResolver |
| `actor` **or** `automation_identity` | Who/what initiated |
| `idempotency_key` | Deduplicate retries |
| `correlation` / `source_event_id` | Trace to domain event / UI action |
| `channel_account_id` / sender preference | Optional override within policy |

**Pipeline inside the platform (normative order):**

1. Intent normalization + IntentPolicy  
2. Authorization  
3. Capability resolution  
4. Recipient resolution  
5. Policy / consent check  
6. Template version resolution (`TemplateResolver`)  
7. Variable validation  
8. Public link generation (`LinkResolver` → later `PublicActionLinkService`)  
9. Signature resolution  
10. Thread resolution  
11. G13 linkage  
12. `CommunicationMessage` snapshot  
13. Delivery / outbox creation  
14. Audit  

Transport may run after the atomic unit (async worker); durable message + delivery + G13 must exist before “accepted”.

**PR #100 code:** `CommunicationCommand` + `prepare_and_send_communication` gate intent/capabilities; `send_communication` is the persistence executor. Questionnaire depends on `CommunicationSender`, not on SMTP helpers directly for the platform write path.

---

## 5. CommunicationTemplate

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

## 6. LinkIntent

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

## 7. PublicActionLinkService / LinkResolver

**Seam now:** `LinkResolver` (protocol) + first impl `QuestionnaireLinkResolver`.  
**Later:** full `PublicActionLinkService` (token store, reuse, auth modes, audit).

Sole owner of public URL creation for outbound prepare.

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

## 8. CommunicationActionPolicy

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

## 9. `resolve_communication_capabilities`

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

## 10. Thread resolution

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

## 11. Message snapshot

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

## 12. Consent / RODO contract

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

## 13. Automation contract

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

## 14. Settings ownership

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

## 15. Idempotency

| Key | Scope |
|-----|--------|
| Command `idempotency_key` | Same logical send → same message/delivery (no duplicates) |
| Automation `deduplication_key` | Same rule+entity+window → one command |
| G13 ensure | Idempotent upsert of `(thread, entity_type, entity_id)` |
| Public link reuse | Per intent reuse policy; do not mint unbounded duplicates |
| Provider retry | Safe against duplicate outbox rows via delivery/message keys |

Unknown delivery result is allowed; duplicate successful business send for the same idempotency key is not.

---

## 16. Transaction boundaries

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

## 17. Migration path for existing writers

Target: every outbound path becomes a caller of `prepare_and_send_communication` (or thin adapter → command).

| Current path | Migration |
|--------------|-----------|
| Questionnaire invite (PR #100) | **Done as first intent caller:** Intent → TemplateResolver → LinkResolver → CommunicationCommand → CommunicationSender |
| `lead_communications` / auto lead ops | Adapter → intent + command; retire direct `send_email_for_tenant` for product mail |
| `lead_rodo` / ingest auto-send | DomainEvent → automation/command; stop sync send in ingest handler |
| `candidate_notifications` / stage Telegram-or-email | DomainEvent → intent + command; shared engine |
| Inbox `create_thread_message` + dispatch | Gate already G13-aware; compose path must resolve capabilities + command |
| Hardcoded `/public/apply/{token}` | Callers use `LinkResolver`; evolve impl into full `PublicActionLinkService` |
| Seed `CommunicationTemplate` dataclass / C4 metadata | Evolve into durable registry matching §5; callers stay on `TemplateResolver` |
| Tenant JSON communication settings | Split into settings buckets (§14) |

**Order:** Canon + PR #100 contract seams → close #100 → C0.2 / C0.3 → C2 product surfaces. Do not add new module-specific senders during migration.

---

## 18. Anti-patterns (forbidden)

| Anti-pattern | Why |
|--------------|-----|
| **Hardcoded public URLs** in templates, modules, or frontend | Stale tokens after stage/form/vacancy change; no audit of intent |
| **Module-specific senders** (questionnaire / recruitment / sales / RODO / bulk each composing differently) | Divergent G13, snapshot, consent, idempotency |
| **Sync send from stage or RODO handlers** inside domain transactions | Couples pipeline to provider; double-sends; weak audit |
| **Template / channel logic inside frontend or domain modules** | Capability matrix and policies drift per screen |
| Treating **`ensure_thread_entity_link` alone** as completed Communication foundation | Linkage is necessary but not Intent, templates, links, consent, automation, or one engine |
| Starting from **`send_communication` without Intent** | Business rules leak into callers; stage/module forks proliferate |
| **Address-primary threading** when origin is known | Collapses distinct work contexts into one person-thread |
| **One consent boolean** for all purposes | Violates purpose separation / RODO evidence needs |
| **Campaign = N× Write in the browser** | Must be server-side campaign orchestration (C2) on the same command |

---

## 19. Relationship to PR #100

| Artifact | Role under this canon |
|----------|------------------------|
| PR #100 | **First implementation of the Communication Canon** for the outbound path: Intent + Command + resolvers + G13 + questionnaire first caller + entity_links API/UI. Not the full Communication *product* (C2), and not Inbox/consent/campaign engines. |
| C0.2 / C0.3 | Inbound + delivery diagnostics |
| C2 | Templates product, automations product, campaigns — all on the same Intent → Command path |

---

## 20. Acceptance for C0.0 itself

- [x] This document exists and is linked from the sequential queue and Epic C0  
- [x] Communication Intent is documented as the primary layer  
- [x] C2 scope states templates + automations + campaigns  
- [x] PR #100 aligns code to Intent / Command / TemplateResolver / LinkResolver / CapabilityResolver seams  
- [x] PR #100 does **not** ship template admin, automation engine, consent engine, campaigns, Inbox, or full Public Link Service  
