# Architecture Review Checklist (L0)

**Status:** canonical · **обязателен** перед каждым **ADR** и каждым **PR**, затрагивающим modules / capabilities / settings / contracts / integrations  
**L0:** [`L0-platform-architecture.md`](L0-platform-architecture.md) (**CLOSED**) · [`ADR-030`](ADR-030-l0-platform-architecture-closure.md)  
**Rules:** P-01…P-05 · Catalog · Settings Manifest  

Без прохождения чеклиста — **не merge** и **не accept ADR**.

---

## Десять обязательных вопросов

| # | Вопрос | Если «нет» / неясно |
|---|--------|---------------------|
| 1 | **Кто владелец** затронутой / новой capability? | Стоп → P-02 / Catalog |
| 2 | **Не существует ли уже** такой capability? | Стоп → P-03 compose |
| 3 | Через какой **Adapter** (**Exposes**) идёт взаимодействие? | Стоп → P-01 |
| 4 | Не нарушает ли PR **Capability Boundary** / **Forbidden**? | Стоп → Boundary |
| 5 | Не **дублируются** ли настройки (чужой **Configures** / Manifest)? | Стоп → P-04 / P-05 |
| 6 | Не нарушается ли **SoT** / Data Ownership? | Стоп → P-02 |
| 7 | Какие **Events** публикуются / потребляются? | Зафиксировать в Passport |
| 8 | Какие **Requires / Optional** зависимости добавляются? | Граф ADR-030; циклы запрещены |
| 9 | Требуется ли новая **лицензия** / меняется license class? | Catalog + commercial L1 |
| 10 | Изменяется ли **публичный контракт** (breaking / deprecated / additive)? | Versioning ADR-030 §C |

Дополнительно для settings: UI = **capability space**, не техническая свалка (**P-05**).

---

## Быстрые чекбоксы

### P-01 / Exposes
- [ ] Нет прямого импорта / SQL / ORM / provider SDK в обход adapter  

### P-02 / Owns / SoT
- [ ] Owner совпадает с Catalog; нет второго SoT  

### P-03 / Consumes
- [ ] Compose first; новая capability только если нет покрытия  

### P-04 / P-05 / Config
- [ ] Knobs только в Manifest владельца; нет SMTP/OCR/LLM в Business settings  

### Lifecycle / License / Deps (ADR-030)
- [ ] Requires/Optional/Forbidden обновлены при необходимости  
- [ ] License class указан  
- [ ] Disable/Enable семантика учтена  

### Contract versioning
- [ ] Additive / deprecated / breaking классифицированы; breaking = major + review  

### L0 freeze
- [ ] PR **не** меняет P-rules / L0 шаблоны без Architecture RFC (`architecture-rfc` / `l0-change`)  
- [ ] Или это `l0-errata` (явная ошибка) с аппрувом owner  

### Docs
- [ ] Passport / Manifest / §0.1 / ADR синхронизированы в том же PR  

---

## История

- 2026-07-18: P-01…P-05 checklist.  
- 2026-07-18: **L0 closure** — 10 вопросов; обязателен перед ADR и PR; freeze gate.
