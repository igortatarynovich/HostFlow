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

## History

- **2026-07-18** — L0 closed (ADR-030): lifecycle, versioning, licensing, deps.  
- **2026-07-18** — **Final seal:** Non-Goals · Contract Stability · Architecture Invariants → **FROZEN**.
