# Epic P — Acquisition Stage 3D (Outcome Attribution)

**Status:** active · **Phase 1 first product vertical**  
**Canon:** [`ADR-024`](../architecture/ADR-024-acquisition-campaigns-intake-routing.md) §9 · §14  
**Module scope:** [`../../acquisition/module-scope.md`](../../acquisition/module-scope.md)  
**Gate:** closes Acquisition V1 vertical → unlocks Forms Sprint 1 ([`ADR-007`](../architecture/ADR-007-forms-platform-capability.md))

---

## Why now

3A–3C уже замкнули Growth → Intake. **3D** замыкает Operations → Intelligence feedback:

```text
Campaign → Flight → Endpoint → Submission → Result → Outcome
```

После Epic P Forms строятся на **стабильной** вертикали, а не параллельно с незакрытой Acquisition.

**Не вводить** новые сущности вне канона ADR-024. **Не менять** ownership (Acquisition ≠ Result SoT; destination modules own business objects).

---

## Goal

Полностью замкнуть цепочку от рекламы до результата: автоматическая атрибуция + Outcome progress + базовые Primary KPI агрегаты — без сложной BI и без ручных связей.

---

## Public chain (единственная)

```text
Campaign
  ↓
Flight
  ↓
Endpoint
  ↓
Submission
  ↓
Result
  ↓
Outcome
```

Любой модуль обязан работать **только** через эту цепочку. Обход (ручные campaign↔result links, локальные KPI tables) — **запрещён**.

---

## Scope

### 1. Attribution (automatic)

Каждый **Result** всегда знает:

| Field | Source |
|-------|--------|
| `campaign_id` | existing routing (`acquisition_routing_v1`) |
| `flight_id` / `campaign_run_id` | existing routing |
| `endpoint` identity | Form / Intake Source / future Endpoint id from binding |
| `submission_id` | intake submission that produced the Result |

Получение — **только** через существующий Universal Routing (3C). Никаких ручных связей UI/API.

Continuation Submissions наследуют attribution context (**routing once**); не переписывают Result attribution.

### 2. Outcome Progress

**Outcome** — основная единица продуктовой аналитики (не Result).

Минимальные статусы:

| Status | Meaning |
|--------|---------|
| `created` | Outcome объявлен на Campaign (квант цели) |
| `active` | Идёт накопление progress |
| `completed` | Цель достигнута (по Primary KPI units) |
| `failed` | Цель не достигнута / закрыта как провал |
| `cancelled` | Отменён без attainment |

KPI и Intelligence позже строятся **вокруг Outcome**, не вокруг сырых Result-счётчиков.

### 3. Primary KPI aggregates (Flight + Campaign)

Базовые продуктовые показатели (roll-up Flight → Campaign):

| Metric | Notes |
|--------|-------|
| Spend | базовые расходы волны / кампании |
| Leads | attributed submissions / leads |
| Qualified | qualified subset (policy-light; V1 rule documented) |
| Converted | Results that count toward Outcome |
| Cost per Lead | Spend / Leads |
| Cost per Qualified | Spend / Qualified |
| Cost per Outcome | Spend / completed Outcome quanta (or progress units) |

**Без** сложной BI, warehouse, произвольных dashboards. Только агрегаты, выводимые из attributed chain.

### 4. Contract surface

Публичный контракт Epic P = цепочка выше + read APIs / projections для KPI на Flight и Campaign. Модули **потребляют** attribution/KPI через Acquisition contracts; не дублируют.

---

## Out of scope (explicit)

- Multi-Flight UX / wave compare  
- CampaignTemplate catalog  
- Full Intelligence suite / ROI modeling  
- Timeline events (→ **3E**)  
- Automation Campaigns  
- Platform Forms Builder  
- New ownership of Candidate / Application / Inquiry / Client  
- Manual attribution APIs  
- Generic Endpoint migration off Form/Intake specializations (post-V1)

---

## Contract tests (mandatory)

Файл-ориентир: `backend/tests/api/test_stage_3d_outcome_attribution.py`

Покрыть полный путь:

```text
Campaign → Flight → Endpoint → Submission → Result → Outcome
```

Проверки:

1. **Ссылки сохраняются** — Result хранит campaign / flight / endpoint / submission; Outcome связан с Campaign (+ progress от attributed Results).  
2. **Ownership не меняется** — нет FK Acquisition → Candidate/Application/Inquiry/Client; destination modules remain SoT Results.  
3. **Удаление запрещённых объектов** — detach/delete правил 3B/3C + нельзя orphan attribution или silent re-bind.  
4. **Атрибуция не теряется** — re-read after routing; continuation submission не сбрасывает; KPI roll-up согласован с Results.  
5. **Нет manual attribution path** — API/service reject or ignore hand-set campaign links outside routing.  
6. **Outcome lifecycle** — transitions `created → active → completed|failed|cancelled` enforced.  
7. **KPI without user extra calls** — aggregates available from Campaign/Flight read after Results land (no “please refresh attribution” step).

---

## Definition of Done

Epic P закрыт **только если**:

- [ ] Вся цепочка проходит contract tests  
- [ ] Attribution полностью автоматический (через routing)  
- [ ] Ownership нигде не нарушается  
- [ ] KPI строятся без дополнительных запросов пользователя  
- [ ] Нет временных special case в attribution/KPI path  
- [ ] ADR-007 / Forms Sprint 1 считается **разблокированным** (Acquisition V1 vertical closed; 3E Timeline может идти параллельно Forms prep)

После DoD: **не** начинать Forms Builder. Сначала Forms Sprint 1 = Passport + Manifest + Public Contract + Adapter + Contract Tests ([`capability-contract.md`](../architecture/capability-contract.md)).

---

## Suggested PR sequence

| PR | Focus | Status |
|----|--------|--------|
| **PR-1** | Result attribution record/projection from `acquisition_routing_v1` + submission id; contract test skeleton | ✅ DONE · [PR #31](https://github.com/igortatarynovich/HostFlow/pull/31) MERGED |
| **PR-2** | Outcome entity + lifecycle statuses + progress from attributed Results | ✅ DONE · [PR #32](https://github.com/igortatarynovich/HostFlow/pull/32) MERGED |
| **PR-3** | Flight/Campaign KPI aggregates (Spend, Leads, Qualified, Converted, CPL, CPQ, Cost per Outcome) | 🔄 opening |
| **PR-4** | Full chain contract tests green; DoD checklist; unlock note in ADR-024 / ADR-007 | planned |

Не мержить PR-1, если появился manual link API или ownership FK на domain Results.

### PR-1 delivered

- Model/table: `acq_result_attributions` (`CampaignResultAttribution`) — FK only to Campaign/Flight
- Service: `backend/app/acquisition/result_attribution.py` — build/record **only** from routing stamp; manual `campaign_id`/`flight_id` rejected
- Hook: `intake_submit_service` records attribution after Decision Layer when campaign-routed
- Migration: `202607180004_acq_3d`
- Tests: `backend/tests/api/test_stage_3d_outcome_attribution.py`

### PR-2 delivered

- Outcome + ledger; soft-revoke; no intake hook — [PR #32](https://github.com/igortatarynovich/HostFlow/pull/32)

### PR-3 delivered (this branch)

- Spend source: `acq_flight_spend_entries` (Decimal/NUMERIC + currency)
- Qualification contract: `acq_result_qualifications`
- Read model: `kpi_aggregates.py` — Flight + Campaign (Campaign = sum of Flights)
- Cost per Outcome from **completed** Outcomes (soft-revoke / failed / cancelled excluded)
- Zero denominator → `null`; mixed currencies → error
- Migration: `202607180006_acq_3d_k`
- Tests: `backend/tests/api/test_stage_3d_kpi_aggregates.py`

---

## Implementation context (L3 pointers)

- Routing stamp: `backend/app/acquisition/submission_routing.py` (`acquisition_routing_v1`)  
- Campaign models: `backend/app/models/campaign.py`  
- Prior tests: `test_stage_3a_*`, `test_stage_3b_*`, `test_stage_3c_*`  
- No Result/Outcome acquisition tables yet — introduce per ADR-024 §9 without breaking 3A–3C

---

## History

- 2026-07-18: Epic P locked as Phase 1 start; Capability Contract sequence adopted for subsequent L1 (Forms first after V1).  
- 2026-07-18: **PR-1 DONE** — `acq_result_attributions` + routing-only attribution service + submit hook + contract tests.  
- 2026-07-18: **PR-2** — Outcome + ledger links; progress monotonic; soft-revoke on Result delete; no intake hook for Outcome.  
- 2026-07-18: **PR-3** — KPI read model (Flight+Campaign); spend source; qualification contract; Decimal-only ratios.
