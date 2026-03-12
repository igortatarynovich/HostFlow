# F7 Scenario Protocol (A/B/C)

Цель: формально фиксировать прогон сценариев успеха из `docs/crm-production-readiness-ssot.md` (раздел `4.2` и `10`) без двусмысленности.

## Правила фиксации

- Статус прогона: только `PASS`, `FAIL`, `BLOCKED`.
- `PASS` выставляется только после полного ручного прогона шагов `4.2` на целевом окружении.
- `PASS_STATIC` допустим только как промежуточная отметка в комментарии (code/UI audit), но не как финальный статус сценария.
- Для `FAIL` обязательно указывать bug-id/ссылку на issue.
- Для `BLOCKED` обязательно указывать внешний блокер (например, production Stripe/webhooks).
- Каждый прогон фиксируется отдельным run-record файлом по шаблону [f7-run-record-template.md](/opt/HostFlow/docs/manual-checklist/f7-run-record-template.md), а в SSOT `10.1` добавляется ссылка на этот файл в колонке `Evidence`.
- Для ускорения фиксации можно сгенерировать run-record через CLI: `npm run f7:run-record:new -- --scenario <a|b|c> --env <staging|production> --tenant <slug> --owner "<name/role>"`.
- CLI поддерживает `--print-ssot-row`, который выводит готовую markdown-строку для вставки в таблицу `10.1`.
- CLI поддерживает `--append-ssot`: после создания run-record автоматически добавляет строку в `10.1` (с anti-duplicate проверкой по `date/scenario/env/tenant`).
- По умолчанию `--append-ssot` запускает post-update валидацию (`f7:run-log:check`); для отключения только в отладке использовать `--no-validate`.
- Перед финальной фиксацией run-log в SSOT проверять консистентность: `npm run f7:run-log:check`.
- `f7:run-log:check` валидирует не только таблицу `10.1`, но и соответствие header-полей run-record файлам (`date/scenario/environment/tenant/result`) для linked evidence.
- `f7:run-log:check` запрещает дубли ключа прогона (`scenario + date + environment + tenant`) в таблице `10.1`.
- Для записей с результатом `PASS/FAIL` evidence-файл должен использовать каноническое имя: `f7-run-<scenario>-<date>-<env>-<tenant-slug>.md`.

## Шаблон записи

```
Date: YYYY-MM-DD
Scenario: A | B | C
Business type: services | agency | employer
Environment: staging | production
Tenant: <tenant-id-or-slug>
Result: PASS | FAIL | BLOCKED
Blocker (if any): <text>
Evidence:
  - UI: <screen/video link or note>
  - API/logs: <endpoint/log snippet>
  - Notes: <key observations>
Issues:
  - <BUG-ID or N/A>
Owner sign-off: <name/role>
```

## Минимальный чек на сценарий

1. Signup/Login/Invite не создают тупиков, recovery path понятен.
2. Onboarding доводит до first value без ручной помощи.
3. Основной workflow сценария выполняется end-to-end.
4. Есть явный следующий шаг при ошибке (retry/fallback).
5. Результат и evidence записаны в board (раздел `10` SSOT).
