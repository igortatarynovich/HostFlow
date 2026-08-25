# Threat Model — Exports (CSV, reports, bulk download)

## Assets

- Массивы PII, CLASS 3 вложенности, история коммуникаций.

## Trust boundaries

- Авторизованный пользователь (в т.ч. insider) ↔ система экспорта ↔ файл в браузере/интеграции.

## Угрозы

| ID | Угроза | Вектор |
|----|--------|--------|
| EX-1 | Mass exfiltration | повторные большие экспорты без лимитов |
| EX-2 | Hidden columns leak | «внутренние» поля в CSV для client role |
| EX-3 | Async export IDOR | скачивание чужого job id |
| EX-4 | CSV injection | поля начинаются с `=`, `+`, `-`, `@` в Excel |

## Митигации (baseline)

- Audit: actor, report type, row count, time, channel.
- **Anomaly v1:** `export.anomaly.detected` при порогах row_count / byte_size / CLASS3 (см. `runtime-roadmap.md` Phase 4); не блокирует ответ.
- Rate limits + максимальный batch; watermarking — backlog post-MVP.
- Проверка владельца export job = тот же пользователь/tenant.
- Санитизация полей для CSV (префикс `'`, экранирование) для полей из пользовательского ввода.

## Тесты

- Роль без export → 403.
- Чужой `export_job_id` → отказ.
- Наличие audit записи (integration test или log assertion где принято).

## Связанные спеки

- `docs/specs/architecture/rbac_matrix.md` (действия export по ролям)
