# Hard invariants: Recruitment, HR, Document Hub

**Статус:** канон. Не roadmap и не «как удобно сейчас» — **что запрещено нарушать** при росте сложности (6–12 месяцев).

**Связь:** [ADR-002](ADR-002-modular-recruitment-hr-boundary.md), [ADR-009](ADR-009-document-hub-platform-layer.md), [ADR-014](ADR-014-document-hub-access-model.md) (**§5–§11**: миграция, фазы, policy-driven resolver, инварианты реализации, acceptance scenarios), [**handoff-contract.md**](handoff-contract.md) (стадии + типы handoff), [**operational-event-boundaries.md**](operational-event-boundaries.md) (vocabulary: stage vs handoff vs HR case/employee), [module-separation-implementation-order.md](../workflows/module-separation-implementation-order.md), [first-operational-flow…](../workflows/first-operational-flow-recruitment-documents-hr.md).

---

## Инварианты (нарушение = баг или срочный tech debt)

1. **Documents are never copied between modules** — один канонический `Document` / storage ref; между модулями только links, permissions, review context.

2. **Recruitment never owns Employee lifecycle** — найм/онбординг/контракт/ZUS как процесс владения HR (Workforce и спутники), не «тихий» side-effect карточки кандидата без явного handoff / system transition.

3. **HR never owns Recruitment pipeline** — стадии воронки рекрутмента и решения по qualification не являются источником истины в HR-модуле.

4. **Handoff changes operational responsibility, not document ownership** — владение файлом остаётся в Document Hub; handoff добавляет права, требования, reviews, не дубликаты.

5. **Document Hub is the single owner of documents** — типы, сроки, верификация на уровне Hub; Recruitment/HR потребляют через API/контракты Hub.

6. **Company type never restricts module availability** — пресеты компании не превращаются в жёсткий запрет модулей (см. [ADR-003](ADR-003-tenant-company-module-data-boundaries.md)).

7. **Internal (одна company) и company-to-company handoff используют одну абстракцию handoff** — различается scope и поля, не «два несовместимых мира».

8. **Pipeline = operational stages + platform system transitions** ([ADR-035](ADR-035-module-object-pipeline-settings.md) A1/A2) — объект никогда не «стоит» на transition; запрещены псевдоэтапы `ready_for_hr` / `processing_by_hr` / `ready_for_fleet` как текущая позиция Candidate (legacy codes = strangler only).

9. **Four objects** — Sales creates Client; Recruitment creates Candidate; HR creates Employee; Fleet creates Assignment. Linked, not one growing row.

10. **Module → Objects → Pipelines → Settings** — pipelines не живут в глобальном Settings dump; ownership order fixed by ADR-035.

---

## Операционный контракт стадий (single-tenant)

**Ready for HR** — завершение части Recruitment: рекрутер довёл кандидата, подтвердил готовность к передаче в кадры. Рекрутер **может** выставить `ready_for_hr` (при включённом handoff lane на tenant).

**Hired** — подтверждение трудоустройства со стороны **HR / company**, не рекрутера. Рекрутер **не** должен выставлять `hired` при включённом agency handoff (enforcement: `enforce_agency_handoff_stage_change_allowed`).

**Handoff event (текущая имплементация):** см. детальный контракт [**handoff-contract.md**](handoff-contract.md) (часть B): stage-driven vs `CandidateHandoff`, source/destination, идемпотентность. Кратко: смена стадии при выполнении правил резолвера → `handoff_from_candidate` + activity `workforce.handoff_from_candidate`; либо запись `CandidateHandoff` с нужным `destination`.

**Employee:** создаётся при переходе в стадии handoff (в т.ч. `ready_for_hr` и при настроенном мосте — `ready_for_handoff`) — см. `workforce_employees.py`. Идемпотентно по `candidate_id`.

**HR Case (MVP):** строка **`workforce_hr_cases`** + `WorkforceEmployee` + спутники + `document_entity_links` для reuse; см. roadmap §2.1 блок B.

---

## Риски (осознанно держать в голове)

- Accidental coupling между модулями.
- Временные shortcuts, которые становятся постоянными.
- HR logic, ползущая обратно в Recruitment.
- Document Hub, снова превращающийся в «только документы кандидата» без links.
- Смешение ownership на границе handoff.

---

## AI Agent Notes

- Перед изменением стадий, handoff или документов — свериться с этим файлом.
- Новый код не должен нарушать инварианты выше; если продукт требует исключения — обновить этот документ и ADR в том же PR.
- **Документный доступ**, поведение **`DocumentAccessResolver`**, **implementation invariants** и **acceptance scenarios** заданы в [**ADR-014**](ADR-014-document-hub-access-model.md) (разделы **§5–§11**). Это единый контракт для миграции, фаз внедрения, policy-driven резолвера, последствий для кода, заметок для AI, **жёсткого чеклиста для PR** и **критериев приёмки** (таблица сценариев).
- **Агентам и контрибьюторам запрещено** вводить **module-specific document ACL** вне модели **resolver / policy**, определённой в ADR-014. Не добавлять параллельные движки доступа в духе `ensure_hr_document_scope`, `ensure_transport_document_scope`, finance-specific ACL forks и candidate-only shortcuts, если это не расширение **политик** того же резолвера. Иначе инварианты этого файла и ADR-009/014 расходятся — это срочный tech debt.
