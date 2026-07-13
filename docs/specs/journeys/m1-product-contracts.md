# M1 Product Contracts

**Status:** canonical (L2 — product behavior contracts for Milestone 1).  
**Parent:** [`first-successful-customer-journey.md`](first-successful-customer-journey.md).  
**Setup canon:** [`canonical-setup-flow.md`](../workflows/canonical-setup-flow.md) (S0–S5, G0–G8).

**Назначение:** поведение системы — не API, не UI, не backlog. Один контракт на functional block. Разработчик не придумывает свою трактовку.

---

## M1-01 Workspace Entry

**Закрывает DoD:** M1-D1, M1-D2 · **Scope:** S0

### Когда workspace существует?

Tenant active + admin user + membership. Gate **G0** = PASS.

### Когда компания создана?

Operating `Company` привязана к tenant. Начало **G1** (без `business_type` G1 не PASS).

### После регистрации

- Не dashboard с demo-данными.
- Не фиктивный pipeline.
- Не три параллельных onboarding UI.
- Единый setup-контекст + первый failed gate.

### Skip компании?

Нет.

### Source of truth

| Вопрос | Источник |
|--------|----------|
| Workspace? | Tenant + User + membership |
| Компания? | Operating Company |
| Прогресс? | Gates G0–G8, не wizard step |
| Куда вести? | Первый failed gate S0→S5 |

### Запрещено

Triple onboarding; demo seed; bootstrap tenant; wizard progress как прогресс setup.

---

## M1-02 Operating Context

**Закрывает DoD:** M1-D3 · **Scope:** S1

### Когда настроен?

Valid `business_type` на operating company. **G1** = PASS.

### После выбора типа

| business_type | Обязательно | Не обязательно |
|---------------|-------------|----------------|
| agency | client (G2) + vacancy (G3) | — |
| employer | vacancy (G3) | client |
| services | intake policy | vacancy по preset |

Неприменимые шаги не показываются. Обязательные нельзя замаскировать под optional.

### Изменение business_type

Пересчёт readiness. NOT READY если новый тип требует отсутствующих объектов.

### Source of truth

`business_type` на operating company — единственный источник.

---

## M1-03 Hiring & Process Context

**Закрывает DoD:** M1-D4, M1-D5 · **Scope:** S2 + S3

### Hiring context (G2, G3)

| Тип | G2 | G3 |
|-----|----|----|
| agency | ≥1 client или явный waiver | ≥1 active vacancy |
| employer | — | ≥1 active vacancy |
| services | client или «без клиента» policy | по preset |

### Process context (G4, G5)

- **G4:** vacancy → funnel с ≥1 stage
- **G5:** resolved `entity_profile_code` + active ruleset

### Skip

Только где gate не применим. «Потом донастрою» для обязательного gate — запрещено.

### Где настраивается

Внутри единого setup path. После действия — return в setup hub или следующий failed gate (no Type-2 dead end).

### Source of truth

Client, Vacancy, Funnel binding, `entity_profile_code` — данные; применимость — gates G2–G5 в snapshot.

---

## M1-04 Intake Source & Routing

**Закрывает DoD:** M1-D6, M1-D7 · **Scope:** S4

### Source подключён (G6)

≥1 active source (OAuth complete / form published / webhook live) **или** declared manual policy.

OAuth без complete route ≠ готов.

### Маршрут существует (G7)

Для каждого active source — полная строка:

```text
Источник → Вакансия → Воронка → Требования → Ответственный
```

Любое пустое поле = маршрут не существует.

### Неполный маршрут

Система указывает **какое** поле пустое. G8 fail при dual routing (`meta_ads_map` vs IntakeSourceBinding).

### Первый неизвестный source

Один interrupt → полная строка → «Запомнить» → binding. Второй inbound с тем же key — автоматически.

### Известный source

IntakeRouter → binding applied → Lead с vacancy, funnel, profile, assignee. disposition ≠ `needs_routing`.

### Source of truth маршрута

**Intake Routing** (`IntakeSourceBinding`). Не Meta-only table, не vacancy-only, не form builder-only.

### READY (routing часть)

G6 + G7 + G8 PASS. Снятие READY при деактивации source, удалении binding, conflict route.

---

## M1-05 Setup Readiness

**Закрывает DoD:** M1-D8, M1-D9 · **Scope:** S5

### READY

Вычисляемое состояние: AND всех applicable G0–G8 для tenant + operating company + `business_type`.

Пользовательская формулировка: inbound из настроенного источника попадёт в известный hiring context **без повторной настройки**.

### Не READY

Wizard finished; demo seed; `first_lead_created`; `next_action_created`; OAuth без G7; vacancy без G5; «Finish anyway».

### Пересчёт

При любом изменении данных, влияющем на gate. Snapshot — live projection.

### NOT READY после READY

Показать failed gates + blockers + одно next action. Inbound может деградировать в `needs_routing` — сигнал, не норма.

### Health Check

Проекция G0–G8. Не отдельный процесс. Не wizard progress.

### Next Action (PI-1)

Ровно одно. Валидно iff: опубликован · достижим · выполняется · меняет gate · публикует следующее.

### M1-D9 (понимание)

После READY пользователь формулирует: куда попадёт человек из [источник] → [вакансия] → [воронка] → [требования] → [ответственный]. UI показывает итоговую строку маршрута.

### Source of truth

`readiness_snapshot`; blockers ← failed gates; next action ← first failed gate S0→S5. Wizard и activation counters — не source of truth.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-03 | Initial: five M1 product contracts |
