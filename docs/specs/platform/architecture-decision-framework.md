# Architecture Decision Framework — как принимать решения

**Status:** canonical (L1 — процесс; стабильнее ADR, меняется реже шаблонов entity).  
**Audience:** product, architecture, engineering.  
**Опирается на:** [`hostflow-constitution.md`](hostflow-constitution.md) (L0 — *как мыслить*).  
**Этот документ:** *как принимать* архитектурные решения и *какой документ* для этого использовать.

---

## Три слоя документации

| Слой | Вопрос | Документы |
|------|--------|-----------|
| **L0 — Конституция** | Как мыслить? | [`hostflow-constitution.md`](hostflow-constitution.md) |
| **L1 — Решения** | Как принимать решения? | этот документ + шаблоны ниже |
| **L2 — Экземпляры** | Что решили конкретно? | ADR, Domain Contracts, Entity Specs |

**Конституция заморожена (L0).** Framework и шаблоны (L1) **достаточны**.

Новое правило в L0 — **только** если практика покажет, что **без него невозможно** принять архитектурное решение. Не «можно лучше», а «невозможно работать».

**Следующий приоритет — продукт, не спеки.** ADR и Entity Spec **фиксируют проверенное**, не гипотезу. Не начинать с ADR Search до прохождения денежного пути end-to-end.

**Ближайшая цель (10–15 мин):** человек заходит в HostFlow → получает **ссылку на форму для рекламы** → может запустить ads → первый отклик приходит в правильном виде → менеджер работает без доп. настроек.

См. [`m1-money-path.md`](../journeys/m1-money-path.md).

---

## Architecture Layers of Change

Любое изменение относится к **одному** слою. Слой определяет **частоту**, **рецензию** и **риск**.

| Слой | Частота | Примеры | Кто утверждает |
|------|---------|---------|----------------|
| **UI** | очень часто | copy, layout, порядок кнопок | команда / design review |
| **Workspace** | часто | новый View, Command, рабочая зона | product + eng |
| **Domain** | иногда | API, контракт, side effects transition | **ADR обязателен** |
| **Life Cycle** | редко | новый state, transition graph, handoff | **ADR + Entity Spec** |
| **Constitution** | почти никогда | новый принцип L0 | явное решение архитектора / founders |

**Правило:** «Переставить кнопку» (UI) и «изменить Life Cycle Search» — изменения **разного масштаба**. Life Cycle и Domain **не** прячут в UI-only PR.

**На code review:** указать слой изменения в описании PR или ссылке на ADR.

---

## Когда какой документ

| Ситуация | Документ |
|----------|----------|
| Любое изменение Domain, Life Cycle, новая Business Entity, handoff, breaking API | **ADR** ([шаблон](templates/ADR-template.md)) |
| Описание / изменение границ домена (Recruitment, HR, Fleet, …) | **Domain Contract** ([шаблон](templates/domain-contract-template.md)) |
| Новая или существенно меняющаяся Business Entity | **Entity Specification** ([шаблон](templates/entity-specification-template.md)) |
| Только новый View/Command в существующем workspace | ADR **не обязателен**, если не меняются domain contract и life cycle; достаточно product spec / ticket со слоем **Workspace** |
| Только UI copy / layout | слой **UI**; конституционный чеклист не нужен |

**Если ADR нельзя заполнить по шаблону — идея ещё не созрела.** Не кодить «на потом разберём».

---

## Маршрут ADR (обязательный)

Каждый ADR проходит **фиксированный** шаблон — не свободный текст. См. [`templates/ADR-template.md`](templates/ADR-template.md).

Краткий чеклист (14 пунктов):

1. Какой **бизнес-процесс** изменяется?  
2. Какая **Business Entity**?  
3. Существующая или новая? Почему? (Evolution principle)  
4. Какой **Life Cycle** используется или изменяется?  
5. Кто **Owner Domain**?  
6. Какой **Domain Contract** меняется?  
7. Меняется ли **Canonical State**?  
8. Появляются ли новые **Transition**?  
9. Затрагивается ли **History**?  
10. Меняется ли **Workspace** (Command / View)?  
11. Это **Start**, **Optimize** или **Scale**?  
12. Почему **существующая модель** не подходит?  
13. Какие **альтернативы**?  
14. Почему выбран **этот** вариант?

---

## Domain Contract (обязательный формат)

Один домен — один документ по [`templates/domain-contract-template.md`](templates/domain-contract-template.md).

Целевое расположение экземпляров: `docs/specs/domains/<domain-slug>.md`  
*(каталог создаётся по мере заполнения; Recruitment — первый кандидат)*

---

## Entity Specification (самый частый артеfact)

Каждая Business Entity — один документ по [`templates/entity-specification-template.md`](templates/entity-specification-template.md).

Целевое расположение: `docs/specs/entities/<entity-slug>.md`

**Создание entity без Entity Spec = «создали таблицу»**, не архитектурное решение.

---

## Первая волна применения (после денежного пути)

**Сейчас — не ADR.** Сначала пройти [`m1-money-path.md`](../journeys/m1-money-path.md) глазами пользователя; Entity Search и ADR — **после**, когда путь работает.

| # | Тема | Когда |
|---|------|-------|
| 1 | **Search** | после M1 money path PASS |
| 2 | Candidate → Employee handoff | после recruitment Start стабилен |
| 3 | Document | по приоритету продукта |
| 4 | Interview | по приоритету продукта |
| 5 | Fleet Assignment | по приоритету продукта |

**Критерий успеха L0:** 20–30 ADR без систематических «исключений» — **после** того как денежный путь доказан в продукте.

---

## Связанные документы

- [`hostflow-constitution.md`](hostflow-constitution.md) — L0  
- [`templates/ADR-template.md`](templates/ADR-template.md)  
- [`templates/domain-contract-template.md`](templates/domain-contract-template.md)  
- [`templates/entity-specification-template.md`](templates/entity-specification-template.md)  
- [`platform-architecture-principles.md`](../architecture/platform-architecture-principles.md)  
- [`hostflow-operational-model.md`](../architecture/hostflow-operational-model.md)  
- Существующие ADR: `docs/specs/architecture/ADR-*.md`

**При конфликте:** конституция (L0) → framework (L1) → конкретный ADR (L2), если ADR явно не supersede старый ADR с версионированием.
