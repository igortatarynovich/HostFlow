# ADR-022 Phase 1 Backend — Architecture Merge Request

**ADR:** [ADR-022](../architecture/ADR-022-intake-form-purpose-and-submission-policy-model.md) (Proposed → target: Accepted)  
**Contract:** [intake-form-purpose-phase1-backend.md](intake-form-purpose-phase1-backend.md)  
**Review checklist:** [ADR-022-review-checklist.md](../architecture/ADR-022-review-checklist.md)

> Документ для решения архитектора: **можно ли мержить backend slice**. Не отчёт о разработке.

---

## 1. Почему появился PR

Вводит каноническую модель **Purpose + Target Entity Profile + Submission Policy** для Intake Forms, позволяющую одной форме либо создавать новую Application, либо дополнять существующую — в зависимости от политики submit и контекста входа (public / invite).

---

## 2. Что решает для продукта

Только пользовательские сценарии. Если сценарий здесь не описан — код в PR не претендует на product value.

| Сценарий | Пользователь | Результат |
|----------|--------------|-----------|
| **Публичная B2B ссылка** | Неизвестная компания открывает форму по slug | Ответы попадают в CRM как новая или существующая Sales Inquiry — по policy `match_or_create` |
| **Персональный follow-up** | Менеджер отправил анкету на известный лид | Ответы **дополняют** существующую Inquiry (`attach`), второй лид не создаётся |
| **Одна форма → новая заявка** | Публичный submit без совпадения по email+phone | Создаётся новая open Sales Inquiry + Submission #1 |
| **Одна форма → дополнение** | Публичный submit с strong match (email+phone, одна open Inquiry) | Submission append к существующей Inquiry; draft Lead помечается abandoned |
| **Оператор в CRM** | Менеджер открывает лид | Видит presentation answers и историю submit через `submissions_v1[]` с policy snapshot |

---

## 3. Reuse audit

PR **расширяет** платформу, а не строит вторую intake-систему.

| Existing component | Reused | New capability in this PR |
|--------------------|--------|---------------------------|
| **IntakeRouter** / `IntakeSourceProfile` | ✓ — route/inbox не переписаны | — |
| **Decision Layer** (`evaluate_ingest_decision`) | ✓ — вызывается после выбора target Application | — |
| **Outcome Executor** (`submit_public_intake_lead_draft`) | ✓ — disposition/candidate path без изменений контракта | — |
| **Entity Profile runtime** (`ingest_runtime`, presentation bridge) | ✓ — routing source остаётся profile | Gate validation purpose×profile×policy |
| **Public intake draft session** (`public_intake_draft_session`) | ✓ — transport in-progress fill | Token valid after submit (idempotent re-submit) |
| **Duplicate resolution** (`duplicate_resolution.py`) | ✓ — Candidate scope не тронут | — |
| **Contact normalization** | ✓ — вынесено в shared layer | `services/contact_identifiers.py` (канон для matching) |
| **Lead transport (Application facade)** | ✓ — ADR-021 Phase 1 | Append-only `submissions_v1[]` |
| **Sales Application matching** | — | `intake_platform.application_matcher` (Lead→Lead open Inquiry) |
| **Submission Policy resolution** | — | `policy_resolver`, `form_definition`, `entity_profile_gate` |
| **Submit orchestration** | — | `submit_resolver` + `intake_submit_service` (match → Decision Layer → append) |
| **Submission storage** | — | `submission_store` (FOR UPDATE, idempotency key) |

**Anti-patterns отсутствуют:** нет второго routing engine, нет второго Decision Layer, нет matching ClientAccount/Candidate напрямую на submit.

---

## 4. Что принципиально НЕ изменилось

Архитектор должен видеть **отсутствие drift**:

| Invariant | Status |
|-----------|--------|
| IntakeRouter не заменён | ✓ |
| Decision Layer не переписан | ✓ |
| Outcome Executor не изменён по контракту | ✓ |
| Entity Profile остаётся источником routing / route_intent | ✓ |
| Lead остаётся transport object для Application (ADR-021 Phase 1) | ✓ |
| Recruitment candidate intake path не затронут в этом slice | ✓ |
| `duplicate_resolution` (Candidate) не заменён Application matcher'ом | ✓ |
| Таблица `applications` не введена | ✓ |

---

## 5. Scope

### Входит (Phase 1 backend slice)

- Поля Form Definition: `purpose`, `target_entity_profile_code`, `submission_policy`
- Entity Profile gate при save формы
- Effective policy resolver (form + publication config prep + invite override)
- Режимы runtime: **`match_or_create`** (public default для targeted-ad preset), **`attach`** (invite)
- Sales Inquiry matching по email+phone с Match Matrix (ADR-022 §4.4)
- Append-only Submission в `Lead.normalized.submissions_v1[]` с policy snapshot
- P1 safety: idempotent submit, PATCH guard, abandoned draft isolation
- Schema prep: `published_version`, `is_system_preset`, `publication_config_v1` (columns only)

### Сознательно не входит

| Item | Phase |
|------|-------|
| Immutable published versions / publish workflow | 2 |
| Publication CRUD / multi-campaign first-class | 2 |
| Intake Review Queue UI (`review` mode — enum only) | 2–3 |
| Candidate / universal Application matching | 2+ |
| Admin UI: Form Definition editor, policy builder | Next slice |
| `applications` table | ADR-021 Phase 2+ |
| `reviewed_values` / operator correction writes | 2 |
| `document_collection`, `notify` runtime paths | Later |

---

## 6. Acceptance — бизнес-сценарии

Не список API-тестов. Критерий: **оператор получает ожидаемый результат в CRM без ручной починки данных**.

### Scenario A — Meta Lead → questionnaire → strong match → existing Inquiry updated

```
Meta Lead (open Sales Inquiry)
    ↓
Manager: «Отправить анкету» (questionnaire invite)
    ↓
Client opens personal link, fills targeted-advertising presentation, submits
    ↓
Policy: attach (forced by invite)
    ↓
Submission appended to **same** Sales Inquiry
    ↓
No second Inquiry created
    ↓
Manager sees updated answers on existing lead
```

**Backend contract:** invite attach + submission append — покрыто API-тестами (`test_adr022_invite_attach_submission`, `test_sales_targeted_advertising_intake`).

---

### Scenario B — Unknown company → public link → new Sales Inquiry

```
Unknown contact
    ↓
Opens public B2B form slug (match_or_create policy)
    ↓
Fills presentation, submits
    ↓
No strong match (new email+phone or no single open Inquiry)
    ↓
New Sales Inquiry created
    ↓
Submission #1 with effective policy snapshot
    ↓
Operator reviews in Sales inbox
```

**Backend contract:** public `match_or_create` + create path — покрыто API-тестами (`test_adr022_public_match_or_create_no_match`).

---

### Scenario C — Personal invite → attach → only existing Inquiry updated

```
Known Sales Inquiry
    ↓
Manager sends questionnaire invite
    ↓
Client submits via invite token
    ↓
Policy: attach (always; Application known at invite creation)
    ↓
Submission appended; invite marked submitted
    ↓
Repeat submit returns same result (idempotent)
    ↓
No duplicate Inquiry; abandoned draft excluded from inbox counts
```

**Backend contract:** attach + idempotent re-submit — покрыто API-тестами (`test_adr022_public_submit_idempotent`, attach tests).

---

### Scenario acceptance matrix

| Scenario | Backend contract gate | Product release gate |
|----------|----------------------|----------------------|
| **A** — Meta → invite → attach | API/E2E required before backend merge | UI walkthrough after UI/publication slice |
| **B** — Public → match_or_create → create | API/E2E required before backend merge | Public publication walkthrough (no manual URL) |
| **C** — Invite → attach → idempotent | API/E2E required before backend merge | Manager invite walkthrough in Sales workspace |

---

## 7. Known limitations

Честно — не заявлять в release notes:

- **Immutable published versions** — schema column only; Phase 2
- **Publication entity / multi-campaign admin** — Phase 2
- **Candidate matching** — Phase 2+ (duplicate_resolution unchanged)
- **Universal Application matching** — Sales Inquiry only in Phase 1
- **Review Queue UI** — `review` mode in enum; no runtime UI
- **Offering match** — implemented when `require_offering_match=true` and attribution present; default policy has it `false`
- **Abandoned draft** — excluded from list/quota; physical row retained (no cleanup policy in P1)
- **Operator reviewed_data** — Phase 2 (ADR-021)
- **Form Definition admin UI** — not in this PR

---

## 8. Merge gate

Два независимых gate. Backend PR **не блокируется** UI, которое строится поверх него.

### Backend PR merge (this PR)

Merge **разрешён после**:

1. **Architecture review PASS** — [ADR-022-review-checklist.md](../architecture/ADR-022-review-checklist.md)
2. **ADR-022 → Accepted (L1)**
3. **Engineering + security gates** — P1 fixes done, tests green, no candidate intake regression
4. **Backend contract scenarios A/B/C** — подтверждены API/E2E-тестами (§6 matrix, left column)
5. **Reuse audit принят** (§3)
6. **Migration roundtrip** — `202607151000_adr022_form_purpose`
7. **Multi-form scalability accepted** (§9) — Publication contract + versioning design; Phase 1 gaps explicit
8. **Явная декларация в PR:** product UI acceptance **ещё не выполнен** — release gate, not merge blocker

Product sign-off на этом этапе: **semantics и сценарии** (purpose/policy, match_or_create, release flow) — не implementation details.

### Phase 1 capability release (after UI/publication slice)

Capability считается готовой к релизу **только после**:

- UI/publication slice merged (минимальный путь без ручных URL)
- Full A/B/C **browser walkthrough** (§6 matrix, right column):
  - Meta lead → personal invite → submit → answers in Sales
  - Public link → new or existing Inquiry
  - Manager sees form, version, source, answers (Submission attribution)
  - Operator can take decision without manual URL, JSON, or DB edits

---

## Post-merge priority

**Следующий PR:** минимальный UI/publication slice для Product B walkthrough — **не** full Form Definition editor.

Целевой walkthrough (release gate):

```
Meta Lead
    → Отправить анкету
    → Клиент ответил
    → Менеджер увидел ответы
    → Принял решение
```

Form Definition admin UI — после закрытия release gate.

---

## 9. Multi-form scalability (pre-merge architecture check)

Product B подразумевает **десятки форм одновременно** у одного tenant. Вопрос merge gate: масштабируется ли выбранная модель?

### Пример tenant (целевое состояние)

| Entry point | Form Definition | Publication role |
|-------------|-----------------|------------------|
| Meta Ads → «Таргетированная реклама» | Sales inquiry form A | `IntakeSourceProfile` + binding (campaign/page) |
| Meta Ads → «Подбор водителей» | Recruitment form B | Отдельный profile + binding |
| Google Ads → «Консультация» | Sales form C | Profile + `public_slug` |
| Сайт → «Запрос демо» | Sales form D | Profile / form slug |
| QR на выставке | Event form E | Profile + campaign attribution |
| Email / WhatsApp follow-up | Любая form | **Invite** (attach, known Application) |

### Модель: Form Definition × Publication × Submission

```
TenantLeadForm          = Form Definition (purpose, profile, policy, presentation draft)
IntakeSourceProfile     = Publication transport (channel, attribution, optional policy override)
IntakeSourceBinding     = Provider key → Publication (Meta campaign, page, etc.)
LeadQuestionnaireInvite = Personal entry (forced attach)
Submission              = snapshot: form_id + publication_id + published_version + effective_policy + source
```

**ADR-022 контракт:** one Form Definition → many Publications; each Publication carries attribution; Submission stores immutable effective policy snapshot.

### Scalability matrix

| Requirement | Model (ADR-022) | Phase 1 backend shipped |
|-------------|-----------------|-------------------------|
| Many Form Definitions per tenant | ✓ `TenantLeadForm` rows, tenant-scoped | ✓ |
| Each form — own purpose / policy / entity profile | ✓ three mandatory axes | ✓ |
| Many Publications per form | ✓ `IntakeSourceProfile` + bindings | Partial — resolver + `publication_config_v1`; no Publication CRUD UI |
| Publication — own attribution (source, campaign, channel) | ✓ stored on Submission `source` + `publication_id` | ✓ data path |
| Publication — limited policy override | ✓ `publication_config_v1.submission_policy_override` | ✓ resolver |
| Independent disable (form or channel) | ✓ `is_active` on form + profile + binding | ✓ |
| Per-publication analytics | ✓ Submission attribution fields | Data ✓; analytics UI — later |
| Long-lived campaigns across form versions | ✓ immutable `published_version` on Submission (ADR §6) | Design ✓; publish workflow — Phase 2 |
| Email/WhatsApp follow-up | ✓ Invite path (attach, no match) | ✓ |
| Cross-form isolation (wrong form ≠ wrong inbox) | ✓ Entity Profile → route_intent; match scoped by tenant + profile | ✓ Sales slice |

### Architecture verdict (merge gate item)

**Выбор фундамента — правильный:** три оси + Publication/Invite entry context + Submission snapshot масштабируются на десятки форм без второй intake-системы.

**Phase 1 — vertical slice, не full ops:** Publication admin, immutable publish workflow и analytics dashboards — Phase 2; они не меняют модель, только operational maturity.

**Blocker для merge:** архитектор подтверждает, что §5.2 Publication contract + §6 versioning **design** принимаются как путь к multi-form ops; отсутствие Publication CRUD UI в этом PR — expected gap, не architectural flaw.

---

## 10. Post-merge development filter

**Operational model:** [`release-revenue-flow-audit.md`](release-revenue-flow-audit.md) §0 — Foundation → Scenario Step → Revenue Flow.

**This PR (ADR-022 backend):** **Foundation** — unblocks `F3-B-04`, `F3-B-06`; **Operator gain: none** until PR B-1/B-2.

| PR | Level | Steps | Operator gain |
|----|-------|-------|---------------|
| **B-1** | Scenario Step | F3-B-02, F3-B-03 | Send questionnaire + waiting status |
| **B-2** | Scenario Step | F3-B-04..F3-B-07 | Answers + attribution + decision in Sales |

## References

| Artifact | Path |
|----------|------|
| ADR-022 | `docs/specs/architecture/ADR-022-intake-form-purpose-and-submission-policy-model.md` |
| Match Matrix | ADR-022 §4.4 |
| Component ownership | ADR-022 §5.5 |
| Implementation contract | `docs/specs/tasks/intake-form-purpose-phase1-backend.md` |
| Tests (engineering only) | `test_adr022_intake_policy_phase1.py`, `test_adr022_p1_fixes.py`, `test_sales_targeted_advertising_intake.py` |
