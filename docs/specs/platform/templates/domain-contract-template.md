# Domain Contract: <Domain Name>

**Status:** draft | active | deprecated  
**Version:** 1.0.0  
**Date:** YYYY-MM-DD  
**Owner Domain for:** *(список Business Entities)*  
**Related ADR:** ADR-NNN

> Каждый Business Domain HostFlow описывается **одинаково** по этому шаблону.  
> Расположение: `docs/specs/domains/<domain-slug>.md`

---

## 1. Назначение домена

*(2–4 предложения: какую операционную работу организации покрывает домен; не «модуль в коде».)*

---

## 2. Owner Business Entities

| Business Entity | Notes |
|-----------------|-------|
| | |

**Не owner (read / use / events only):**

| Entity | Owner Domain | Как этот домен использует |
|--------|--------------|----------------------------|
| | | |

---

## 3. Публикуемые контракты

| Контракт | Тип | Версия | Stability |
|----------|-----|--------|-----------|
| | read API / command API / event / snapshot | | stable / evolving |

**Base path / namespace** *(если применимо):*  

**OpenAPI / schema links:**

---

## 4. Что домен гарантирует

*(Обязательства перед другими доменами и потребителями.)*

1.  
2.  
3.  

**Примеры формулировок:**

- Recruitment: Candidate всегда валиден относительно правил домена; canonical state и history доступны по контракту.  
- HR: Employee соответствует требованиям трудоустройства; изменения только через допустимые transitions.  
- Fleet: Vehicle и Driver Assignment отражают актуальное операционное состояние.

---

## 5. Что домен не гарантирует

*(Явные non-goals — снижают скрытые зависимости.)*

1.  
2.  

---

## 6. Входящие зависимости

| From | Контракт | Зачем | Allowed |
|------|----------|-------|---------|
| Platform / Tenant / … | | | yes |

---

## 7. Исходящие зависимости

| To | Контракт | Зачем | Allowed |
|----|----------|-------|---------|
| | read / event / handoff | | yes |

---

## 8. Запрещённые зависимости

| Запрещено | Почему |
|-----------|--------|
| Прямой SQL / ORM к таблицам другого owner domain | нарушение ownership |
| UI types в domain service | нарушение слоёв |
| Дублирование canonical state другого domain | нарушение SSOT |
| | |

---

## 9. События

| Event | Payload (summary) | Consumers | Version |
|-------|-------------------|-----------|---------|
| | | | |

**Delivery:** at-least-once / outbox / sync only —  

**Handoff events** *(если есть):*

| Event | From state | To domain | Snapshot fields |
|-------|------------|-----------|-----------------|
| | | | |

---

## 10. Границы ответственности

**В зоне домена:**

-  

**Вне зоны домена** *(делегируется другим owner / platform):*

-  

**Серая зона** *(требует ADR при расширении):*

-  

---

## Identity, State, History (cross-cutting)

| Entity (owned) | Identity (immutable) | State (mutable) | History |
|----------------|----------------------|-----------------|---------|
| | | | append-only |

---

## Versioning / breaking changes

| Change type | Process |
|-------------|---------|
| Additive (new field, event) | minor version |
| Breaking read shape | major + migration window |
| New owned entity | ADR + Entity Spec |

---

## Связанные документы

- [`hostflow-constitution.md`](../hostflow-constitution.md) — Ownership, Domain Contract  
- Entity Specs: `docs/specs/entities/`  
- ADR:  
