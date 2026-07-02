# ADR-013: Public Intake Strategy (Lead-first vs Candidate-first)

## Status

**Accepted (2026-07-02).** Decision **(2) Lead stub on submit** — implemented as **P5C Lead-first draft session** ([entity-profile-definition-registry.md](../platform/entity-profile-definition-registry.md) P5C). Operational contract: [ingestion-contract-public-intake.md](../workflows/ingestion-contract-public-intake.md).

**Residual exceptions (documented, not accidental):**

- **Legacy in-flight** Candidate-backed draft tokens (compatibility shim until TTL expiry).
- **Client application kind** — company inquiry Leads (`source=public-intake`, hyphen) remain a separate branch.
- **Telegram** — parallel bootstrap; not unified in this ADR (separate ingestion contract when extended).

## Context

Система одновременно поддерживала:

| Path | Типичный порядок | Doctrine сегодня |
|------|------------------|------------------|
| **Meta / import / manual CRM** | **Lead-first** → intake → conversion → Candidate | Согласовано с [lead-intake-resolution-and-activity-continuity.md](../workflows/lead-intake-resolution-and-activity-continuity.md): intake decision **до** полноценного dossier-режима. |
| **Public candidate intake** | ~~**Candidate-first**~~ → **Lead-first (P5C)** | Lead draft on create; Candidate on submit via Decision Layer + Outcome Executor. |
| **Telegram** | Параллельный bootstrap (dossier / сервисный контур) | Не тот же intake workspace, что CRM Meta-pipeline. |

Это **не** баг отдельной фичи, а **две operating models** без зафиксированного контракта. Long-term риск: дублирование правил (duplicate, Application, routing), расхождение analytics («когда считается intake»), и усиление **Candidate-centric ATS** UX на публичных каналах при том, что CRM движется к **Intake Decision Workspace**.

Доказательная база: [lead-intake-conversion-flow-audit.md](../workflows/lead-intake-conversion-flow-audit.md) §2.1 (updated 2026-07-02).

Связанные ADR: [`ADR-002`](ADR-002-modular-recruitment-hr-boundary.md), [`ADR-007`](ADR-007-forms-platform-capability.md) (формы как capability; не задают сами по себе intake order).

---

## Decision

**Chosen: (2) Lead stub on submit** — минимальный Lead (intake record) создаётся **на create/reuse** public form session; Candidate создаётся **только** на submit через Decision Layer + Outcome Executor. CRM показывает Lead для audit/navigation; intake-decision rail **не** дублирует form submit.

**Not chosen:**

- **(1) Documented exception only** — superseded для нового candidate traffic; остаётся только для legacy tokens + client kind.
- **(3) Full Lead-first alignment** — не требуется: P5C достигает governance/analytics alignment без перестройки public UX в Meta-style manual intake.

**Implementation reference:**

```
POST /public/intake → Lead (stage=intake_draft, source=public_intake)
PUT  /apply/{token} → update draft on Lead.normalized.public_intake_draft_v1
POST /apply/{token}/submit → Decision Layer → Outcome Executor → Candidate (optional)
```

Code: `backend/app/entity_profile/public_intake_draft_session.py`

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

**Public intake contract (filled):** [ingestion-contract-public-intake.md](../workflows/ingestion-contract-public-intake.md)

---

## Consequences

- **Accepted (2):** analytics и intake governance выровнены с Lead-first doctrine; CRM — audit mode для public submit; legacy Candidate drafts и client kind явно в §9 contract.
- **Guardrails сохранены:** не смешивать intake и dossier ops на одном экране без роли; Intake Resolution MVP slices 1–6 закрыты для CRM Meta path.
- **Direction C (C1):** Form Constructor treats public forms as Lead-first surfaces — **Done (2026-07-02)**; see [ingestion-contract-public-intake.md](../workflows/ingestion-contract-public-intake.md).

**Guardrails:** (1) не смешивать в одном экране «intake» и «dossier ops» без явного разделения ролей UI; (2) закрывать **Intake Resolution MVP** ([lead-intake-resolution-and-activity-continuity.md](../workflows/lead-intake-resolution-and-activity-continuity.md) §8) до масштабного расширения Activities / Rehire / Person. **Canonical Intake Resolution Layer** = архитектурная программа; **Intake Resolution MVP** = поэтапная поставка (6 срезов).

---

## Links

- [ingestion-contract-public-intake.md](../workflows/ingestion-contract-public-intake.md) — filled contract for this channel  
- [ingestion-contract-template.md](../workflows/ingestion-contract-template.md) — template for new channels  
- [lead-intake-conversion-flow-audit.md](../workflows/lead-intake-conversion-flow-audit.md)  
- [recruitment-domain-model.md](recruitment-domain-model.md)  
- [lead-intake-resolution-and-activity-continuity.md](../workflows/lead-intake-resolution-and-activity-continuity.md)
