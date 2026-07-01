# Phase 8 — Поиск, аналитика, NBA v2 (инвентаризация)

Источник чеклиста: `docs/HOSTFLOW_AUDIT_AND_PLAN.md` §Фаза 8. **Baseline инженерно закрыт** по §8.1 и §8.3 (см. чекбоксы в плане); остаток — wave 2. Сводка с фазами 2–7: `docs/specs/phases-2-8-engineering-closure.md`.

Цель документа — отделить **уже сделанное в коде** от **остатка**, чтобы не дублировать работу и не обещать «с нуля» то, что уже есть.

| # | Пункт плана | Статус | Где в коде / что осталось |
|---|-------------|--------|---------------------------|
| 8.1 | Глобальный поиск: документы + join к кандидату | **Сделано** | `GET /api/v1/search` → `backend/app/services/global_search_v1.py::_search_documents_slice` — `outerjoin(Candidate)`, subtitle с именем кандидата, FTS по полям кандидата. Фронт: `hostflow-frontend/src/api/search.ts` (`searchGlobal`). |
| 8.2 | Семантический поиск (pgvector / внешний) | **Открыто** | Нет embedding-пайплайна; решение по данным (объём запросов, бюджет). Зависимость: Фаза 0 (очередь) если индексация асинхронная. |
| 8.3 | Воронка конверсии v2: произвольное окно, WoW, сценарные шаблоны | **Baseline да** | Backend + UI: cohort presets, custom bounds, WoW, slices, insights; UI custom range на `AnalyticsLeadConversionFunnelPage`. **Wave 2:** сохранённые сценарные шаблоны срезов. |
| 8.4 | NBA v2: rule engine, `assign_pipeline` в automation, rich triggers | **Частично** | Есть `lead_criteria_eval`, automation rules (`automation_rules`), G-8 next-action по сущностям. Нет единого «конструктора правил лидов» уровня плана; расширение триггеров — отдельный эпик. |
| 8.5 | Custom fields лидов: операторы фильтров, typed custom, UI правил | **Открыто** | Зависит от модели custom fields в БД и списка лидов; не смешивать с 8.1. |

## Рекомендуемый порядок работ (остаток)

1. **8.3 UI** — произвольное окно когорты + опционально WoW на custom range (без дублирования с `cohort_window_days`).
2. **8.3** — сохранённые сценарии срезов (если продуктово приоритетно) — отдельная таблица или localStorage v0.
3. **8.5** — контракт typed custom fields + фильтры в `GET /leads`.
4. **8.4** — матрица триггеров automation + связка с `lead_criteria_eval` / assign pipeline.
5. **8.2** — только после метрик поиска и решения pgvector vs API.

## Связь с §6.3 плана

| SSOT-блок | Фаза |
|-----------|------|
| Лиды / NBA / квалификация | 8 |
| Глобальный поиск | 8 (8.1 закрыт) |
| Воронка конверсии v2 | 8 (8.3 в работе) |
