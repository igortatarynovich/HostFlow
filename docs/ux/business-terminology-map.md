# Business Terminology Map (Agency / Employer / Services)

Дата: 2026-03-12
Владелец: Product + Frontend
Статус: ACTIVE

## 1) Цель

Единый словарь терминов для UI, onboarding и коммуникаций, чтобы пользователь видел один и тот же термин на всех экранах.

## 2) Канонические термины по типу бизнеса

| Domain concept | `agency` | `employer` | `services` |
|---|---|---|---|
| B2B entity (company module) | `Client` | `Company` | `Client` |
| Hiring unit | `Vacancy` | `Vacancy` | `Order` (в модуле Services) |
| Intake object | `Lead` | `Lead` | `Lead` |
| Person in pipeline | `Candidate` | `Candidate` | `Candidate` |
| Operational next step | `Reminder` / `Task` | `Reminder` / `Task` | `Reminder` / `Task` |

## 3) Правила использования

1. На одном экране нельзя смешивать термины `Client` и `Company` для одного и того же объекта.
2. Для `agency/services` в user-facing copy по умолчанию используем `Client`.
3. Для `employer` в user-facing copy по умолчанию используем `Company`.
4. Технические названия (`companies`, `company_id`) допустимы только в коде/API и не должны попадать в UX-тексты.
5. Empty states, CTA и KPI-блоки используют тот же термин, что и заголовок раздела.

## 4) Scope wave-1 (выполнено)

- `Dashboard`: business-aware labels для entity-блоков (`Client/Company`), удален конфликтный label `Clients / Companies`.
- `AgencyClientsPage`: empty-state CTA выровнен на `Open clients`.

## 5) Scope wave-2 (следом)

- Sidebar / Topbar / Breadcrumbs: сверка терминов с текущим `business_type`.
- Empty states в `Leads`, `Reminders`, `Candidates`, `Services` на предмет смешения `clients/companies`.
- Финальный copy-pass в `en/ru/pl` (без mixed-language fallback).
