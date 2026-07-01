# UAT 2.2.C — Administrator (`administrator`)

**План:** Solo vs Team влияет на профиль Work Hub (`resolveWorkHubProfile`: `GET /users/me` → `is_solo_admin` → `admin_solo`, иначе `admin_team`). Источник секций: `hostflow-frontend/src/modules/workHub/profile.ts`.

**Предусловия прогона (2.2.C):** тенант на тарифе **Solo** и один администратор без «полноценной» команды, чтобы `is_solo_admin === true` и отрисовался **`admin_solo`**. Если нужно проверить **Team** (`admin_team`) — отдельная сессия или прогон **2.2.D** (supervisor на Team).

**Дефекты:** не вносить в этот файл — только в **[`UAT_DEFECT_LOG.md`](./UAT_DEFECT_LOG.md)**; owner / ETA — **`docs/SSOT.md` §2.1**.

---

## Шаг 1 — Work (обязательно для G-6)

**URL:** `/app/work`

**Ожидаемое поведение:** Role strip показывает персону Owner; hero и секции соответствуют профилю.

**Solo (`admin_solo`):** секции по порядку — `hero` → `critical` → `myTasks` → `todayPlanner` → `bottlenecks` → `quickActions`. Нет `handoffQueue`, `riskDigest`, `managerLoad`.

**Team (`admin_team`):** `hero` → `critical` → `handoffQueue` → `myTasks` → `todayPlanner` → `riskDigest` → `managerLoad` → `bottlenecks` → `quickActions`.

- [ ] Страница открывается; при ошибке загрузки — карточка с **Refresh**.
- [ ] Я могу сказать: «вижу **свой** план дня» (задачи + планёрка; на Team — ещё handoff / risk digest / team load).
- [ ] `MyTasksPanel` и `TodayPlannerPanel` видны при `notifications.view`; иначе секции корректно скрыты (нет бесконечного 403).
- [ ] На **Team**: `RiskDigestPanel` виден для роли administrator; CTA ведёт на `/app/overview`; строки ведут на tasks overdue / leads stale (проверить отсутствие 404).
- [ ] На **Team**: `ManagerLoadPanel` виден при `candidates.view`; drill-down на кандидатов с `recruiter_id` открывается.
- [ ] Deep-link из hero/critical (candidates, leads, tasks) не даёт 404.
- [ ] Mobile (≤ 640 px): primary-действия доступны без горизонтального скролла.

---

## Шаг 2 — Tasks

**URL:** `/app/tasks`

- [ ] Список и счётчики согласованы (G-7 parity, если включён planner-merge).
- [ ] Complete/snooze обновляет hub при возврате на `/app/work` (событие `reminder-updated` / focus).

---

## Шаг 3 — Calendar

**URL:** `/app/calendar`

- [ ] Открывается; при наличии `?event_id=` из Work Hub — фокус на событии (G-6 Stage 2f).

---

## Шаг 4 — Candidates (выборочно)

**URL:** `/app/candidates`

- [ ] Открывается; фильтры из drill-down Work Hub / dashboard совпадают с ожиданием.

---

## Шаг 5 — Settings / billing (если применимо к Solo)

**URL:** `/app/settings/billing` (сравнение планов: `/app/settings/billing/plan`).

- [ ] Виден тариф / лимиты без «шок-модалки» (см. `personas.md`); при высокой загрузке квот — soft-баннер (не блокирующий), не неожиданная модалка на каждом клике.

---

### Итог сессии

- Метаданные (дата, окружение, исполнитель, тенант/план) и дефекты — **[`UAT_DEFECT_LOG.md`](./UAT_DEFECT_LOG.md)**.
- После полного **PASS** без блокеров — вручную отметить **2.2.C** в **`docs/HOSTFLOW_AUDIT_AND_PLAN.md`**.
