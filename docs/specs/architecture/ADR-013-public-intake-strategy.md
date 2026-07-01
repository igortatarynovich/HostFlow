# ADR-013: Public Intake Strategy (Lead-first vs Candidate-first)

## Status

**Proposed.** Конкурирующие семантики уже есть в продакшене; этот ADR фиксирует **проблему и варианты решения**. Переход в **Accepted** — только после явного продуктового выбора (возможно по каналам, не обязательно один глобальный режим).

## Context

Система одновременно поддерживает:

| Path | Типичный порядок | Doctrine сегодня |
|------|------------------|------------------|
| **Meta / import / manual CRM** | **Lead-first** → intake → conversion → Candidate | Согласовано с [lead-intake-resolution-and-activity-continuity.md](../workflows/lead-intake-resolution-and-activity-continuity.md): intake decision **до** полноценного dossier-режима. |
| **Public candidate intake** | **Candidate-first** (draft dossier до явного intake resolution) | Расходится: «Lead всегда фиксирует вход» выполняется **не** для всех сценариев; Lead для `client` и вспомогательных связей — отдельная ветка. |
| **Telegram** | Параллельный bootstrap (dossier / сервисный контур) | Не тот же intake workspace, что CRM Meta-pipeline. |

Это **не** баг отдельной фичи, а **две operating models** без зафиксированного контракта. Long-term риск: дублирование правил (duplicate, Application, routing), расхождение analytics («когда считается intake»), и усиление **Candidate-centric ATS** UX на публичных каналах при том, что CRM движется к **Intake Decision Workspace**.

Доказательная база: [lead-intake-conversion-flow-audit.md](../workflows/lead-intake-conversion-flow-audit.md) §2.1.

Связанные ADR: [`ADR-002`](ADR-002-modular-recruitment-hr-boundary.md), [`ADR-007`](ADR-007-forms-platform-capability.md) (формы как capability; не задают сами по себе intake order).

---

## Decision (to be chosen)

Один из явных исходов (или **комбинация по каналу**):

1. **Documented exception (status quo + контракт)**  
   Публичный кандидатский intake остаётся Candidate-first; в доменной документации и UI это названо **исключением** с чёткими правилами: когда создаётся Application, как связывается Lead (если есть), как duplicate/replay.

2. **Lead stub на submit**  
   Минимальный Lead (или аналог intake record) создаётся **раньше или вместе** с первым Candidate touch, чтобы единообразно кормить intake resolution и analytics без полной перестройки форм.

3. **Full Lead-first alignment**  
   Публичный поток перестраивается так, что **сигнал intake** и решение по вакансии/пулу проходят через тот же слой, что Meta — **breaking / дорого**; делать только после явного ROI.

Пока ADR в статусе **Proposed**, код **не обязан** меняться: достаточно не расширять расхождение новыми фичами без учёта выбранного исхода.

### Ingestion governance (emerging rule)

Ingestion — это **governed operational contract**, а не «любой endpoint создаёт кандидата». Meta, public form, Telegram, import, manual, WhatsApp (будущее), client portal, workforce import, AI parsing — это не набор **разных фич**, а **разные contracts** на одной governance-модели; подключение нового входа = явное заполнение контракта, а не новая «тихая» ветка кода.

**Системные вопросы** перед добавлением или расширением канала (чеклист для ревью):

- Какой **ingestion contract** у канала (что создаётся, в каком порядке, идемпотентность)?
- Где **conversion boundary** (Lead → Candidate / иной)?
- Где **intake resolution** и кто принимает решение в продукте?
- Где **duplicate semantics** (exact / review / attach)?
- Где **ownership** и **operational owner** в CRM?
- Где **continuity** после handoff / convert?
- Где **допустимое расхождение** от CRM Lead-first (если есть) и есть ли **ADR** на это отклонение?

Новый канал или крупное расширение существующего — только с явной записью в спеке/ADR (какой из исходов Decision выше применим) и тестами на стыках с Application/duplicate. **Обязательный артефакт:** заполненный [ingestion-contract-template.md](../workflows/ingestion-contract-template.md) (или его копия с именем канала) — contract-review checkpoint, не «документ ради документа». Иначе типичная деградация: «Telegram временно отдельно», «public напрямую», «HR в другом pipeline» → несколько несовместимых ingestion-моделей. Правило продукта: **не расширять без записанной модели** (см. [lead-intake-conversion-flow-audit.md](../workflows/lead-intake-conversion-flow-audit.md) §5).

---

## Consequences

- **Принято (1):** быстрее всего; нужны явные диаграммы «public vs CRM» и тесты на Application/duplicate для обеих веток.  
- **Принято (2):** лучшее выравнивание analytics и intake UX; потребует миграции/двойной записи на границе форм.  
- **Принято (3):** максимальное единообразие doctrine; высокая стоимость и регрессионная поверхность.

**Guardrails:** (1) не смешивать в одном экране «intake» и «dossier ops» без явного разделения ролей UI; (2) закрывать **Intake Resolution MVP** ([lead-intake-resolution-and-activity-continuity.md](../workflows/lead-intake-resolution-and-activity-continuity.md) §8) до масштабного расширения Activities / Rehire / Person. **Canonical Intake Resolution Layer** = архитектурная программа; **Intake Resolution MVP** = поэтапная поставка (6 срезов).

---

## Links

- [ingestion-contract-template.md](../workflows/ingestion-contract-template.md) — operational checklist для нового ingestion source  
- [lead-intake-conversion-flow-audit.md](../workflows/lead-intake-conversion-flow-audit.md)  
- [recruitment-domain-model.md](recruitment-domain-model.md)  
- [lead-intake-resolution-and-activity-continuity.md](../workflows/lead-intake-resolution-and-activity-continuity.md)
