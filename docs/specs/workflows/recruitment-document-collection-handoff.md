# Recruitment: подтверждение Requirements и handoff в HR

**Status:** Accepted (operating canon). **Implementation:** Phase 0–1 bridge only — **Candidate Evidence persistence required next** (ADR-016).  
**Hierarchy:** L2 workflow canon.  
**Owner:** Recruitment + Document Hub + HR handoff.

**Architecture:** [ADR-016](../architecture/ADR-016-requirement-evidence-document-separation.md) · Platform: [`requirement-evidence-model-p0.md`](../platform/requirement-evidence-model-p0.md)

---

## 1. Цель

Операционный flow Recruitment **до** HR, построенный на **четырёх сущностях** — не на типах документов:

| # | Сущность | Вопрос |
|---|----------|--------|
| 1 | **Requirement** | Что нужно подтвердить? |
| 2 | **Accepted Evidence** | Какими способами это можно подтвердить? |
| 3 | **Candidate Evidence** | Чем **этот** кandidat подтверждает? |
| 4 | **Document Instance** | Конкретный файл + поля в Document Hub |

Process Engine и readiness спрашивают: **выполнено ли требование Legal stay?** — не «есть ли visa».

---

## 2. Владение

| Домен | Владеет |
|-------|---------|
| **Platform / Requirement catalog** | Requirement definitions, Accepted Evidence variants, applicability |
| **Document Hub** | Document Instance (файл, type, lifecycle) |
| **Recruitment** | Создание Candidate Evidence, approve до handoff, trigger handoff |
| **HR** | Чтение fulfillments, HR review на том же document_id, Work Eligibility |

**Forbidden:** копирование Document Instance при handoff ([handoff-contract](../architecture/handoff-contract.md)).

---

## 3. Откуда берётся список Requirements

Система резолвит **Requirements** (не document types):

```
Entity Profile + vacancy + citizenship + role + stage
        ↓
Requirement Engine → applicable requirements[]
        ↓
Recruiter checklist (Identity, Legal stay, Driving qualification, …)
```

Рекрутер **не** составляет список документов вручную.

---

## 4. Flow сбора (Recruitment)

### 4.1 Checklist по Requirements

```
☐ Identity confirmation
☐ Legal stay confirmation      (если applicable)
☐ Driving qualification
☐ Code 95 qualification        (или bundled — см. catalog)
☐ Tachograph qualification
☐ Medical fitness              (по process profile)
```

### 4.2 Выбор Accepted Evidence

Рекрутер открывает **Legal stay confirmation**.

Система показывает **Accepted Evidence** (не типы документов как отдельные blocking-строки):

```
Чем подтверждается?
○ Visa
○ Karta pobytu / Residence card
○ Permanent residence
○ EU passport (если applicable)
```

Выбор → `evidence_variant_code` → форма соответствующего Document Type.

### 4.3 Upload + поля + Approve

1. Создаётся / обновляется **Document Instance** в Hub.  
2. Создаётся **Candidate Evidence**:  
   - `requirement_code = legal_stay_confirmation`  
   - `evidence_variant_code = visa`  
   - `document_id = #734`  
3. Recruitment approve → Candidate Evidence `satisfied`.  
4. Requirement автоматически **satisfied** для PE / readiness.

### 4.4 Driving qualification — два пути

**Accepted Evidence** для одного Requirement (или bundled catalog entry):

| Variant | Document mapping |
|---------|------------------|
| Combined EU license | один `driver_license_code95` |
| Separate documents | `driver_license` **и** `code95` (`all_of`) |

Candidate Evidence для separate path — **одна** строка evidence + **две** junction links на documents #41 и #52.

### 4.5 Gate перед `ready_for_hr`

Blocking если любой blocking **Requirement** ∉ `{satisfied, not_applicable}`.

---

## 5. Handoff в HR

Передаётся **`requirement_fulfillments[]`**, не угадывание по списку файлов:

```json
{
  "requirement_code": "legal_stay_confirmation",
  "status": "satisfied",
  "chosen_evidence_variant_code": "visa",
  "documents": [
    {
      "document_id": "734",
      "document_type_code": "visa",
      "extracted_fields": { "number": "AB123456", "expiry_date": "2028-04-12" }
    }
  ],
  "recruitment_verification": { "approved_at": "…", "approved_by_user_id": "…" }
}
```

HR сразу знает: **что** требовалось, **чем** подтверждено, **где** документ, **что** проверил recruitment.

Plus: `document_entity_links` на те же `document_id` — без копий.

---

## 6. Замена документа (visa → karta pobytu)

1. Старая Candidate Evidence → `superseded`.  
2. Новая: тот же `requirement_code`, новый `evidence_variant_code`, новый `document_id`.  
3. Requirement **не меняется**.  
4. Handoff / HR видят новый fulfillment record.

---

## 7. UI / API контракт (target)

Recruitment dossier API:

```json
{
  "requirements": [
    {
      "requirement_code": "legal_stay_confirmation",
      "status": "missing",
      "accepted_evidence_variants": [
        { "evidence_variant_code": "visa", "public_name": "Visa" },
        { "evidence_variant_code": "residence_card", "public_name": "Karta pobytu" }
      ],
      "candidate_evidence": null
    }
  ]
}
```

Frontend **не** вычисляет satisfaction локально.

---

## 8. Gap vs код сегодня

| Есть | Нет (блокер для HR flow) |
|------|---------------------------|
| Bridge evaluator (`slot_evaluator`) | Таблица **`candidate_evidence`** |
| Catalog seed (bridge JSON) | Recruitment API write Candidate Evidence |
| Requirement rules in PE (partial) | Handoff `requirement_fulfillments[]` |
| Document Hub instances | Product UI «Requirement → picker → form» |

---

## 9. UAT scenarios

1. Non-EU: Legal stay via karta pobytu only → one Candidate Evidence row → handoff shows `residence_card` variant.  
2. Driver: combined EU license → one document, one evidence row, requirement satisfied.  
3. Driver: separate license + code95 → one evidence row, two document links.  
4. Replace visa with karta pobytu → supersede chain, same requirement_code.  
5. EU citizen → legal stay `not_applicable`.

---

## 10. AI Agent Notes

- Canon: ADR-016 + requirement-evidence-model-p0.md.  
- Не добавлять PE gates по `document_type_code` где есть Requirement.  
- Следующий код: **Candidate Evidence persistence (Phase 2)**, не HR UI.
