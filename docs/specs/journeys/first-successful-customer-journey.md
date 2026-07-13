# First Successful Customer Journey

**Status:** canonical (L2 journey — delivery KPI).  
**Owner:** Product.  
**Hierarchy:** L2 journey canon. Operational backbone: [`canonical-setup-flow.md`](../workflows/canonical-setup-flow.md), [`consumer-setup-flow-people-to-employee.md`](../workflows/consumer-setup-flow-people-to-employee.md).

**Назначение:** единый продуктовый KPI HostFlow — не MVP, не список модулей, а **замкнутый цикл пользователя**: от первого контакта до оформленного сотрудника без помощи разработчика.

**Freeze до завершения journey:** новые ADR, platform invariants, flow audits, UX debt epics — если не приближают M1, M2 или M3.

---

## Лестница работы

```text
Definition of Done
        ↓
Functional Blocks
        ↓
Product Contracts
        ↓
Backlog
        ↓
Implementation
        ↓
Browser Test
        ↓
Human Gate
```

| Слой | M1 артефакт |
|------|-------------|
| DoD + Blocks | §2 ниже |
| Product Contracts | [`m1-product-contracts.md`](m1-product-contracts.md) |
| Backlog | [`../tasks/m1-first-successful-tenant-backlog.md`](../tasks/m1-first-successful-tenant-backlog.md) |
| Browser Test | `e2e/milestone-1-tenant-ready.browser.spec.ts` |
| Human Gate | [`../../runbooks/m1-human-gate.md`](../../runbooks/m1-human-gate.md) |

---

## Milestones

| Milestone | Результат | Human gate |
|-----------|-----------|------------|
| **M1** | First Successful Tenant — самостоятельный setup до READY | [`m1-human-gate.md`](../../runbooks/m1-human-gate.md) |
| **M2** | First Successful Lead → Candidate | *(после M1 green)* |
| **M3** | First Successful Employee — полный journey | *(после M2 green)* |

M2/M3 DoD и contracts — **только после** M1 human gate green.

---

## M1 — Definition of Done

M1 пройден, когда новый пользователь **без помощи разработчика** выполнил все пункты.

| ID | Пункт | PASS когда |
|----|-------|------------|
| **M1-D1** | Зарегистрировался | `/signup` → `/auth/register` → tenant + admin; автологин |
| **M1-D2** | Создал компанию | Обязательный `/app/onboarding/company` до доступа к setup hub |
| **M1-D3** | Настроил операционный контекст | `business_type` на company form; G1 PASS на setup hub |
| **M1-D4** | Настроил hiring context | Client+vacancy (agency) / vacancy (employer) / services policy |
| **M1-D5** | Настроил process context | Funnel (G4) + requirement profile (G5) на vacancy |
| **M1-D6** | Подключил источник | ≥1 active source (v1: Meta OAuth) или manual policy |
| **M1-D7** | Настроил routing | Полная binding-строка; G8 single winner |
| **M1-D8** | Увидел READY | Snapshot G0–G8 PASS; Health Check проекция |
| **M1-D9** | Понимает готовность | Может объяснить, куда попадёт первый человек — без docs |

**Не PASS:** wizard finished, demo seed, скрытые activation counters, dev подсказки.

---

## M1 — Functional Blocks

| Block | Закрывает DoD | Contract |
|-------|---------------|----------|
| **M1-01** Workspace Entry | D1, D2 | [`m1-product-contracts.md` § M1-01](m1-product-contracts.md#m1-01-workspace-entry) |
| **M1-02** Operating Context | D3 | [§ M1-02](m1-product-contracts.md#m1-02-operating-context) |
| **M1-03** Hiring & Process Context | D4, D5 | [§ M1-03](m1-product-contracts.md#m1-03-hiring--process-context) |
| **M1-04** Intake Source & Routing | D6, D7 | [§ M1-04](m1-product-contracts.md#m1-04-intake-source--routing) |
| **M1-05** Setup Readiness | D8, D9 | [§ M1-05](m1-product-contracts.md#m1-05-setup-readiness) |

---

## Правило задач

Любая задача отвечает: **какой пункт DoD она делает возможным?**

Формат ID: `M1-{block}.{n}` — например `M1-04.3`.

Ответ «никакой» → freeze до v1.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-03 | Initial: M1 journey canon, ladder, links to contracts/backlog/e2e/human gate |
