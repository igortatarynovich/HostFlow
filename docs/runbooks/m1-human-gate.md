# M1 Human Gate — First Successful Tenant

**Status:** runbook (operational acceptance).  
**Parent:** [`first-successful-customer-journey.md`](../specs/journeys/first-successful-customer-journey.md).  
**Automated pre-check:** `npm run e2e:milestone-1` (browser spec).

**Назначение:** milestone M1 считается завершённым **только** после прохождения независимым человеком. Зелёные тесты без human gate ≠ M1 done.

---

## Кто проходит gate

| Подходит | Не подходит |
|----------|-------------|
| Product manager без знания codebase | Разработчик, писавший M1 |
| Support / ops без доступа к internal docs | Архитектор проекта |
| Знакомый «как новый клиент» | Тот, кто знает workaround (Settings paths, seed, PATCH) |

**Правило:** участник **не** читает `docs/`, **не** получает подсказок из Slack/чата, **не** смотрит на экран разработчика.

---

## Подготовка (facilitator)

1. Свежий stand: production-like URL (например `https://hostflow.cc` staging) или локальный с `PLAYWRIGHT_BASE_URL`.
2. **Новый** email (не bootstrap, не seed tenant): `human-gate-{date}@example.com`.
3. Meta test app подключена **или** заранее согласован controlled Meta sandbox для OAuth.
4. Browser E2E `milestone-1-tenant-ready` **зелёный** на том же stand (pre-check).
5. Facilitator фиксирует: время старта, URL, email, business_type сценария (рекомендуется **agency** — полный путь G2+G3).

Facilitator **не** подсказывает куда кликать. Только отвечает на вопросы «что означает это слово на экране» (словарь UI), не «куда идти дальше».

---

## Сценарий для участника (script)

Дайте участнику **только** этот текст:

> Вы — владелец небольшого рекрутингового агентства. Вы купили HostFlow и хотите настроить систему так, чтобы люди из Facebook-рекламы автоматически попадали к вам в работу по вакансии «Водитель CE».
>
> Зарегистрируйтесь, настройте всё необходимое и доведите систему до состояния, когда она **готова принимать людей**. Когда будете уверены — скажите facilitator: «Готово».

**Запрещено давать участнику:** ссылки на Settings, названия экранов, порядок шагов, internal термины (G4, IntakeSourceBinding, entity profile).

---

## Checklist facilitator (по DoD)

Отмечайте PASS/FAIL **в момент наблюдения**. Любой FAIL = M1 не пройден.

| DoD | Наблюдение | PASS | FAIL |
|-----|------------|------|------|
| **M1-D1** | Сам зарегистрировался, вошёл в workspace | ☐ | ☐ |
| **M1-D2** | Создал operating company без помощи | ☐ | ☐ |
| **M1-D3** | Выбрал тип бизнеса (agency); понял зачем | ☐ | ☐ |
| **M1-D4** | Создал client + vacancy (или понял что agency требует client) | ☐ | ☐ |
| **M1-D5** | Настроил воронку и требования к кандидату | ☐ | ☐ |
| **M1-D6** | Подключил Meta (или согласованный source) | ☐ | ☐ |
| **M1-D7** | Настроил полный маршрут источника | ☐ | ☐ |
| **M1-D8** | Увидел явный READY / «готова принимать людей» | ☐ | ☐ |
| **M1-D9** | См. § вопрос понимания ниже | ☐ | ☐ |

### Вопрос понимания (M1-D9) — обязателен

После «Готово» спросите **дословно**:

> «Представьте: завтра из вашей Facebook-рекламы приходит новый человек. Что с ним произойдёт в HostFlow — по шагам, своими словами?»

**PASS** если участник без подсказки называет минимум:

1. Откуда пришёл человек (источник / реклама).
2. В какую **вакансию** попадёт.
3. Что будет дальше по **процессу отбора** (воронка / этапы — своими словами).
4. Кто **ответственный**.

**FAIL** если: «не знаю», «надо посмотреть в настройках», «разработчик покажет», описание неверное.

---

## Красные флаги (автоматический FAIL)

- Участник спросил «куда нажать дальше» более **двух** раз на разных шагах.
- Участник открыл **три разных** onboarding / getting-started / wizard без понимания связи.
- Участник попал на demo pipeline / фиктивную статистику и принял за реальную.
- Участник завершил wizard, но READY **не** показан.
- Facilitator дал навигационную подсказку (не словарную).
- Путь занял > **45 мин** для agency с Meta (запишите как UX debt, не блокируйте gate если DoD PASS — optional metric).

---

## Запись результата

```text
Date:
Stand URL:
Participant role:
Business type tested:
Browser E2E pre-check: PASS / FAIL
M1-D1 … M1-D9: PASS / FAIL each
M1-D9 verbatim answer: (quote)
Verdict: M1 PASS / M1 FAIL
Blockers observed: (free text)
```

Хранить в: PR comment, Linear issue, или `docs/specs/journeys/m1-human-gate-runs/` (по желанию команды).

---

## После PASS

- M1 = **done**. Можно открывать M2 contracts + backlog.
- M1 FAIL → исправления только по failed DoD пунктам; повтор human gate на **новом** email.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-03 | Initial human gate runbook for M1 |
