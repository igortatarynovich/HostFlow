# UAT 2.2.E — Recruiter (`recruiter`)

**Контекст:** agency tenant (`Tenant.type` agency). Профиль: `recruiter` — personal-first: `hero` → `myTasks` → `todayPlanner` → `critical` → `bottlenecks` → `quickActions`. Нет `handoffQueue`, `riskDigest`, `managerLoad`.

---

## Шаг 1 — Work (обязательно для G-6)

**URL:** `/app/work`

- [ ] Role strip: Recruiter; lens про «your candidates and your tasks for today».
- [ ] **Порядок:** сразу под hero — мои задачи, затем планёрка дня, затем critical — без «team noise» handoff queue.
- [ ] Я могу сказать: «вижу **свой** план дня» (не чужой team dashboard).
- [ ] `Bottlenecks` только если есть insights; нет пустого раздражающего блока (или осмысленный empty).
- [ ] Deep-links на candidates из critical/bottlenecks работают.

---

## Шаг 2 — Tasks

**URL:** `/app/tasks`

- [ ] `assignee_scope=mine` в hub preview согласован с списком задач на сегодня.

---

## Шаг 3 — Calendar

**URL:** `/app/calendar`

- [ ] Planner events только meeting/call/shift в Today Planner; task/followup не дублируют MyTasks (G-7).

---

## Шаг 4 — Candidates

**URL:** `/app/candidates`

- [ ] Быстрый доступ из Work Hub без 404.

---

### Найденные баги

- [ ] (id) …

**Сессия:** дата ______ · окружение ______ · исполнитель ______

**Статус UAT 2.2.E:** ☐ PASS ☐ FAIL
