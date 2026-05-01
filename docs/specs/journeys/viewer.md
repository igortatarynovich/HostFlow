# UAT 2.2.H — Viewer (`viewer`)

**Профиль:** `viewer` — минимальный layout: `viewerSummary` → `critical` (read-only ссылки). Нет `myTasks` / `todayPlanner` / handoff / quick actions как у action-ролей.

---

## Шаг 1 — Work (обязательно для G-6)

**URL:** `/app/work`

- [ ] Видна карточка read-only summary (browse-only messaging).
- [ ] Critical block: если есть строки — ссылки ведут на списки **только для просмотра** (нет скрытого edit).
- [ ] Я могу честно сказать: «вижу, что происходит в воронке» / план как **наблюдатель** (acceptance для viewer переформулирован — не «мой план действий», а «понятна картина без права ломать данные»).
- [ ] Нет 403-болтанины от `MyTasksPanel`/`TodayPlannerPanel` (секции не должны монтироваться без permissions).

---

## Шаг 2 — Read-only smoke

**URL:** выборочно `/app/candidates`, `/app/leads` (если разрешено)

- [ ] Нет редактирующих CTA, которые потом дают 403.

---

### Найденные баги

- [ ] (id) …

**Сессия:** дата ______ · окружение ______ · исполнитель ______

**Статус UAT 2.2.H:** ☐ PASS ☐ FAIL
