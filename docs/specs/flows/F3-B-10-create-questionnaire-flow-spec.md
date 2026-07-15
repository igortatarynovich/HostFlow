# Flow Spec — F3-B-10: First working questionnaire (manager)

**Status:** Rev 4 — create path implemented; **usage + destination + convert contract** defined (PR gate)  
**Date:** 2026-07-15 (rev. 4)  
**Persona:** Services tenant manager (Sales / client acquisition)  
**Prerequisite:** Product B send → submit → answers path passable (F3-B-02..07)  
**Related:** [release-revenue-flow-audit.md](../release-revenue-flow-audit.md), [ADR-022](../architecture/ADR-022-intake-form-purpose-and-submission-policy-model.md), G-B-05 (Entity Profile registry on tenant)

---

## 1. Goal (user language)

**Real goal:** not «save a form record» — a **working tool** the manager can send to a client today.

> **Менеджер создаёт первую рабочую анкету за 2–3 минуты, не понимая внутренних сущностей платформы.**

**PR pass/fail rule:** if walkthrough requires explaining Entity Profile, Preset, Purpose, or Submission Policy — **PR failed**, even when backend is correct.

| Yesterday | Today (target) |
|-----------|----------------|
| Platform assembly kit (Purpose → Profile → preset → fields → routing) | Pick **direction** → tweak questions → save → **see what to do next** |
| «Save» and silence — «what now?» | Post-save **questionnaire card** with obvious actions |
| «Create form» from empty catalog | **Capability** spawns pre-filled questionnaire; custom path is advanced |
| Mixed locales / field keys | One locale; human labels only |

**End-to-end success (full Product B manager path — PR gate):**

1. «Создать анкету» → pick **Таргетированная реклама** → save → **questionnaire card**.
2. Open a **specific** Sales Inquiry → «Отправить анкету» → pick compatible questionnaire → personal link.
3. Client submits → **Submission on that same inquiry** (no new inquiry).
4. Manager sees answers + attribution on inquiry work page.
5. «Создать клиента» → ClientAccount + Company (when applicable) with mapped fields.
6. Original **Submission unchanged** on inquiry; ClientAccount links to source inquiry; manager can reopen answers.

**Create-only (F3-B-10a/b) is necessary but not sufficient** for PR merge — see §13–§17.

**Non-goals:** manual policy/profile design; slug entry; empty-form wizard for 90% path.

---

## 2. Primary object: Capability (not Form)

Manager never thinks «form». They think:

> «Мне нужна анкета для продажи таргетированной рекламы.»

**Product chain (user-visible):**

```text
Capability (направление / услуга)
    → Questionnaire (анкета — рабочий инструмент)
    → Invite / public link (отправка)
    → Submission (ответ клиента)
    → Sales Inquiry (где менеджер работает)
```

**Platform chain (hidden):**

```text
Capability bundle
    → entity_profile_code + presentation preset + purpose + submission_policy + routing
    → TenantLeadForm + IntakeSourceProfile + presentation (implementation detail)
```

**Rule:** **Capability spawns the questionnaire** — not the other way around.  
Form rows in DB are persistence; **Capability is the product noun** in UI.

---

## 2.1 Product rule — questionnaire is never an orphan

An questionnaire must **not exist as a dead record** after save.

**Invariant:** after «Сохранить» the manager lands on **this questionnaire’s card** with obvious next actions — never on a bare list wondering «what now?».

| Pass | Fail |
|------|------|
| Card opens with send / copy / open / preview / edit | Save → list or silent redirect |
| Status **Активна** visible immediately | User must hunt settings to use the form |
| At least one action works without docs | User asks «what do I do next?» |

If the user asks «what now?» after save — **the scenario is incomplete**, not the user.

---

## 2.2 Product rule — Capability is the only user decision

Backend may keep Entity Profile, Purpose, Submission Policy, Routing, Preset — **unchanged**.

**Invariant:** in the create flow the manager makes **one** choice:

> «Какое направление / услугу я хочу использовать?»

Everything else is resolved **silently** from the Capability bundle.

| User decides | System decides (hidden) |
|--------------|-------------------------|
| Direction card (Capability) | `entity_profile_code`, `purpose`, preset fields, `submission_policy`, routing defaults, slug prefix |

**Platform evolution rule:** new platform knobs **must not** appear in the create wizard. They attach to **Capability bundles** (or advanced-only paths), never to the default 90% path.

---

## 3. Entry — no «create from scratch» by default

**Forbidden as primary CTA:** `Create form` (empty constructor).

**Primary CTA:** «Создать анкету» → **Выберите направление**

| Card (Capability) | Who uses it |
|-------------------|-------------|
| Таргетированная реклама | services / B2B sales |
| Найм водителей (C+E) | recruitment |
| Другая услуга… | tenant catalog (filtered) |
| **Создать свою** *(advanced)* | power users only — explicit secondary path |

**90–95% path:** pick a ready Capability → system does the rest.  
**«Создать свою»:** labeled advanced; may expose more controls later — **out of F3-B-10 v1** unless explicitly scoped.

Optional **Step A (type)** only when Capability catalog is ambiguous — e.g. same tenant sells services + recruitment:

- Получить заявку от **компании**
- Получить заявку от **кандидата**
- …  

Then filter Capability cards. Prefer **one screen** (direction = Capability) when tenant type is clear.

---

## 4. User flow — Part A: Create (F3-B-10a)

| # | Step | User sees | System (silent) |
|---|------|-----------|-----------------|
| 1 | Entry | «Создать анкету» | — |
| 2 | Direction | Capability cards (§3) | Resolve capability bundle |
| 3 | Questions | Editor, **pre-filled** preset | `presentation-preset`, auto-select fields |
| 4 | Quality hint | 🟢/🟡/🔴 by question count (§7) | count selected fields |
| 5 | Preview | Client view | public renderer / smoke token |
| 6 | Save | «Сохранить» | `createIntakeForm`, activate |

**One-line reassurance** (editor only, not routing table):

> «Ответы — в обращениях Sales. Если отправите с заявки — прикрепятся к ней.»

**Forbidden in default path:** Entity Profile, Purpose, Load preset, field codes, public slug, Module/Inbox/Policy rows.

---

## 5. User flow — Part B: Questionnaire card (F3-B-10b)

**Trigger:** immediately after successful save — **auto-navigate**, no dead-end list.

**Never ask:** «What now?»

### Header

```text
Анкета «Таргетированная реклама»
Статус: Активна
```

(Optional one line: «Направление: таргетированная реклама» — capability label, not profile code.)

### Primary actions (large buttons)

| Action | Behavior |
|--------|----------|
| **Отправить клиенту** | Deep link to Sales: pick recent inquiry or «choose inquiry» — reuses F3-B-02 send |
| **Открыть публичную ссылку** | Opens public intake URL in new tab |
| **Скопировать ссылку** | Clipboard + toast |
| **Предпросмотр** | Same as wizard preview |
| **Редактировать вопросы** | Back to editor (wizardMode off OK here — user already committed) |

**Not on this card:** Policy, Profile, Routing, slug editor (advanced/settings collapse).

### Usage copy (required on card)

Two short lines — manager must understand **both modes** without reading docs:

> **При отправке из заявки:** ответ дополнит выбранную заявку.  
> **При публичной ссылке:** система найдёт подходящую заявку или создаст новую.

(See §13 for behaviour contract.)

### Secondary (footer / menu)

- Деактивировать анкету  
- Billing / limits (if near cap)

**Walkthrough minimum for F3-B-10 PASS:** card visible + **Copy link** OR **Send from Sales** works without docs.

---

## 6. Capability bundle (implementation map)

```text
Capability (user-facing)
  ├── id, label, description, icon
  ├── tenant_filter (business_type, entitlements)
  ├── purpose (ADR-022) — hidden
  ├── entity_profile_code — hidden
  ├── presentation_code / preset — hidden
  ├── default_submission_policy — hidden
  ├── routing defaults — hidden
  ├── default_title — suggested in editor
  ├── default_slug_prefix — auto on save
  ├── post_save_card_copy — card subtitle
  └── spawns → Questionnaire (TenantLeadForm + intake stack)
```

**Example — Таргетированная реклама:** same bundle as `provision_targeted_advertising_capability` / G-B-05 auto-seed.

**v1 catalog:** frontend registry → existing APIs; later `GET /capabilities/intake-forms` without UX change.

---

## 7. Questionnaire quality indicator (product rule)

**Principle:** don’t block long forms — **educate**.

Show while editing (live count of **included** questions):

| Count | Indicator | Copy (RU example) |
|-------|-----------|-------------------|
| ≤ 8 | 🟢 | «6 вопросов — оптимально» |
| 9–12 | 🟡 | «10 вопросов — длинная анкета» |
| ≥ 13 | 🔴 | «16 вопросов — возможна низкая конверсия» |

Thresholds tunable per Capability later; v1 global bands OK.

---

## 8. Reuse audit

| User step | Existing reuse | Change |
|-----------|----------------|--------|
| Capability pick | `listIntakeFormEntityProfiles`, provision bundles | **Catalog layer**; Capability-first entry |
| Auto-config | `presentation-preset`, `default_submission_policy_for_entity_profile`, `_intake_routing_for_entity_profile` | Auto on editor mount |
| Editor | `IntakeFormPresentationEditor`, `createIntakeForm` | wizardMode; preset applied; quality indicator |
| Preview | public apply / smoke-test | reuse |
| Save | `POST /settings/intake-forms`, quota gates | auto slug; friendly 402 |
| **Questionnaire card** | `IntakeFormDetailPage` partial, public URL copy, Sales send panel | **New composition** — action-first layout |
| Send → answers | F3-B-02..07 ✓ | no backend change |

**Do not surface:** `IntakeFormAnswersRoutingCard` technical rows, duplicate profile `<select>`, `PURPOSE_WIZARD_OPTIONS` EN hardcode.

---

## 13. A — Questionnaire usage modes

Two **distinct** modes. Manager never chooses inbox, route, or attach policy.

### Mode 1 — Personal invite from Sales Inquiry

**Entry:** manager opens a **specific** B2B Sales Inquiry → «Отправить анкету».

| Step | User sees | System (silent) |
|------|-----------|-----------------|
| 1 | Compatible questionnaires only (§14) | Filter by inquiry context |
| 2 | Pick questionnaire (if >1) | `lead_form_id` |
| 3 | Personal link created / resent | `POST /leads/{lead_id}/questionnaire-invite` |
| 4 | Copy / WhatsApp / wait | Token bound to **this** `lead_id` |
| 5 | Client submits | Policy = **attach** (never user-visible) |
| 6 | Answers on **same inquiry** | Submission → current Sales Inquiry |

**Invariants:**

- Personal link is **hard-bound** to `lead_id` of the inquiry it was sent from.
- **No new Sales Inquiry** is created on submit.
- Manager does **not** choose attach mode, inbox, or routing.

**Backend anchor:** `resolve_effective_policy_for_invite` → `DEFAULT_INVITE_POLICY.mode = attach`; `append_submission` on invite lead.

### Mode 2 — Public link

**Entry:** manager copies/opens public URL from questionnaire card (ads, site, QR, social).

| Step | System behaviour |
|------|------------------|
| Submit | Policy from form definition → **`match_or_create`** for `service_sales.*` |
| Strong match (email **and** phone → one open inquiry) | Submission → **matched** Sales Inquiry; draft abandoned |
| No match | **New** Sales Inquiry created |
| Partial / multiple / conflict match | **No auto-attach** → review path (§15) |

**Invariants:**

- Public link is **not** bound to a lead until match/create resolves.
- Manager is **not** asked how to attach.

**Backend anchor:** `submit_client_public_intake_with_policy` → `resolve_submit_target` → `find_sales_inquiry_matches`.

---

## 14. B — Compatibility rules (form picker in inquiry)

When manager sends from an inquiry, show **only questionnaires compatible** with that inquiry.

| Rule | Match required |
|------|----------------|
| **Module owner** | Sales / `client_lead` inquiry (not recruitment candidate) |
| **Entity profile** | Form `target_entity_profile_code` compatible with inquiry's service context |
| **Purpose** | `inquiry` / `questionnaire` for B2B sales (hidden — enforced by Capability bundle) |
| **Capability / service** | e.g. targeted advertising ↔ `service_sales.targeted_advertising` |
| **Active status** | `TenantLeadForm.is_active = true` |

**v1 (targeted advertising):** picker lists active forms where `target_entity_profile_code == service_sales.targeted_advertising`.

**Future:** generalize filter via Capability id on form metadata — same UX, richer catalog.

**Forbidden in picker:** inactive forms, recruitment profiles on client inquiries, cross-module forms.

---

## 15. C — Submission destination

Answers belong to the **inquiry first**, not the client account (until convert).

**Data chain (user-visible):**

```text
Questionnaire → Submission → Sales Inquiry → manager decision → ClientAccount
```

Until «Создать клиента», data stays on the inquiry because the contact may be spam, duplicate, unqualified, or not ready.

### Destination by mode

| Mode | Policy (hidden) | Result |
|------|-----------------|--------|
| **From inquiry** (personal invite) | `attach` | Submission → **current** Sales Inquiry |
| **Public link**, strong single match | `match_or_create` | Submission → **matched** Sales Inquiry |
| **Public link**, no match | `match_or_create` | Submission → **new** Sales Inquiry |
| **Public link**, conflict / ambiguous | `match_or_create` → review | **Review queue** — no silent attach |

**Attribution UI (inquiry work page):** manager sees form, submission, attach mode, source — without jargon where possible (F3-B-06).

---

## 16. D — Convert mapping («Создать клиента»)

On **«Создать клиента»**, copy normalized data from inquiry → ClientAccount (+ Company when corporate data exists).

**Principles:**

- **Submission is immutable** — remains on Sales Inquiry history.
- ClientAccount gets **`source_lead_id`** → manager can reopen origin inquiry + raw answers.
- Company is created **only** when legal/corporate identity exists (company name minimum).
- Not every questionnaire field becomes a ClientAccount column — mapping follows **Entity Profile field role**.

### Targeted advertising — field mapping (v1)

| Questionnaire / normalized source | Target layer | Target field / storage |
|-----------------------------------|--------------|------------------------|
| `contact_full_name` | Contact | ClientAccount primary contact `full_name` |
| `contact_phone` | Contact | ClientAccount primary contact `phone` |
| `contact_email` | Contact | ClientAccount primary contact `email` |
| `contact_website` | Company | Company `website` |
| `contact_company_name` | Company | Company `name` (create Company when present) |
| `industry` | Company / profile | Company `extra` / profile context |
| `need_type`, `primary_outcome` | Need | ClientAccount need `summary` |
| `monthly_ad_budget`, `start_timeline`, … | Need / commercial | `need.questionnaire` + Company `extra.intake` |
| `additional_notes` | History | Inquiry notes / `need.questionnaire` — **not** silent overwrite of CRM fields |
| Diagnostic / consent / one-off | — | **Stay in Submission only** — no ClientAccount field |

**Do not auto-promote:** temporary answers, diagnostic questions, consent flags, internal routing metadata.

**Post-convert visibility (acceptance):**

- ClientAccount shows contact + display name.
- Company exists when company name was provided.
- Manager can navigate **inquiry → submission answers** after convert.

---

## 17. Backend reuse audit & gaps (2026-07-15)

Verified against current integration branch. **Create path (F3-B-10a/b)** partially implemented in frontend; **usage + convert** gaps remain before PR.

### Already works (reuse)

| Capability | Backend / UI | Evidence |
|------------|--------------|----------|
| Personal invite bound to `lead_id` | `attach_questionnaire_invite_to_lead`, `LeadQuestionnaireInvite` | `lead_questionnaire_invite.py` |
| Invite submit → attach policy | `resolve_effective_policy_for_invite` → `mode: attach` | `policy_resolver.py`, `constants.py` |
| Invite submit → Submission on same lead | `mark_invite_submitted` → `append_submission` | `lead_questionnaire_invite.py` |
| Merge answers into inquiry normalized | `merge_presentation_into_sales_summary` | contact_person, company_profile, need, sales_questionnaire |
| Public submit → match_or_create | `submit_client_public_intake_with_policy` | `intake_submit_service.py` |
| Strong email+phone match → attach | `find_sales_inquiry_matches` + `resolve_submit_target` | `application_matcher.py` |
| Form picker (targeted advertising) | `list_questionnaire_forms_for_targeted_advertising` | filters active + profile code |
| Send panel on inquiry | `SalesQuestionnairePanel` | F3-B-02 |
| Answers + attribution rails | `SalesQuestionnaireSummaryRail`, `SalesQuestionnaireAttributionRail` | G-B-03, G-B-04 |
| Convert client | `convert_client_lead` | contact_person, company_profile, need → ClientAccount + Company |
| Convert idempotency | `source_lead_id` on ClientAccount | tests in `test_client_account_conversion.py` |
| E2E test path | invite → submit → convert | `test_sales_targeted_advertising_intake.py` |

### Gaps (must close or explicitly defer before PR)

| Gap | Spec § | Current state | Required for PR |
|-----|--------|---------------|-----------------|
| **G-B-07-UI-card-copy** | §5 usage copy | Card lacks two-mode explanation | Add copy to questionnaire card |
| **G-B-07-UI-send** | §13 Mode 1 | Card links to Sales home, not inquiry | OK if send always from inquiry; card copy must say so |
| **G-B-08-review-queue** | §15 conflict row | `resolve_submit_target` creates new lead when match suggests `review` — no review inbox | Implement review queue **or** document Phase 2 + show manager warning on ambiguous public submit |
| **G-B-08-convert-mapping** | §16 | `industry`, `monthly_ad_budget`, `additional_notes` not mapped to structured Company/need fields — live in `sales_questionnaire` blob | Extend `extract_lead_conversion_context` / Company `extra` **or** accept v1 with need.questionnaire only + UI to show it |
| **G-B-08-post-convert-nav** | §16 post-convert | ClientAccount UI may not surface link back to source inquiry + submission | Verify / add «Исходная заявка» link on ClientAccount |
| **G-B-08-compatibility** | §14 | Picker hard-coded to targeted_advertising profile | OK for v1 walkthrough; generalize with Capability metadata later |

### PR merge gate (rev 4)

**Do not open PR** until walkthrough passes:

```text
create → card (with usage copy)
  → open specific inquiry → send questionnaire
  → client submit → answers on THAT inquiry
  → create client → see mapped contact/company/need
  → submission still on inquiry + traceable from client
```

Plus **F3-B-11 naive-user test** (§9).

---

## 9. Scenario registration

| ID | Scope | Status |
|----|-------|--------|
| **F3-B-10** | Create + card + **usage modes** + card copy (§13–§15 UI) | partial — create/card in progress |
| **F3-B-11** | Full path incl. convert + naive-user test (§9) | not_started |
| **F3-B-12** | Public link match / conflict / review (§15) | not_started — gap G-B-08 |

### F3-B-11 — naive-user acceptance (mandatory)

**Tester:** someone who has **never** used HostFlow.

**Task (given verbally, no docs):**

> «Создай анкету для продажи таргетированной рекламы, отправь её клиенту по конкретной заявке, дождись ответа и создай клиента.»

**Pass — all required:**

| # | Criterion |
|---|-----------|
| 1 | Completes without asking «what is Entity Profile / Purpose / Policy?» |
| 2 | Does not open documentation |
| 3 | Does not need hand-holding on platform concepts |
| 4 | Finishes in **2–3 minutes** (create + send); full path with submit may take longer |
| 5 | Questionnaire card after save; send from **inquiry** works |
| 6 | Answers visible on **same** inquiry after client submit |
| 7 | «Создать клиента» produces ClientAccount; contact/company data recognizable |
| 8 | Can find original questionnaire answers after convert |

**Fail interpretation:** if explanation is required, **the product failed** — not the tester.

**Environment:** new **services** tenant, **no** repair CLI, **no** pre-seeded forms.

**Gap registry:** **G-B-07** (create + card), **G-B-08** (usage destination + convert mapping UI).

**Implementation gate:** rev 4 contract approved → close gaps in §17 → full walkthrough → F3-B-11 → then PR.

---

## 10. i18n

All wizard + card copy: **ru / pl / en** (`admin.capabilities.*`, `admin.questionnaire_card.*`).  
Field labels: resolved human text — never raw `fields.*` keys in default UI.

---

## 11. Open questions

1. **Send from card:** open inquiry picker modal vs navigate to Sales inbox?  
2. **F3-B-10a type step:** skip for pure services tenants?  
3. **«Создать свою»:** defer to G-B-08 or hide until catalog stable?  
4. Show remaining lead-source quota before save?

---

## 12. Changelog

| Date | Change |
|------|--------|
| 2026-07-15 | **Rev 4** — §13–§17 usage modes, compatibility, submission destination, convert mapping; backend audit + PR gate extended to full path |
| 2026-07-15 | **Rev 3** — orphan questionnaire rule; single Capability decision rule; F3-B-11 naive-user acceptance; approved for implementation |
| 2026-07-15 | **Rev 2** — Capability-first entry; flow extends to questionnaire card; no default empty create; quality indicator; PR acceptance rule |
| 2026-07-15 | Initial Flow Spec — manager-first, reuse audit |
