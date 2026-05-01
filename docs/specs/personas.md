# Personas — Канонические пользовательские пути HostFlow

**Назначение:** определить ровно кто пользуется HostFlow, что они хотят, что им разрешено, и какой путь они проходят. Журналы UAT: каталог `docs/specs/journeys/` (`README.md` + по файлу на персону), опираются на эту спеку.

**Связи:**

- Permission-матрица: `hostflow-frontend/src/hooks/usePermissions.ts`, `backend/app/auth/deps.py` (`Role` enum).
- Plan-tier matrix: `docs/specs/plans-matrix.md`.
- Module-флаги: `Tenant.modules` (`candidates`, `companies`, `vacancies`, `documents`, `leads`, `services`, `client_portal`).

**Правило UAT:** каждый журнал должен покрыть три измерения: (1) **роль** видит только релевантное; (2) **тарифный план** виден заранее, лимиты не «выскакивают модалкой»; (3) **production-checklist** — skeleton/error/empty-states, нет хардкод-строк, есть keyboard-a11y.

---

## P-1. `administrator` (Solo, Owner)

**Кто:** основатель агентства/компании, оплачивает подписку, принимает все ключевые решения.
**Тариф (типичный):** Solo → Team (после первого месяца).
**Цель:** «у меня должна работать воронка лидов и я должен видеть, что застряло, без отчётов».
**Top-3 jobs-to-be-done:**

1. Подключить источник лидов (Meta / форма) и увидеть, что лиды реально приходят.
2. Назначить себя или одного рекрутёра ответственным, увидеть, что задачи выполняются.
3. Понять, что в продукте есть и сколько это будет стоить, когда команда вырастет.

**Должен видеть:** всё (`*` в `usePermissions`), включая Settings, Billing, Tenants (если superadmin).
**НЕ должен видеть:** «другие тенанты» (за исключением реального superadmin).
**Лимиты, которые касаются:** все лимиты Solo-плана (см. `plans-matrix.md` §2-3); особенно — `max_recruiters=0`, `max_companies=1`, `max_public_portal_links=0`.

**Журнал:** `docs/specs/journeys/administrator.md` — UAT 2.2.C в HOSTFLOW_AUDIT_AND_PLAN Phase 2.

---

## P-2. `supervisor` (Team Lead)

**Кто:** старший рекрутёр / менеджер группы, отвечает за результат своей подгруппы.
**Тариф:** Team / Business (есть в `max_supervisors`).
**Цель:** «мои рекрутёры должны успевать в SLA, я хочу видеть стак-картинку и быстро тушить пожары».
**Top-3 JTBD:**

1. Видеть Manager Dashboard: чьи лиды простаивают, чьи кандидаты в no-next-action.
2. Передавать кандидата от одного рекрутёра другому без потери истории.
3. Утверждать клиентские handoff'ы и спорные документы.

**Должен видеть:** `manager.tools`, settings (view-only), companies (manage), candidates/leads/vacancies (full ops + pipeline), Meta admin, deletion queue.
**НЕ должен видеть:** `admin.users` (нельзя приглашать новых пользователей), `users.manage` (нельзя менять роли), Tenants admin, Ruleset versions редактирование.
**Лимиты:** в основном Team — `max_recruiters=2` (как ограничение для оунера-админа, не для самого supervisor'а).

**Журнал:** `docs/specs/journeys/supervisor.md` — UAT 2.2.D.

---

## P-3. `recruiter` (Operational user)

**Кто:** ежедневный пользователь, которого мы должны влюбить в HostFlow.
**Тариф:** Team / Business — назначается админом.
**Цель:** «мне не нужны отчёты, мне нужно знать что делать прямо сейчас и сделать это в 2 клика».
**Top-3 JTBD:**

1. Открыть утром Tasks/Inbox, ответить, переключиться к кандидатам.
2. Внутри карточки кандидата — назначить задачу, отправить сообщение, запросить документ.
3. Перевести кандидата по pipeline-этапам без открытия 5 модалок.

**Должен видеть:** Companies, Leads, Vacancies, Candidates (manage + pipeline), Documents, Services view + Orders manage, Notifications, Inbox.
**НЕ должен видеть:** Settings (любые), Users admin, Manager tools, Meta admin, Company ACL, Deletion queue, Billing.
**Лимиты:** обычно не сталкивается напрямую, но видит soft-banner если общий tenant-лимит близок к 100 %.

**Журнал:** `docs/specs/journeys/recruiter.md` — UAT 2.2.E.

---

## P-4. `client_manager` (Client-side admin)

**Кто:** менеджер компании-клиента, у которого есть доступ к собственному агентскому workspace через шаринг.
**Тариф:** Business у агентства; client_manager сам не платит.
**Цель:** «я хочу видеть, как агентство ведёт моих кандидатов и подписывать документы».
**Top-3 JTBD:**

1. Видеть свою компанию в `/app/clients` и кандидатов на вакансиях.
2. Подписывать документы / комментировать.
3. Назначать своих сотрудников (`users.manage` в рамках своего scope).

**Должен видеть:** `manager.tools`, Companies view, Candidates view/manage/pipeline, Vacancies view, Documents, Users view + manage (свой scope), Settings (view), Notifications.
**НЕ должен видеть:** Leads (это агентский pipeline), Meta admin, Deletion queue, Billing агентства.
**Лимиты:** seats `max_client_managers=0` сейчас на всех планах — **TODO: разобраться с моделью** (либо это аddon, либо мы продаём branded portal без CRM-сидов).

**Журнал:** `docs/specs/journeys/client-manager.md` — UAT 2.2.F.

---

## P-5. `client_processor` (Client-side recruiter)

**Кто:** сотрудник компании-клиента, которому делегировали обработку кандидатов.
**Тариф:** Team у агентства.
**Цель:** «сюда передали 5 кандидатов на мою вакансию — я должен с ними работать как рекрутёр».
**Top-3 JTBD:**

1. Видеть только своих кандидатов (по handoff).
2. Менять стадии своего sub-pipeline'а.
3. Подгружать документы по требованию системы.

**Должен видеть:** Companies view, Candidates view/manage/**pipeline**, Vacancies view, Documents manage.
**НЕ должен видеть:** Leads, Services, Settings, Notifications-list, Manager tools, Users admin.
**Особый кейс:** определяется логикой `tenant.type === 'company'` AND role `recruiter` → нормализуется в `client_processor` в `usePermissions.ts`.

**Журнал:** `docs/specs/journeys/client-processor.md` — UAT 2.2.G.

---

## P-6. `viewer` (Read-only stakeholder)

**Кто:** инвестор, наблюдатель, аудитор, новый сотрудник в режиме обучения.
**Тариф:** любой; viewer не считается seat-ом по большинству планов (TODO 2.1: проверить `max_viewers` enforcement).
**Цель:** «я хочу всё видеть, ничего не сломать».
**Top-3 JTBD:**

1. Просматривать companies / leads / vacancies / candidates / services view-only.
2. Нет права создавать/редактировать.
3. Нет права смотреть комм-историю чужих тредов (TODO: уточнить comms scope).

**Должен видеть:** все списки, карточки read-only.
**НЕ должен видеть:** primary-CTA «Создать», bulk-actions, settings.
**Acceptance:** ни одной кнопки, которая на нажатие вернёт 403. Если вернёт — баг.

**Журнал:** `docs/specs/journeys/viewer.md` — UAT 2.2.H.

---

## P-7. `candidate_portal_user` (External — magic link)

**Кто:** соискатель, которому отправили магик-линк или публичный intake-URL.
**Аутентификация:** не CRM-JWT. Token-based (`backend/app/api/public/intake.py`).
**Цель:** «открыть с телефона, загрузить паспорт, оставить контакты, понять статус».
**Top-3 JTBD:**

1. Заполнить intake-форму (`/intake/...`) без регистрации.
2. Сделать фото документа камерой → auto-crop → submit.
3. Получить статус-страницу: «Спасибо, мы связались с {менеджер}, ожидаемый ответ — {дата}».

**Должен видеть:** только свою intake-страницу + статус-страницу.
**НЕ должен видеть:** ничего про tenant, других кандидатов, цены, внутренние стадии.
**Acceptance:** работает на iOS Safari + Android Chrome без логина. Нет dropdowns с >5 пунктами без поиска. Каждый шаг подтверждается «галочкой».

**Журнал:** `docs/specs/journeys/candidate-portal.md` — UAT 2.2.I.

---

## P-8. `client_portal_user` (External — branded portal)

**Кто:** клиент агентства (HR из компании-заказчика), у которого нет CRM-аккаунта, но есть branded-портал.
**Аутентификация:** portal token (`getClientPortalByToken` → `ClientPortalPage.tsx`).
**Тариф:** агентство платит Business + branded portal SKU.
**Цель:** «я открыл ссылку от агентства и вижу, что они для меня делают».
**Top-3 JTBD:**

1. Видеть свою воронку кандидатов (своя компания, свои вакансии).
2. Подписать документ.
3. Оставить комментарий рекрутёру.

**Должен видеть:** branded UI с лого/доменом агентства, ограниченный набор экранов: candidates, documents, threads (по своей компании).
**НЕ должен видеть:** название HostFlow (если SKU branded включён), внутренние NBA-рекомендации, цены, других клиентов агентства.
**Acceptance:** white-label полный (favicon, title, домен, email-шаблоны). Если поломан — баг.

**Журнал:** `docs/specs/journeys/client-portal.md` — UAT 2.2.J.

---

## Cheat-sheet — что показывать кому (модули и тарифы)

| Модуль / Persona | P-1 admin | P-2 supervisor | P-3 recruiter | P-4 client_manager | P-5 client_processor | P-6 viewer | P-7 candidate | P-8 client_portal |
|---|---|---|---|---|---|---|---|---|
| Dashboard | ✓ all | ✓ team-scope | ✓ self-scope | ✓ self-scope | ✗ | ✓ read | ✗ | ✓ branded |
| Leads | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ read | ✗ | ✗ |
| Candidates | ✓ | ✓ | ✓ | ✓ scope | ✓ scope | ✓ read | ✗ | ✓ scope |
| Pipeline | ✓ | ✓ | ✓ | ✓ scope | ✓ scope | ✓ read | ✗ | ✓ scope |
| Companies (own) | ✓ | ✓ manage | ✓ manage | ✓ view | ✓ view | ✓ read | ✗ | ✗ |
| Companies (clients) | ✓ | ✓ | ✓ | ✓ self only | ✗ | ✓ read | ✗ | ✓ self |
| Vacancies | ✓ | ✓ | ✓ | ✓ view | ✓ view | ✓ read | ✗ | ✓ view |
| Documents | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ read | upload only | ✓ sign |
| Tasks/Reminders | ✓ | ✓ | ✓ | ✓ scope | ✗ | ✗ | ✗ | ✗ |
| Inbox/Comms | ✓ | ✓ | ✓ | ✓ scope | ✗ | ✗ | ✗ | ✓ scope |
| Services / Invoices | ✓ | ✓ | ✓ orders | ✗ | ✗ | ✗ | ✗ | ✗ |
| Settings/* | ✓ all | ✓ view | ✗ | ✓ view (subset) | ✗ | ✗ | ✗ | ✗ |
| Billing | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Tenants admin | ✓ superadmin | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |

---

## Acceptance — UAT-прогон одной персоны (template)

Для каждого UAT (2.2.C–J) фиксируем чек-лист в `docs/specs/journeys/{persona}.md`:

```
## Шаг N — {название экрана / модуля}

URL: /app/...
Ожидаемое поведение: ...

- [ ] Экран открывается за < 1 с (skeleton ≤ 300 мс, payload ≤ 700 мс).
- [ ] Primary-CTA виден в правом верхнем углу или явно отсутствует с пометкой «browse-only».
- [ ] Я вижу, на каком я тарифе (если применимо к экрану).
- [ ] Если фича недоступна — есть «Upgrade to {plan}» CTA, не модалка-шок.
- [ ] Empty-state имеет осмысленный CTA, не просто «No items».
- [ ] Error-state имеет текст ошибки + retry.
- [ ] Все строки i18n (нет хардкод-кириллицы, см. правило в SSOT).
- [ ] Tab/Esc/Arrow-навигация работает.
- [ ] Нет deep-link 404 в любых ссылках со страницы.
- [ ] Mobile (≤ 640 px): primary-action достижима без горизонтального скролла.

### Найденные баги
- [ ] (id) ...
```
