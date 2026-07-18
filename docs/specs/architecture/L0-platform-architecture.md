# L0 — Platform Architecture Constitution

**Status:** **CLOSED / FROZEN** (2026-07-18)  
**Normative closure:** [`ADR-030`](ADR-030-l0-platform-architecture-closure.md)  
**Owner:** Architecture canon owner ([`../../governance/ownership.md`](../../governance/ownership.md))

> HostFlow **L0 Platform Architecture** — конституция платформы.  
> Это **фундамент**, не рабочий черновик. Дальнейшая разработка идёт на **L1–L3**.  
> Изменения L0 — **исключение**, только через **Architecture RFC** (см. ниже).

---

## Freeze rule

1. После закрытия L0 **запрещено** «улучшать фундамент» в обычных feature/ADR PR.  
2. Изменение любого артефакта L0 допускается **только** через **Architecture RFC** с:
   - явным обоснованием (почему нельзя на L1–L3);
   - impact на Passport / Manifest / P-rules / checklist;
   - аппрувом Architecture canon owner;
   - отдельным PR с меткой `architecture-rfc` / `l0-change`.  
3. Исправление **явных ошибок** (битая ссылка, опечатка, противоречие факту уже принятого ADR) — допустимо без полного RFC, но с пометкой `l0-errata` и аппрувом owner.  
4. Новые продуктовые решения **не** меняют L0: они **применяются внутри** L0 (новый Passport / Manifest entry / L1 ADR / L2 module-scope).

---

## Completeness matrix (закрытие)

| # | Тема | Статус | Где закреплено |
|---|------|--------|----------------|
| 1 | Ownership данных / SoT | ✅ | P-02 · Catalog Data Ownership |
| 2 | Границы ответственности | ✅ | Capability Boundary · Forbidden · Owns |
| 3 | Взаимодействие | ✅ | P-01 · Exposes · Standard Adapter |
| 4 | Композиция | ✅ | P-03 · Consumes |
| 5 | Конфигурация | ✅ | P-04 · P-05 · Settings Manifest |
| 6 | Жизненный цикл capability | ✅ | ADR-030 § Lifecycle |
| 7 | Версионирование контрактов | ✅ | ADR-030 § Contract Versioning |
| 8 | Лицензирование capability | ✅ | ADR-030 § Licensing |
| 9 | Зависимости capability | ✅ | ADR-030 § Dependencies · Catalog |
| 10 | Architecture Review Checklist | ✅ | [`architecture-review-checklist.md`](architecture-review-checklist.md) — **обязателен** перед ADR и PR |

**Вердикт:** L0 **закрыт**. Остаточные JSON Schema / registry API / UI shell — **реализация на L1–L2**, не переоткрытие конституции.

---

## L0 artifact index

### Platform Rules (P-01…P-05)

| Rule | ADR | One-liner |
|------|-----|-----------|
| **P-01** Standard Adapter Boundary | [`ADR-025`](ADR-025-standard-adapter-boundary.md) | Только канонические adapters (**Exposes**) |
| **P-02** Capability Ownership | [`ADR-026`](ADR-026-capability-ownership.md) | Один owner функциональности (**Owns**) |
| **P-03** Capability Composition | [`ADR-027`](ADR-027-capability-composition.md) | Новое = композиция (**Consumes**) |
| **P-04** Configuration Ownership | [`ADR-028`](ADR-028-configuration-ownership.md) | Один owner конфигурации (**Configures**) |
| **P-05** Settings Contract | [`ADR-029`](ADR-029-settings-contract.md) | Публикация через Settings Manifest |

### L0 operating norms (non-P)

| Norm | ADR / doc |
|------|-----------|
| Lifecycle (Install…Remove) | [`ADR-030`](ADR-030-l0-platform-architecture-closure.md) |
| Contract versioning | ADR-030 |
| Licensing class | ADR-030 |
| Dependency graph | ADR-030 + Catalog |
| Capability Passport | [`platform-capability-catalog.md`](platform-capability-catalog.md) |
| Settings Manifest | [`capability-settings-manifest.md`](capability-settings-manifest.md) |
| Review Checklist | [`architecture-review-checklist.md`](architecture-review-checklist.md) |
| Guide | [`architecture-guide.md`](architecture-guide.md) |
| Principles §0 | [`platform-architecture-principles.md`](platform-architecture-principles.md) |

### Related L1 (not L0, but adjacent)

Domain map, ADR-003…024 product/domain ADRs, ADR-005 storage hierarchy, module-catalog product keys — развиваются на L1 **без** изменения P-rules / L0 freeze, если не требуют RFC.

---

## What L0 is / is not

| L0 IS | L0 is NOT |
|-------|-----------|
| Конституция: правила, границы, passport shape, checklist | Список всех knobs в JSON (→ Manifest implementations L2) |
| Kinds Infrastructure / Platform / Business | UI wireframes admin shell |
| Dependency + license + lifecycle **модели** | Конкретные биллинг-SKU цены |
| Freeze + RFC | Еженедельный рефакторинг принципов |

---

## After L0: where work happens

| Level | Работа |
|-------|--------|
| **L1** | Domain ADRs, module boundaries, API surfaces, process specs |
| **L2** | Module-scope, workflows, Manifest JSON, adapter implementations |
| **L3** | Implementation notes, runbooks, experiments |

Новая capability: Passport + Manifest + deps/license/lifecycle fields **по шаблону L0** — это **применение** конституции, не изменение L0 (если не меняются сами P-rules / шаблоны границ).

---

## History

- **2026-07-18** — L0 declared **CLOSED**; completeness 1–10 accepted via [`ADR-030`](ADR-030-l0-platform-architecture-closure.md).
