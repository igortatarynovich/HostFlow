# Flow Spec — F3-B-10: Create questionnaire (manager)

**Status:** Draft — **user scenario first** (no implementation commitments)  
**Date:** 2026-07-15  
**Persona:** Services tenant manager (Sales / client acquisition)  
**Prerequisite:** Product B send → submit → answers path passable (F3-B-02..07)  
**Related:** [release-revenue-flow-audit.md](../release-revenue-flow-audit.md), [ADR-022](../architecture/ADR-022-intake-form-purpose-and-submission-policy-model.md), G-B-05 (Entity Profile registry on tenant)

---

## 1. Goal (user language)

**Create a working questionnaire in 2–3 minutes** without learning platform concepts.

| Yesterday | Today (target) |
|-----------|----------------|
| Manager sees Entity Profile, Purpose, preset, routing, slug — and closes the screen | Manager picks *what business case the form is for*, edits ready-made questions, saves |
| «Did I land in the right place?» after choosing B2B | Each choice visibly changes the suggested questions |
| Mixed EN/RU/keys in labels | One locale; human labels only |

**Success criteria (walkthrough):**

1. Manager opens Settings → Forms → **Create questionnaire**.
2. Picks business intent in plain language (no «Purpose»).
3. If needed, picks **service line** (one card = one bundled capability).
4. Lands in editor **with questions already selected** (not empty catalog).
5. Adjusts title, toggles/adds/removes questions, previews, saves.
6. Form appears in Sales picker and can be sent on an inquiry (reuse F3-B-02..04).

**Non-goals for this flow:**

- Designing Entity Profile manifests
- Configuring submission policy / match rules manually
- Choosing technical slug (auto-generated; advanced override optional later)

---

## 2. How the manager thinks (mental model)

The manager does **not** think:

- Entity Profile, Purpose, preset, routing, inbox, module, submission policy

The manager **does** think:

1. «I need a form clients will fill out»
2. «Is this for a **company** or a **candidate**?»
3. «**What are we selling / collecting?**» (targeted ads, drivers, survey, extra info on existing deal)
4. «What questions should we ask?» (edit defaults)
5. «Will answers show up where I work?» → yes, in **Sales inquiries** (one sentence, no paths)

**One user decision = one business capability**, not five platform knobs.

---

## 3. User flow (canonical steps)

### Step 0 — Entry

**Screen:** Settings → Lead forms / Questionnaires  
**Action:** «Создать анкету» / «Create questionnaire»

---

### Step 1 — What do you need the form for?

Single question. Four options (manager language):

| Option ID (internal) | User sees (RU example) | User sees (EN) |
|----------------------|------------------------|----------------|
| `company_inquiry` | Получить заявку от компании | Get an inquiry from a company |
| `candidate_application` | Получить заявку от кандидата | Get an application from a candidate |
| `follow_up_info` | Собрать дополнительную информацию | Collect additional information |
| `survey` | Провести опрос | Run a survey |

No word «Purpose». No cards with English-only hints.

**System:** maps selection → internal `purpose` axis (ADR-022) **silently**.

---

### Step 2 — What are you collecting? (conditional)

Shown only when Step 1 needs a **service line** (e.g. `company_inquiry`, `follow_up_info` on services tenant).

**Question:** «Какую услугу продаёте?» / «What service is this for?»

Examples (capability catalog — business names only):

| Capability (user label) | Hidden bundle (platform) |
|---------------------------|---------------------------|
| Таргетированная реклама | `service_sales.targeted_advertising` + preset + sales routing |
| Поиск водителей (C+E) | `recruitment.candidate.driver_ce` + preset + recruitment routing |
| … | tenant-visible capabilities only |

If Step 1 = `candidate_application` → skip to driver/recruitment capabilities (no B2B services list).

If Step 1 = `survey` → optional short path: «Краткий опрос» with minimal default template.

**System:** resolves **Capability** record (see §4). User never sees profile codes.

---

### Step 3 — System configures everything (invisible)

No screen. Automatic on entering Step 4:

| Platform artifact | Source |
|-------------------|--------|
| Entity Profile | Capability → `entity_profile_code` |
| Presentation preset | `GET …/presentation-preset` |
| Purpose | Capability → `purpose` |
| Submission policy | `default_submission_policy_for_entity_profile()` |
| Route intent / inbox | `_intake_routing_for_entity_profile()` |
| Default form title | Capability → suggested title (editable in Step 4) |
| Public slug | auto from title (hidden; collision-safe) |

User sees optional **one-line reassurance** (not a spec table):

> «Ответы появятся в разделе **Обращения → Sales**. При отправке с заявки — прикрепятся к этой заявке.»

No Module, Inbox path, Submission Policy, Match policy.

---

### Step 4 — Editor (pre-filled)

**Not empty.** Preset fields already **included** (checkboxes on, sensible order).

| Block | User sees |
|-------|-----------|
| Title | «Анкета — таргетированная реклама» (editable) |
| Questions | Company, contact, phone, email, need, … — toggle, reorder, label edit, show-if (advanced collapsed) |
| Add question | From catalog of **same capability** only (filtered) |

**Forbidden in default UX:**

- Second Entity Profile dropdown
- «Load preset» button (preset already applied)
- Column «Field code» / `qualified_code` (developer mode only)
- Raw i18n keys as labels

---

### Step 5 — Preview

Client-facing preview (same renderer as public apply / invite). Language switch if form supports it.

---

### Step 6 — Save

**Primary:** «Сохранить и активировать»  
**Result:** toast + redirect to form detail or back to list; form in Sales picker.

**On limit (402):** human message — what limit, what to do (deactivate unused form / billing), link to lead forms list + billing. Never «402» or internal codes alone.

---

### Step 7 — Done

Manager can immediately open Sales inquiry → send this form (F3-B-02).

---

## 4. Capability (product concept)

**Capability** = one manager-facing choice that bundles everything the platform already splits today.

```text
Capability (user-facing)
  ├── label, description, icon
  ├── business_type filter (services | recruitment | …)
  ├── purpose (ADR-022)
  ├── entity_profile_code
  ├── presentation_code (preset)
  ├── default_submission_policy
  ├── routing defaults (sales vs recruitment)
  ├── default_title, default_slug_prefix
  ├── post_save_outcome_hint (one sentence)
  └── entitlement / plan gate (optional)
```

**Example — «Таргетированная реклама»:**

| User picks once | Platform resolves |
|-----------------|-------------------|
| Таргетированная реклама | `service_sales.targeted_advertising`, `public_pl` preset, `inquiry`, `match_or_create`, Sales inbox, convert/reject actions |

This is the same bundle `provision_targeted_advertising_capability` already creates for auto-seed — exposed as **one catalog row**, not eight decisions.

**v1 catalog (minimal):**

| Capability ID | User label | Tenant filter |
|---------------|------------|---------------|
| `targeted_advertising` | Targeted advertising / Таргетированная реклама | `business_type=services` |
| `driver_ce` | Driver C+E application | recruitment / agency |
| … | from tenant `listIntakeFormEntityProfiles` + manifest metadata | filtered |

Catalog can start as **frontend registry** mapping to existing API; later move to backend `GET /capabilities/intake-forms` without changing user flow.

---

## 5. Reuse audit (flow step → existing code)

**Principle:** no new architecture; reorder UI and auto-call existing APIs.

| User step | Existing reuse | Change type |
|-----------|----------------|-------------|
| Entry | `LeadFormsSettingsPage`, `createIntakeForm` API | UX only |
| Step 1 intent | ADR-022 `purpose` values | Map 4 UI options → `purpose` |
| Step 2 service | `listIntakeFormEntityProfiles`, capability registry | New **catalog layer** (thin); filter by intent |
| Step 3 auto-config | `getEntityProfilePresentationPreset`, `default_submission_policy_for_entity_profile`, `_intake_routing_for_entity_profile`, `create_public_intake_form` | **Auto-invoke** on mount; hide UI |
| Step 4 editor | `IntakeFormPresentationEditor`, `upsert_public_intake_form_presentation` fields shape | `wizardMode`: no profile select, no preset btn, preset on load, hide codes |
| Step 5 preview | Public apply renderer / smoke-test token | Wire or reuse existing preview |
| Step 6 save | `POST /settings/intake-forms`, `ensure_lead_source_limit`, `ensure_tenant_lead_form_active_count_allows_transition` | Slug auto; friendly 402 for `lead_sources_limit_reached` |
| Send → answers | F3-B-02..07 (done) | No change |

**Already provisioned on services tenant (G-B-05):**

- `recover_targeted_advertising_capability` — same bundle as Capability `targeted_advertising`
- New tenant walkthrough should **not** require repair CLI if tenant create hook + catalog align

**Do not reuse as user-facing concepts:**

- `PURPOSE_WIZARD_OPTIONS` English strings as-is
- `IntakeFormAnswersRoutingCard` technical rows (Module, Inbox path)
- Duplicate profile `<select>` inside editor

---

## 6. Anti-patterns (explicit)

| Show | Why forbidden |
|------|----------------|
| `recruitment.candidate.driver_ce` in UI | Developer identifier |
| Purpose + Entity Profile + Load preset + Fields as separate decisions | One Capability |
| Empty field catalog after intent | Breaks trust («wrong place») |
| `fields.recruitment_*` keys as labels | Unfinished product signal |
| `/app/sales` as inbox hint | Internal route |
| Public slug on create | Technical; auto-generate |

---

## 7. Scenario registration

| ID | Step | Status |
|----|------|--------|
| **F3-B-10** | Manager creates questionnaire (capability wizard) | **not_started** |
| **F3-B-11** | New services tenant: create → send → submit without repair | **not_started** (acceptance for catalog + auto-provision) |

**Gap registry name:** **G-B-07** — Form creation UX (Capability wizard).  
**Implementation gate:** this Flow Spec approved → one Scenario Step PR (F3-B-10) → walkthrough → then F3-B-11 on clean tenant.

---

## 8. i18n requirement

All wizard copy: **ru / pl / en** via `admin.intake_forms.wizard.*` and `admin.capabilities.*`.

Field labels in editor: resolve via presentation/API label, fallback to field registry i18n — **never** show raw `qualified_code` or unresolved `fields.*` keys in default mode.

---

## 9. Open questions (product, not blockers for spec)

1. **Capability catalog source:** static frontend map vs `GET /capabilities` — start frontend for speed?
2. **Follow-up info** vs **company inquiry** — same capabilities or subset?
3. **Preview** in v1: inline modal vs link to smoke-test token?
4. **Plan limits:** show remaining active forms / lead sources before create?

---

## 10. Changelog

| Date | Change |
|------|--------|
| 2026-07-15 | Initial Flow Spec — manager-first, Capability model, reuse audit (post F3-B-02..07 PASS) |
