# UAT 2.2.D — Supervisor (`supervisor`)

**Профиль Work Hub:** `supervisor` — зеркало `admin_team` по секциям: `hero` → `critical` → `handoffQueue` → `myTasks` → `todayPlanner` → `riskDigest` → `managerLoad` → `bottlenecks` → `quickActions`.

---

## Шаг 1 — Work (обязательно для G-6)

**URL:** `/app/work`

- [ ] Role strip: «Supervisor» (или локализованный label).
- [ ] Я могу сказать: «вижу **свой** план дня» — личные задачи/планёрка **и** сигналы команды (critical, handoff, risk digest, manager load).
- [ ] `RiskDigestPanel`: heat badge / строки SLA + overdue + stale intake; primary CTA → `/app/overview`.
- [ ] `ManagerLoadPanel`: строки по рекрутерам; ссылка с `recruiter_id` открывает список кандидатов.
- [ ] Нет 404 на ссылках из панелей.
- [ ] Error/empty состояния осмысленны; retry на ошибке digest.

---

## Шаг 2 — Tasks

**URL:** `/app/tasks?tab=tasks&filter=overdue` (из Risk digest row)

- [ ] Фильтр overdue применяется; список согласован с счётчиком в digest (порядок величины).

---

## Шаг 3 — Calendar

**URL:** `/app/calendar` + smoke `?event_id=<planner-uuid>` из Today Planner

- [ ] Фокус по `event_id` работает (G-6 2f).

---

## Шаг 4 — Candidates drill-down

**URL:** из `ManagerLoadPanel` / critical

- [ ] `?recruiter_id=` распознаётся URL-sync (G-5 Stage F).

---

### Найденные баги

- [ ] (id) …

**Сессия:** дата ______ · окружение ______ · исполнитель ______

**Статус UAT 2.2.D:** ☐ PASS ☐ FAIL
