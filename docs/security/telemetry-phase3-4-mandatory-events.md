# Phase 3 / 4 — mandatory security events (documents & exports)

Короткий **контракт для ревью**: какие `event_type` ожидаются на критичных read/export путях и какие поля канона v1 должны быть заполняемы. Детали схемы: [`runtime-roadmap.md`](./runtime-roadmap.md) (canonical fields), редaction: [`event_redaction.py`](../../backend/app/security/event_redaction.py).

Producers: только **`emit_security_event_v1`** или тонкие обёртки **`document_events` / `export_events`** (см. `scripts/security/check_telemetry_helpers_v1_only.py`).

---

## Document access (`document.*`)

| `event_type` | Когда | `entity_type` / `entity_id` | Обязательные смыслы в payload |
|--------------|--------|------------------------------|------------------------------|
| `document.metadata.read` | GET метаданных документа | `document` / UUID документа | `tenant_id`, `actor_id`, `correlation_id`, `access_kind`, `result`, `source`; в `extra`: `document_class`, при наличии `candidate_id`, при deny `reason` |
| `document.file.access_requested` | Выдача file-url (чтение URL) | `document` / UUID | то же + `extra` без сырых URL; при presigned-форме — только флаги (`has_presigned_url_shape`), не строка URL |
| `document.file.downloaded` | Отдача файла (stream / скачивание) | `document` / UUID | то же |
| `document.signed_url.generated` | Сгенерирован presigned / redirect URL | `document` или контекст intake | то же; **никогда** raw URL / token в `extra` |
| `document.signed_url.denied` | Отказ до выдачи URL / файла | `document` или кандидат (public) | `result=denied`, `reason` (код), без PII в `reason` |
| `document.signed_url.expired` | *Зарезервировано* — только если есть достоверная проверка TTL/replay | — | не эмитить «для галочки» |
| `document.signed_url.replay_denied` | *Зарезервировано* | — | то же |

---

## Export (`export.*`)

| `event_type` | Когда | `entity_type` / `entity_id` | Обязательные смыслы |
|--------------|--------|------------------------------|---------------------|
| `export.requested` | Доступ к export-пути подтверждён, начало сборки | `candidate` / `tenant` + соответствующий id | `tenant_id`, `actor_id`, `correlation_id`, `access_kind`, `result`, `source`, **`export_type`**, **`export_scope`**, **`contains_class3`**, **`bulk_operation`**; `filter_scope` — только короткий таксономический scope (см. `clip_export_filter_scope`) |
| `export.generated` | Артефакт собран | то же | + **`row_count`**, **`byte_size`** где применимо; **`async_job_id`** если появится async-export |
| `export.downloaded` | Ответ-вложение / stream отдан клиенту (где отделён от generated) | то же | те же метрики; без имён файлов с PII и без путей архива в `extra` |
| `export.denied` | Отказ (например owner-access / HTTP до сборки) | то же | `reason` как код, не сырой текст ошибки с PII |
| `export.expired` | *Зарезервировано* — async / signed TTL | — | не эмитить без реального сценария |

**Не логировать в `extra` и не обходить через `logger.*`:** сырые строки export, пути архивов, signed export URLs, произвольные `rows` / `records` (ключи зарезервированы под redaction в `event_redaction.py`).

---

## Сводка: общие канонические поля (v1)

| Поле | Document | Export |
|------|----------|--------|
| `tenant_id` | да | да |
| `actor_id` | да (или runtime default) | да где есть пользователь |
| `correlation_id` | да | да |
| `access_kind` | да (`session.info`) | да где сессия с bind |
| `entity_type` / `entity_id` | `document` + UUID (или `null` только где явно задокументировано) | `candidate` / `tenant` + id |
| `result` / `source` | да | да |
| Специфика в `extra` | allowlist `DOCUMENT_EVENT_EXTRA_ALLOWLIST` | allowlist `EXPORT_EVENT_EXTRA_ALLOWLIST` |

Изменения таксономии и новых call sites — отдельный PR + обновление этой таблицы.
