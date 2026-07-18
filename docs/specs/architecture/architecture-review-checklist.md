# Architecture Review Checklist (P-01 · P-02 · P-03)

**Status:** canonical  
**Normative rules:** [`ADR-025`](ADR-025-standard-adapter-boundary.md) · [`ADR-026`](ADR-026-capability-ownership.md) · [`ADR-027`](ADR-027-capability-composition.md)  
**Principles:** [`platform-architecture-principles.md`](platform-architecture-principles.md) §0  
**Catalog (boundaries):** [`platform-capability-catalog.md`](platform-capability-catalog.md)  
**Owners index:** [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md) §0.1  

Обязательная проверка для **каждого PR**, который затрагивает модули, shared capabilities, integrations или публичные контракты. Если любой пункт «нет» / «не применимо без обоснования» — **архитектурный review до merge**.

---

## Четыре главных вопроса

| # | Вопрос | Правило |
|---|--------|---------|
| 1 | Использует ли изменение **только канонические** Standard Adapters? | **P-01** |
| 2 | Обращается ли оно **только к владельцам** соответствующих capabilities? | **P-02** |
| 3 | Не создаёт ли оно **новую capability**, где уже есть подходящая (нужна ли композиция)? | **P-03** |
| 4 | Не забирает ли оно ответственность из **Forbidden** / вне **Capability Boundary** паспорта? | **P-02 Boundary** |

Ответ «да» на 1–3 и «нет, не забирает» на 4 → обычно достаточно обычного code review.  
Иначе → architecture canon owner / ADR до реализации.

---

## P-01 — Adapter Boundary

- [ ] Нет прямого импорта внутренних сервисов другого модуля  
- [ ] Нет SQL / запросов к таблицам другого модуля  
- [ ] Нет использования ORM-моделей другого модуля  
- [ ] Нет зависимости от внутреннего формата хранения чужого модуля  
- [ ] Нет прямого вызова внешнего провайдера (SMTP, LLM SDK, Meta SDK, S3, …) из бизнес-модуля  
- [ ] Нет локального «адаптера», дублирующего уже существующий платформенный контракт  
- [ ] Нет второго несовместимого контракта той же интеграции в другом модуле  
- [ ] Новый межмодульный доступ оформлен как канонический adapter interface + contract tests (или явно отложен с issue)

## P-02 — Capability Ownership + Boundary

- [ ] Затронутые capabilities указаны; владелец совпадает с каталогом  
- [ ] Изменение укладывается в **Owned** паспорта; не реализует пункты из **Forbidden**  
- [ ] Settings / Data Ownership не переезжают к чужому модулю  
- [ ] Нет второй реализации Forms / Documents / Notifications / Search / AI / Endpoint / Automations / …  
- [ ] Derived cache / projection помечены как non-SoT (если есть)  
- [ ] Passport в [`platform-capability-catalog.md`](platform-capability-catalog.md) обновлён при смене границы (тот же PR)

## P-03 — Capability Composition

- [ ] Функция собрана из существующих capabilities, где это возможно  
- [ ] Новая capability (если есть) имеет ADR + Owner + **полный passport 1–8** + Index entry **до** кода  
- [ ] Бизнес-модуль не добавляет «свой» Form/Document/Notify/AI/Search/Automation stack  
- [ ] Оркестрация в модуле только вызывает чужие Public contracts (тонкий facade OK)

## Intake / Endpoint (если затрагивается)

- [ ] Соблюдён spine: `Endpoint → Submission → Routing → Decision → Business Entity`  
- [ ] Campaign не зависит от Forms internals  
- [ ] Routing once per new Lead; continuation не пересчитывает Campaign  

## Документация

- [ ] `platform-capability-catalog.md` / ADR / module-scope / §0.1 index обновлены в том же PR при смене ownership или контракта  
- [ ] Breaking change публичного контракта отмечен + architecture review  

---

## История

- 2026-07-18: введен вместе с P-01/P-02/P-03 platform canon milestone.
- 2026-07-18: добавлен вопрос 4 — Capability Boundary / Forbidden check; catalog SoT.
