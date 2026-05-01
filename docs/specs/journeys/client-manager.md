# UAT 2.2.F — Client manager (`client_manager`)

**Профиль:** `client_manager` — handoff-first: `handoffQueue` → `hero` → `myTasks` → `todayPlanner` → `critical` → `quickActions`. Нет `bottlenecks` (agency pipeline не в фокусе).

---

## Шаг 1 — Work (обязательно для G-6)

**URL:** `/app/work`

- [ ] Первый блок — **Handoff queue** (pending/returned/accepted), не спрятан под scroll если есть данные.
- [ ] Hero framing: «candidates handed over… need a decision».
- [ ] Я могу сказать: «вижу **свой** план дня» — решения по handoff + мои задачи/планёрка.
- [ ] Нет блоков bottlenecks/risk/manager load (не должны рендериться).
- [ ] Links из handoff ведут на сущности без 404.

---

## Шаг 2 — Tasks / Calendar

**URL:** `/app/tasks`, `/app/calendar`

- [ ] Согласовано с панелями на Work Hub.

---

## Шаг 3 — Handoff detail (smoke)

- [ ] Открытие кандидата из очереди; primary CTA на карточке осмысленлен (G-8).

---

### Найденные баги

- [ ] (id) …

**Сессия:** дата ______ · окружение ______ · исполнитель ______

**Статус UAT 2.2.F:** ☐ PASS ☐ FAIL
