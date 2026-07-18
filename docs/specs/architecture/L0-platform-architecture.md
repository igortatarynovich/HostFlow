# L0 — Platform Architecture Constitution

**Status:** **FROZEN** (final, 2026-07-18)  
**Closure:** [`ADR-030`](ADR-030-l0-platform-architecture-closure.md) (incl. final seal: Non-Goals · Contract Stability · Invariants)  
**Owner:** Architecture canon owner ([`../../governance/ownership.md`](../../governance/ownership.md))

> HostFlow **L0** — конституция платформы. Фундамент **заморожен**.  
> Дальнейшая работа — **L1–L3**. Изменения L0 — только **Architecture RFC** / `l0-errata`.

---

## Freeze rule

1. Обычные feature/ADR PR **не** меняют L0.  
2. Изменение L0 — только **Architecture RFC** (`architecture-rfc` / `l0-change`): обоснование, impact, аппрув Architecture canon owner.  
3. Явные ошибки — `l0-errata` + аппрув owner.  
4. Новые capabilities / knobs / adapters — **применение** шаблонов L0 на L1–L3, не перепись конституции.

---

## Completeness matrix (final)

| # | Тема | Статус | Где |
|---|------|--------|-----|
| 1 | Ownership / SoT | ✅ | P-02 · Data Ownership |
| 2 | Boundaries · Forbidden · **Non-Goals** | ✅ | Catalog Passport |
| 3 | Interaction / Adapters | ✅ | P-01 · Exposes |
| 4 | Composition | ✅ | P-03 |
| 5 | Configuration | ✅ | P-04 · P-05 · Manifest |
| 6 | Lifecycle | ✅ | ADR-030 |
| 7 | Versioning + **Stability** (Stable/Experimental/Internal) | ✅ | ADR-030 |
| 8 | Licensing | ✅ | ADR-030 |
| 9 | Dependencies | ✅ | ADR-030 · Catalog |
| 10 | Review Checklist | ✅ | Checklist (обязателен) |
| 11 | **Architecture Invariants** | ✅ | [`architecture-invariants.md`](architecture-invariants.md) |

**Вердикт:** L0 **окончательно заморожен**. JSON Manifest / registry / UI — L2/L3.

---

## L0 pyramid (constitution contents)

```text
L0 — Constitution
  · Platform Principles (P-01…P-05)
  · Capability Catalog + Passports
  · Settings Manifest (schema)
  · Architecture Invariants
  · Architecture Review Checklist
  · Lifecycle · Versioning/Stability · Licensing · Dependencies (ADR-030)
        │
        ▼
L1 — Platform Architecture
  Endpoint · Forms · Documents · Notifications · AI · Search · Activity · Integrations
  (+ Acquisition, Automations, Process Engine, Submission as platform/infra specs)
        │
        ▼
L2 — Business Architecture
  Recruitment · Sales · HR · Fleet · Finance (+ Services)
        │
        ▼
L3 — Implementation
  Backend · Frontend · Database · API · Workers · UI
```

Любой новый функционал: **сначала L0** (checklist + invariants) → проектирование L1/L2 → реализация L3.

> Примечание: нумерация L1/L2/L3 здесь — **архитектурная пирамида продукта**.  
> Уровни документов в [`hierarchy-of-truth.md`](../../governance/hierarchy-of-truth.md) (L0 constitution / L1 domain canon / L2 operating / L3 notes) согласованы по смыслу freeze, но имена слоёв product pyramid ≠ каждый файл governance.

---

## L0 artifact index

| Artifact | Doc |
|----------|-----|
| This constitution | `L0-platform-architecture.md` |
| P-01…P-05 | ADR-025…029 |
| Closure + lifecycle/versioning/licensing/deps + final seal | [`ADR-030`](ADR-030-l0-platform-architecture-closure.md) |
| Passports | [`platform-capability-catalog.md`](platform-capability-catalog.md) |
| Settings Manifest schema | [`capability-settings-manifest.md`](capability-settings-manifest.md) |
| Invariants | [`architecture-invariants.md`](architecture-invariants.md) |
| Checklist | [`architecture-review-checklist.md`](architecture-review-checklist.md) |
| Guide | [`architecture-guide.md`](architecture-guide.md) |
| Principles §0 | [`platform-architecture-principles.md`](platform-architecture-principles.md) |

### Forbidden vs Non-Goals

| | Forbidden | Non-Goals |
|---|-----------|-----------|
| Смысл | Что **нельзя реализовывать** внутри (нарушение ownership) | Что **вообще не задача** capability (scope) |
| Пример Forms | Нельзя свой SMTP SoT | Не является BPM / CRM / Candidate Evaluation |
| Риск без поля | Вторая реализация | Медленное расползание «ещё чуть-чуть» |

### Contract stability

| Level | Meaning | Consumer rule |
|-------|---------|---------------|
| **Stable** | Платформенный контракт; breaking только major + review | Business может опираться |
| **Experimental** | Может меняться быстрее; documented | Не единственная опора Business без плана |
| **Internal** | Внутри owner; не публичный платформенный API | Внешние модули **не** вызывают |

Каждый пункт **Exposes** в Passport помечается уровнем стабильности.

---

## Organizational rules (keep L0 from spreading)

Эти правила **не** расширяют архитектуру — они закрепляют, как команда **пользуется** конституцией.

### 1. Любой спор сначала проверяется по L0

Вопросы вида «куда положить сущность?», «кто владеет?», «где настройки?», «кто публикует Adapter?» → ответ в L0 / Catalog / Invariants / Checklist.

**Если ответ найден — обсуждение заканчивается.** Не изобретаем параллельное правило.

### 2. L0 не расширяется под конкретную задачу

Запрещён паттерн: «давайте ещё одно маленькое правило в конституцию».

Новое правило попадает в L0 **только** если меняет архитектуру **всей** платформы — и только через Architecture RFC. Проблема одного модуля решается на L1–L3.

### 3. ADR не дублируют L0

Новый ADR **ссылается** на принципы, а не переписывает их:

- «Соответствует **P-01**…»
- «Ownership по **P-02** / Catalog…»
- «Configuration по **P-04** / **P-05**…»
- «Не нарушает **INV-…**…»

Пересказ P-rules в каждом ADR — drift.

### 4. Capability Catalog — главный ежедневный справочник

Последовательность проектирования:

1. Проверить [`platform-capability-catalog.md`](platform-capability-catalog.md)  
2. Найти владельца  
3. Проверить Passport (Owns / Non-Goals / Forbidden / Exposes / deps)  
4. Проверить Settings Manifest  
5. Только потом код / L1 ADR деталей  

L0 — нормативная база; **Catalog** — рабочий инструмент каждого дня.

### 5. Новый модуль / capability только по шаблону

Нельзя появиться без:

- Capability Passport (полный шаблон L0)  
- Settings Manifest (если есть config)  
- Public Contracts (**Exposes** + stability)  
- Data Ownership  
- Dependencies (Requires / Optional / Forbidden)  
- License Class  

«Особенных» модулей вне шаблона нет.

---

## Delivery phases

| Phase | Focus | Status |
|-------|--------|--------|
| **Phase 0** | Архитектурная конституция (**L0**) | ✅ **Complete** (2026-07-18) |
| **Phase 1** | Платформенные capabilities (**L1**) | Next |
| **Phase 2** | Бизнес-модули (**L2**) | After / alongside L1 as entitled |
| **Phase 3** | Implementation, integrations, UX (**L3**) | Continuous on top of L1/L2 |

С этого момента обсуждение фундамента прекращается, кроме RFC. Работа — **построение платформы поверх L0**.

---

## History

- **2026-07-18** — L0 closed (ADR-030): lifecycle, versioning, licensing, deps.  
- **2026-07-18** — **Final seal:** Non-Goals · Contract Stability · Architecture Invariants → **FROZEN**.  
- **2026-07-18** — Organizational rules + Phase 0 complete; switch to Phase 1.
