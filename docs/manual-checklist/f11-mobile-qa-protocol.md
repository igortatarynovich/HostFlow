# F11 Mobile QA Protocol

Цель: формально фиксировать manual mobile проверку по матрице `F11` из `docs/crm-production-readiness-ssot.md` (разделы `5.6.4`, `5.6.5`, `5.6.8`) перед финальным `PASS`.

## Правила фиксации

- Финальный статус прогона: только `PASS` или `FAIL`.
- `PASS` разрешен только после ручного device-level прогона по breakpoints `320/375/390/768`.
- Для `FAIL` обязательно указывать bug-id/issue и влияющий маршрут.
- Для каждого прогона создается отдельный run-record по шаблону [f11-mobile-run-record-template.md](/opt/HostFlow/docs/manual-checklist/f11-mobile-run-record-template.md).
- В run-record обязательно фиксировать:
  - устройство/браузер (`iOS Safari`, `Android Chrome`, desktop responsive emulation);
  - результат по каждому приоритетному экрану из матрицы `F11.1`;
  - статус keyboard overlap, modal scroll и tap comfort;
  - ссылки на screenshot/video evidence.
- После прогона статус `PASS_STATIC` в SSOT переводится в финальный `PASS` только при наличии заполненного run-record.

## Минимальный чек на прогон

1. Проверить key route chain: `/signup -> /app/onboarding/company -> /app/onboarding/getting-started -> /app/overview`.
2. Проверить core CRM screens: `/app/clients`, `/app/leads`, `/app/messages`, `/app/reminders`.
3. Проверить touch baseline:
   - интерактивные controls >= `44px`;
   - нет критичного horizontal overflow;
   - CTA доступны без precision tap.
4. Проверить soft keyboard поведение:
   - поля и CTA не перекрываются;
   - modal/content остается прокручиваемым.
5. Зафиксировать residual risks (если есть) и решение `GO/NO-GO` для mobile.

## Шаблон записи

```
Date: YYYY-MM-DD
Environment: staging | production
Tenant: <tenant-id-or-slug>
Owner: <name/role>
Result: PASS | FAIL
Device matrix:
  - iOS Safari: <device/os/version>
  - Android Chrome: <device/os/version>
  - Desktop emulation: <browser/version>
Evidence:
  - Screenshots: <links>
  - Videos: <links>
  - Notes: <key observations>
Issues:
  - <BUG-ID or N/A>
Sign-off:
  - Product: <name>
  - QA: <name>
```
