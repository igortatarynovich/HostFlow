# M1 — First Successful Tenant: Backlog

**Status:** implementation backlog (L3).  
**Parent:** [`first-successful-customer-journey.md`](../journeys/first-successful-customer-journey.md).  
**Contracts:** [`m1-product-contracts.md`](../journeys/m1-product-contracts.md).  
**Browser acceptance:** `e2e/milestone-1-tenant-ready.browser.spec.ts`.  
**Human gate:** [`../../runbooks/m1-human-gate.md`](../../runbooks/m1-human-gate.md).

**Правило:** каждая задача закрывает конкретный пункт DoD через product contract. Ответ «ни один» → задача не создаётся.

**Milestone complete:** browser E2E green **и** human gate PASS (независимый человек).

---

## M1-01 — Definition of Done (Signup Flow)

M1-01 пройден, когда **новый пользователь** проходит **полный** путь без пропусков:

| Step | DoD | PASS когда |
|------|-----|------------|
| 1 | Открыл `/signup` | Публичная форма доступна |
| 2 | Создал аккаунт | Tenant + admin user + membership через `/auth/register` |
| 3 | — | Автологин после регистрации |
| 4 | Создал operating company | Обязательный шаг `/app/onboarding/company` (не пропускается) |
| 5 | Выбрал `business_type` | Часть company form (agency / employer / services) |
| 6 | Попал в `/app/setup` | **Единственный** redirect после company — не dashboard / wizard / demo |
| 7 | Видит следующий gate | G0+G1 PASS; первый failed gate + next action (agency: G2) |

**Не PASS:** signup → `/app/setup` без company; magic/demo pipeline; wizard/getting-started как entry.

---

## M1-01 Workspace Entry

| ID | Закрывает DoD | Contract | Задача |
|----|---------------|----------|--------|
| M1-01.1 | D1–D3 | M1-01 § signup path | **Done** — signup → mandatory company → setup only |
| M1-01.2 | D1 | M1-01 § workspace | G0: `/auth/register` creates tenant + admin + membership |
| M1-01.2 | D2, D3 | M1-01 § company | **In progress** — minimal company setup UI; no industry/team/hours/demo; auto-demo seed disabled |
| M1-01.4 | D1–D3 | M1-01 § запрещено | **Done** — AppShell locks to company until `onboarding_required=false`; legacy redirects |
| M1-01.5 | D1 | M1-01 § gates | **Done** — setup hub shows G0/G1 pass + next gate; `m1-*` testids |

---

## M1-02 Operating Context

| ID | Закрывает DoD | Contract | Задача |
|----|---------------|----------|--------|
| M1-02.1 | D3 | M1-02 § когда настроен | Обязательный шаг S1: выбор `business_type` блокирует продолжение до G1 PASS |
| M1-02.2 | D3 | M1-02 § после выбора | Adaptive steps: agency / employer / services видят только применимые S2–S5 шаги |
| M1-02.3 | D3 | M1-02 § изменение | Смена `business_type` пересчитывает snapshot и blockers |
| M1-02.4 | D3 | M1-02 § source of truth | G1 в readiness aggregation API |

---

## M1-03 Hiring & Process Context

| ID | Закрывает DoD | Contract | Задача |
|----|---------------|----------|--------|
| M1-03.1 | D4 | M1-03 § agency G2 | Client creation в setup path; return to setup hub после save (no Type-2 dead end) |
| M1-03.2 | D4 | M1-03 § G3 | Vacancy creation в setup path; Skip удалён для обязательных типов |
| M1-03.3 | D5 | M1-03 § G4 | Funnel binding на vacancy внутри setup (не только Settings → Funnels) |
| M1-03.4 | D5 | M1-03 § G5 | Requirement profile / entity profile binding внутри setup |
| M1-03.5 | D4, D5 | M1-03 § где | После каждого S2/S3 действия — обновлённый setup status + next action |
| M1-03.6 | D4, D5 | M1-03 § source of truth | G2–G5 в readiness snapshot с business_type applicability |

---

## M1-04 Intake Source & Routing

| ID | Закрывает DoD | Contract | Задача |
|----|---------------|----------|--------|
| M1-04.1 | D6, D7 | M1-04 § source of truth | Sources (Intake Routing) — primary setup surface для S4 |
| M1-04.2 | D6 | M1-04 § G6 | Meta OAuth completion внутри Sources (не wizard tab + отдельная вкладка) |
| M1-04.3 | D7 | M1-04 § G7 | UI полной binding-строки: source → vacancy → funnel → profile → assignee |
| M1-04.4 | D7 | M1-04 § G8 | Single winner: IntakeSourceBinding каноничен; Meta admin routing — strangler, не setup path |
| M1-04.5 | D7 | M1-04 § известный source | Ingest применяет binding; disposition ≠ `needs_routing` для configured key |
| M1-04.6 | D6, D7 | M1-04 § NOT READY | Деактивация source / binding снимает G6/G7/G8 и READY |

---

## M1-05 Setup Readiness

| ID | Закрывает DoD | Contract | Задача |
|----|---------------|----------|--------|
| M1-05.1 | D8 | M1-05 § READY | Readiness aggregation API: `recruitment.setup.intake` scope, G0–G8 AND |
| M1-05.2 | D8 | M1-05 § Health Check | Health Check screen — проекция snapshot (не wizard progress) |
| M1-05.3 | D8 | M1-05 § Next Action | PI-1: одно next action; pre-publish reachability check |
| M1-05.4 | D8 | M1-05 § пересчёт | Snapshot пересчёт при изменении gate-данных; READY → NOT READY |
| M1-05.5 | D8 | M1-05 § не READY | Убрать legacy activation counters (`first_lead_created`, `next_action_created`) из `setup_ready` |
| M1-05.6 | D9 | M1-05 § M1-D9 | Route summary на READY screen: источник → вакансия → воронка → требования → ответственный |
| M1-05.7 | D1–D8 | Journey § Browser Test | `milestone-1-tenant-ready.browser.spec.ts` green на fresh tenant |
| M1-05.8 | D9 | Journey § Human Gate | Human gate runbook выполнен независимым человеком |

---

## Зависимости (порядок реализации)

```text
M1-01 → M1-02 → M1-03 → M1-04 → M1-05
         │                    │
         └──── G1 в API ──────┴── G0–G8 snapshot перед Health Check UI
```

**Критический путь:** M1-01.4 (единый path) → M1-05.1 (snapshot API) → M1-05.3 (next action PI-1) → M1-04.3 (binding UI) → M1-05.2 (Health Check).

---

## Explicitly frozen (не в M1 backlog)

| Item | Почему |
|------|--------|
| Form Builder polish | Не закрывает M1-D* при Meta path |
| Candidate Card / ADR-017 Step 6 | M2/M3 UX debt |
| `/requirements` route retirement | Не блокирует M1 |
| Новые ADR / PI-2+ | Freeze до journey green |
| Flow 2–7 audits | После M1 human gate |

---

## Definition of Done для backlog item

Задача `M1-xx.n` done когда:

1. Пункт DoD, указанный в таблице, технически достижим на fresh tenant.
2. Соответствующий шаг browser spec (если есть) не падает на этом участке.
3. Не нарушен product contract блока.

Milestone M1 done только при M1-05.7 + M1-05.8.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-03 | Initial backlog derived from M1 product contracts |
