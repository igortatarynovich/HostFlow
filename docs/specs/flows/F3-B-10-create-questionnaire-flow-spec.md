# Flow Spec — F3-B-10: First working questionnaire (manager)

**Status:** Approved for implementation  
**Date:** 2026-07-15 (rev. 3)  
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

**End-to-end success (F3-B-10 walkthrough):**

1. «Создать анкету» → pick **Таргетированная реклама** (not «create from scratch»).
2. Editor opens **with questions already on**; manager adjusts title if needed.
3. Preview → Save.
4. **Questionnaire card** opens automatically — status Active, clear actions.
5. Manager copies link or goes to Sales → sends on inquiry (F3-B-02).
6. Client submits; answers on same inquiry (F3-B-04..06).

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

## 9. Scenario registration

| ID | Scope | Status |
|----|-------|--------|
| **F3-B-10** | Create path + **questionnaire card** (Parts A+B) | not_started |
| **F3-B-11** | New services tenant: Capability → card → send → submit (no repair CLI) | not_started |

### F3-B-11 — naive-user acceptance (mandatory)

**Tester:** someone who has **never** used HostFlow.

**Task (given verbally, no docs):**

> «Создай анкету для продажи таргетированной рекламы и отправь её клиенту.»

**Pass — all required:**

| # | Criterion |
|---|-----------|
| 1 | Completes without asking «what is Entity Profile / Purpose / Policy?» |
| 2 | Does not open documentation |
| 3 | Does not need hand-holding on platform concepts |
| 4 | Finishes in **2–3 minutes** |
| 5 | Questionnaire card visible after save; send or copy link works |

**Fail interpretation:** if explanation is required, **the product failed** — not the tester.

**Environment:** new **services** tenant, **no** repair CLI, **no** pre-seeded forms.

**Gap:** **G-B-07** — first working questionnaire without platform concepts.

**Implementation gate:** approve this spec → **one Scenario Step PR** with acceptance quote in §1 → F3-B-10 walkthrough → F3-B-11 on clean tenant.

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
| 2026-07-15 | **Rev 3** — orphan questionnaire rule; single Capability decision rule; F3-B-11 naive-user acceptance; approved for implementation |
| 2026-07-15 | **Rev 2** — Capability-first entry; flow extends to questionnaire card; no default empty create; quality indicator; PR acceptance rule |
| 2026-07-15 | Initial Flow Spec — manager-first, reuse audit |
