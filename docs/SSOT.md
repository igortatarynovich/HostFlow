# HostFlow SSOT (Single Source of Truth)

Этот файл — **короткий операционный документ**: **правила, которые влияют на разработку**, и **что ещё предстоит сделать**.  
История релизов, Evidence PASS, развёрнутые спеки и аудиты **не дублируются** здесь: смотри **git history**, **`docs/pipe.md`**, **`docs/pipedesign.md`**, **`docs/specs/**`**.

> **Precedence (added 2026-08-28).** Этот файл — **не** релизная и **не** планировочная власть. Он не определяет scope v1, порядок слайсов и готовность к запуску:
>
> | Вопрос | Кто отвечает |
> |---|---|
> | Что входит в v1, что «позже» | [`hostflow-v1-release-goal.md`](specs/gates/hostflow-v1-release-goal.md) |
> | В каком порядке делаем | [`sales-to-comms-sequential-queue.md`](specs/tasks/sales-to-comms-sequential-queue.md) |
> | Готовы ли к запуску | [`release-readiness-gate.md`](specs/gates/release-readiness-gate.md) — **только он** |
> | Кому принадлежит непринадлежащая работа | [`v1-unowned-work-register.md`](specs/gates/v1-unowned-work-register.md) |
>
> Пункт §1.1 («не создавать отдельные markdown-трекеры») **не отменяет** канон `docs/specs/**` и `docs/governance/**`: гейты, briefs и журналы приёмки — это канонические слои по [`hierarchy-of-truth.md`](governance/hierarchy-of-truth.md), а не «третий исторический MD-трекер». Запрет читается узко: не заводить **параллельные общие трекеры прогресса** вне канонических папок.
>
> Открытые `[ ]` в §2 — операционный список идей и мелкой работы. **Всё, что блокирует релиз, обязано иметь строку в реестре бесхозной работы**, иначе Release Readiness Gate не проходит (EC-6).

---

## 1. Правила для разработки

### 1.1 Роль `docs/SSOT.md`

- **Не создавать** отдельные markdown-файлы-трекеры прогресса **вне канонических папок**. Открытая мелкая работа фиксируется **здесь** (или в issue-трекере команды), но канонические слои — гейты (`docs/specs/gates/`), слайс-брифы (`docs/specs/tasks/`), журналы приёмки (`docs/specs/journeys/`) — живут по своим правилам и **имеют приоритет** над этим файлом в вопросах scope и релиза (см. precedence-блок выше).
- Поддерживающая документация (blueprint, дизайн, модульные спеки) **может** существовать в `docs/`, но **не заменяет** этот файл для мелкого операционного бэклога.

### 1.2 Ветки и merge

- Один и тот же путь **`docs/SSOT.md`** на всех ветках; правки — как обычный код (feature branch → merge).
- При **merge conflict**: **сохранить оба** набора открытых пунктов, не удалять чужие `[ ]` без прочтения. Формулировки — **нейтральные к ветке** (что нужно сделать в продукте, а не «только на моей ветке»).

### 1.3 Как обновлять бэклог

- Закрыл задачу — пометь **`[x]`** или **удали** строку (если шумит).
- Новая работа — добавь **`[ ]`** в подходящий подраздел **§2**.
- Указывай **стабильные пути к коду** (`hostflow-frontend/src/...`, `backend/app/...`), без привязки к номерам строк.

### 1.4 Гигиена репозитория

- **Не коммитить** содержимое **`node_modules/`**, **`.venv/`**, **`backend/uploads/`**, **`backend/app/uploads/`** — только **`.gitignore`**; артефакты ручных прогонов — **`docs/manual-checklist/_artifacts/`** (gitignored) или вне репо.

### 1.5 Продуктовые ориентиры (не бэклог)

- Workflow / UX: **`docs/pipe.md`**
- Лендинг / SEO / токены: **`docs/pipedesign.md`**
- Публичные воронки Growth / Auth / Candidate + Success Path: **[ADR-034](specs/architecture/ADR-034-self-service-public-funnels.md)**, **[`self-service-success-path.md`](specs/journeys/self-service-success-path.md)**
- Модульные спеки: **`docs/specs/**`**

### 1.6 Платформа (superadmin) vs операционный тенант (агентство)

- **`superadmin`** — роль **управления платформой**: тенанты, биллинг-оверрайды, имперсонация, разбор инцидентов, доступ ко всем контурам при необходимости. Это **не** роль ежедневной работы рекрутингового агентства в CRM.
- **Операционная работа** (лиды, вакансии, кандидаты, Meta, реальные клиенты) ведётся в **тенантах клиентов и в собственном агентском тенанте** (для HostFlow как оператора — **Focus Personnel**, канонический UUID в **`backend/app/constants/hostflow_canonical_tenants.py`**).
- **Bootstrap / legacy default tenant** (`11111111-1111-1111-1111-111111111111`) — служебный контекст суперадмина в приложении; **не целевое место** для хранения подключений Meta, маппинга объявлений и потока лидов агентства. Перенос уже созданных данных: **`scripts/migrate_superadmin_meta_connection_to_focus.sql`**; API-ремап superadmin → Focus для Meta (**`meta_tenant_resolve.py`**) — чтобы с платформенного JWT не править пустой срез на bootstrap, когда строки уже на Focus.
- Все прочие пользователи — **существующие роли** (`administrator`, `supervisor`, `recruiter`, …) **внутри своего тенанта** без расширения смысла `superadmin`.

### 1.7 Покрытие SSOT: что значит «100%»

Документ **§2** смешивает три типа пунктов:

| Тип | Смысл | Обязательность |
|-----|--------|----------------|
| **Gate пилота (1a)** | Операционная CRM: лиды, кандидаты, Work/Dashboard, IA v1, own-company v1, поиск — см. **§2.19** и контекст **§2** | Для **внутреннего пилота** контур считается **закрытым**, если нет **блокирующих** регрессий; открытые пункты **§2.1** в зонах **Comms stretch**, **Client portal**, **Stripe/биллинг** и **§2.17** **не удерживают** merge для **1a**, пока release gate не объявлен иным. |
| **Фазы 1b / 1c** | Монетизация (**§2.16–§2.18**, **§2.17**), клиентский портал (бэклог **§2.1**) | Отдельные вехи; **«100% коммерции»** = обнуление **`[ ]`** в **§2.1** (подразделы **Настройки владельца**, **Stripe и биллинг**) и доведение кода до спеки **§2.16–§2.18**. |
| **Stretch** | Полировка, perf SLA, декомпозиция файлов, UOS (**§2.1**) | По приоритету продукта; не метрика «готовности SSOT». |

**Практическая метрика «100% §2 для пилота»:** критерий **§2.19 (1a)** выполнен (стабильный операторский продукт); пункты **§2.1** без блокирующих регрессий для пилота трактуются как **roadmap 1b/1c/stretch**, а не как «дыра в SSOT» для **1a**.

**Практическая метрика «100% продукта по SSOT»:** нет **`[ ]`** в **§2.1** в блоках коммерции (**Настройки владельца**, **Stripe и биллинг**) либо каждый перенесён в явный **вне scope** с владельцем. Это **не** синоним ежедневной готовности репозитория.

**Сводка открытых `[ ]` (проверка актуальности):** поиск по файлу **`^- \[ \]`** — перечень дорожной карты; при закрытии задачи в коде — **`[x]`** или удаление строки (**§1.3**).

### 1.8 Канонические URL SPA под `/app`

- **Единый машиночитаемый источник правды:** **`shared/crm_app_paths.json`** (+ **`shared/crm_app_paths.schema.json`**). Оттуда генерируются таблицы путей для фронта и Python-константы/хелперы для API. Редактировать вручную только манифест (и при необходимости схему), затем **`npm run codegen:crm-app-paths`** или **`make codegen-crm-app-paths`**; в CI дрейф ловится **`npm run codegen:crm-app-paths:check`** / **`make check-codegen-crm-paths`**.
- **Фронт:** **`hostflow-frontend/src/app/crmAppPaths.generated.ts`** — сгенерированные **`CRM_APP_PATHS`**, **`CRM_APP_DRILLDOWN_HREFS`**. **`hostflow-frontend/src/app/crmAppPaths.ts`** — тонкая обёртка: реэкспорт + ручная логика **`crmAppRouteSegment()`**, **`communicationsThreadPath()`**, **`dashboardInvoiceOpsDrilldownPath()`**.
- **Backend:** **`backend/app/constants/spa_paths.py`** — сгенерирован из того же JSON; только ссылки в API (NBA, global search, billing, письма и т.д.) должны опираться на этот модуль, без сырых литералов **`"/app/..."`** вне **`spa_paths.py`**. Для интеграций в экспорте есть **`SETTINGS_INTEGRATIONS`**, **`SETTINGS_EMAIL`**, **`SETTINGS_INTEGRATIONS_META`** (составлять абсолютный URL как **`{FRONTEND_URL.rstrip('/')}{path}`** — см. **`meta_leads_oauth_redirect_uri()`**).
- **Проверка литералов в `backend/app`:** **`npm run spa-paths:check`** / **`make check-spa-paths`** / **`python3 backend/scripts/check_spa_path_literals.py`**; в CI — после codegen-check в **`backend-ci`** и **`frontend-static-qa`**. Композитный прогон путей + ключевых route-скриптов фронта: **`npm run paths:qa`** (из корня репо).
- **`hostflow-frontend/src/app/activationRoutes.ts`** — **`ACTIVATION_PATHS`** собирается из **`CRM_APP_PATHS`**.
- **Маршруты и навигация:** **`hostflow-frontend/src/app/routes.tsx`** — **`NAV_ITEMS`** и вложенные редиректы на **`CRM_APP_PATHS`**; **`APP_ROUTES`** через **`crmAppRouteSegment`**. Статические проверки, которые разбирают пути маршрутов, должны резолвить **`seg(CRM.*)`** и шаблоны вроде **`` `${seg(CRM.x)}/:id` ``** через **`hostflow-frontend/scripts/crm-paths-ast.mjs`** и **`crmAppPaths.generated.ts`** — см. **`routes:check`**, **`activation:check`**, **`comm:gates:check`**, **`permissions:check`**.
- **Work shell aliases:** **`hostflow-frontend/src/nav/workShellAlias.ts`** — список первых сегментов путей под **`/app/work/...`** выводится из **`CRM_APP_PATHS`** (редирект на канонический URL без дрейфа строк).
- **Глобальный поиск (клиент):** **`hostflow-frontend/src/api/search.ts`** — ссылки в результатах из **`CRM_APP_PATHS`**.
- **Каркас SPA и inbox:** **`main.tsx`**, **`App.tsx`**, **`AppShell.tsx`**, **`WorkPathAliasRedirect.tsx`**, **`utils/inboxDeepLinks.ts`**, редиректы **`CommunicationsMessagesPage` / `CommunicationsEmailInboxPage`**, **`SignupPage`**, **`useCommunicationsThread`**, **`SetupProgressRail`**, **`FunnelSelector`** — базовые пути из **`CRM_APP_PATHS`**.
- **Левый rail (IA):** **`hostflow-frontend/src/components/nav/Sidebar.tsx`** — секции с подписями (**`app.shell.sidebar.section_*`**, i18n **en/ru/pl**): операционка сверху вниз; затем **Организация** (**`my-company`**), **Настройки** (хаб **`/app/settings`**), **Личное** (**`profile`**). Список ключей, скрытых из рейла (но остающихся в **`NAV_ITEMS`**): **`hostflow-frontend/src/nav/appShellNav.ts`** (**`APP_SHELL_SIDEBAR_HIDDEN_ITEM_KEYS`**); детальные экраны — через **`SettingsChrome`** / лендинг. **Topbar → меню пользователя:** те же зоны (**Личное** / **Организация** при **`companies.view`** / **Настройки** при **`settings.view`** / выход) — **`Topbar.tsx`**.
- **Настройки / admin (часть):** страницы под **`pages/admin/*`** (communications, billing, integrations, users, audit, …), **`SettingsChrome`** (табы ↔ **`?section=`**, логика **`hostflow-frontend/src/nav/settingsChromeNav.ts`**), **`OnboardingGettingStartedPage`**, **`Layout`** — ссылки на **`/app/settings/...`** и смежные маршруты через **`CRM_APP_PATHS`**. **Лендинг настроек** (**`SettingsLandingPage`**) — **одна** карточка **Integration hub** → **`/app/settings/integrations`** как **каноническая точка входа для подключения** (Meta, SMTP, мессенджеры, webhook, Google); карточки Meta/Email/Communications **не дублируют** хаб на лендинге. Видимость карточки хаба — по правам (**`admin.metaLeads`**, **`admin.users`**, **`settings.view`**, либо inbox+comms), см. **`SettingsLandingPage`**. Секции лендинга и i18n разводят **интеграции**, **автоматизации (очередь, SLA)** и прочее по смыслу (**en/ru/pl**). **Онбординг и общие CTA «настроить каналы»** — сначала хаб (**`IntegrationsHubPage`**); глубокие ссылки на **`settingsIntegrationsMeta`** / **`settingsEmail`** оставлять там, где нужен конкретный экран (вкладка, диагностика, возврат OAuth). **Карта контуров CRM:** **`CRM_CONTOUR_NAV_ITEMS`** в **`hostflow-frontend/src/nav/crmContourNav.ts`** — на лендинге настроек (карточки + ссылка на **`/app/onboarding/getting-started`**) и компактная полоса **`CrmContourWayfindingStrip`** на **дашборде** (**`Dashboard.tsx`**, i18n **`app.dashboard.crm_wayfinding.*`**) и на **Work hub** (**`WorkHubPage.tsx`**, **`app.work.hub.wayfinding_*`**) и на **Inbox** (**`CommunicationsInboxHubPage.tsx`**, **`app.communications_inbox_hub.wayfinding_*`**), а при просмотре зоны лендинга (**`?section=`**) — на **`SettingsLandingPage`** (**`admin.settings.wayfinding_*`**); на **хабе автоматизаций** (**`AutomationsHubPage`**, **`app.automations.hub.wayfinding_*`**) и на **getting-started** (**`OnboardingGettingStartedPage`**, **`app.onboarding.getting_started.wayfinding_*`**) и на **онбординге компании** (**`OnboardingCompanyPage`**, **`app.onboarding.company.wayfinding_*`**), на **списке кандидатов** (**`Candidates.tsx`**, канбан **`Pipeline.tsx`**, **`app.candidates.wayfinding_*`**) и на **лидах** (**`LeadsPage.tsx`**, **`app.leads.wayfinding_*`**), на **задачах** (**`RemindersPage`**, `/app/tasks`, **`app.tasks.wayfinding_*`**), на **списке клиентов агентства** (**`AgencyClientsPage`**, **`app.clients.wayfinding_*`**) и на **каталоге компаний** (листинг в **`Companies.tsx`**, **`app.companies.list.wayfinding_*`**) и на **карточке компании** (тот же **`Companies.tsx`**, **`app.companies.detail.wayfinding_*`**); под табами **`SettingsChrome`** — на всех вложенных **`/app/settings/...`** (в т.ч. **Integration hub**), кроме корня **`/app/settings`** (i18n **`app.settings.chrome.wayfinding_*`**); на **процессинге / handoff** (**`DoProcesowaniaPage`**, **`app.handoff.wayfinding_*`**), на **услугах** (**`ServicesPage`**, **`app.services.wayfinding_*`**) и на **вакансиях** (**`Vacancies.tsx`**, **`app.vacancies.wayfinding_*`**), на **центре inbox** (**`CommunicationsInboxCenterPage`**, **`app.communications_inbox_center.wayfinding_*`**), на **странице треда** (**`CommunicationsThreadPage`**, **`app.communications_thread.wayfinding_*`**), на **детали лида** (**`LeadDetailPage`**, **`app.leads.detail.wayfinding_*`**), на **карточке кандидата** (**`CandidateCard`**, **`app.candidate_card.wayfinding_*`**), на **полной странице воронки конверсии лидов** (**`AnalyticsLeadConversionFunnelPage`**, **`app.analytics.lead_conversion.wayfinding_*`**), на **автораспределении лидов** (**`LeadsDistributionPage`**, **`app.leads.distribution.wayfinding_*`**), на **редактировании правил распределения** (**`LeadsDistributionRulesPage`**, **`app.leads.distribution.rules.wayfinding_*`**), на **календаре коммуникаций** (**`CommunicationsCalendarPage`**, **`app.communications.calendar.wayfinding_*`**), на **планировщике** (**`CommunicationsPlannerPage`**, **`app.communications.planner.wayfinding_*`**), на **SLA-инцидентах** (**`CommunicationsSlaIncidentsPage`**, **`app.sla_incidents.wayfinding_*`**), на **реестре документов** (**`DocumentsRegistryPage`**, **`admin.documents.registry.wayfinding_*`**), на **детали счёта** (**`InvoiceDetailPage`**, **`app.invoices.detail.wayfinding_*`**), на **карточке вакансии** (**`VacancyDetail`**, **`app.vacancies.detail.wayfinding_*`**), на **списке счетов** (**`InvoicesPage`**, **`app.invoices.list.wayfinding_*`**), на **создании/редактировании счёта** (**`InvoiceCreatePage`**, **`app.invoices.create_page.wayfinding_*`**), на **аудите команд коммуникаций** (**`CommunicationsCommandAuditPage`**, **`app.communications.command_audit.wayfinding_*`**), на **My Company** (**`MyCompanyPage`**, **`app.my_company.wayfinding_*`**), на **профиле** (**`ProfilePage`**, **`app.profile.wayfinding_*`**), на **детали ссылки клиента** (**`ClientLinkDetailPage`**, **`app.clients.link_detail.wayfinding_*`**), на **журнале автоматизаций** (**`AutomationLogPage`**, **`app.automation_log.wayfinding_*`**) и на **правилах автоматизаций** (**`AutomationRulesPage`**, **`app.automation_rules.wayfinding_*`**), на **доступности команды** (**`TeamAvailabilityPage`**, **`app.communications.team_availability.wayfinding_*`**), на **моей доступности** (**`MyAvailabilityPage`**, **`app.communications.my_availability.wayfinding_*`**) и на **заявках на отпуск** (**`TimeOffRequestsPage`**, **`app.communications.timeoff.wayfinding_*`**). Подписи вкладок **`SettingsChrome`** (**`app.settings.chrome.*`**) совпадают по смыслу с зонами **`admin.settings.sections.*`**. На текущем пути соответствующий чип скрывается. **Логотип в онбординге / setup rail:** не вести обычных админов на **`settingsTenants`** — **`resolveBrandingSetupHref()`** в **`hostflow-frontend/src/nav/workspaceQuickSetupNav.ts`** (**`OnboardingGettingStartedPage`**, **`SetupProgressRail`**). Чеклист **первая ценность** (**`OnboardingWizard`**) — подсказки со ссылками в **Настройки** и **getting-started**.
- **Админка коммуникаций:** **`CommunicationsSettingsPage`**, **`CommunicationsMessengerSettingsPage`**, **`CommunicationsQueueSettingsPage`**, **`CommunicationsSlaSettingsPage`** — единая терминология с хабом интеграций (мессенджеры для тредов inbox, исходящий SMTP, очередь/SLA); копирайт **`admin.communications_*`**, **`app.nav.items.settings_communications`** (**en/ru/pl**).
- **Копирайт путей (en/ru/pl):** подсказки onboarding, inbox, OAuth Gmail и чеклисты Meta/webhook описывают вход через **Integration hub**; строки про **`/app/email`** в OAuth/Google Cloud оставлены, где redirect URI по-прежнему должен совпадать с зарегистрированным у провайдера.

### 1.9 Хром подстраниц «Настройки» (ориентир для новичка)

- **Смысл каждого раздела не меняется** (воронки, биллинг, юридические тексты и т.д. остаются теми же по назначению).
- **Единый каркас экрана:** первая строка — ссылка **назад** к **`/app/settings`** (или к логичному родителю: хаб интеграций, админка коммуникаций); короткий **кикер** одной фразой («зачем этот экран»); **`h1`**; одна строка **что здесь делают**; основные кнопки — справа в шапке или ниже, без перегруза первого экрана.
- **Простой язык**; детали, сырой JSON, длинные логи — в шаги, вкладки или **`<details>`**.
- **Реализация:** **`hostflow-frontend/src/components/settings/SettingsSubpageHeader.tsx`**; общие подписи **`admin.settings.subpage.*`**, пер-страничные kickers в **en/ru/pl**.


## 2. Открытая работа

**Контекст:** операционный контур **1a** (лиды, кандидаты, Work/Dashboard, IA v1, own-company v1, поиск, интеграции Meta/Webhook, воронки, NBA, биллинг-гейты базово) **в коде закрыт**; детальные описания экранов и чеклисты «сделано» **не дублируются** здесь — см. **`docs/pipe.md`**, **`docs/pipedesign.md`**, **`docs/specs/**`**, git history.

**Метрики «100%»:** **§1.7** (пилот **1a** vs дорожная карта **1b/1c**/stretch).

### 2.1 Единый бэклог продукта (хвосты и roadmap)

*Поиск открытых пунктов в этом файле:* `^- \[ \]` в `docs/SSOT.md`.

#### Лиды, pipeline, NBA, квалификация

- Смена назначения как триггер next action / task; блокирующая валидация **`required_actions`**, цепочка handoff → следующая задача (см. client portal в **`docs/pipe.md`**); перераспределение по SLA job; полное слияние pipeline ↔ distribution.
- Playbook / NBA: расширение полей и действий из одного места; превью для кандидатов/tasks на дашборде; другие сущности в NBA; расширение **Process batch** под rule engine и не-Meta источники.
- Auto-fix: правила шире Meta-queue; «Fix all» без жёсткого лимита по плану.
- Квалификация: полноценный движок правил поверх **`lead_criteria_eval`**; **`assign_pipeline`** в automation; единый продуктовый слой «пресеты критериев на тенанта»; rich constructor правил для триггеров кроме **`lead.qualification`**.
- Интеграции / источники: **Google** ingest; отдельный mapping UI не-Meta; лимиты field_mapping / источников при нескольких реальных каналах; трансформации mapping; биллинг/апгрейд-копирайт.
- **`GET /leads` / `LeadOut`:** поле **`external_id`** — внешний id источника (для Meta — **`leadgen_id`**); используется в админском Graph picker. Канон: **`backend/app/modules/leads/schemas.py`** (`LeadOut`), сборка в **`service.py`**, **`router.py`**, **`admin_service.py`**.
- Публичный intake **client application (v1):** `POST /public/intake` с **`application_kind=client`**; при успешном **`POST .../submit`** создаётся **`Lead`** (`lead_type=client`, `source=public-intake`, `external_id=public-intake:{candidate_id}`), если известен **`company_id`** (кандидат / вакансия / **`meta_lead_settings.default_company_id`**). Иначе только **`Candidate`** (лог + in-app **`intake_client_lead_skipped_no_company`**). При создании лида — in-app **`lead_public_intake_client`** (payload с **`href`** на лид / кандидата); **`log_public_event`** для аудита. Публичный UI: баннер client mode в **`PublicIntakeNew`**, **`cloneData`** сохраняет **`application_kind`** / **`lead_form`**; операторский контекст: подсказка на **`LeadDetailPage`**, Meta admin про **`default_company_id`**. Канон: **`backend/app/api/public/intake.py`**, **`Topbar`** и вкладка Events в **`RemindersPage`** (тот же текст + **`href`** / deep link на карточку лида). Покрытие: **`test_public_intake_client_*`** в **`backend/tests/api/test_public_intake.py`**. Отключение in-app: **`ProfilePage`** → те же ключи, что **`event_type`** (`lead_public_intake_client`, `intake_client_lead_skipped_no_company`). CRM: **`GET /candidates/{id}`** отдаёт **`intake_application_kind`** (`_serialize_candidate_row`); бейдж в **`CandidateHeader`**. Публичный портал: ссылка на client intake в **`PublicPortalLanding`**. Уведомление **`intake_client_lead_skipped_no_company`** — повышенный приоритет в колокольчике (**`notificationUos`** / **`Topbar`**). Список (**`GET /candidates`**) отдаёт **`intake_application_kind`** в каждой строке; фильтр query **`intake_application_kind=client|candidate`** (**`backend/app/api/v1/candidates/router.py`**, **`repo._build_conditions`**). Таблица кандидатов (**`Candidates.tsx`**): опциональная колонка **Intake**, фильтр в шапке колонки, бейджи / localStorage / сохранённые виды. Очередь **`queue=no_next_action`** — **`GET /candidates/no-next-action`**: тот же query **`intake_application_kind`**, в **`items`** есть **`intake_application_kind`** (как в основном списке). В **Settings → Lead forms** — вторая ссылка с **`application_kind=client`** (**`LeadFormsSettingsPage`**).
- Custom fields лидов: колонка **`Lead.extra`**; расширенные операторы фильтра; typed custom + UI правил (см. **`docs/pipe.md`** / **`docs/specs/**`**).
- Воронка конверсии **v2+:** сценарные шаблоны (документы/портал), WoW-инсайты, произвольное окно когорты, тяжёлые пресеты; продуктовый слой **`lost_reason`** в root funnel.
- **`conversion-funnel` / UI:** отдельный **`lost_reason`** в продуктовом смысле (сейчас — CRM lost + аудит).

#### Multi–own-company

- Перенос FK (**`vacancies.company_id`**, **`tenant_links`**) и UI на **`client_companies`**; уход от operating-строк в **`companies`**.
- Прочие модули вне уже покрытых контуров — по аудиту скоупа.
- UI ACL (**`allowed_own_company_ids`**); продуктовые роли-матрицы; тесты.
- Own-company UX: upsell-модал, mobile-first свитчер.

#### Глобальный поиск

- Документы с join к кандидату в выдаче; ML / семантический поиск.

#### Comms / Inbox

- Массовое применение command templates к выбранным письмам/тредам при multi-select в unified inbox.

#### Полировка / stretch

- UOS / IA: общая полировка; опционально единый объект политики escalation.
- Декомпозиция **`ServicesPage`**: **`OrdersTab`**, **`OrderDetail`**, **`ServicesAnalyticsTab`**.
- Performance: формальные бюджеты SLA — после договорённости (**`pipe.md`**).
- Публичный захват документов (LLM/vision) — отдельное продуктовое решение, не регрессия.

#### Хабы Integrations / Automations (контрол-центр)

- **`IntegrationsHubPage`** / **`AutomationsHubPage`**: **`IntegrationsHubPage`** разводит **подключения** и **операционку** (inbox, админка коммуникаций) — канон входа **`§1.8`**; дальше — наполнение контрол-центром (статус, цепочка «источник → обработка», активность), не только сетка ссылок; при необходимости лёгкие API агрегатов.

#### Work / Dashboard

- Единая модель stuck / SLA / need next action с NBA/API; общий shell фильтров Work при продуктовом решении.
- Главный CTA «fix in one click» + paywall-копирайт (**§2.16**).
- Paywall: auto-assign в таблице кандидатов; выравнивание копирайта с тарифами.
- Limit modal: CTA **buy pack** / **add seats** с ценой без лишних шагов.
- Stretch: полная согласованность kanban с произвольными очередями API.

#### Client portal (хвосты)

- UX/маршрутизация портала в потоках Comms (единый слой, не отдельный чат-продукт).
- Шаблоны писем, доставляемость; чип NBA **Remind client**.
- Матрица ролей портала; скрытие internal notes как отдельный слой.
- Branded / per-client billing (**§2.16**).

#### Настройки владельца (**§2.17**)

- [ ] **Upgrade / compare**, **add-ons**, **Customer Portal** поверх текущего Checkout (**§2.18**).
- [ ] **Team:** invite + seat gate + matrix доступа к workspace (**`BillingTeamPage`** / **`UserFormInvite`**).
- [ ] **Roles** editor с серверной валидацией.
- [ ] **Companies** CRUD с предупреждением цены и enforcement **§2.16**.
- [ ] **TenantsPage:** override limits, billing adjust (**п.10**). Отдельный Platform Admin app **не** делаем.
- [ ] **Аудит:** plan change, override, invite, role change — лог в БД + минимальный UI.
- Продуктовые мастера онбординга по матрице маршрутов (п.14).

#### Stripe и биллинг (**§2.16–§2.18**)

- [ ] **Stripe:** довести до спеки **§2.18** (сводка line items / add-ons / seats; **Stripe Tax**, tax IDs, **VIES**; Checkout + webhook для остальных SKU и subscription items; **past_due grace 3d**; живые Price IDs в Stripe, в т.ч. founder **€99/€199**).
- [ ] Webhook: при необходимости **`invoice.finalized`**; очередь/ретраи при ошибках после частичного commit.
- [ ] **Trial:** UI баннеры / post-trial messaging; read-only + grace **3** дня на **всех** write-API (**сейчас** частично **`billing_restrictions`** — лиды, исходящие comms).
- [ ] **SKU паков** и UI **buy pack**; фильтры/экспорт инвойсов; синхронизация с **`invoice.finalized`**.
- Checkout/API + webhooks для SKU: seats, client portal, паки лидов/полей и т.д. (не только конфиг).
- Enforcement: логика форм (не только slug + intake); **instances** воронок vacancy↔funnel; **`storage_used_gb`**, обход загрузки без `size`; расширение post-trial гейтов; лимит instances при необходимости; остальные **402** в админ-потоках.
- Маркетинговая страница pricing; richer upsell в операционных потоках.
- Юридические черновики billing: вычитка, локализации, связка с Checkout/офертой в UI, e-sign.
- Пресеты **`business_type`** в онбординге/настройках.
- Маппинг **`TenantLicense`**, `business_type`, module flags → полная матрица **Plan + Modules + Limits** (**§2.16**).

### 2.16 Тарифы и коммерческая модель HF (SSOT для биллинга и договора)

**Назначение раздела:** единая основа для **дешёвого входа Solo**, **роста чека на Team+**, монетизации **ценности процесса** (не «доступ в CRM»), а также для **пользовательского соглашения**, биллинга, лимитов, **trial**, апгрейдов / даунгрейдов и **оверэджей**. Цены — в **EUR**, пересчёт в другие валюты — отдельная политика.

#### Задачи модели (4 цели)

1. Дешёвый вход для **solo**.  
2. Резкий рост **MRR** при переходе к **командной** работе.  
3. Оплата **модулей, лимитов и usage**, а не одной кнопки «CRM».  
4. Правовая и продуктовая база: лимиты, trial, смена плана, превышения.

#### Пять слоёв тарификации

| Слой | Смысл |
|------|--------|
| **1. Plan** | Базовый тариф: **Solo / Team / Business / Enterprise** |
| **2. Workspace / Company** | Сколько **независимых** рабочих пространств (own company / workspace) в аккаунте |
| **3. Seats** | Сколько **сотрудников** с доступом в продукт |
| **4. Modules** | Какие **функциональные блоки** включены (порталы, авто-лиды, финансы и т.д.) |
| **5. Usage / Limits** | Потолки: лиды/мес, активные сущности, файлы, поля, правила, интеграции, уведомления и т.д. |

---

#### Главная линейка (4 плана, не 7–8)

- **Solo** — индивидуальный вход.  
- **Team** — **основной коммерческий** план (ядро выручки).  
- **Business** — команда, несколько workspace, порталы, услуги, финансы, расширенная аналитика.  
- **Enterprise** — кастом, договор, объёмы.

---

#### Solo

| | |
|--|--|
| **Цена** | **€29**/мес (monthly) · **€24**/мес при годовой оплате (эквивалент месяца) |
| **Аудитория** | Индивидуальный рекрутер, solo-агент, микросервисный бизнес без команды |

**Включено (core):** 1 пользователь, **1 workspace / 1 компания**, 1 профиль бизнеса, **1 активная воронка**, базовый Dashboard и Work, лиды / кандидаты / клиенты, задачи, календарь, базовые документы, базовый Inbox, базовый просмотр email / Telegram / WhatsApp при подключённой интеграции, **ручной** перевод лида в кандидата/клиента, **assisted** recommendations **без** полного auto mode, базовая аналитика и базовая воронка конверсии, базовые фильтры, **1** форма лида, **1** подключённый источник входящих лидов.

**Не включено:** приглашение сотрудников, **client portal**, полноценный **candidate portal**, **auto-distribution**, **автообработка** лидов, массовые авто-действия, advanced analytics, командное управление, отпуска/больничные/графики, инвойсы/финблок, несколько компаний, расширенные rulesets, сложные автоматизации, white-label.

**Лимиты (ориентир):**

- До **200** новых лидов / мес.  
- До **300** активных записей в работе одновременно (активные кандидаты + клиенты + лиды, **без** архива).  
- До **5 GB** файлов.  
- До **10** кастомных полей.  
- До **1** pipeline (одна активная воронка), **1** source mapping, **1** интеграции типа lead source, **1** формы.  
- До **1** communication channel (один подключённый instance любого типа: **email inbox** / Telegram / WhatsApp — см. **«Решения по политике»**).  
- До **100** исходящих уведомлений / мес из **разрешённых** на Solo автоматизированных сервисных событий (если такие вообще доступны на плане).

**Логика апселла:** Solo **рабочий**, но с **потолком** — упирается при: invite, второй компании, портале, auto-distribution, второй воронке, доп. источниках, счетах/услугах.

---

#### Team

| | |
|--|--|
| **Цена** | **€129**/мес (monthly) · **€109**/мес при годовой оплате |
| **Аудитория** | Агентства, работодатель + рекрутер/координатор, малые команды, бизнес, которому нужен **процесс**, не таблица |

**Включено (core+):** до **3** пользователей, **1** workspace, до **3** pipeline **templates (presets)** и до **10** pipeline **instances** на workspace (см. лимиты ниже и **«Решения по политике»**), кандидаты / клиенты / лиды / вакансии / заказы, Work, Dashboard с **NBA**, Inbox / messages / email center, задачи, календарь, документы, ручная + assisted обработка лидов, **автообработка** по правилам, **auto-distribution**, SLA tracking, next action engine, **automation rules**, **candidate portal**, **client portal**, **3** клиентских доступа в портал, до **300** **active portal candidates / мес** (Team; счётчик в **`tenant.settings`** + UI **Billing**, на капе — **402** для **нового** `candidate_id` в месяце), базовый handoff клиенту, базовая аналитика воронки / источников / команды, базовые уведомления, field mapping входящих лидов, кастомные поля в фильтрах и правилах, базовая история изменений, **3** формы лидов, **3** интеграции lead sources.

**Не включено:** advanced finance analytics, полный модуль услуг с инвойсингом, расширенный branded portal, white-label, расширенные аудиты, cross-workspace orchestration, кастомные SLA matrix, сложные versioned rulesets, enterprise support / SLA guarantees.

**Лимиты (ориентир):**

- До **1 500** новых лидов / мес.  
- До **2 000** активных сущностей.  
- До **50 GB** файлов.  
- До **50** кастомных полей.  
- До **10** automation rules.  
- До **3** lead forms, **3** источников рекламы/лидов, **3** client portal clients.  
- **3** seats включено.  
- До **3** email inboxes (каждый inbox = **1** communication channel, см. **«Решения по политике»**).  
- Telegram / WhatsApp и прочие каналы — в **общем** лимите **3** channels (каждое подключение = 1 unit).  
- До **1 000** автоматических системных уведомлений / мес.  
- До **3** pipeline **templates (presets)**; до **10** pipeline **instances** на workspace.  
- **Стадии** в воронке — **без тарифного лимита**; только **tech-max** (БД / перфоманс) в продукте.

**Смысл плана:** HF становится **системой управления процессом**, а не хранилищем.

---

#### Business

| | |
|--|--|
| **Цена** | **€249**/мес (monthly) · **€219**/мес при годовой оплате |
| **Аудитория** | Несколько пользователей и **несколько** workspace/брендов, активные порталы, услуги, счета, нагрузка, бизнес-аналитика |

**Включено:** всё из **Team** + до **10** пользователей, до **3** компаний / workspaces, полноценная работа с несколькими профилями бизнеса, расширенные client/candidate portal, **branded portal basic**, handoff с историей и статусами решений, модуль **услуг/сервисов**, заказы, привязка услуг к сущностям, **счета/фактуры**, банковские и юридические реквизиты, финучёт по услугам, базовая аналитика продаж / услуг / клиентов / причин остановок, расширенная воронка, срезы по источнику / менеджеру / компании / pipeline, team management, рабочие часы, отпуска/больничные/перерывы, подтверждение запросов руководителем, распределение по доступности/нагрузке/языку, расширенные правила распределения и workflow, доп. формы и источники, приоритетная поддержка.

**Лимиты (ориентир):** до **5 000** лидов / мес, **10 000** активных сущностей, **200 GB** файлов, **200** кастомных полей, **50** automation rules, **20** lead forms, **10** источников, **25** client portal-аккаунтов, **10** seats включено, **10** communication channels (email / telegram / whatsapp — каждый подключённый instance = 1 channel), **10 000** системных уведомлений / мес, до **20** pipeline instances на workspace (presets — в рамках продуктового max). **Branded portal basic:** **add-on per workspace** (**+€49**/мес за workspace), см. **«Решения по политике»**.

---

#### Enterprise

| | |
|--|--|
| **Цена** | **от €499**/мес или **индивидуально** (workspaces, seats, хранение, white-label, интеграции, onboarding, support SLA) |

**Включено:** индивидуальные лимиты; в roadmap — **SSO**; кастомные rulesets; выделенные условия хранения; договорные условия; white-label / custom branding; кастомные интеграции; расширенный аудит; приоритетная поддержка; кастомный onboarding.

---

#### Дополнительные компании / workspaces

**Базовое включение:** **1** workspace — Solo и Team; **3** — Business. **Solo:** вторую компанию **не давать** без апгрейда до Team (альтернатива «+€35 за вторую» ломает позиционирование Solo — **не рекомендуется**).

**Аддон (помесячно):**

| План | Цена за доп. workspace |
|------|-------------------------|
| **Team** | **+€25**/мес за каждую доп. компанию |
| **Business** | **+€20**/мес за каждую доп. компанию |

**Для договора:** дополнительная company/workspace — **отдельная оплачиваемая единица**, даже если создана тем же владельцем. В определении: отдельные сущности, pipelines, пользователи/доступы, брендинг/юридические настройки, данные.

---

#### Seats

| План | Включено | Доп. seat |
|------|----------|-----------|
| **Solo** | **1** | недоступно |
| **Team** | **3** | **+€18**/мес |
| **Business** | **10** | **+€15**/мес |
| **Enterprise** | по договору | индивидуально |

**Определение seat:** любой **активный** пользователь с постоянным доступом (owner, recruiter, manager; **viewer** — по политике).

**Рекомендация для оферты:** не делать **viewer** бесплатным по умолчанию (обход лимита). Варианты: **1–2** viewer включено только в **Business**, иначе **viewer = seat**; или проще: **любой пользователь = seat** (предпочтительно для однозначности условий).

---

#### Порталы (отдельная монетизация)

**Принцип:** порталы нельзя воспринимать как «бесплатное приложение к CRM» — только через **планы + лимиты + оверейдж/апгрейд** (этот раздел и бэклог **§2.1**).

**Candidate portal**

| План | Включено |
|------|----------|
| **Team** | До **300** **active portal candidates** / календарный мес (UI **Billing** + **402** на капе для новых в месяце) |
| **Business** | До **2 000** **active portal candidates** / календарный мес (та же метрика и enforcement) |

**Overage (candidate portal, v1):** **без** Stripe metered; только **upgrade** или **pack через Checkout** (SKU, напр. +500 active portal candidates — цена в Stripe). Метрика учёта — **только** active portal candidates, **не** interactions / клики.

**Active portal candidate — метрика и счётчик (канон)**

- **Определение (месяц):** **уникальный `candidate_id`**, у которого **`portal_access = enabled`** в **любой** момент календарного месяца.  
  - **Единица учёта:** один `candidate_id`.  
  - **Период:** календарный месяц в **UTC** (зафиксировать в системе и в оферте).  
  - **Дедупликация:** один кандидат = **1** единица за месяц, независимо от числа входов, действий, сессий.

- **Не считается:** interactions (клики, просмотры, сообщения), число сессий, повторные включения/выключение в том же месяце (по-прежнему **1**).

- **Событие учёта (v1, упрощённо):** при переходе **`portal_access.enabled → true`** в текущем месяце — зафиксировать `candidate_id` в **`usage(month)`**. Повторное включение в том же месяце **не** добавляет строку.  
  - *Продуктовое поле **`portal_access`***: в данных может называться иначе до полной конвергенции; **источник истины для лимита** — описанное правило и idempotent-учёт по `candidate_id` + месяц (UTC).

- **Счётчик v1:** в **`tenant.settings`** (см. **`portal_candidate_usage.py`**); UI — **«X of cap used»** в **Billing**, предупреждения **~80%** / **100%**; API — **402** при попытке учесть **новый** `candidate_id` в текущем UTC-месяце на капе (уже учтённые могут обновлять ссылки).

**Client portal**

| План | Включено |
|------|----------|
| **Team** | До **3** активных клиентских portal-аккаунтов |
| **Business** | До **25** активных клиентских portal-аккаунтов |

**Доп. клиентский портал:** **Team +€7**/мес · **Business +€5**/мес за каждый активный доп. аккаунт.

**Брендированный портал:** **basic** — в **Business** (как в базовом плане); **full branded:** **+€49**/мес **за workspace** (**own_company**), не глобально на аккаунт — см. **«Решения по политике»**.

#### Автоматизации

Критичный слой монетизации. **Виды:** lead processing, stage-based automation, reminders, SLA actions, portal reminders, auto-assignment, communication triggers.

| План | Доступ |
|------|--------|
| **Solo** | Модуль автоматизаций как таковой **недоступен**; только **assisted suggestions** |
| **Team** | До **10** активных **automation rules** |
| **Business** | До **50** активных **automation rules** |

**Паки:** +10 rules = **€15**/мес · +25 rules = **€30**/мес.

**Определение rule (оферта):** одно **активное** правило, реагирующее на событие/условие и выполняющее действие (пример: «If source = Meta and experience ≥ 6 months → convert to candidate and assign pipeline»).

#### Кастомные поля

| План | Лимит |
|------|-------|
| **Solo** | до **10** |
| **Team** | до **50** |
| **Business** | до **200** |

**Паки:** +25 полей = **€10**/мес · +100 полей = **€25**/мес.

**Оговорка в условиях:** HF **не обязана** обеспечивать одинаковую поддержку **всех** кастомных полей во **всех** модулях, если тип поля не поддерживается конкретной функцией.

#### Источники лидов и маппинг

| План | Включено |
|------|----------|
| **Solo** | **1** source |
| **Team** | **3** sources |
| **Business** | **10** sources |

**Доп. source:** **+€10**/мес за каждый активный дополнительный источник.

**Source:** одна активная интеграция, передающая лиды (Meta Leads, Google Lead Form / webhook, website form, custom webhook, landing и т.д.).

**Field mapping:** **Solo** — базовый · **Team** — полный + custom fields · **Business** — полный + templates + multiple forms.

#### Формы лидов

| План | Лимит |
|------|-------|
| **Solo** | **1** активная форма |
| **Team** | до **3** активных форм |
| **Business** | до **20** активных форм |

**Пак:** +5 активных форм = **€10**/мес. **Форма:** отдельная конфигурация с полями, логикой и ссылкой.

#### Коммуникации (каналы)

| План | Включено |
|------|----------|
| **Solo** | **1** email channel + **1** Telegram **или** WhatsApp — базовое использование |
| **Team** | до **3** communication channels |
| **Business** | до **10** communication channels |

**Доп. channel:** **+€8**/мес. **Channel:** отдельно подключённый канал (inbox, Telegram bot, WhatsApp Business и т.д.).

**Сторонние провайдеры:** в оферте явно — *external provider fees excluded* **или** *HF may pass through third-party communication fees*.

#### Финансы / счёта / услуги

| Вариант | Содержание |
|---------|------------|
| **A (проще юридически/UI)** | Услуги, привязка к сущностям, счета/фактуры, реквизиты, аналитика продаж — **только Business и Enterprise** |
| **B (ARPU на Team)** | **Finance & Services add-on +€49**/мес к Team: услуги, счета, реквизиты, базовая аналитика продаж |

**Канон (v1):** только **вариант A** — услуги / счета / финблок **только Business+**. **Вариант B** (add-on **+€49** к Team) **не** запускаем в v1.

#### Team management

| План | Объём |
|------|--------|
| **Solo** | Нет |
| **Team** | Базовая: доступность, нагрузка, базовые часы |
| **Business** | Полная: графики, отпуска, больничные, подтверждения руководителем, расширенное распределение (availability / load / language) |

#### Analytics (уровни)

1. **Basic** (Solo): dashboard, базовая воронка, counts.  
2. **Operational** (Team): bottlenecks, overdue, no next action, pipeline performance, source/team basic.  
3. **Business** (план Business): source quality, sales, weak points, client/service analytics, time-to-stage, conversion by manager/source, drill-downs.

**Опционально:** **Advanced Analytics add-on +€39**/мес для Team/Business; можно не запускать в v1.

#### Trial

**Длительность:** **7 дней**, функционал уровня **Team или Business**, но **не** безлимит.

**Trial даёт:** **1** workspace, до **2** test seats, ограниченный test volume, demo/seeded data; **порталы, автоматизации, auto-distribution** — можно попробовать.

**Лимиты trial (канон):** **50** лидов, **20** conversion actions, **2** portal shares, **5** automation runs.

**Real sending в trial:** **запрещены** исходящие сообщения во **внешние** каналы (email / WhatsApp / Telegram). **Разрешены** internal simulation / preview.

**После окончания trial:** режим **ограниченной работы** с **grace 3 дня** (см. ниже и **§2.18** для `past_due`). **Общий принцип:** разрешено редактирование **без изменения состояния системы**; запрещено всё, что влияет на **процесс**, **коммуникации** или **автоматизацию**.

**Grace после trial:** **3** календарных дня — затем те же правила без смягчений.

##### Post-trial / past_due — редактирование без side-effects (канон)

**Разрешено (allowlist)**

- **Сущности (существующие):** Candidate, Client, Lead.  
- **Поля:** текстовые (имя, заметки, комментарии), контакты (телефон, email), **кастомные поля без триггеров**, внутренние заметки.  
- **Действия:** просмотр; правка перечисленных полей; просмотр истории.

**Запрещено**

- **Процесс:** смена стадии воронки (**pipeline stage**); создание новых сущностей; удаление.  
- **Коммуникации:** исходящие email / WhatsApp / Telegram; запуск диалогов.  
- **Автоматизация:** запуск/триггер automation rules; auto-distribution.  
- **Порталы:** выдача нового portal access; обновление доступа (кроме политики реализации для «безопасных» правок — по умолчанию **запрет**).  
- **Интеграции:** входящие вебхуки можно принимать (**опционально**), но **не** создавать новые бизнес-записи — или складывать в буфер/queue до восстановления оплаты.

**Поведение:** UI — отключённые кнопки side-effect, CTA **Upgrade to continue**; API — **403** на запрещённые действия (**`billing_restrictions`** и точечные гейты по модулям — **бэклог**).

**Оферта / анти-абьюз trial (v1 минимальный):** один trial на связку **email + домен + browser fingerprint** (карта / телефон — позже).

**Технический поток (Stripe, баннеры, read-only):** **§2.18**.

#### Overages / превышения

Режимы: **hard block** · **soft + upgrade** · **automatic overage billing** (только при **явном согласии** на автосписание).

| План | Рекомендация |
|------|----------------|
| **Solo** | **Hard block** / **forced upgrade** |
| **Team / Business** | Warning **~80%**, **100%** → upgrade **или** paid overage pack |

**Примеры паков:** +500 leads/mes **€15** · +2 000 active records **€20** · +50 GB **€10** · +10 automation rules **€15** · +5 client portal accounts **€20** (bundle к **per-unit €7/€5** — см. **«Решения по политике»** в **§2.16**).

**Оферта:** без согласия на overage **не** включать неожиданные автосписания.

#### Архивация и активные сущности

В условиях разделить **active** и **archived**. **Рекомендация:** архив **вне** лимита активных; хранение в разумных пределах; удаление по **retention** при отмене плана / закрытии / превышении хранения. Описать: что такое **active record**, когда **archived**.

**Retention после отмены подписки (канон для оферты):** данные клиента — **30** дней до **удаления**; **бэкапы** инфраструктуры до **90** дней **без** гарантии доступа клиентом (восстановление — не обещаем как право).

#### Upgrade / downgrade / cancellation

- **Upgrade:** сразу, оплата **пропорционально**.  
- **Downgrade:** со **следующего** billing cycle.

**После downgrade при превышении лимитов:** read-only, запрет новых сущностей, ограничение users/companies/rules/portals — **явно в оферте**.

#### Founder pricing

**Канон:** **да**, запускаем. Первые **50** платящих клиентов: **Team €99**/мес (вместо **€129**), **Business €199**/мес (вместо **€249**); **Solo не участвует**. Только новые подписчики в рамках квоты.

**Источник истины:** **primary** — статус подписки **Stripe** (webhooks + периодическая согласованность); **secondary** — зеркало в **`tenant.settings`** (или колонки тенанта) для UI и защиты от рассинхрона.

**«Не активна» для таймера паузы:** `canceled`, `unpaid`, `past_due` (пока не оплачено), отсутствие активной подписки; **active** / **`trialing`** считаются активными для удержания founder-льготы (пока подписка в этом статусе в Stripe).

**Правило:** если подписка **не** в активном состоянии **> 14** суток подряд → **founder pricing снимается навсегда** (**без** восстановления и исключений).

**Данные в БД (ориентир):** `founder_pricing` (или эквивалент), таймстемпы начала «простоя» и/или момента **revoke**; логика на webhook **Stripe** + обновление зеркала. **Реализация:** **`backend/app/services/founder_pricing.py`** + запись при синхронизации подписки (**`settings/billing.py`**).

#### Сегменты: Agency / Employer / Services

**Канон:** **одна** pricing-модель и **один** набор Stripe Products/Prices; сегменты = **UI presets** (**`business_type`**), **не** отдельные прайс-листы и **не** отдельные Stripe-продукты на сегмент.

- **Agency:** кандидаты, client portal, handoff, вакансии, recruitment analytics.  
- **Employer:** кандидаты, teamwork, hiring funnel, SLA, internal processing.  
- **Services:** клиенты, услуги, заказы, invoices, sales analytics.

См. **`business_type`** и IA / навигацию в **`docs/pipe.md`**.

#### Меню по планам (связь с IA)

| План | Dashboard | Inbox | Work | Tasks | Finance | Analytics | Settings |
|------|-----------|-------|------|-------|---------|-----------|----------|
| **Solo** | basic | basic | leads, candidates, clients, **1** pipeline, без advanced automation | да | **нет** | basic | limited |
| **Team** | full operational | full | full core, automation, auto-distribution, portals basic | full | **нет** (финансы только **Business+**, **§2.16** вариант **A**) | operational | full team-level |
| **Business** | полный контур | full | multi-company, расширенные модули | full | services, invoices | business analytics | расширенные |

#### Сводная таблица планов (карточка)

| | **Solo €29** | **Team €129** | **Business €249** | **Enterprise** |
|---|--------------|---------------|---------------------|----------------|
| Users | 1 | 3 | 10 | custom |
| Workspaces | 1 | 1 | 3 | custom |
| Leads/mo | 200 | 1 500 | 5 000 | custom |
| Active records | 300 | 2 000 | 10 000 | custom |
| Custom fields | 10 | 50 | 200 | custom |
| Sources | 1 | 3 | 10 | custom |
| Forms | 1 | 3 | 20 | custom |
| Portals | нет | client + candidate basic + лимиты | расширено | custom |
| Full automation / auto-distribution | нет | да | да | custom |
| Services / invoices | нет | **нет** (только **Business+**) | да | custom |

#### Дополнительные опции (единый реестр)

Extra user Team **€18** / Business **€15** · extra workspace Team **€25** / Business **€20** · extra source **€10** · +5 forms **€10** · +10 rules **€15** (+25 **€30**) · +50 GB **€10** · +5 client portal accounts **€20** (bundle; база — **€7/€5** per account, см. **«Решения по политике»**) · branded portal **+€49**/workspace · advanced analytics **+€39** (опционально). *(Finance add-on Team **+€49** — **не** в v1; см. вариант **A** выше.)*

#### Пользовательское соглашение — обязательный чеклист

**Определения:** аккаунт, пользователь, seat, workspace/company, active/archived record, source, communication channel, automation rule, portal account, **active portal candidate** — см. подраздел **«Active portal candidate — метрика и счётчик»** выше (уникальный `candidate_id` с включённым portal access за календарный месяц UTC, учёт по событию включения в v1), form, storage, billing cycle.

**Биллинг:** периодичность, авто-продление, налоги/VAT (**Stripe Tax** + **tax IDs**, базовая проверка VAT **VIES**), неуспешный платёж, заморозка.

**Лимиты и превышения:** поведение на лимите, overage, soft/hard, согласие на автосписание.

**Trial / downgrade / cancellation:** см. подразделы выше; данные после отмены.

**Third-party:** нет ответственности за стабильность внешних API; провайдеры могут менять контракты.

**Mapping / custom fields:** ответственность пользователя за настройки; HF не гарантирует корректность авто-логики при ошибочных правилах.

**Automation disclaimer:** исполнение по правилам пользователя; пользователь валидирует правила; HF не отвечает за последствия неверной настройки (**критично для юридической защиты**).

#### Запуск v1 pricing

Не усложнять: **Solo / Team / Business / Enterprise** + **extra users, workspaces, sources, branded portal** — достаточно для цены, договора и роста без демпинга. Финансы на Team через add-on **не** планируем в v1 (**вариант A**).

#### Стратегия (итог в одном блоке)

**Дёшево:** Solo. **Дорого:** команда, multi-company, **порталы**, **автоматизация**, **финансы**, многоканальные коммуникации. **Не бесплатно:** auto-distribution, client portal, automation engine, multi-company, полноценный team management.

**HF** продаётся как **план + seats + workspaces + modules + usage**; **Terms** строятся на чётких определениях единиц и лимитов.

#### Решения по политике (v1 — зафиксировано)

Одна строка SSOT для биллинга, договора и приоритета внедрения; детали metered usage — в **§2.18** / коде.

| Тема | Решение |
|------|---------|
| **Telegram / WhatsApp vs лимит каналов** | **Суммарный лимит communication channels** по плану (**§2.16**, строка про 1 / 3 / 10). Каждое **отдельное подключённое** интеграционное «окно» (Telegram bot, WhatsApp Business account, отдельный email inbox и т.д.) = **один канал**. **Нет** отдельных тарифных «корзин» вида «2 Telegram + 1 WhatsApp» на v1 — только общий счётчик. |
| **Presets vs instances vs стадии** | **Templates (presets):** Team до **3**. **Pipeline instances** на workspace: Team до **10**, Business до **20** (см. лимиты планов). Формулировка «неограниченные воронки» **не** используется. **Стадии** — **без** тарифного лимита, только **tech-max** (БД/перфоманс). |
| **Branded portal** | **Add-on per workspace:** **+€49/мес за workspace (own_company)**, в котором включён branded client/candidate portal (**§2.16**, доп. опции). Не «один флаг на весь тенант» без привязки к workspace — чтобы multi-company платил выборочно. |
| **Candidate portal — метрика лимита** | **Канон:** **Team** до **300** / **Business** до **2 000** **active portal candidates / календарный мес** (UTC), определение и счётчик — подраздел **«Active portal candidate — метрика и счётчик»**. UI **«X of cap used»**, алерты **~80%** / **100%**; API — жёсткий кап для **нового** `candidate_id` в месяце (**402**). Stripe metered — **вне** v1. |
| **Client portal — пак €20 vs €7/€5** | **Базовая модель: per account** — **Team +€7** / **Business +€5** за каждый **дополнительный** клиентский портал-аккаунт (seat **client_manager** / эквивалент в **§2.16**) сверх включённого. **Пак +5 за €20** — **опциональный bundle** при апселле (ниже, чем 5× per-unit на Team), а не вторая базовая цена. В оферте и Checkout описывать **одну** логику: по умолчанию per unit, bundle как скидочный SKU. |

---

#### Связь с продуктом (NBA, портал, автоматизация)

- Paywall и CTA в приложении (в т.ч. Work/Dashboard, портал — **§2.1**) должны ссылаться на **конкретные** строки **§2.16** (план + лимит).  
- Кодовые флаги (**`TenantLicense`**, `business_type`, module flags) — маппинг на **Plan + Modules + Limits** (бэклог **§2.1**).

#### Договор и биллинг (сводка)

Полный чеклист — подраздел **«Пользовательское соглашение — обязательный чеклист»** и блоки **Trial**, **Overages**, **Upgrade/downgrade**, **Архивация** в **§2.16** выше. Дополнительно в оферте: **неоплата**, **grace period**, соответствие заявленных модулей UI/API.

#### Код и платформа (кратко)

- **`TenantLicense`**: **`backend/app/models/tenant.py`**; лимиты — **`tenant_limits`**, **`profile_limits`**.
- Портал кандидатов / мес: **`portal_candidate_usage.py`**, **`GET /settings/billing/summary`**, enforcement при upload-link / notify.
- Founder: **`founder_pricing.py`**, Checkout / **`TenantsPage`**.
- Webhook → лимиты: **`billing._apply_license_limits`**, **`PLAN_LICENSE_LIMITS`** (**`billing.py`**).
- Platform: **`backend/app/api/v1/platform/tenants.py`**; UI — **`TenantsPage.tsx`** (superadmin в приложении).

#### Жизненный цикл SKU add-on checkout (канон v1)

| Статус | Смысл |
|--------|--------|
| **STRIPE_CATALOG** | SKU в **`stripe_price_catalog.py`**; в приложении — env Price ID (**`configured`** в **`addon_checkout_offers`**). |
| **EFFECT_READY** | Лимит + учёт + enforcement + эффект покупки + Stripe → webhook → apply. Только такие SKU в **`ADDON_PACK_CHECKOUT_READY`**. |
| **PURCHASE_ALLOWED** | Пользователь может **`POST /settings/billing/addon-pack/checkout`**: EFFECT_READY ∧ гейты ∧ (в Stripe-режиме — задан Price ID). |

**Правило:** в **`ADDON_PACK_CHECKOUT_READY`** только **EFFECT_READY**. Любой новый add-on: (1) лимит, (2) usage, (3) enforcement, (4) effect, (5) billing linkage.

**Пример полного цикла в коде:** пак форм лидов **`pack_lead_forms_5`** — таблица **`tenant_lead_forms`**, публичный intake **`/public/intake`**, magic-link с привязкой к форме; см. **`billing.py`**, **`stripe_price_catalog.py`**, OpenAPI **`public/intake.py`**.

**Ориентир лимитов в продукте:** `leads_per_month`, `active_records`, `users`, `workspaces`, `automation_rules`, `client_portals`, `candidate_portals`, `lead_forms`, `custom_fields`, `storage`, `channels`, …

**Custom fields packs на Team/Business:** лимит полей лида не применяется; **`purchase_allowed`** = нет, **`purchase_block_reason`** = `custom_fields_not_on_team_plan`.

### 2.17 Подписка, пользователи, доступы и Platform Admin

**Цель:** владелец видит **план + usage + биллинг** на одном экране; изменения согласованы с **§2.16**. Платежи — **§2.18**.

**Иерархия данных:** Account → Workspaces → Users (seats) → Roles → Subscription → Modules & Limits.

**Целевой UX (сжато):** Billing — summary, usage с прогресс-барами, CTA upgrade / add-ons / Customer Portal. Team — список, invite, workspace access matrix. Roles — матрица прав. Companies — создание с ценой за доп. workspace (**§2.16**). Platform (**TenantsPage**, не отдельное приложение) — тенанты, override limits, impersonate, аудит.

**Принципы:** лимиты видимы; апселл = действие с ценой; один Settings тенанта + один вход platform admin.

#### Матрица маршрутов Settings / CRM IA (канон vs вход)

**Источник путей:** **`shared/crm_app_paths.json`** → **`CRM_APP_PATHS`**.  
**Лендинг настроек:** **`/app/settings`** + **`?section=`** — **`SETTINGS_AREA_KEYS`** в **`hostflow-frontend/src/nav/settingsAreaNav.ts`**.

**Легенда:** **canonical** — единственное место правки; **hub** — обзор + ссылки; **entry** — вход без дубля формы; **alias** — редирект; **operational** — не в Settings.

| Ключ | Путь | Область `?section=` | Тип | Код / примечание |
|------|------|---------------------|-----|------------------|
| `settings` | `/app/settings` | — | entry | **`SettingsLandingPage`** |
| `settingsUsers` | `/app/settings/users` | `team` | canonical | **`UsersPage`** |
| `settingsCompanyAccess` | `/app/settings/company-access` | `team` | canonical | **`CompanyAccessPage`** |
| `settingsBilling` | `/app/settings/billing` | `billing` | canonical | **`BillingWorkspacePage`** |
| `settingsLegal` | `/app/settings/legal` | `workspace` | canonical | **`LegalDocumentsPage`** |
| `settingsTenants` | `/app/settings/tenants` | `workspace` | canonical | **`TenantsPage`** (superadmin) |
| `settingsTenantLinks` | `/app/settings/tenant-links` | `workspace` | canonical | **`TenantLinksSettingsPage`** |
| `settingsAudit` | `/app/settings/audit` | `workspace` | canonical | **`AuditLogPage`** |
| `settingsFunnels` | `/app/settings/funnels` | `crm_setup` | canonical | **`FunnelsPage`** |
| `settingsHiringPipelineGates` | `/app/settings/hiring-pipeline-gates` | `crm_setup` | canonical | **`HiringPipelineGatesSettingsPage`** |
| `settingsRiskIntel` | `/app/settings/risk-intel` | `crm_setup` | canonical | **`RiskIntelSettingsPage`** |
| `settingsDocs` | `/app/settings/docs` | `crm_setup` | canonical | **`DocumentTypesPage`** |
| `settingsCandidateProfiles` | `/app/settings/candidate-profiles` | `crm_setup` | canonical | **`CandidateProfilesPage`** |
| `settingsCustomFields` | `/app/settings/custom-fields` | `crm_setup` | canonical | **`CustomFieldsPage`** |
| `settingsLeadForms` | `/app/settings/lead-forms` | `crm_setup` | canonical | **`LeadFormsSettingsPage`** |
| `settingsTtvReport` | `/app/settings/ttv-report` | `crm_setup` | canonical | **`TtvReportPage`** |
| `settingsRuleset` | `/app/settings/ruleset` | `automations` | canonical | **`RulesetVersionsPage`** |
| `settingsEmail` | `/app/settings/email` | `integrations` | canonical | **`EmailSettingsPage`** |
| `settingsIntegrations` | `/app/settings/integrations` | `integrations` | hub | **`IntegrationsHubPage`** |
| `settingsIntegrationsMeta` | `/app/settings/integrations/meta` | `integrations` | canonical | **`MetaLeadsAdminPage`** |
| `settingsIntegrationsGoogle` | `/app/settings/integrations/google` | `integrations` | canonical / заглушка | **`IntegrationsSourcePlaceholderPage`** |
| `settingsIntegrationsWebhook` | `/app/settings/integrations/webhook` | `integrations` | canonical | **`IntegrationsWebhookPage`** |
| `settingsCommunications` | `/app/settings/communications` | `integrations` | canonical | **`CommunicationsSettingsPage`** |
| `settingsCommunicationsMessengers` | `/app/settings/communications/messengers` | `integrations` | canonical | **`CommunicationsMessengerSettingsPage`** |
| `settingsCommunicationsQueue` | `/app/settings/communications/queue` | `automations` | canonical | **`CommunicationsQueueSettingsPage`** |
| `settingsCommunicationsSla` | `/app/settings/communications/sla` | `automations` | canonical | **`CommunicationsSlaSettingsPage`** |
| `settingsLeads` | `/app/settings/leads` | `integrations` | **alias** | Редирект → **`settingsIntegrationsMeta`** |
| `profile` | `/app/profile` | `personal` | canonical | **`ProfilePage`** |
| `automations` | `/app/automations` | — | hub | **`AutomationsHubPage`** |
| `automationRules` | `/app/automation-rules` | — | canonical | **`AutomationRulesPage`** |
| `automationLog` | `/app/automation-log` | — | canonical | **`AutomationLogPage`** |
| `leadsDistribution` | `/app/leads/distribution` | — | operational | **`LeadsDistributionPage`** |
| `leadsDistributionRules` | `/app/leads/distribution/rules` | — | operational | **`LeadsDistributionRulesPage`** |
| `tasks` | `/app/tasks` | — | operational | Напоминания — не дублировать в Settings |

**Meta Leads:** самообслуживание — `GET /api/v1/settings/leads/meta/self-serve-onboarding`; быстрый коннект (Facebook Login) — `POST /api/v1/settings/leads/meta/oauth/start`, `.../complete`, `.../finalize` (только **administrator**, план Team+). Подробнее: `docs/specs/integrations/meta_leads_setup.md`.

**Правила:** новый экран → строка в таблице + карточка на **`SettingsLandingPage`**; без двойного монтирования формы без **`alias`**; **`SettingsChrome`** ↔ **`settingsChromeNav.ts`**.

**Состояние в коде:** биллинг — **`BillingWorkspacePage.tsx`**, **`billing.py`** (**`usage`** / **`usage_caps`** в summary). Команда — черновик **`TeamManagementPanel`** на **`BillingTeamPage.tsx`**. Platform — **`TenantsPage.tsx`**.

### 2.18 Stripe: trial → оплата → лимиты → UX

**Цепочка:** действие пользователя → Checkout / Portal / update subscription → webhooks → состояние подписки → лимиты и фичи. **Канон:** одна подписка на тенант; add-ons = **line items**.

**Состояния:** trial, active, past_due, canceled, incomplete — см. таблицы и UX в предыдущей версии спеки; **post-trial / past_due** allowlist правок без side-effects + grace — **§2.16**.

**Обязательные webhooks:** `checkout.session.completed`, `customer.subscription.created|updated|deleted`, `invoice.payment_succeeded` / `invoice.paid`, `invoice.payment_failed`. Идемпотентность — **`StripeWebhookEventLog`** (**`billing.py`**).

**Код (актуально):** **`backend/app/api/v1/settings/billing.py`** (checkout, webhook, portal); фронт **`BillingWorkspacePage.tsx`**, **`billing.ts`**; ограничения — **`billing_restrictions.py`**; модалка лимита — **`PlanLimitModalProvider`**, **`friendlyError.ts`**, **`showPlanLimitIfNeeded`** на ключевых экранах (кандидаты, лиды, pipeline, документы, comms, биллинг, инвайт и т.д.); квоты — **`lead_quota.py`**, **`tenant_quota.py`**.

**Бэклог:** см. **§2.1** (Stripe/Trial/webhooks/packs). **Целевой UX (сжато):** сводка перед Checkout (план, seats, add-ons, VAT ID, Monthly/Yearly); **Stripe Tax** / tax IDs / **VIES**; список инвойсов в Settings; proration при смене подписки; **cancel_at_period_end**; **past_due** → Retry → Portal; лимит → тот же Stripe-поток (**§2.16** цены). Пошаговая редакция с таблицами состояний — при необходимости **git history** файла до сокращения 2026-04-02.

### 2.19 Порядок работ (зафиксировано)

1. **Продукт и платформа (итеративно):**
   - **1a** — операционная CRM: критерий пилота — **§1.7**; stretch (**§2.1** полировка, perf, comms bulk) не блокирует 1a без объявленного release gate.
   - **1b** — монетизация (**§2.16–§2.18**, **§2.17**).
   - **1c** — клиентский портал — хвосты в **§2.1** после стабилизации 1a или по приоритету.
2. **GTM / коммерция снаружи** — после достаточной готовности **1b**, не после механического обнуления каждого **`[ ]`**.

**Примечание:** полный ноль **`[ ]`** по **§2** — ориентир дорожной карты; для пилота использовать **§1.7**.

---

*Обновлено: 2026-04-02 — сокращение SSOT: удалены выполненные чеклисты и дублирующие «исторические» описания; коммерция **§2.16**, матрица **§2.17**, целевая цепочка **§2.18** и единый бэклог **§2.1** сохранены.*

