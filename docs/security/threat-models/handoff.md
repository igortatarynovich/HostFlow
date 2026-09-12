# Threat Model — Handoff & Cross-Tenant Visibility

## Assets

- Кандидат при передаче между агентством и работодателем; документы; timeline; internal notes.

## Trust boundaries

- Tenant A (agency) ↔ Tenant B (client/employer) ↔ shared processing ↔ candidate portal.

## Угрозы

| ID | Угроза | Вектор |
|----|--------|--------|
| HF-1 | Wrong tenant sees candidate | сломанный RLS при `tenant_links` / shared tables |
| HF-2 | Over-sharing | клиент видит internal notes, source, другие вакансии |
| HF-3 | IDOR на handoff record | прямой доступ по UUID без проверки relationship |
| HF-4 | Notification leak | push/email с данными чужого тенанта |
| HF-5 | Export cross-tenant | отчёт тянет строки без фильтра по ACCESS CONTEXT |
| HF-6 | Source-local facts in ready package | Handoff / transfer assembling citizenship (or other decision facts) from `field_answers` / nationality / country twins instead of canonical occupancy |
| HF-7 | Premature Transfer / host confuse | Fits-stage Candidate transferred to HR before Ready package, or employment started from Application host instead of Candidate → Ready → Transfer boundary (ADR-042) |

## Модель контроля

Канонически: **ACCESS CONTEXT** — см. `docs/security/security-ssot.md` §5.

Типы: `OWNER`, `SHARED_READ`, `SHARED_PROCESSING`, `TRANSFERRED`.

## Митигации (baseline)

- Явная таблица/модель отношения доступа; не выводить данные без join на эту модель.
- Policy layer: единая функция «может ли пользователь X видеть поле Y для кандидата Z».
- Audit на смену ownership и на первый доступ клиента к набору полей.
- Тесты: два тенанта, два recruiter, client portal — полный cross-matrix (см. SSOT §17A).
- Package / handoff projection for citizenship uses `read_citizenship_alpha2` (canonical occupancy). Source bags stay provenance; they are not decision authority across the agency↔employer boundary. See [canonical-facts-completeness.md](../../specs/tasks/canonical-facts-completeness.md).
- Operator Host Cutover (ADR-042): Fits enters Candidate on the Recruitment host; Transfer to HR is allowed only after Ready-for-employment package. Formalize → Started remains HR-owned and is out of Recruitment acceptance. See [recruitment-spine-orchestrator-v1.md](../../specs/tasks/recruitment-spine-orchestrator-v1.md).

## Связанные спеки

- `docs/specs/architecture/handoff-contract.md`
- `docs/specs/architecture/multi_tenant_model.md` (tenant_links)
- `docs/specs/architecture/ADR-042-operator-host-boundary.md`
- `docs/specs/tasks/canonical-facts-completeness.md`
- `docs/specs/tasks/recruitment-spine-orchestrator-v1.md`
