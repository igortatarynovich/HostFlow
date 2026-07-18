# Architecture Review Checklist (P-01 · P-02 · P-03 · P-04)

**Status:** canonical  
**Normative rules:** [`ADR-025`](ADR-025-standard-adapter-boundary.md) · [`ADR-026`](ADR-026-capability-ownership.md) · [`ADR-027`](ADR-027-capability-composition.md) · [`ADR-028`](ADR-028-configuration-ownership.md)  
**Principles:** [`platform-architecture-principles.md`](platform-architecture-principles.md) §0  
**Catalog:** [`platform-capability-catalog.md`](platform-capability-catalog.md)  
**Owners index:** [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md) §0.1  

Обязательная проверка для **каждого PR**, который затрагивает модули, shared capabilities, integrations, settings или публичные контракты.

---

## Пять главных вопросов

| # | Вопрос | Правило |
|---|--------|---------|
| 1 | Только канонические Standard Adapters? | **P-01** / **Exposes** |
| 2 | Только к владельцам capabilities? | **P-02** / **Owns** |
| 3 | Композиция, а не дубликат capability? | **P-03** / **Consumes** |
| 4 | Не забирает ли ответственность из **Forbidden**? | **Boundary** |
| 5 | Новые/изменённые настройки только в **Configures** владельца? | **P-04** |

Иначе → architecture review **до** merge.

---

## P-01 — Adapter Boundary (Exposes)

- [ ] Нет прямого импорта / SQL / ORM чужого модуля  
- [ ] Нет прямого вызова внешнего провайдера из Business capability  
- [ ] Нет локального адаптера, дублирующего платформенный контракт  
- [ ] Новый доступ оформлен через **Exposes** владельца + contract tests (или отложен с issue)

## P-02 — Ownership (Owns) + Forbidden

- [ ] Затронутые capabilities и **kind** (Infrastructure / Platform / Business) указаны  
- [ ] Изменение в **Owns** паспорта; не в **Forbidden**  
- [ ] Business не владеет Infrastructure/Platform stacks  
- [ ] Нет второй реализации Forms / Documents / Notifications / Search / AI / Endpoint / Automations / …  
- [ ] Derived cache помечен non-SoT  

## P-03 — Composition (Consumes)

- [ ] Функция собрана через **Consumes** существующих capabilities  
- [ ] Новая capability = ADR + kind + полный passport **до** кода  
- [ ] Тонкий facade OK; второй SoT — нет  

## P-04 — Configuration Ownership (Configures)

- [ ] Каждый новый/изменённый knob есть в **Configures** ровно одной capability  
- [ ] Нет SMTP / OCR Engine / LLM Provider / Meta App / CAPTCHA SoT в Business settings  
- [ ] Нет дублирования authoritative config между модулями  
- [ ] ADR-005 уровень (Tenant/Company/Module) не подменяет configuration owner  

## Intake / Endpoint (если затрагивается)

- [ ] Spine: `Endpoint → Submission → Routing → Decision → Business Entity`  
- [ ] Campaign ↛ Forms internals; routing-once per new Lead  

## Документация

- [ ] [`platform-capability-catalog.md`](platform-capability-catalog.md) обновлён при смене Owns / Configures / Exposes / Consumes / Forbidden  
- [ ] §0.1 index / ADR / module-scope синхронизированы  

---

## История

- 2026-07-18: P-01…P-03 + Boundary.  
- 2026-07-18: P-04 Configuration Ownership; Owns/Configures/Exposes/Consumes.
