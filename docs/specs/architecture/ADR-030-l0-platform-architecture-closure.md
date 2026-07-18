# ADR-030: L0 Platform Architecture Closure

## Status

**Accepted.**  
**2026-07-18:** Официальное **закрытие L0** ([`L0-platform-architecture.md`](L0-platform-architecture.md)). Завершает пробелы lifecycle / contract versioning / licensing / dependencies и фиксирует freeze.

## Context

К канону уже приняты P-01…P-05, Capability Catalog (Passport), Settings Manifest, Architecture Review Checklist. Без явного закрытия L0 остаётся «живым черновиком» и продолжает размываться. Нужны:

1. Оставшиеся нормы (п. 6–9 completeness matrix).  
2. Объявление стабильности: L0 = конституция; изменения только через Architecture RFC.

## Decision

### A. L0 CLOSED

1. [`L0-platform-architecture.md`](L0-platform-architecture.md) — конституция; **Status: CLOSED / FROZEN**.  
2. Изменения L0 — только **Architecture RFC** (или `l0-errata` для явных ошибок) — см. L0 Freeze rule.  
3. Дальнейшая работа — **L1–L3** внутри фундамента.  
4. [`architecture-review-checklist.md`](architecture-review-checklist.md) **обязателен** перед каждым ADR и каждым PR, затрагивающим модули / capabilities / settings / contracts.

### B. Capability Lifecycle (единый для всех)

Каждая capability описывает один и тот же жизненный цикл:

| Phase | Meaning |
|-------|---------|
| **Install** | Capability доступна тенанту как установленный пакет / platform component (код + schema + Manifest registered) |
| **Enable** | Capability включена для tenant/company (entitlement + gate) |
| **Configure** | Применяются defaults из Settings Manifest; admin может менять knobs владельца |
| **Operate** | Runtime: Exposes используются consumers |
| **Upgrade** | Миграции Manifest/schema/adapters по правилам versioning (§C) |
| **Disable** | Выключена: Manifest не в shell; Exposes reject/gated; данные сохраняются per retention |
| **Remove** | Деинсталляция / purge по политике (редко; Enterprise / ops) — только с явным data plan |

**Пример tenant bootstrap:**

```text
Tenant created
  → Forms: Install + Enable + Configure (default Manifest)
  → Notifications: Install + Enable + Configure (SMTP defaults)
  → AI: Install + Disable (licensed later)
  → Finance: not Install (Business Licensed — absent until sold)
```

Passport / Catalog фиксирует default bootstrap class (см. §D). Runtime enforcement — L1/L2; **модель** — L0.

### C. Contract Versioning (общее правило)

Публичные контракты (**Exposes** / Settings Manifest / Events) версионируются единообразно:

| Change type | Rule |
|-------------|------|
| **Additive** (новое optional поле, новый endpoint рядом) | Разрешено в minor; consumers не обязаны сразу обновляться |
| **Deprecated** | Объявляется в release notes + `deprecated_since` / `remove_after`; минимум **2 minor** или **180 дней** (что дольше), если нет security exception |
| **Breaking** | Только major; Architecture review; migration guide; dual-run где возможно |
| **Adapter version** | Стабильный id + semver; consumers pin major |
| **Settings Manifest** | Manifest `version`; breaking key rename = migration_required + major |

Forms versioning остаётся частным случаем Forms Owns; **общее правило** — это §C (не отменяет Forms).

Нарушение: breaking change без major / без checklist § contract — блокер.

### D. Capability Licensing (свойство capability, не UI)

Каждая capability имеет **ровно один** primary license class:

| Class | Meaning | Examples (normative intent) |
|-------|---------|-----------------------------|
| **Always Available** | У каждого tenant с workspace; нельзя «не установить» core pipe | Endpoint, Submission (intake spine) |
| **Platform** | Включено в platform base (часто Enable+Configure при bootstrap) | Forms (Basic), Documents (Basic), Notifications, Activity, Search |
| **Licensed** | Требует product/module entitlement (ADR-004 keys / addons) | Recruitment, HR, Fleet, Sales/Services, Finance; AI Advanced; Automations Advanced |
| **Enterprise Only** | Только enterprise SKU / private offer | Advanced compliance packs, custom isolation — по product matrix |

Детали SKU/цен — **не** L0 (L1/commercial). L0 фиксирует: лицензия = **свойство capability** в Catalog; Settings Manifest `license` gates; Disable/Remove подчиняются class.

### E. Capability Dependencies (граф)

В Catalog / Passport каждая capability объявляет:

| Field | Meaning |
|-------|---------|
| **Requires** | Hard deps: Enable consumer ⇒ Required must be Install+Enable (или Always Available) |
| **Optional** | Soft deps: feature degrade OK if absent |
| **Forbidden** | Нельзя Enable вместе / нельзя Depends-on (архитектурный запрет) |

Пример:

```text
Recruitment
  Requires:  Forms, Documents, Notifications
  Optional:  AI, Automations, Acquisition
  Forbidden: (none as hard co-install ban; Finance not a dep — compose Billing Events only via contract)
```

Граф используется для: install order, enable validation, architecture review («не добавили ли скрытую dep»).

Циклы Requires **запрещены**. Optional не создаёт hard install edge.

### F. Catalog fields (L0 template extension)

К Passport добавляются (без раздувания knobs):

- `license_class`: Always Available | Platform | Licensed | Enterprise Only  
- `requires` / `optional` / `forbidden_deps`  
- `lifecycle_defaults`: bootstrap Install/Enable/Configure/Disable intent  

Settings остаются в Manifest (**P-05**).

### G. Explicit Non-Goals (final seal)

Каждый Passport содержит **Non-Goals** — что **не является задачей** capability (scope), отдельно от **Forbidden** (что нельзя реализовывать как SoT/стек).

| | Forbidden | Non-Goals |
|---|-----------|-----------|
| Вопрос | Можно ли это *построить внутри*? | Является ли это *миссией* capability? |
| Пример Forms | Свой SMTP | BPM, Workflow engine, CRM, Candidate Evaluation, Notifications |

Тихое превращение Non-Goal → Owns без RFC запрещено (**INV-15**).

### H. Contract Stability levels (final seal)

Каждый публикуемый контракт в **Exposes** имеет уровень:

| Level | Rule |
|-------|------|
| **Stable** | Платформенный; breaking только major + review (ADR-030 §C) |
| **Experimental** | Может меняться; не единственная опора Business без плана стабилизации |
| **Internal** | Только внутри owner; внешние модули не вызывают |

### I. Architecture Invariants (final seal)

Аксиомы INV-01…15 — [`architecture-invariants.md`](architecture-invariants.md). Не ADR; не могут стать ложными без L0 RFC.

После §G–I L0 считается **окончательно FROZEN**.

## Consequences

1. L0 — конституция; feature work на L1–L3.  
2. Checklist + Invariants обязательны до ADR/PR.  
3. Registry/JSON/UI — L2/L3.  
4. Дальнейшие «улучшения фундамента» без RFC — нарушение freeze.

## Relationship

[`L0-platform-architecture.md`](L0-platform-architecture.md) · [`architecture-invariants.md`](architecture-invariants.md) · ADR-025…029 · Catalog · Settings Manifest · Checklist · [`../../governance/hierarchy-of-truth.md`](../../governance/hierarchy-of-truth.md)

## История

- 2026-07-18: L0 closed; lifecycle, versioning, licensing, dependencies accepted as L0 norms.
- 2026-07-18: **Final seal** — Non-Goals, Contract Stability, Architecture Invariants → FROZEN.
