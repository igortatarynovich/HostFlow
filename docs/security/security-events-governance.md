# Security events — governance (canonical layer)

Короткие правила, чтобы **security telemetry не дрейфовала** после введения canonical schema v1. Код: `backend/app/security/canonical_emit.py`, `event_taxonomy.py`, `event_redaction.py`, `events.py` (legacy shim).

---

## Что зафиксировать

| Правило | Смысл |
|---------|--------|
| **Event schema v1** | Текущий canonical contract — `emit_security_event_v1`, payload `schema: hostflow.security_event_canonical`, обязательные поля и семантика из Phase 2 spike и [`runtime-roadmap.md`](./runtime-roadmap.md) (раздел canonical fields). |
| **Новые `event_type`** | Только через **отдельный taxonomy PR**: добавить константу/имя, прогнать `validate_event_type`, обновить тесты; не «добавил строку в одном месте». |
| **Новые namespace / prefix** | Только через **review** (platform + security champion): расширение `ALLOWED_EVENT_PREFIXES` в `event_taxonomy.py` — осознанное решение, не случайный импорт. |
| **Breaking `schema_version` bump** | **Отдельный PR**: меняется обязательный набор полей или семантика — bump версии, запись в changelog `runtime-roadmap.md`, без смешивания с продуктовой логикой в том же PR. |
| **Новые producer call sites** | Только **`emit_security_event_v1`** (или тонкая обёртка над ним в том же модуле security). |
| **Legacy shim** | `emit_security_event` — **временный migration path**; новые события через него **не добавлять** (кроме расширения явного маппинга старых строк в рамках отдельного PR на миграцию). |
| **Raw security events** | **Запрещены**: произвольный `logger.info(..., extra={...})` с «security» смыслом вместо canonical emitter — нет. |
| **CLASS 3 / document / export / AI / search** | События на этих путях должны иметь **audit-grade** набор полей: `tenant_id`, `actor_id`, `correlation_id`, `entity_type`/`entity_id` где применимо, `result`, `source`; cross-tenant — `access_kind` / scope по SSOT. |
| **Redaction** | Обязательна **до** попадания в лог: только `extra` после `event_redaction`; чувствительные ключи не обходить. |
| **Transport** | **Не влияет на producers**: stdout / ELK / SIEM / queue — вне этого документа; продьюсеры не импортируют и не ветвятся по sink. |

---

## Почему это важно

Один короткий governance-файл останавливает **drift быстрее**, чем очередной технический скрипт без социального контракта: ревьюеры и авторы PR знают, *куда* смотреть и *что* нельзя ломать молча.

---

## CI enforcement (merge gate)

- **Workflow:** `.github/workflows/security-gates.yml` — job `no-raw-emit-security-event`.
- **Скрипт:** `scripts/security/check_no_raw_emit_security_event.py` — сканирует `backend/app/**/*.py`; падает, если встречается `emit_security_event(` не на строке с `def emit_security_event(` и файл **не** в allowlist.
- **Разрешено без allowlist:** только строки-определения `def emit_security_event(`; вызовы **`emit_security_event_v1(`** везде разрешены.
- **Allowlist:** `scripts/security/emit_security_event_allowlist.txt` — repo-relative пути; в начале файла **burn-down** комментарий. Сейчас явно разрешён только модуль legacy shim: `backend/app/security/events.py`.

### Как добавить исключение (редко)

1. Открыть `scripts/security/emit_security_event_allowlist.txt`.
2. Добавить **одну** строку с путём `path/to/file.py` (как в репо, `/`).
3. В PR описать: зачем временное исключение, ссылка на issue/задачу миграции на `emit_security_event_v1`, срок удаления из allowlist.

### Когда исключение **нельзя**

- Для **новых** security-событий или «быстрого лога» — только canonical emitter и taxonomy PR.
- Чтобы обойти redaction или CLASS 3 правила — запрещено; исправлять контракт события, не allowlist.

---

## Следующий кодовый шаг (после CI gate)

1. ~~CI grep на raw `emit_security_event(`~~ — сделано (`security-gates` + скрипт выше).
2. Controlled rollout: **document / signed URL / export** на `emit_security_event_v1` — **отдельные PR**, не смешивать с расширением allowlist без burn-down.

---

## Ownership (минимум)

- **Новые префиксы / namespaces** — approve: platform lead + security champion (или назначенный owner в команде).
- **Taxonomy PR** — второй reviewer с контекстом security roadmap.
- **Mandatory events** для critical paths — по мере rollout дополняется таблицей в этом файле или в `runtime-roadmap.md` (без дублирования деталей implementation).
