# Security / runtime cycle — operational checklists (HostFlow)

Практические задачи с **измеримым результатом**. Не governance policy: только процедуры, шаблоны таблиц и ссылки на существующие чеклисты.

Связанный отчёт спринта: [`../runtime-validation-report-hf-sec-stabilization-01.md`](../runtime-validation-report-hf-sec-stabilization-01.md).

---

## Задача 1 — Runtime log validation (staging)

**Цель:** оценить качество реального `hostflow.security.events` потока.

### Сделать

1. На staging собрать **100–300** последних строк логера `hostflow.security.events` (или эквивалент JSON в stdout/Loki).
2. Отфильтровать по `category` / `event_type`:
   - `document.*`
   - `export.*`
   - `superadmin.*` / `auth.*` (elevated)
   - `webhook.*` / worker-related `source` (`http:communications_scheduler`, `http:arq:…`, и т.д.)

### Пример (jq, если одна JSON-строка на событие в поле `security_event`)

Зависит от формата вашего collector; адаптируйте путь к payload.

```bash
# Псевдокод: из файла sample.ndjson вытащить actor_id distribution
grep 'security_event' sample.ndjson | jq -r '.security_event.actor_id' | sort | uniq -c | sort -nr
grep 'security_event' sample.ndjson | jq -r '.security_event.correlation_id' | awk 'length==0' | wc -l
grep 'security_event' sample.ndjson | jq -r '.security_event.tenant_id' | awk 'length==0' | wc -l
```

### Проверить

| Проверка | Критерий «ок» |
|-----------|----------------|
| Actor | Нет массовых `system:unknown` без ожидаемого `source`; нет пустого `actor_id` |
| Correlation | Нет пустого `correlation_id`; цепочки HTTP→worker не обрываются произвольно |
| Tenant | Нет `tenant_id: null` там, где ожидается tenant-bound событие; нет несогласованности с `entity_id` |
| Redaction | В JSON **нет** строковых полей с подписями URL, именами файлов с ФИО, prompt/query, токенами, путями архивов |

### Результат (заполнить после прогона)

| Область | Status (ok/issues) | Fixes / tickets |
|---------|-------------------|-----------------|
| Actor | | |
| Correlation | | |
| Tenant | | |
| Redaction | | |
| Sample size | | |

---

## Задача 2 — Legacy shim burn-down #1

**Цель:** уменьшить legacy telemetry surface.

### Инвентаризация (репозиторий, 2026-05-12)

| Паттерн | Результат |
|---------|-----------|
| `emit_security_event(` в `backend/app` вне `def emit_security_event` | **0** (только `backend/app/security/events.py`) |
| Импорт `emit_security_event` из `security.events` | **0** |
| Allowlist `scripts/security/emit_security_event_allowlist.txt` | **1** путь (`events.py`) |

**Вывод:** мигрировать **3–5 call sites** в этом цикле **нечего** — внешние вызовы уже на `emit_security_event_v1`. Следующий burn-down PR — только когда появится новый legacy caller (сразу v1 + не расширять allowlist).

**Acceptance:** CI зелёный; allowlist **не** вырос; поведение не менялось.

---

## Задача 3 — Worker context audit (код)

Актуальные точки **`tenant_enforced_session`** / **`security_job_context`** в приложении:

| Job / flow | Файл | Tenant | Actor | Correlation | `security_job_context` | Status |
|------------|------|--------|-------|-------------|------------------------|--------|
| Email poll + dispatch (per tenant) | `communications_scheduler.py` | `tenant_enforced_session` + bind | `system:communications-scheduler` | опционально (ген. в helper при `None`) | внутри `tenant_enforced_session` | **OK** |
| Converted lead sweep | `communications_scheduler.py` | да | `system:converted-lead-sweep` | опционально | да | **OK** |
| Risk intel hourly | `communications_scheduler.py` | да | `system:risk-intel-hourly` | опционально | да | **OK** |
| ARQ `automation_evaluate_trigger` | `arq_worker.py` | да | job arg или `system:automation_evaluate_trigger` | опционально | да | **OK** |
| Meta webhook | `modules/leads/webhook.py` | bind в handler | `system:meta-leads-webhook` | из запроса | оборачивает обработчик | **OK** |
| Generic inbound | `modules/leads/inbound_public.py` | bind | `system:leads-generic-inbound-webhook` | из запроса | да | **OK** |

**Замечания:** у scheduler-пассов correlation часто не передаётся — для сквозного трейсинга рассмотреть передачу `correlation_id` из tick/request (отдельный маленький PR, не в этом документе).

**Exports / reminders как фон:** синхронные export API идут через `get_db_with_tenant`; отдельного background export worker с `tenant_enforced_session` в коде **не** найдено — при появлении фонового экспорта обязателен тот же контракт.

---

## Задача 4–5 — PR process + Search/AI entry

Реализовано в репозитории:

- Расширен [`../security-review-checklist.md`](../security-review-checklist.md): блок **mini-review** для high-risk surfaces и блок **Search/AI feature entry (merge criterion)**.
- Обновлён [`.github/pull_request_template.md`](../../../.github/pull_request_template.md): строки таблицы risk + явная отсылка к чеклисту.

**Measurable outcome:** reviewer открывает один файл чеклиста и видит обязательные критерии для AI/search/retrieval.

---

## Задача 6 — Security event volume snapshot

**Цель:** шум и полезность событий на staging/prod-lite.

### Сделать

1. За окно **24h** (или 72h) агрегировать: `event_type`, `result`, `source`.
2. Топ-20 по count; отдельно топ `result=denied`.
3. Оценить cardinality по `source` и по редким `event_type`.

### Результат (заполнить вручную)

**Noisy (сократить / снизить severity / объединить):**

- …

**Useful (оставить):**

- …

**Suspicious (расследовать):**

- …

**Dead (не встречаются / удалить из roadmap ожиданий):**

- …

---

## Задача 7 — Document access flow (manual)

Пройти на **staging** (ручной или E2E):

| Шаг | Проверить в логах |
|-----|-------------------|
| Document read | `document.metadata.read`, tenant/actor/correlation |
| Presigned / file-url | `document.signed_url.*` / `document.file.*`, нет raw URL в `extra` |
| Denied | `document.signed_url.denied` или `export.denied` с `reason` |
| Export | `export.requested` / `generated` / `downloaded` где применимо |
| Public intake | события с `intake_channel` / без утечки PII |
| Expired (если есть сценарий) | только если есть достоверный путь |

**Результат:** ok/issues — вписать в таблицу задачи 1 или отдельный тикет.

---

## Что не делать в этом цикле

SIEM, anomaly engine, realtime alerts, dashboards, Kafka, OpenTelemetry migration, compliance expansion, массовый rollout telemetry.
