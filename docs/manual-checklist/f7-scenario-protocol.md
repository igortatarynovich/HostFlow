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
- Для полного авто-пакета (создать run-record + добавить в `10.1` + синхронизировать board + валидация) использовать: `npm run f7:run-record:apply -- --scenario <a|b|c> --env <staging|production> --tenant <slug> --owner "<name/role>" --result <PASS|FAIL|BLOCKED|IN_PROGRESS>`.
- Для повторного прогона по тому же ключу (`scenario/date/env/tenant`) использовать upsert-режим: `npm run f7:run-record:upsert -- --scenario <a|b|c> --env <staging|production> --tenant <slug> --owner "<name/role>" --result <PASS|FAIL|BLOCKED|IN_PROGRESS>`.
- Базовая доступность CLI-команд проверяется командой `npm run f7:cli:smoke` (help-smoke для `new/apply/upsert`), в том числе в CI.
- CLI поддерживает `--print-ssot-row`, который выводит готовую markdown-строку для вставки в таблицу `10.1`.
- CLI поддерживает `--append-ssot`: после создания run-record автоматически добавляет строку в `10.1` (с anti-duplicate проверкой по `date/scenario/env/tenant`).
- CLI поддерживает `--upsert-ssot`: вставляет или обновляет строку `10.1` по ключу (`date/scenario/env/tenant`).
- В upsert-режиме при совпадающем имени `f7-run-...` run-record файл обновляется (overwrite), чтобы повторный прогон не требовал ручного удаления старого файла.
- CLI поддерживает `--sync-board-status`: после фиксации run-record обновляет статус сценария в execution board (раздел `10`) согласно результату прогона.
- Для `BLOCKED`-прогонов можно передать `--blocker "<text>"`, чтобы при `--sync-board-status` автоматически обновить blocker-колонку в board.
- По умолчанию `--append-ssot` запускает post-update валидацию (`f7:run-log:check`); для отключения только в отладке использовать `--no-validate`.
- При ошибке update/validation CLI откатывает изменения SSOT (rollback), чтобы не оставлять `10/10.1` в частично обновленном состоянии.
- Перед финальной фиксацией run-log в SSOT проверять консистентность: `npm run f7:run-log:check`.
- `f7:run-log:check` валидирует не только таблицу `10.1`, но и соответствие header-полей run-record файлам (`date/scenario/environment/tenant/result`) для linked evidence.
- `f7:run-log:check` запрещает дубли ключа прогона (`scenario + date + environment + tenant`) в таблице `10.1`.
- `f7:run-log:check` сверяет статус board (`раздел 10`) с последним результатом сценария в `10.1` (минимум для `PASS/BLOCKED`), где “последний” определяется по максимальной дате (а не по позиции строки), чтобы перестановка строк не ломала проверку.
- `f7:run-log:check` дополнительно валидирует board-таблицу: только допустимые статусы (`PASS/FAIL/BLOCKED/IN_PROGRESS`), обязательное покрытие `A/B/C` и отсутствие duplicate rows по сценарию.
- `f7:run-log:check` валидирует соответствие `Scenario -> Business type` в `10.1` (`A=services`, `B=agency`, `C=employer`).
- `f7:run-log:check` валидирует то же соответствие внутри linked run-record (`business type` header должен совпадать со сценарием).
- Для board-статуса `BLOCKED` валидатор требует явный текст в колонке blocker (пустые/`N/A` значения не допускаются).
- Валидатор также проверяет `FAIL` консистентность между board и последним результатом в `10.1`.
- Для `PASS/FAIL` валидатор проверяет, что linked run-record не содержит шаблонные placeholder-маркеры (`<...>`), то есть evidence действительно заполнен.
- Для `PASS/FAIL` валидатор требует заполненный sign-off в run-record (`Product` и `QA` не placeholder-значения).
- Для `PASS/FAIL` в `10.1` валидатор требует явные `Environment`, `Tenant` и `Owner` (без `N/A`/placeholder), иначе запись считается неготовой к финальной фиксации.
- Для записей с результатом `PASS/FAIL` evidence-файл должен использовать каноническое имя: `f7-run-<scenario>-<date>-<env>-<tenant-slug>.md`.
- Для `PASS/FAIL` evidence-link должен указывать на файл в `docs/manual-checklist/` (а не во внешние/временные директории).

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
