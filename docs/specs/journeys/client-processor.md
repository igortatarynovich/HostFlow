# UAT 2.2.G — Client processor (`client_processor`)

**Профиль:** `client_processor` — `handoffQueue` → `hero` → `myTasks` → `todayPlanner` → `critical` → `quickActions`; `defaultCounterScope: mine`.

---

## Шаг 1 — Work (обязательно для G-6)

**URL:** `/app/work`

- [ ] Handoff queue виден, если есть права и данные; иначе — адекватный empty.
- [ ] Я могу сказать: «вижу **свой** план дня» — назначенные кандидаты + задачи + календарь на сегодня.
- [ ] Нет agency-only панелей (`managerLoad`, `riskDigest`, `bottlenecks`).
- [ ] Critical использует team-scoped ops там, где задумано профилем — счётчики не «пустые заглушки» без объяснения.

---

## Шаг 2 — Tasks

**URL:** `/app/tasks`

- [ ] Hub preview (`myTasks`) совпадает по смыслу со списком (overdue / today / tomorrow).

---

## Шаг 3 — Calendar

**URL:** `/app/calendar`

- [ ] События на сегодня в планёрке совпадают с календарём.

---

### Найденные баги

- [ ] (id) …

**Сессия:** дата ______ · окружение ______ · исполнитель ______

**Статус UAT 2.2.G:** ☐ PASS ☐ FAIL
