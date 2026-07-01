# Vacancy Statuses — backend `Vacancy.status` ↔ UI states

**Назначение:** один справочник по поводу `Vacancy.status` — какие значения существуют сегодня, как они используются, чем отличаются от `is_active`/`is_archived`, и каким должен быть канонический enum.

**Связанные документы:**

- `docs/HOSTFLOW_AUDIT_AND_PLAN.md` Phase 2 §2.6.D (todo, закрываемый этим документом).
- `docs/specs/operations-loop.md` §2 (NBA для vacancy).
- `docs/specs/operational-metrics.md` (метрика «open vacancies без кандидатов»).

**Краткое решение:** ввести Python enum `VacancyStatus = {open, on_hold, closed, filled, cancelled}` (без `paused` / `archived`). Колонка `vacancies.status` остаётся `TEXT NOT NULL DEFAULT 'open'` (без миграции на postgres ENUM, чтобы не блокировать). UI унифицируется на тех же 5 значениях. `is_archived` остаётся отдельным булевым флагом «soft-delete».

---

## 1. Текущая модель

```69:107:backend/app/models/vacancy.py
    status: Mapped[str] = mapped_column(String, nullable=False, default="open")
    ...
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("1")
    )
    is_archived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0")
    )
```

- **`status`** — `TEXT` (без длины), NOT NULL, default `"open"`. **Не enum** — свободная строка. Раньше был postgres ENUM (`open|closed`), мигрирован в TEXT в `backend/alembic/versions/202512090002_vacancies_status_text.py:19-22`:

```sql
ALTER TABLE vacancies ALTER COLUMN status DROP DEFAULT;
ALTER TABLE vacancies ALTER COLUMN status TYPE TEXT USING status::text;
ALTER TABLE vacancies ALTER COLUMN status SET DEFAULT 'open';
DROP TYPE IF EXISTS vacancystatus;
```

- **`is_active`** — boolean, default `True`. Семантически — «вакансия принимает кандидатов».
- **`is_archived`** — boolean, default `False`. Семантически — «вакансия скрыта из default-списков (soft-delete)».

API-схема (`backend/app/api/v1/vacancies/schemas.py:17-18, 67-68`) — `status: str` без `Literal`/`Enum`.

**Frontend type** (`hostflow-frontend/src/api/types.ts:527-532`, `hostflow-frontend/src/api/vacancies.ts:27-31`) — `status: string`. Нет именованного `VacancyStatus`.

---

## 2. Реальный набор значений в коде

### 2.1. Что бэкенд **записывает** (literals)

| Точка | Значение |
|---|---|
| `VacancyService.create` | `"open"` (default из payload) |
| `VacancyService.patch` через `is_archived: true` | `status="archived"`, `is_archived=true`, `is_active=false` |
| `VacancyService.patch` через `is_open: true` | `status="open"`, `is_active=true`, `is_archived=false` |
| `VacancyService.patch` через `is_open: false` | `status="closed"`, `is_active=false`, `is_archived=true` |
| `VacancyService.patch` со свободным `status` | любая строка, прошедшая `validate_status_transition` (см. §2.4) |
| `db/seeds/dev_full_seed.py:613` | `"open"` |

`VacancyService.patch` (`backend/app/api/v1/vacancies/service.py:182-242`):

```182:193:backend/app/api/v1/vacancies/service.py
        status_val = _pick("status", "status_alt1", "status_alt2")
        if status_val is not None:
            validate_status_transition(getattr(obj, "status", "new"), status_val)
            values["status"] = status_val
            normalized_status = str(status_val).strip().lower()
            if payload.is_archived is None:
                if normalized_status == "archived":
                    values["is_archived"] = True
                    values.setdefault("is_active", False)
                else:
                    values["is_archived"] = False
                    values.setdefault("is_active", True)
```

```225:242:backend/app/api/v1/vacancies/service.py
        if payload.is_archived is not None:
            archived_flag = bool(payload.is_archived)
            values["is_archived"] = archived_flag
            if archived_flag:
                values.setdefault("is_active", False)
                values.setdefault("status", "archived")
            else:
                values.setdefault("is_active", True)
                values.setdefault("status", getattr(obj, "status", "open") or "open")
        ...
        if payload.is_open is not None:
            open_flag = bool(payload.is_open)
            values["is_active"] = open_flag
            values["is_archived"] = not open_flag
            values["status"] = "open" if open_flag else "closed"
```

### 2.2. Что бэкенд **читает** (filters / branches)

| Точка | Значение(я) | Поведение |
|---|---|---|
| `backend/app/modules/leads/crud.py:156, 174` | `"open"` | счёт открытых вакансий tenant-а |
| `backend/app/api/v1/tenants/service.py:151` | `"open"` | tenant metrics |
| `backend/app/api/v1/analytics.py:381` | `"open"` | KPI "open vacancies" |
| `backend/app/services/tenant_quota.py:100` | `"open"` | quota: open vacancies count vs license |
| `backend/app/api/v1/vacancies/repo.py:131-141` | `"archived"` (через `is_archived`), любое другое — strict equality `Vacancy.status == status` | list filter |

**`vacancy_is_recruiting`** (`backend/app/services/uos_auto_activities.py:66-75`) — единственный helper, который перечисляет «не-recruiting» статусы:

```66:75:backend/app/services/uos_auto_activities.py
def vacancy_is_recruiting(v: Any) -> bool:
    if bool(getattr(v, "is_archived", False)):
        return False
    st = str(getattr(v, "status", "") or "").strip().lower()
    if st in ("closed", "archived", "cancelled", "filled", "draft", "on_hold"):
        return False
    if st == "open":
        return True
    return bool(getattr(v, "is_active", True))
```

Это **единственное место**, где упоминаются `cancelled`, `filled`, `draft`, `on_hold` — но только для отрицания (если status таков, считаем «не-recruiting»). Бэкенд **нигде** не записывает `filled` / `cancelled` автоматически.

### 2.3. Что NBA трактует как терминал

`backend/app/services/next_action.py:477-478`:

```python
_VACANCY_TERMINAL_STATUS_CODES: frozenset[str] = frozenset({"closed"})
_VACANCY_PAUSED_STATUS_CODES: frozenset[str] = frozenset({"paused"})
```

- Терминал: `is_archived=true` ИЛИ `status == "closed"`.
- Idle: `status == "paused"` (НЕ `on_hold`!).

### 2.4. `validate_status_transition` (исторический контекст; см. §6 Stage D для актуального состояния)

Изначально `validate_status_transition` (`backend/app/api/v1/vacancies/rules.py`) работал по матрице **candidate** stages (`new`/`interview`/`hiring`/`employed`/`probation`/`rejected`) и для vacancy-значений (`open`/`closed`/`on_hold`/...) silently no-op-ал — т.е. в API можно было поставить любую строку. Эта дыра закрыта в Stage D: для vacancy теперь зовётся `validate_vacancy_status_transition` со строгой матрицей по §5.3, а старый candidate-валидатор оставлен в файле без изменений (никем больше не используется, но и удалять без аудита нет смысла).

---

## 3. Что фронт **показывает**

### 3.1. Form / detail (canonical edit values)

```29:34:hostflow-frontend/src/components/vacancies/VacancyDetail.tsx
const STATUS_OPTIONS = ['open', 'paused', 'closed'] as const
...
  status: z.enum(STATUS_OPTIONS).default('open'),
```

Любой неизвестный статус из API **схлопывается в `open`** при загрузке формы:

```124:127:hostflow-frontend/src/components/vacancies/VacancyDetail.tsx
  const rawStatus = (source?.status ?? source?.state ?? source?.stage ?? 'open') as string
  const normalizedStatus = (STATUS_OPTIONS.includes(rawStatus as typeof STATUS_OPTIONS[number])
    ? (rawStatus as typeof STATUS_OPTIONS[number])
    : 'open')
```

`VacancyForm.tsx:14` использует тот же `STATUS_OPTIONS = ['open', 'paused', 'closed']`.

### 3.2. List filter

```235:241:hostflow-frontend/src/components/vacancies/VacancyList.tsx
  const statusOptions = useMemo(
    () => [
      { value: '', label: t('app.vacancies.list.status.all') },
      { value: 'open', label: t('app.vacancies.list.status.open') },
      { value: 'on_hold', label: t('app.vacancies.list.status.on_hold') },
      { value: 'closed', label: t('app.vacancies.list.status.closed') },
      { value: 'archived', label: t('app.vacancies.list.status.archived') },
```

### 3.3. Badge

```168:178:hostflow-frontend/src/components/vacancies/VacancyList.tsx
function StatusBadge({ value, archived, label }: ...) {
  const v = archived ? 'archived' : (value || '')
  const badgeClass = archived
    ? 'badge badge-ghost'
    : v === 'open' ? 'badge badge-success'
    : v === 'on_hold' ? 'badge badge-warning'
    : v === 'closed' ? 'badge badge-error'
    : 'badge'
```

### 3.4. **Главное расхождение**

- **Form** редактирует `paused`.
- **List** фильтрует и стилизует `on_hold`.
- **NBA** ожидает `paused` для idle-индикации.
- **`vacancy_is_recruiting`** считает `on_hold` не-recruiting.

Если пользователь в форме поставил «Paused», список покажет вакансию **без warning-стиля** (badge fallback на дефолтный), потому что `paused != on_hold`. NBA будет считать её idle. Это видимый баг.

---

## 4. `is_active` / `is_archived` — пересечения с `status`

| Сценарий | Что обновляется |
|---|---|
| `PATCH { is_open: true }` | `is_active=true`, `is_archived=false`, `status="open"` |
| `PATCH { is_open: false }` | `is_active=false`, `is_archived=true`, `status="closed"` |
| `PATCH { is_archived: true }` | `is_archived=true`, `is_active=false`, `status="archived"` |
| `PATCH { is_archived: false }` | `is_archived=false`, `is_active=true`, `status` → текущий или `"open"` |
| `PATCH { status: "..." }` без `is_archived` | `status` пишется как есть; `is_archived` авто-проставляется по `status == "archived"` |

`backend/app/modules/vacancies/crud.py::archive_vacancy` ставит **только** `is_archived=true`, **без** обновления `status`. Это создаёт `is_archived=true && status="open"` гибрид — другие читатели (`vacancy_is_recruiting`, NBA) с этим справляются, но на UI badge будет «archived» (по `is_archived`), а форма покажет «open» — несогласованность.

**Семантические перекрытия:**

- `is_archived=true ⇔ status="archived"` (по факту, но поддерживается только в API-патче, не в archive_vacancy).
- `is_active=false ⇔ status ∈ {closed, archived, paused, ...}` (по сути; нет explicit-сохранения).

`is_active` сегодня — **redundant**: можно вычислить из `status` + `is_archived`. Но т.к. фильтры и счётчики опираются именно на `is_archived` (а не на `status="archived"`), мы оставляем оба флага и канонизируем правила.

---

## 5. Канонический контракт (target state)

### 5.1. Python enum

```python
# backend/app/models/enums.py
class VacancyStatus(str, Enum):
    open = "open"
    on_hold = "on_hold"
    closed = "closed"
    filled = "filled"
    cancelled = "cancelled"
```

**Решение по `paused` vs `on_hold`:** убираем `paused` (это не-английский гибрид), оставляем `on_hold` (стандартный термин ATS). UI меняем на `on_hold`, миграция нормализует существующие `paused` → `on_hold`.

**Решение по `archived` как статусу:** убираем (`archived` остаётся **только** boolean-флагом `is_archived`). Это устраняет двойной источник truth.

**Решение по `draft`:** **не вводим**. Сегодня черновик вакансии не моделируется отдельно (вакансия создаётся сразу видимой). Если в Phase 4 понадобится — добавим тогда.

### 5.2. Семантика финальных статусов

| Статус | Значение | Кто пишет |
|---|---|---|
| `open` | принимает кандидатов | default; manual reopen |
| `on_hold` | временно приостановлена; не показывается рекрутерам как приоритет, но не закрыта | manual |
| `closed` | закрыта без найма (отказ клиента, сменились приоритеты) | manual |
| `filled` | закрыта успешным наймом | автомат при `Candidate.stage == 'employed'` для **последнего активного** candidate-а на вакансии (см. §5.5) |
| `cancelled` | отменена (ошибочно создана, отменена клиентом до начала работы) | manual |

`is_archived` — ортогонально: «спрятать вакансию из default-списков». Может применяться к **любому** не-`open` статусу (типичный flow: `closed/filled/cancelled` → archive через 30 дней).

### 5.3. Допустимые переходы

```
open → on_hold | closed | filled | cancelled
on_hold → open | closed | cancelled
closed → open  (reopen)
filled → open  (reopen — нанимаем ещё одного)
cancelled → open  (восстановление)
```

Запрещены: `closed → filled`, `cancelled → filled`, `filled → cancelled` (если нужен — сначала reopen).

`validate_status_transition` для vacancies должна стать строгой (сегодня пропускает любое значение, см. §2.4). Это **breaking change** для PATCH-API — нужен deprecation-период.

### 5.4. UI контракт

| Слой | Канонический набор |
|---|---|
| `VacancyDetail` form | `open`, `on_hold`, `closed`, `filled`, `cancelled` |
| `VacancyList` filter | `All`, `Open`, `On hold`, `Closed`, `Filled`, `Cancelled`, `Archived` (отдельный фильтр для `is_archived`) |
| `StatusBadge` | success=open, warning=on_hold, error=closed/cancelled, info=filled, ghost=archived |
| `Pipeline` page | по умолчанию показывает `open + on_hold`; чекбокс «Show closed/filled» |

### 5.5. Auto-flip при найме

В Phase 2.6.D out-of-scope (это поведенческое изменение, требующее UX-решения), но фиксируем как открытую задачу:

- Когда `Candidate.stage` переходит в `employed` И на вакансии нет других active-кандидатов в pre-hire стадиях → `Vacancy.status` авто-flip в `filled`.
- Реализация — в `services/candidate_lifecycle.py` (рядом с G-1 zero-leak логикой).
- Конфигурируется per-tenant: `tenant.settings.vacancies.auto_close_on_hire = bool` (default `false` пока поведение не подтверждено в UAT).

### 5.6. Миграция данных

Одноразовый script (`backend/alembic/versions/<new>_canonize_vacancy_status.py`):

1. `UPDATE vacancies SET status = 'on_hold' WHERE status = 'paused'`
2. `UPDATE vacancies SET status = 'open', is_archived = true WHERE status = 'archived'` (`archived` больше не статус — переезжает в boolean)
3. `UPDATE vacancies SET status = 'open' WHERE status NOT IN ('open','on_hold','closed','filled','cancelled')` — clamp всего неизвестного к `open` (защитная нормализация).
4. **НЕ** конвертировать `String` → postgres ENUM (избегаем downtime). Колонка остаётся `TEXT`, валидация — на уровне Python enum в `LeadOut`/`VacancyOut`.

### 5.7. Frontend type

```ts
// hostflow-frontend/src/api/types.ts (добавить)
export type VacancyStatus = 'open' | 'on_hold' | 'closed' | 'filled' | 'cancelled'

// Vacancy.status в типах сделать VacancyStatus вместо string.
```

`STATUS_OPTIONS` в `VacancyDetail.tsx` / `VacancyForm.tsx` импортировать из общего модуля.

---

## 6. План исполнения

| Стадия | Зависимости | Риск | Объём | Статус |
|---|---|---|---|---|
| Stage A — Python enum + Pydantic нормализация в `VacancyOut`/`VacancyPatch` | — | низкий | ½ дня | **DONE** |
| Stage B — миграция данных (paused→on_hold; archived-status→is_archived; clamp unknown) | A | **средний** (data migration) | ~1 день + ревью | **DONE** |
| Stage C — UI унификация (`STATUS_OPTIONS` shared, badge map, list filter) | A | низкий | ~1 день | **DONE** |
| Stage D — `validate_status_transition` для vacancy с допустимыми переходами | A | средний (breaking PATCH-contract) | ½ дня | **DONE** |
| Stage E — auto-flip `Candidate.employed → Vacancy.filled` (опт-ин) | A, B | средний (UX-решение нужно) | ~1 день | TODO |
| Stage F — обновить `_VACANCY_TERMINAL_STATUS_CODES` / `_VACANCY_PAUSED_STATUS_CODES` в NBA | A | низкий | ½ дня | **DONE** |
| Stage G — `archive_vacancy` синхронизирует `status` (если `status="open"` И archive → `status="closed"` или сохранять?) | B | низкий | ½ дня | **DONE** |

**Recommended порядок:** A → C → F → B → D → G → E. Auto-flip (E) делаем последним и за feature-flag.

**Текущий статус (2026-04-19):** Stage A + B + C + D + F + G завершены. UI-баг `paused`/`on_hold` рассогласования закрыт, новые терминальные коды (`filled`, `cancelled`) появились в NBA и в form/list, переходы валидируются строгой матрицей, archive синхронизирует `status` чтобы инвариант `is_active = (status='open' AND NOT is_archived)` держался.

- **Stage A** (`backend/app/models/vacancy.py` + `backend/app/api/v1/vacancies/schemas.py`): `VacancyStatus` enum + `normalize_vacancy_status` (alias `paused → on_hold`, unknown → `open` + warning). Применён в `VacancyIn.status`, `VacancyPatch.status|status_alt1|status_alt2`, `VacancyOut.status`. Тесты в `backend/tests/test_vacancy_status_normalization.py` (30 шт.).
- **Stage F** (`backend/app/services/next_action.py`): `_VACANCY_TERMINAL_STATUS_CODES = {closed, filled, cancelled}`, `_VACANCY_PAUSED_STATUS_CODES = {on_hold, paused}` (legacy alias сохранён до Stage B backfill). Тесты в `backend/tests/test_vacancy_next_action.py` — добавлены branch-тесты для `filled`, `cancelled`, `on_hold` и backward-compat для `paused`.
- **Stage C** (`hostflow-frontend/src/api/vacancies.ts` + `VacancyForm.tsx` + `VacancyDetail.tsx` + `VacancyList.tsx` + i18n EN/RU/PL): `VACANCY_STATUSES` + `normalizeVacancyStatus` экспортируются из `api/vacancies.ts`. Form/Detail используют один enum, list-filter включает `filled`/`cancelled`, badge map расширен. Frontend typecheck чист.
- **Stage B** (`backend/alembic/versions/202604031200_vac_status_canon.py`): backfill `paused → on_hold`, `archived → closed + is_archived=true`, lowercase canonical, clamp unknown → `open` с pg `RAISE NOTICE`. Idempotent, postgres-only. SQLite-test runs пропускают.
- **Stage D** (`backend/app/api/v1/vacancies/rules.py` + `service.py`): новая функция `validate_vacancy_status_transition(cur, new)` с матрицей `VACANCY_ALLOWED_TRANSITIONS` ровно по §5.3 (open → on_hold|closed|filled|cancelled; on_hold → open|closed|cancelled; closed/filled/cancelled → open). Same-status patches — no-op. Inputs прогоняются через `normalize_vacancy_status` ⇒ legacy `paused`, casing, whitespace ловятся. `VacancyService.patch` теперь зовёт vacancy-валидатор (а не candidate-stage `validate_status_transition`, который для vacancy-значений был silent no-op). Router конвертит `ValueError → HTTP 409 Conflict` (state conflict, не malformed input — исправили акцептанс §8.3 с 422 на 409). Тесты: `backend/tests/test_vacancy_status_transitions.py` — 34 unit-кейса, включая matrix self-consistency guards (новые статусы автоматически ломают тест, пока их не добавят в матрицу). API-кейсы в `tests/api/test_vacancies.py`: open→filled allowed, closed→filled blocked (409), on_hold→filled blocked, legacy `paused` alias → `on_hold`.
- **Stage G** (`backend/app/api/v1/vacancies/service.py` + `backend/app/modules/vacancies/crud.py`): убрали запись `status='archived'` из всех путей. (a) В `VacancyService.patch` legacy alias `status='archived'` теперь маршрутизируется в `status='closed' + is_archived=True` (intent сохранён, persisted row каноничен; transition validator пропускается — это alias-ветка, не generic move). (b) В archive-flag-ветке `setdefault("status", "archived")` заменён на `setdefault("status", VacancyStatus.closed.value)` для active-исходов; терминалы (closed/filled/cancelled) сохраняют свой `status`, archive — это visibility flag сверху. (c) `crud.archive_vacancy` теперь grew up: всегда ставит `is_archived=True` + `is_active=False` + `status='closed'` если текущий статус active (open/on_hold/paused/empty); терминалы не трогает. Это закрывает hybrid `is_archived=True && status='open'` который раньше путал NBA, list-фильтры и `vacancy_is_recruiting`. (d) `crud.unarchive_vacancy` НЕ авто-reopen-ит status — оператор должен явно `PATCH {status: 'open'}`, иначе Stage D guarantee "every state move is intentional" нарушится. Тесты: `tests/api/test_vacancies.py::test_archive_flag_canonicalises_status_to_closed`, `test_legacy_status_archived_alias_routes_to_closed_plus_is_archived` — оба ассертят `status='closed' + is_archived=True + is_active=False` после archive (был раньше `status='archived'`).

**Итого по Phase 2.6.D:** 6 из 7 sub-stages закрыто. Открыт **Stage E** (auto-flip on hire) — UX-вопрос (см. §9), требует решения по `Vacancy.headcount`; делаем последним и за feature-flag.

---

## 7. Контракты и инварианты

1. **Канонические значения:** `status ∈ {open, on_hold, closed, filled, cancelled}` строго после Stage B. Любая запись с другим значением — data-corruption.
2. **`archived` — это `is_archived`**, не `status`. После Stage B `status="archived"` не должно встречаться.
3. **Терминальные статусы** (для NBA, lifecycle): `closed`, `filled`, `cancelled`. `is_archived=true` — также терминал (вакансия скрыта).
4. **Idle статус:** `on_hold` (не `paused`). NBA читает его для priority IDLE.
5. **`is_active` — derived**, но сохраняем как explicit-флаг для производительности фильтров. Инвариант: `is_active = (status == 'open') AND NOT is_archived`. Должен поддерживаться writer-ом — добавить assertion в `VacancyService.patch`.
6. **Reopen flow:** `closed | filled | cancelled → open` разрешён, но требует подтверждения в UI (модалка «Reopen vacancy?»). Reopen из `is_archived=true` тоже допустим, но снимает archive-флаг.

---

## 8. Acceptance / тесты

1. **Enum coverage** — `VacancyStatus` exhaustively проверяется в `VacancyOut`.
2. **Миграция** — после Stage B нет ни одной строки в `vacancies` со status вне канонического множества (DB-assert).
3. **Transition validation** — `PATCH /vacancies/{id}` с запрещённым переходом возвращает **HTTP 409 Conflict** (state conflict, не malformed input). Стандартизировано в Stage D — router конвертит `ValueError` от `validate_vacancy_status_transition` в 409. Спек ранее предлагал 422, но 409 семантически точнее.
4. **NBA** — `compute_vacancy_next_action` отдаёт `terminal_filled`, `terminal_cancelled` reason_codes для соответствующих статусов; idle для `on_hold`.
5. **UI consistency** — `VacancyForm`, `VacancyList`, `StatusBadge`, `Pipeline` все используют один `STATUS_OPTIONS` из shared-модуля. Test: snapshot для каждого статуса.
6. **`is_active` invariant** — для каждой вакансии `is_active == (status == 'open' AND NOT is_archived)`. Test: backfill-чек после Stage B; runtime-assert в writer.
7. **Auto-flip (если включено)** — при `Candidate.stage = employed` для последнего active candidate-а на вакансии → `Vacancy.status = filled`. Test: candidate lifecycle → vacancy auto-flip + audit-event.
8. **Aggregate-drilldown consistency** — после канонизации обновить `docs/specs/operational-metrics.md` (метрика «open vacancies без кандидатов» теперь имеет чёткое определение `status='open' AND is_archived=false AND NOT EXISTS active candidates`).

---

## 9. Открытые вопросы

- **Auto-flip on hire** — UX-вопрос: если рекрутер нанимает одного из десяти на вакансию, вакансия должна автоматически становиться `filled`? Ответ зависит от того, моделируется ли «headcount > 1» (сколько слотов на вакансии). Сейчас в модели нет `headcount`, считаем 1 слот. **Решение:** добавить `Vacancy.headcount: int default 1`; auto-flip срабатывает при `hired_count >= headcount`.
- **`draft` статус** — нужен ли черновик вакансии (ручной ввод, не публикуется)? Сегодня нет, новые вакансии сразу `open`. Если в Phase 4 появится «save draft» — добавить `draft` (между нет и `open`).
- **Reopen sla** — стоит ли ограничивать reopen после `cancelled` (например, 30 дней)? Откладываем до UAT.
- **`is_active` deprecation** — можно ли удалить колонку и вычислять через computed-field? Возможно, но требует ревью всех querу `WHERE is_active = true`. Откладываем до Phase 6.
- **Translation keys** — текущий `app.vacancies.list.status.on_hold` уже есть для list, нужен такой же для form/detail. Аудит i18n после Stage C.
