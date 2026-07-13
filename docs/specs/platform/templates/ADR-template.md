# ADR-NNN: <краткий заголовок>

**Status:** proposed | accepted | superseded by ADR-XXX | deprecated  
**Date:** YYYY-MM-DD  
**Layer of change:** UI | Workspace | Domain | Life Cycle | Constitution  
**Start / Optimize / Scale:** Start | Optimize | Scale  
**Authors:**  
**Related:** Entity Spec, Domain Contract, prior ADR links

> **Gate:** ADR не принимается, пока не заполнены разделы 1–14. Пустые поля = «не готово».

---

## 1. Какой бизнес-процесс изменяется?

*(Операционная деятельность, не экран. 2–5 предложений: кто делает что, зачем, в каком контексте.)*

---

## 2. Какая Business Entity затрагивается?

| Entity | Класс (Business / Support / Infrastructure) | Owner Domain |
|--------|-----------------------------------------------|--------------|
| | | |

---

## 3. Существующая Entity или новая? Почему?

**Evolution check** (отметить):

- [ ] Можно использовать **существующую** Business Entity  
- [ ] Можно расширить **существующий** Life Cycle (transition, не новая entity)  
- [ ] Можно использовать **существующий** Workspace (Command / View)

**Ответ:** существующая / новая / support reclassification  

**Почему существующая не подходит** *(если новая)*:

---

## 4. Life Cycle

**Используется существующий / изменяется / новый**

```
<state A> → <state B> → …
```

**Запрещённые переходы** (explicit transitions):

---

## 5. Owner Domain

| Entity | Owner Domain | Меняется ownership? |
|--------|--------------|---------------------|
| | | да / нет |

---

## 6. Domain Contract

**Какие домены затронуты:**

| Domain | Изменение контракта |
|--------|---------------------|
| | read API / events / handoff / guarantees |

**Ссылки:** `docs/specs/domains/<domain>.md` (создать или обновить)

---

## 7. Canonical State

- Меняется ли **единственный** канонический state? да / нет  
- Где хранится SSOT после изменения:  
- Риск параллельных «истин» (dashboard, legacy flags):  

---

## 8. Transitions

| Transition | Trigger | Side effects | Новый? |
|------------|---------|--------------|--------|
| | | | |

---

## 9. History

- [ ] History first-class затронута  
- [ ] Только append; compensating events при исправлениях  
- [ ] Миграция существующих данных в history:  

---

## 10. Workspace

| Элемент | Тип (Command / View) | Domain Workspace | Новый? |
|---------|----------------------|------------------|--------|
| | | | |

**Workspace хранит state?** *(должно быть «нет»)*  

**Navigation follows work?** да / нет — комментарий:

---

## 11. Start / Optimize / Scale

**Класс:** Start | Optimize | Scale  

**Обоснование:** *(Start = первый правильный результат для нового пользователя; Optimize = улучшение существующего потока; Scale = объём, автоматизация, multi-tenant edge cases)*

---

## 12. Почему существующая модель не подходит?

*(3–7 предложений. Если Evolution check везде «да» — этот ADR, возможно, не нужен; достаточно Entity Spec patch.)*

---

## 13. Альтернативы

| Альтернатива | Плюсы | Минусы | Отклонена потому что |
|--------------|-------|--------|---------------------|
| A | | | |
| B | | | |

---

## 14. Решение

**Выбранный вариант:**  

**Почему именно он:**  

---

## Последствия

### Для кода / данных

- 

### Для Domain Contracts

- 

### Для Entity Specs

- 

### Human Language (UI)

| Модель | UI (язык пользователя) |
|--------|------------------------|
| | |

---

## Compliance checklist

- [ ] Первый принцип: моделируем работу, не экран  
- [ ] Identity отделена от State  
- [ ] Business time зафиксировано где нужно  
- [ ] Layer of change указан и соответствует scope PR  
- [ ] Entity Spec / Domain Contract обновлены или созданы  

---

## Ссылки

- Constitution: [`hostflow-constitution.md`](../hostflow-constitution.md)  
- Framework: [`architecture-decision-framework.md`](../architecture-decision-framework.md)  
- Entity Spec:  
- Domain Contract:  
