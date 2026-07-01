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

## Модель контроля

Канонически: **ACCESS CONTEXT** — см. `docs/security/security-ssot.md` §5.

Типы: `OWNER`, `SHARED_READ`, `SHARED_PROCESSING`, `TRANSFERRED`.

## Митигации (baseline)

- Явная таблица/модель отношения доступа; не выводить данные без join на эту модель.
- Policy layer: единая функция «может ли пользователь X видеть поле Y для кандидата Z».
- Audit на смену ownership и на первый доступ клиента к набору полей.
- Тесты: два тенанта, два recruiter, client portal — полный cross-matrix (см. SSOT §17A).

## Связанные спеки

- `docs/specs/architecture/handoff-contract.md`
- `docs/specs/architecture/multi_tenant_model.md` (tenant_links)
