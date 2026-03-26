# HostFlow SSOT (Single Source of Truth)

Этот файл — **короткий операционный документ**: **правила, которые влияют на разработку**, и **что ещё предстоит сделать**.  
История релизов, Evidence PASS, развёрнутые спеки и аудиты **не дублируются** здесь: смотри **git history**, **`docs/pipe.md`**, **`docs/pipedesign.md`**, **`docs/specs/**`**.

---

## 1. Правила для разработки

### 1.1 Роль `docs/SSOT.md`

- **Не создавать** отдельные markdown-файлы-трекеры прогресса в репозитории. Открытая работа фиксируется **здесь** (или в коде/issue-трекере команды — но не третьим «историческим» MD-трекером).
- Поддерживающая документация (blueprint, дизайн, модульные спеки) **может** существовать в `docs/`, но **не заменяет** этот файл для бэклога.

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
- Модульные спеки: **`docs/specs/**`**

### 1.6 Канонические URL SPA под `/app`

- **Единый машиночитаемый источник правды:** **`shared/crm_app_paths.json`** (+ **`shared/crm_app_paths.schema.json`**). Оттуда генерируются таблицы путей для фронта и Python-константы/хелперы для API. Редактировать вручную только манифест (и при необходимости схему), затем **`npm run codegen:crm-app-paths`** или **`make codegen-crm-app-paths`**; в CI дрейф ловится **`npm run codegen:crm-app-paths:check`** / **`make check-codegen-crm-paths`**.
- **Фронт:** **`hostflow-frontend/src/app/crmAppPaths.generated.ts`** — сгенерированные **`CRM_APP_PATHS`**, **`CRM_APP_DRILLDOWN_HREFS`**. **`hostflow-frontend/src/app/crmAppPaths.ts`** — тонкая обёртка: реэкспорт + ручная логика **`crmAppRouteSegment()`**, **`communicationsThreadPath()`**, **`dashboardInvoiceOpsDrilldownPath()`**.
- **Backend:** **`backend/app/constants/spa_paths.py`** — сгенерирован из того же JSON; только ссылки в API (NBA, global search, billing, письма и т.д.) должны опираться на этот модуль, без сырых литералов **`"/app/..."`** вне **`spa_paths.py`**.
- **Проверка литералов в `backend/app`:** **`npm run spa-paths:check`** / **`make check-spa-paths`** / **`python3 backend/scripts/check_spa_path_literals.py`**; в CI — после codegen-check в **`backend-ci`** и **`frontend-static-qa`**. Композитный прогон путей + ключевых route-скриптов фронта: **`npm run paths:qa`** (из корня репо).
- **`hostflow-frontend/src/app/activationRoutes.ts`** — **`ACTIVATION_PATHS`** собирается из **`CRM_APP_PATHS`**.
- **Маршруты и навигация:** **`hostflow-frontend/src/app/routes.tsx`** — **`NAV_ITEMS`** и вложенные редиректы на **`CRM_APP_PATHS`**; **`APP_ROUTES`** через **`crmAppRouteSegment`**. Статические проверки, которые разбирают пути маршрутов, должны резолвить **`seg(CRM.*)`** и шаблоны вроде **`` `${seg(CRM.x)}/:id` ``** через **`hostflow-frontend/scripts/crm-paths-ast.mjs`** и **`crmAppPaths.generated.ts`** — см. **`routes:check`**, **`activation:check`**, **`comm:gates:check`**, **`permissions:check`**.
- **Work shell aliases:** **`hostflow-frontend/src/nav/workShellAlias.ts`** — список первых сегментов путей под **`/app/work/...`** выводится из **`CRM_APP_PATHS`** (редирект на канонический URL без дрейфа строк).
- **Глобальный поиск (клиент):** **`hostflow-frontend/src/api/search.ts`** — ссылки в результатах из **`CRM_APP_PATHS`**.
- **Каркас SPA и inbox:** **`main.tsx`**, **`App.tsx`**, **`AppShell.tsx`**, **`WorkPathAliasRedirect.tsx`**, **`utils/inboxDeepLinks.ts`**, редиректы **`CommunicationsMessagesPage` / `CommunicationsEmailInboxPage`**, **`SignupPage`**, **`useCommunicationsThread`**, **`SetupProgressRail`**, **`FunnelSelector`** — базовые пути из **`CRM_APP_PATHS`**.
- **Настройки / admin (часть):** страницы под **`pages/admin/*`** (communications, billing, integrations, users, audit, …), **`SettingsChrome`**, **`OnboardingGettingStartedPage`**, **`Layout`** — ссылки на **`/app/settings/...`** и смежные маршруты через **`CRM_APP_PATHS`**.

---

## 2. Открытая работа

### 2.1 Критично (лиды / «живая» система)

Открытых пунктов под этим заголовком нет. Бэклог по лидам / pipeline / NBA — **§2.3**.

### 2.2 Онбординг

- [x] Одна кнопка: удалить / скрыть **демо-данные** после onboarding — **`POST /api/v1/onboarding/clear-demo-data`** (admin), **`clearOnboardingDemoData`** + rail **`SetupProgressRail`** на Dashboard; флаг **`settings.onboarding.demo_data_cleared_at`**; **`GET /onboarding/status` → `demo_seeded`** = активные демо ещё не очищены.
- [x] Пресеты воронки **по отрасли** — **`backend/app/modules/companies/funnel_presets.py`** (`business_funnel_presets(company_type, industry)`); industry из онбординга / **`settings.onboarding.industry`** / **`Company.extra.industry`**; bootstrap в **`companies/crud.py`** → **`_bootstrap_default_funnels_for_business_type`**.
- [x] Preset **рабочих часов** → **`User.extra.working_hours_v1`** + маршрутизация: **`working_hours_presets.py`** (онбординг / `actor_user_id`), **`working_hours_window.py`**; **`lead_distribution._build_distribution_team`** помечает вне окна **offline**, если в **`criteria_order`** есть **`working_hours`**; UI выбора — **`OnboardingCompanyPage`**.
- [x] Жёсткий **paywall по плану** для automation / **client portal** (**§2.15**) / team invites (не только CTA в UI). Конкретика планов, лимитов и аддонов — **§2.16**. **В коде:** `plan_feature_gates` (automation rules: `plan_requires_team`, исключение — только `PATCH enabled=false`; auto-distribution тот же слой `plan_allows_team_tier_features`); `portal_link_limits` по **`TenantLicense.max_public_portal_links`**; seats — **`users`**: `seat_limit_reached` при наличии строки **`tenant_licenses`** (роли → `max_recruiters` / `max_supervisors` / `max_client_managers` / `max_viewers`, учёт pending invites).
- [x] **i18n** для ключей онбординга (убрать опору на `defaultValue` где осталось) — **`OnboardingCompanyPage`**, **`OnboardingGettingStartedPage`**, **`OnboardingWizard`**; строки в **`hostflow-frontend/src/i18n/{en,ru,pl}.json`** под **`app.onboarding.*`** (включая часы, отрасли, type cards, magic/ready, upsell, getting_started checklist).

### 2.3 Лиды: distribution, pipeline, карточка, NBA

**Состояние в коде (частично):** напоминания / «next action» — **`GET /api/v1/notifications`**, **`RemindersPage`** (`/app/tasks`); строки **`app.reminders.*`** (вкл. **`filters.search_tasks` / `search_events`**, действия по уведомлениям), **`app.notifications.*`** (типовые заголовки событий), **`app.topbar.*`** (панель уведомлений, quick create, trial, язык) и **`app.shell.account.my_account`** — в **`i18n/{en,ru,pl}.json`**; в **`Topbar.tsx`** aria для кнопок inbox — **`app.nav.items.messages_inbox` / `email_inbox`**, ссылка «Inbox» — **`app.nav.items.inbox`**. Динамические подписи (**RemindersPage**: приоритет, SLA, статус строки; **Topbar**: ключи из payload / **`app.notifications.event_types.*`**) оставляют **`defaultValue: ''`** там, где ключ может отсутствовать. Метрики no-next-action / leads — блоки в **`analytics`** и **Overview** (`Dashboard.tsx`). Это **не** ещё единый **NBA API** и продуктовый слой из пунктов ниже.

- [x] **Хук смены стадии лида (v0):** при **`PATCH /api/v1/leads/{id}`** и при **`PATCH /api/v1/leads/bulk`** (если в payload есть **`stage`**) — **`pipeline_hooks.py`**: на каждый лид с реальным изменением стадии — activity **`lead.stage_changed`**, in-app **`lead.pipeline.stage_changed`**, automation **`lead.pipeline.stage_changed`** (контекст `from_stage` / `to_stage` / `lead_id` / `assignee_id`; правила **после** commit, по аналогии с **`lead.processed`**). UI триггера — **`AutomationRulesPage`**.
- [x] **Единая система с pipeline (v1 — часть):** авто-distribution (**`pick_assignee_user_id_for_ingest`**, **`lead_distribution.py`**) сужает пул по **`FunnelStage.stage_contract_v1.owner_role`** текущей CRM-стадии лида (воронка типа **lead**: **`lead.funnel_id`** или дефолт тенанта): маппинг на **`User.role`** (`recruiter` / `manager`→supervisor / `admin`→administrator; несколько значений через запятую/пробел); при пустом пересечении — откат к полному пулу; в **`team`** snapshot каждого члена добавлено поле **`role`**. Уже было: хуки смены стадии (**`pipeline_hooks`**), workload/language/working_hours/round-robin, enforcement next action при смене стадии, automation **`lead.pipeline.stage_changed`**. **Остаётся (целевая модель):** смена назначения как триггер создания next action / task; блокирующая валидация **`required_actions`** и цепочка handoff → следующая задача (**§2.15**); перераспределение по SLA как отдельный job; полное слияние pipeline ↔ distribution сверх текущих правил.
- [x] **Модель стадии в данных воронки (v1):** JSON **`stage_contract_v1`** на **`FunnelStage`** с полями **`owner_role`**, **`required_actions`**, **`sla_hours`**, **`auto_rules`**; миграция **`202603252000_funnel_stage_contract_v1`**; API **`FunnelStageIn` / `FunnelStageOut`** в **`funnels.py`** (PATCH не затирает контракт, если тело без **`stage_contract`**). UI: **`FunnelsPage`** — вкладки **Candidates / Leads**, в модалке стадии блок **Pipeline contract**. Сиды онбординга пока не заполняют контракт — только ручной ввод / API.
- [x] **Карточка лида / inbox (v1):** ручная смена стадии + **`assignment_locked`** → **`normalized.assignment_lock_v1`** (**`PATCH /leads/{id}`**; поле **`stage`** только если передано в теле — нет лишнего сброса); **enforcement** next action только при **реальной** смене стадии; **`GET /leads`** — **`funnel_id`**, **`stage_contract`**; **Composer** — сводка next action + контракт стадии; **bulk** — enforcement; **`pick_assignee_user_id_for_ingest`** пропускает авто-назначение при **`assignment_lock_v1.locked`**. **Full-page (v0):** **`GET /api/v1/leads/{id}`** — тот же **`LeadOut`**, что элемент списка; SPA **`/app/leads/:leadId`** (**`LeadDetailPage`**) — сводка полей, **Meta troubleshoot:** компонент **`LeadMetaProblemPanel`** (**Retry** / **Reroute** / ссылки Integrations) — на **`LeadDetailPage`** и на вкладке **Fix** inbox **`LeadsPage`** (единая реализация), **CRM:** стадия + **`assignment_locked`** (**`PATCH /leads/{id}`**), **follow-up** (**`listReminders` / `createActivity` / `completeActivity`**), таймлайн, ссылки (кандидат / клиент / заказ / **Process** для Meta); **тихий refresh** карточки после Meta-fix (**`loadLead({ silent })`**, без полноэкранного loading); при **Retry** / **Process** в строке таблицы и вкладке **History** — обновление таймлайна, если открыт тот же лид; после **Process** на полной карточке — **`loadLead({ silent })`** + таймлайн. **Общие CRM-хелперы лида:** **`hostflow-frontend/src/utils/leadCrm.ts`** — **`CRM_STAGE_VALUES`**, **`leadAssignmentLocked`**, **`isMetaProblemLead`** (список / inbox Fix / **`LeadMetaProblemPanel`**). **Виджет next action + контракт стадии (v0):** общий компонент **`LeadNextActionPlaybook`** — **`LeadsPage`** (вкладки **Composer**, **Focus**, **History**, **Fix** для Meta-troubleshoot) и **`LeadDetailPage`**; строки **`app.leads.inbox.*`** (вкл. **`playbook.*`**, баннер фильтров, вкладки, toasts **`stage_updated` / `lock_saved`**, **`lock_assignment`**, **`stage_unset`**) и **`app.leads.detail.*`** (**`LeadDetailPage`**, ошибки стадии/lock в inbox), плюс **`app.leads.messages.*`**, **`app.leads.bulk.*`**, **`app.leads.stage_health.*`**, **`app.leads.workspace.distribution_cta`** (рядом с заголовком workspace; отдельно от **`app.nav.items.leads_distribution`** в сайдбаре), **`app.reminders.*`** для follow-up на лиде, корень **`common.retry`** в **`i18n/{en,ru,pl}.json`**; для перечисленных ключей в коде **`t()`** без дублирующего **`defaultValue`**; в шапке inbox-панели — ссылка на **`/app/leads/:leadId`**. **Dashboard NBA (v1):** под заголовком — текстовая подсказка **`app.dashboard.nba.playbook_hint_*`** + ссылка на **`/app/leads`**; под чипами — **`LeadNextActionPlaybook`**: превью по **`GET /leads?limit=1`** с теми же **`status` / `stage` / `next_action`**, что у первой непустой группы лидов NBA (порядок как в **`GET /next-actions`**, приоритет разблокированных очередей); строка **`app.dashboard.nba.playbook_loading`**. **Остаётся:** расширение полей / действий из одного места; превью playbook для кандидатов/tasks на дашборде — не делали (только чипы).
- [x] Правила distribution: **drag-and-drop** порядка критериев — **`LeadsDistributionRulesPage.tsx`** (`@dnd-kit` + ручка **IconGripVertical**); строки **`app.leads.distribution.rules.*`** в **`i18n/{en,ru,pl}.json`**.
- [x] **Working hours** из календаря (**`User.extra.working_hours_v1`**) в фильтре назначения (статус **offline** вне окна при **`working_hours`** в **`criteria_order`**) — уже было в **`lead_distribution.py`**; **«why» (v0):** **`assignment_detail_lines`** + **`next_preview.detail_lines`** (сколько коллег вне окна; уточнение по календарю в **`rules_summary_lines`**); карточки команды на **`LeadsDistributionPage`** — **`within_working_hours`** / **`working_hours_configured`**.
- [x] **Round-robin** с сохранённым указателем между назначениями — **`lead_distribution.round_robin_last_user_id`** в **`Tenant.settings.lead_distribution_v1`**; циклический следующий в порядке команды из **`_build_distribution_team`**; сброс курсора при смене стратегии с **round_robin** на другую в **`patch_distribution_settings`** (`lead_distribution.py`).
- [x] **Явный маппинг language → user (v0):** **`Tenant.settings.lead_distribution_v1.language_routing_v1`** — объект **`{ "pl": ["uuid", …], "en": […] }`** (порядок = приоритет); **`_lang_pool_for_distribution`** / **`language_route_user_ids`** в **`lead_distribution.py`**; PATCH **`language_routing_v1`** с фильтром по активным пользователям тенанта; UI — **`LeadsDistributionRulesPage`** (PL/EN/DE). Если никто из карты не eligible — откат к языкам из **`preferences`/`extra`**.
- [x] **Воронка в UI (health по CRM-стадиям, v0):** **`GET /api/v1/leads/stage-health`** — **`lead_stage_health_snapshot`** в **`service.py`**; строки **`LeadStageHealthRow` / `LeadStageHealthResponse`** в **`schemas.py`**; роут **до** **`PATCH /{lead_id}`** в **`router.py`**. **`LeadsPage`**: горизонтальная полоса карточек по стадиям — processed в стадии, ссылки на **`GET /leads`** с теми же **`status` / `stage` / `next_action`**, что NBA; **`fetchLeadStageHealth`** в **`api/leadStageHealth.ts`**. Фильтр **stuck** при явном **`stage`**: не режем по allowlist **`leads_next_action_sla_v1.stages`** (иначе **converted/lost** всегда 0). **Остаётся:** канбан-колонки, dwell / потери (**§2.12**).
- [x] **Dashboard Auto-fix (v0):** **`POST /api/v1/leads/bulk/auto-process-queue`** — до **50** Meta-лидов со статусами **`needs_routing` / `failed`** (тот же контур, что **`POST /leads/{id}/process`**); фильтр **`own_company_id`** как у списка; paywall **`plan_allows_team_tier_features`** (как automation / distribution). UI: **`DashboardLeadAutoFixCard`** под NBA-секцией; **`bulkAutoProcessLeadQueue`** в **`client.ts`**. **Остаётся:** расширить правилами (не только Meta queue), «Fix all» без лимита / очереди по плану.
- [x] **NBA — лиды + кандидаты (v0–v1):** **`GET /api/v1/next-actions`** — **`next_actions.py`**; **`lead_next_actions_snapshot`** в **`service.py`** (`actor_user_id` = текущий пользователь). **Лиды:** как раньше + **gating** / **`plan_code`** / **`nba_tier`** / **`locked`** на **stuck**. **Кандидаты (v1):** **`candidates_no_next_action`** (как **`GET /candidates/no-next-action`**, учёт **`own_company_id`**); **`candidates_next_overdue`** — join **`Reminder`↔`Candidate`**, просрочка как у лидов; **`entity=candidate`**, **`path`** → **`/app/candidates/no-next-action`** или **`/app/tasks`** + **`query.tab` / `t_*` / `t_due_bucket=overdue`**. Схема **`NextActionQueryParams`** расширена под SPA. UI: **`LeadsPage`** — индиго чипы кандидатов, **`nbaGroupHref`** в **`nextActions.ts`**; **`RemindersPage`** — чтение **`t_due_bucket`** и фильтр списка. **Do now:** bulk через **`useNbaQuickBulkFlow`** + **`NbaNextActionsChips`** — **`POST /activities/bulk`** для **лидов** и **кандидатов** (как выше). **Dashboard:** **`DashboardNbaSection`** (`components/nba/DashboardNbaSection.tsx`) под **`SetupProgressRail`**, при **`leads.view`** и непустых группах. **Topbar:** **`TopbarNbaMenu`** (`components/nba/TopbarNbaMenu.tsx`) — попап NBA + badge суммы счётчиков, **`useNbaQuickBulkFlow`** + **`BulkActivitiesModal`**. **Остаётся:** другие сущности в NBA.
- [x] **Управляемая квалификация / конверсия лидов (v1 — хранение + ingest):** колонка **`meta_lead_settings.leads_processing_mode_v1`** (`manual` / `assisted` / `automatic`; в API **`MetaLeadSettingsOut`** при `NULL` в БД отдаётся **`assisted`**); миграция **`202603252100_meta_lead_processing_mode_v1`**; **`ensure_schema`** / **`admin_service._ensure_settings_schema`**. **`GET/PATCH /api/v1/settings/leads/settings`**. В **`process_normalized_lead`**: в **`normalized`** — **`leads_processing_mode_configured_v1`**, эффективный **`leads_processing_mode_v1`** (для **`automatic`** без Team-tier плана — **`manual`**, плюс **`leads_processing_mode_downgrade_v1`=`team_plan_required`**); автосоздание кандидата только если **`auto_create_enabled`** и эффективный режим **не** **`manual`**. UI: **`MetaLeadsAdminPage`**, **`i18n`** **`app.admin.meta_leads.settings.processing_mode_*`**. **Остаётся:** движок правил, Assisted на карточке лида, NBA/CTA и прочее по **§2.10**; связка с fit-check (**§2.5**).
- [x] **§2.11 v0 (каркас):** хаб **Integrations** — **`/app/settings/integrations`** (список источников; Meta → **`/app/settings/integrations/meta`**); **View incoming (Meta)** — **`GET /api/v1/settings/leads/meta/incoming-preview`**, вкладка **Incoming** на **`MetaLeadsAdminPage`** (последние лиды `source=meta`, превью JSON `payload` / `normalized`). Старые ссылки **`/app/settings/integrations?tab=…`** редиректят на **`/meta?tab=…`**.
- [ ] **Единая цепочка источников → поля → правила → pipeline** — целевая модель **§2.11** (полный продукт: Google/Webhook как источники, централизованный custom fields + rule engine, pipeline builder UI и т.д.).
- [ ] **Воронка конверсии как инструмент управления** (потери, скорость, причины, действия) — **§2.12**; связка с NBA (**§2.3**) и маппингом pipeline (**§2.11**).

### 2.4 Multi–own-company (scoped `own_company_id`)

- [ ] **Legacy `companies` → миграция**: правила маппинга в `client_companies`; ссылки в биллинге/инвойсинг на `own_companies`; при необходимости read-only слой на переходный период.
- [ ] **Полное покрытие скоупом**: аудит модулей — list/get/update везде с **`own_company_id`**; create без тихого `null`.
- [ ] **Права**: опционально ACL «не все own-companies» для ролей; **audit** переключения активной own-company (who/when/from/to).
- [ ] **UX**: действие **«Создать own-company»** в свитчере (лимит плана, upsell).
- [ ] **Vacancy requirements + fit-check** корректны при смене скоупа; опционально флаг **`leads_auto_convert_on_fit_v1`** (lead→candidate) per tenant / vacancy.

### 2.5 Vacancy requirements / lead fit-check (v2+)

Критерии вакансии, глобальные правила тенанта (**§2.10**) и типизированные поля лида (**§2.11**) нужно **свести в одну стратегию** (общая модель или явные слои), чтобы не было двух несовместимых «истин».

- [ ] UI менеджера пресетов (create/edit/delete), не только API.
- [ ] Расширение критериев (nationality, location, языки, реальные статусы документов из модуля Documents).
- [ ] Авто-конверсия лида при `fit` — см. **§2.4** (флаг + safeguards).

### 2.6 Глобальный поиск и IA

- [x] **v1** единый backend **`GET /api/v1/search`** — кандидаты, компании, вакансии **и лиды**; маскирование клиентского тенанта как в списке кандидатов; серверная склейка + эвристика ранжирования (**`backend/app/services/global_search_v1.py`**, **`backend/app/api/v1/global_search.py`**). **Лиды:** **`_search_leads_slice`** — поиск по тексту **`normalized` / `payload`**, id, source, stage, status, тип лида, имя связанной **`Company`**; те же **`tenant_id` / `own_company_id`**, что у вакансий; **не** для ролей **`client_manager` / `client_processor`** (как список **`GET /leads`**); тип ответа **`lead`**, ссылка **`/app/leads/{id}`**. Фронт: **`searchGlobal`** → **`/search`**; тип **`lead`** в **`search.ts`**, подпись в **`Topbar`** + **`i18n`**. Документы, треды, задачи, счета и service orders по-прежнему с клиента.
- [ ] **Остаётся:** полнотекст / ML-релевантность; остальные сущности в том же endpoint (документы и т.д. на бэкенде).
- [x] При **`scope_tenant_id`** (как у списка кандидатов): компании и вакансии в **`GET /search`** идут в том же скоупе (**`global_search_v1`**: временный контекст сессии + **`compute_tenant_visibility_for_tenant`**); запросы к сущностям выполняются **последовательно** на одной сессии (без гонок **`set_config`**). Опционально на фронте передать **`scopeTenantId`** в **`searchGlobal`** там, где списки уже шлют override.

### 2.7 Comms / Inbox

- [ ] **Email bulk command templates** (заметка из прошлого бэклога UOS — уточнить продуктово и разбить на задачи при старте).

### 2.8 Прочее / полировка

- [ ] **Первичное меню по сценариям работы** (не «карта БД») — целевая IA **§2.13**; код: **`hostflow-frontend`** — **`Sidebar.tsx`**, **`NAV_ITEMS`**, **`routes.tsx`**; канон URL — **§1.6**.
- [ ] **UOS / IA — stretch**: общая полировка; при необходимости **единый объект политики escalation** (vs разрозненные пути M1/M4 в старых доках).
- [ ] **R1.P0 follow-up**: при регрессиях — перепроверить DnD колонок / resize таблицы кандидатов под нагрузкой.
- [ ] Опционально: декомпозиция **`ServicesPage.tsx`** без изменения продуктового PASS.
- [ ] **Performance (`pipe.md`)**: формальные бюджеты под aggressive цифры — только когда станут **договорным SLA** (до тех пор — существующие perf keys / budgets в коде).

### 2.9 Публичный захват документов

- [ ] Старый публичный scanner снят; **новый** поток захвата документов (например LLM/vision) — отдельное решение продукта; не восстанавливать OpenCV-публичный UI без явного решения.

### 2.10 Управляемая автоматизация обработки лидов (не «магия»)

**Цель:** предсказуемая система с ответами на три вопроса: **кандидат или клиент?** · **проходит ли критерии?** · **что делать дальше?**  
**Поток:** `Lead → Qualification → Decision → Conversion → Pipeline start` (далее — next action / distribution, **§2.3**).

#### Режимы (не прыгать сразу в full auto)

| Режим | Смысл | План (ориентир) |
|--------|--------|-----------------|
| **Manual** | решает пользователь | **SOLO** |
| **Assisted** | система **предлагает**, пользователь **подтверждает** | рекомендованный промежуточный дефолт |
| **Automatic** | конверсия + назначение **без участия** | gating **Team+**; включать осознанно |

**UI настройки:** блок *Lead processing* — выбор режима (например radio: Manual / Assisted (recommended) / Automatic).

#### Правила (ядро)

- Условия **как фильтры** (без кода): source, язык, страна, опыт, документы, ключевые слова, ответы анкеты, наличие контакта, тип лида и т.д.
- **Then:** `convert_to` (candidate / client), `assign_pipeline`, `assign_recruiter` (в т.ч. auto + связка с **`lead_distribution_v1`**).
- **Приоритет** при нескольких матчах: поле `priority` на правиле; в UI — «Multiple matches» со списком и явным **Selected**.
- **Ограничение продукта:** не перегружать — ориентир **3–5 условий** на правило, не десятки.

Логическая схема (не обязательно финальный JSON):

```yaml
rule:
  priority: 1
  if:
    - field: experience_eu_months
      op: ">="
      value: 6
    - field: country
      equals: UA
  then:
    convert_to: candidate
    assign_pipeline: "Driver pipeline"
    assign_recruiter: auto
```

#### UX карточки лида (Assisted)

- Статус лида + блок **Suggested** (например «Convert to Candidate»).
- **Reason:** всегда «почему» (буллеты: совпало по опыту, по документам, …).
- Кнопки **[Accept] [Edit]**; всегда доступен **override** (контроль оператора).

#### Full automatic

На событии лида (создан / нормализован): `evaluate_rules` → при матче: **convert + assign + create_task / next action** (см. единый контур pipeline **§2.3**).

#### Ошибки и fallback

- **Нет матча:** «No rule matched» — лид остаётся, ручная обработка.
- **Неполные данные:** список missing fields + **[Request info]**.

#### Связка с NBA

- Агрегат вроде «⚠ N leads not processed» + **[Process automatically]** (и paywall по плану) — тот же слой, что **§2.3** NBA.

#### Paywall (выровнять с `TenantLicense.plan`)

| Возможность | Ориентир |
|-------------|----------|
| Режим **Automatic** | **Team** |
| **Advanced rules** (мульти-условия / сложная логика) | **Pro** |
| **Bulk** «обработать все» | **Team** |

**SOLO:** manual + простые рекомендации, **без** авто-конверсии.

#### Анти-паттерны

- Длинные правила без объяснения; нет **reason** для оператора; нет **override**.

#### Бэклог (внедрение)

- [x] **Хранение режима обработки лидов (v1):** **`leads_processing_mode_v1`** в **`meta_lead_settings`** + **`GET/PATCH`** **`/settings/leads/settings`** + stamp в **`normalized` при ingest** (см. **§2.3** «Управляемая квалификация»). **Остаётся:** расширить продуктовые отличия **Assisted** vs **Automatic** сверх gating по плану и автосоздания.
- [ ] Движок оценки правил + **priority** + разрешение конфликтов + аудит срабатывания.
- [ ] UI конструктора правил (if/then как фильтры).
- [ ] Карточка лида: Assisted — suggested + reasons + Accept/Edit + override.
- [ ] Automatic: хук на создание/нормализацию лида → convert + assign + next action; fallback и «missing data».
- [x] **NBA — необработанные лиды (v1):** счётчик **`leads_new_unprocessed`** в **`GET /next-actions`**; **`POST /api/v1/leads/bulk/process-new-queue`** — Meta, **`status=new`**, до **50** за вызов, FIFO (**`created_at`** ↑), общий контур с **`POST /leads/{id}/process`** (**`bulk_auto_process_meta_lead_queue`**: аргументы **`statuses`**, **`prefer_oldest_first`**). Gating: **`plan_allows_team_tier_features`**, **`plan_requires_team`**, feature **`leads_bulk_process_new_queue`**. UI: **`bulkProcessNewMetaLeads`** + **`Process batch`** / апгрейд на чипе (**`NbaNextActionsChips`**, **`useNbaQuickBulkFlow`**, Dashboard / Leads / Topbar). **Остаётся:** расширение под **§2.10** rule engine и не-Meta источники.
- [ ] Согласовать с существующим **fit-check** по вакансии (**§2.5**) — одна модель данных критериев или явные слои «вакансия vs глобальные правила тенанта».

### 2.11 Источники лидов → маппинг → поля → pipeline → авто-решения (единая система)

**Цель:** один понятный поток данных и экраны без «скрытой магии».

#### Канонический поток

`Source (Meta / Google / Webhook / Site) → Raw payload → Field mapping → Normalized (system + custom) → Lead → Rule engine (qualification) → Entity (Candidate / Client) → Pipeline + Next actions`

Связка с **§2.10** (режимы Manual/Assisted/Automatic) и **§2.3** (distribution, NBA): правила и поля кормят **один** движок условий.

#### Уровни данных

| Уровень | Назначение |
|---------|------------|
| **System fields** | Фиксированный контракт для логики: type (candidate/client), name, phone, email, country, language, experience, флаги документов, source (`meta` / `google` / …). Задаются **маппингом**, не произвольным вводом в карточке с нарушением схемы. |
| **Custom fields** | Создаёт пользователь: text / number / select / boolean / date; флаги **use in filters** / **use in automation**. Хранение: **JSONB + schema** (целевая модель). |
| **Raw payload** | Полный JSON источника — для отладки, аудита и **пере-маппинга** без потери данных. |

#### Экраны (продукт)

1. **Sources / Integrations** — список источников (Meta, Google, Website form, Webhook), статус connected/active, **View data** / **Edit mapping**.  
2. **View incoming data** — показ **реальных** последних полей сырья (доверие: «что реально пришло»).  
3. **Field mapping** — таблица Source field → System field; DnD или dropdown; автоподсказки по имени/типу; для неизвестных полей — **Create custom field** из того же UI.  
4. **Custom fields manager** — централизованный список полей, edit/delete, типы и флаги.  
5. **Pipeline builder** — стадии, **required actions**, **SLA**, **owner role** (см. также **§2.3** богатая модель стадии).  
6. **Rules / Automation** — IF/THEN с доступностью **всех** system + custom полей; then: convert, pipeline, assign (согласовать с **automation_rules** и **§2.10**).  
7. **Карточка лида** — source + campaign + mapped поля + блок **Suggested** (**§2.10**); опционально вкладка **Raw + Mapped** рядом.

#### UX-принципы

- Всегда возможность увидеть **raw + mapped** (доверие и контроль).  
- **Авто-маппинг** первого прохода (имя поля, тип).  
- **Пере-маппинг** без потери сырья.  
- Минимум свободного текста — выбор из схемы / dropdown.  
- Поля с **типами** (не безтиповый JSON для правил).

#### Монетизация (ориентиры, выровнять с `TenantLicense.plan`)

| Ярус | Что даём |
|------|----------|
| **SOLO** | 1 источник, базовый mapping, лимит custom fields (напр. 10) |
| **TEAM** | несколько источников, полный mapping, без жёсткого лимита полей |
| **SCALE** | сложные правила, трансформации данных в mapping |

#### Анти-паттерны

- Скрытый mapping; нельзя увидеть raw; правила без типизированных полей; только ручной ввод вместо выбора.

#### Состояние в коде (честно)

- **Частично:** Meta (и др.) — **payload** на лиде, **`meta_lead_settings.field_mapping`**, нормализация в **`process_normalized_lead`** / **`normalizer`**. У Meta в UI: **Integrations hub**, вкладки **Incoming** (превью payload) и **Field mapping** (таблица правил) на **`MetaLeadsAdminPage`**.  
- **Нет / слабо:** продуктовый каркас **Google/Webhook** пока без ingest (есть только хаб-карточки и страницы-заглушки **`IntegrationsSourcePlaceholderPage`**); **custom fields для лидов** — схема, синк, фильтр списка, **paywall v0** на количество LEAD-определений на низких планах; **нет** полного rule engine по typed custom; **FunnelsPage** закрывает базовый pipeline builder для лидов и кандидатов (см. бэклог §2.11).

#### Бэклог (внедрение)

- [x] **v0:** каркас **Integrations hub** + у Meta **View incoming** (сырой payload) — см. пункт **§2.3** выше и код **`IntegrationsHubPage`**, **`meta/incoming-preview`**.
- [x] **Meta — Edit field mapping (v1 UI):** вкладка **Field mapping** на **`MetaLeadsAdminPage`** — таблица source / target / format / overwrite; подсказки имён полей из **`incoming-preview`** (datalist); сохранение через **`PATCH /settings/leads/settings`** (`field_mapping`). Сырой JSON в настройках убран в пользу формы (продвинутый JSON при необходимости — через API).
- [x] **Каркас Google/Webhook (v0):** в хабе **`IntegrationsHubPage`** карточки ведут на **`/app/settings/integrations/google`** и **`/webhook`** — страница-заглушка **`IntegrationsSourcePlaceholderPage`** (назад в хаб, бейдж roadmap, ссылка на Meta). Роуты и **`permissions:check`** обновлены. **Остаётся:** реальный ingest, credentials, field mapping / incoming preview для этих источников.
- [x] **Автоподсказки маппинга шире (v1.1):** на **`MetaLeadsAdminPage`** (вкладка **Field mapping**) — source datalist дополняется ключами с объекта **`value`** кроме **`field_data`** (включая один уровень **`parent.child`**), вложенными dot-path из превью **normalized** (глубина ограничена), значениями **`raw_field_names`**; target datalist — пресеты + типовые ключи (**`utm.*`**, Meta ids, **`assignment_lock_v1.*`**) + активные ключи LEAD custom fields + уже введённые targets в таблице.  
- [x] **Paywall (v1) по строкам field_mapping и «слоту» Meta credential:** планы **`solo` / `starter` / `trial` / `free`** — не более **25** правил в **`meta_lead_settings.field_mapping`** и не более **1** записи Meta credential; проверки **`ensure_meta_lead_field_mapping_rows_allowed`** / **`ensure_meta_lead_credential_create_allowed`** в **`plan_feature_gates.py`**, вызов из **`admin_service.update_settings`** / **`create_credential`**; в **`GET/PATCH /settings/leads/settings`** в ответе — **`plan_field_mapping_rules_limit`**, **`plan_meta_credentials_limit`**; UI + i18n на **`MetaLeadsAdminPage`**. **Остаётся:** лимиты при **нескольких реальных источниках** (Google/Webhook ingest), **трансформации** mapping; биллинг/апгрейд-копирайт в продуктовом виде.  
- [x] **Custom fields для лидов (v1):** расширены **`CustomFieldScope.LEAD`** и **`CustomFieldEntityType.LEAD`** (`custom_field.py`); CRUD через существующий **`GET/POST/PATCH /api/v1/custom-fields/definitions`** и values с **`entity_type=lead`**; UI — область **Лид** на **`CustomFieldsPage`**. При ingest **`process_normalized_lead`** синхронизирует значения из **`normalized`** по ключу определения (путь с точками = вложенность) в **`custom_field_values`**; **`LeadOut`** / список лидов отдают **`custom_fields: { key → value }`**. **Фильтр списка (v1):** **`GET /leads?custom_field_key=…&custom_field_value=…`** — точное совпадение со stored **`{"v": …}`** (строка из query); неизвестный ключ → **422**; UI на **`LeadsPage`** при наличии активных LEAD-определений. **Текстовый поиск списка (v1):** **`GET /leads?q=…`** (после trim ≥ **2** символов) — подстрока без учёта регистра по **`normalized` / `payload`**, id, source, stage, status, **`lead_type`**, имени связанной **`Company`** (как **`global_search_v1._search_leads_slice`**); **`count`** с **`outerjoin(Company)`** при активном поиске; UI — поле на **`LeadsPage`**, синхронизация **`?q=`** в URL. **Остаётся:** отдельная колонка **`Lead.extra`**; расширенные операторы фильтра (числа, bool, отдельные поля).  
- [x] **Автоподсказки маппинга + действие «неизвестное поле → создать custom field» (v1):** панель на **`MetaLeadsAdminPage`** (вкладка **Field mapping**), **`createCustomFieldDefinition`** + опциональная строка маппинга.  
- [x] **Rule engine — контекст лидов (v0):** при **`lead.processed`** и **`lead.pipeline.stage_changed`** в контекст автоправил добавляются вложенные **`normalized`** и **`custom_fields`** (`automation_context_for_lead` в **`lead_custom_fields.py`**), условия JSON-правил могут ссылаться по dot-path (**`custom_fields.my_key`**, **`normalized.email`** и т.д.). **Остаётся:** полноценный typed-слой и UI правил поверх **§2.10**.  
- [x] **Карточка лида (v1):** на **`LeadDetailPage`** секция **Source + mapped (custom_fields) + normalized/payload JSON** (раскрывающиеся блоки). **Остаётся:** связка с Assisted (**§2.10**).  
- [x] **Pipeline builder (v1):** **`FunnelsPage`** — вкладки **Кандидаты** / **Лиды**, CRUD воронок и стадий, DnD порядка, модалка стадии с **`stage_contract_v1`** (**owner_role**, **sla_hours**, **required_actions**, **auto_rules** JSON). **Остаётся:** единый «продуктовый» pipeline builder из таблицы §2.11 (связка с источниками / правилами в одном UX).  
- [x] **Paywall (v0):** для планов **`solo` / `starter` / `trial` / `free`** — не более **10** активных (**`is_active`**) несистемных определений **`CustomFieldDefinition`** со scope **LEAD** при **`POST /custom-fields/definitions`** (`ensure_lead_custom_field_definition_create_allowed` в **`plan_feature_gates.py`**, код **`plan_lead_custom_fields_limit`**). Планы Team+ без лимита. **Остаётся:** лимиты при полноценных **доп. источниках** (Google/Webhook), **трансформации** mapping; продуктовый **UI биллинга/апгрейда** (строки field_mapping / Meta credential — **v1**, см. пункт выше).

### 2.12 Воронка конверсии: от лида до найма / сделки (управление, не только отчёт)

**Принцип:** воронка — это **где теряем**, **почему**, **сколько времени теряем**, а не только подписи этапов.

#### Унифицированный «root funnel» (для всех `business_type`)

Любой прикладной pipeline маппится в общие стадии:

| Root | Смысл |
|------|--------|
| **Lead** | вход |
| **Qualified** | прошёл критерии |
| **Active** | в работе |
| **Final** | hired / deal won (и симметрично lost — в метриках потерь) |

**Пример маппинга (агентство):** New→Lead, Contacted→Qualified, Waiting docs / Ready→Active, Hired→Final. Конфиг **per tenant / per funnel** (см. **§2.11** pipeline builder).

#### Метрики по каждому root-этапу

1. **Count**  
2. **Conversion rate** к следующему этапу  
3. **Drop-off** (потери)  
4. **Time in stage** (avg / median)

#### UI основного экрана

Вертикальная / ступенчатая воронка: этап → count → % перехода вниз; сразу видно **узкое место**.

#### Расширение — причины потерь

Клик по этапу / сегменту «lost»: разбивка (**No response**, **No documents**, **Rejected**, …) — коды причин из смены стадии / полей лида / правил.

#### Связка с продуктом (не голая аналитика)

На высокий drop-off, например у **Documents**:

- **Suggest:** automate reminders, send portal link, NBA-группа (**§2.3**) — «Contact N leads», «Request docs» и т.д.

Цепочка: **`Pipeline → Mapping → Funnel → Metrics → Insights → Actions`**.

#### Разрезы (срезы)

- по **источнику** (Meta vs Google vs …)  
- по **рекрутеру / владельцу**  
- по **pipeline / проекту / вакансии**

#### Временные KPI

**Time to:** contact, qualify, close; пороги (напр. avg time to contact **> 24h** → алерт / инсайт).

#### Связка с NBA

Сигнал воронки («drop at Contact») → карточка NBA: **Contact N leads (overdue)** с bulk-действием.

#### Авто-инсайты (без обязательного LLM)

Детерминированные правила: «conversion −15% vs прошлая неделя», «причина: slower response time» — ощущение «умной» системы на фактах.

#### MVP vs позже

**MVP:** этапы root funnel + count + conversion (+ базовое время в стадии при наличии данных).  
**Не в первой итерации:** тяжёлый BI, сложные мультимерные графики.

#### Монетизация (ориентир)

| Ярус | Что даём |
|------|----------|
| **SOLO** | базовая воронка (агрегаты без глубоких срезов) |
| **TEAM** | срезы source / команда / pipeline |
| **SCALE** | причины потерь, инсайты, прогнозы (когда будут данные) |

Конкретные имена планов в продукте/биллинге (**Solo / Team / Business / Enterprise**) и числовые лимиты — **§2.16**; ярусы воронки в таблице выше сопоставить с этими планами при внедрении.

#### Анти-паттерны

- Только диаграмма без действий; без времени; без причин потерь; воронка не связана с NBA / автоматизацией.

#### Состояние в коде (честно)

- **Частично:** **`GET /api/v1/analytics/stage-metrics`**, блок **Stage metrics** на **Overview** (`Dashboard.tsx` — stage time, transitions, readiness).  
- **Частично (лиды, v0):** **`GET /api/v1/leads/conversion-funnel`** — снимок по фиксированному win-path CRM (**`new → contacted → qualified → converted`**), отдельно **`lost`** (processed) и **`status=new`**; доли **`progressed_share`** между соседними шагами (от **`at_or_beyond`**); **dwell (v0.1):** среднее/медиана дней в текущей CRM-стадии по последнему **`ActivityLog`** **`lead.stage_changed`** с **`payload.to_stage`**, иначе **`Lead.created_at`**; UI на **`LeadsPage`** под **stage health**.  
- **Нет:** **`funnel_stage_mapping`**, явного **root funnel** cross-pipeline, продуктовых **Suggested actions** с воронки в NBA; **частично:** срезы TEAM+ на **`conversion-funnel`**; **v0 drill-down потерь:** **`lost_from_stage`** (уникальные лиды по **`from_stage`** при **`→ lost`**) и **`lost_reason_breakdown`** (уникальные по **`lost_reason_code`** в **`lead.stage_changed`**, иначе **`unknown`**); UI на **`LeadsPage`**. **`PATCH /leads/{id}`** с **`stage=lost`**: **`lost_reason_code`** / **`lost_reason_note`**; **`normalized.lead_lost_reason_v1`**; модалка причины в инбоксе и на **`LeadDetailPage`**; в инбоксе и на детали — read-only блок **`lead_lost_reason_v1`**. **`PATCH /leads/bulk`** при **`stage=lost`**: те же поля причины + запись **`normalized`** / аудит по каждому лиду со сменой стадии; модалка в массовой панели списка.

#### Бэклог (внедрение)

- [ ] Модель данных: **`funnel_stage_mapping`** (pipeline stage code → root: lead|qualified|active|final|lost_reason).  
- [x] **API агрегатов воронки (v0, лиды):** **`GET /leads/conversion-funnel`** — counts, **`at_or_beyond`**, **`progressed_share`**, **dwell**, **`lost_from_stage`**, **`lost_reason_breakdown`**. **Дальше:** cohort-based conversion, единый экран с кандидатами.  
- [ ] Отдельный экран **«Conversion funnel»** + drill-down причин (**SCALE** / Pro); **частично:** MVP-виджет на **`LeadsPage`** (**§2.12** v0).  
- [x] **Срезы TEAM+ (v0, лиды):** query **`source`**, **`vacancy_id`**, **`funnel_id`**, **`assignee_user_id`** (recruiter связанного кандидата) на **`GET /leads/conversion-funnel`**; **403** `plan_requires_team` / **`leads_conversion_funnel_slices`**; эхо в ответе **`filter_*`**; UI на **`LeadsPage`**. **Дальше:** срез по **`pipeline_id`** в смысле кандидатского pipeline (если отделим от **`funnel_id`** лида), paywall-копирайт в биллинге, согласованность с глобальным «экраном конверсии».  
- [ ] Пороги времени + инсайты + мост в **NBA** (**§2.3**).  
- [ ] Paywall по сложности срезов и инсайтов.

### 2.13 Меню и IA: сценарии для оператора (не архитектура продукта)

**Принцип:** в левом меню — **что пользователь делает**, а не перечень сущностей как в схеме БД. Разделение: **состояния системы** (SLA, без next action, барьеры, риски) ≠ **пункты навигации** — они живут на **Dashboard / NBA / виджетах**, не как отдельные top-level ссылки.

#### Целевая структура первичного меню (6–7 пунктов)

| # | Раздел | Содержание (сценарий) |
|---|--------|------------------------|
| **1** | **Dashboard** | Обзор + **NBA** + операционные риски + виджеты (в т.ч. агрегаты SLA, «без следующего шага», барьеры — как **состояния**, не как меню) |
| **2** | **Inbox** | Единый центр входящего: сообщения, почта, хаб коммуникаций (**§2.7** / текущий **`/app/inbox`**) |
| **3** | **Work** | Основная работа с процессом: кандидаты, клиенты, лиды, вакансии, заказы, процессинг — **вкладки или подраздел**, не обязательно 6 отдельных top-level пунктов |
| **4** | **Tasks** | Исполнение: задачи + календарь |
| **5** | **Finance** | Опционально по сегменту: счета, доп. услуги (**services** tenant и т.д.) |
| **6** | **Analytics** | Воронка (**§2.12**), метрики, источники |
| **7** | **Settings** | Всё админское: пользователи, роли, воронки, документы, интеграции, коммуникации, биллинг, юридическое — **внутри** сгруппировано (Company, Team & Roles, Pipelines, Documents, Integrations, Communication, Billing, Advanced). Подписка, usage, team, workspace, роли — **§2.17**. |

Детальный layout и логика **Work** и **Dashboard** (проблемы → действия → результат, NBA, paywall) — **§2.14**. **Billing & Subscription, Team, Companies, Platform Admin** — **§2.17**.

#### Что убрать из левого меню как отдельные пункты

- **SLA**, **без следующего действия**, **барьеры**, **риски** — только как входы с Dashboard / deep links / NBA, не как соседи «Кандидаты» в списке модулей.

#### Вложенность и вторичный уровень

- **Work:** например вкладки Pipeline (default) · Candidates · Clients · Leads · Vacancies — один контекст «работа», переключение без смены ментальной модели «я в другом приложении».  
- **Внутри сущности** (карточка кандидата): документы, сообщения, задачи — **рейл / вкладки**, не глобальные разделы.

#### Динамическое меню

- **SOLO:** скрыть **Finance**, упростить блоки team;  
- **Services / employer / agency:** включать **Finance**, **Orders/Services** в **Work** или **Finance** по продуктовому решению;  
- Увязать с **`business_type`**, **`TenantLicense`**, флагами модулей.

#### Анти-паттерны

- Меню = «всё, что умеет система»; нет связи с **«что делать сейчас»** (это Dashboard + NBA).

#### Состояние в коде (честно)

- **Частично:** левое меню (**`components/nav/Sidebar.tsx`**) — секции **Dashboard** / **Inbox** / **Tasks** / **Analytics** / **Work** / при выполнении условий — **Finance** (заказы / услуги / счета) / **System** + свёрнутый **Settings**; **Finance** выносится отдельным заголовком, если план лицензии **team** или **pro** (по **`GET /settings/team`**), либо если **`business_type === services`** (в т.ч. starter); для **starter** agency/employer те же пункты остаются в одном блоке **Work**; если обзор команды недоступен роли — поведение как раньше (один блок **Work**). Хаб **`/app/analytics`** (**`AnalyticsHubPage`**: дашборд, **Work hub**, лиды, при правах — **no-next-action** (кандидаты), **SLA incidents** (коммуникации), **lead distribution**; TTV — админ; пути **`crmAppPaths`**); хаб **`/app/work`** (**`WorkHubPage`**: карточки **без next action** и **SLA incidents** при правах — см. **`crmAppPaths`**); **контекстные вкладки Work** (**`WorkContextTabs.tsx`**, ссылки на модули через **`opsDrilldownPaths`**) под topbar на тех же маршрутах и на **`/app/work`**; логика отделения **Finance** совпадает с сайдбаром (**`nav/financeNavVisibility.ts`**, план из **`GET /settings/team`** + **`business_type`**): при split — вертикальный разделитель и блок заказов / услуг / счетов; порядок: **документы → лиды → Finance** (канонические URL сохранены); один запрос **`getTeamOverview`** на сессию оболочки через **`contexts/TeamOverviewNavContext.tsx`** (сайдбар + вкладки + хаб **`WorkHubPage`**); на **`/app/work`** при split — подзаголовки **Core** / **Finance** и карточка **Счета**; первый пункт в сайдбар-блоке **Work**; **leads distribution** в блоке лидов; отдельные пункты **no-next-action** (кандидаты) и **SLA incidents** в сайдбаре **не показываются** (**`Sidebar.tsx`**, `SIDEBAR_HIDDEN_ITEM_KEYS`) — те же URL и навигационные записи остаются для deep links и скриптов. **Остаётся:** перенос SLA-only пунктов в Dashboard/NBA; донастройка правил по **`TenantModuleSettings`** и edge-кейсам плана. **Частично по вложенности Work:** **`WorkAreaLayout`** + **`<Outlet />`** в **`App.tsx`**; index = хаб; опциональные алиасы **`/app/work/{candidates|clients|…|sla-incidents}/…`** → канонический **`/app/…`** (**`WorkPathAliasRedirect`**, allowlist **`nav/workShellAlias.ts`**); дашборд-дом в реестре **`opsDrilldownPaths.dashboardOverview`** (= **`ACTIVATION_PATHS.overview`**).

#### Бэклог (внедрение)

- [ ] Продуктовый макет нового дерева + миграция **`NAV_ITEMS`** / **`Sidebar`** без потери deep links и прав.  
- [ ] Перенос SLA / no-next-action / risk в **Dashboard** + NBA (**§2.3**) и в **колонки Work** (**§2.14**), удаление дублей из primary nav. — **частично:** из сайдбара убраны **`candidates-no-next-action`** и **`sla-incidents`** (маршруты и **`NAV_ITEMS`** сохранены; входы — дашборд, Inbox, уведомления в topbar).  
- [ ] **Work**-оболочка: табы или hub для Candidates / Clients / Leads / Vacancies / Orders.  
- [ ] **Settings**: единая группировка подпунктов (Company, Team, Pipelines, …); экраны **§2.17** (Billing & usage, upgrade, add-ons, team invite, roles, workspaces).  
- [ ] ~~Правила **динамического** показа **Finance**~~ — **частично:** отдельная секция **Finance** в сайдбаре по плану + **`business_type`**; team-разделы (solo / **`team-availability`** и т.д.) — по-прежнему в бэклоге.  
- [ ] i18n ключей новых ярлыков разделов.

### 2.14 Work и Dashboard: одна модель — проблемы → действия → результат

**Общая логика:** **Dashboard** показывает **проблемы** и толкает к **действию / апгрейду**; **Work** даёт **инструменты решить** в контексте процесса. Пользователь: зашёл → увидел проблемы → нажал → решил — **без изучения «архитектуры» продукта**.

---

#### Work (ядро операций)

**Цели**

- Мгновенно понять, **что происходит сейчас** в потоке.
- Выполнять действия **без лишних переходов** (карточка — не единственный путь).
- Видеть **узкие места прямо в колонках** процесса, а не на отдельных экранах.

**Layout (минимальный каркас)**

1. **Верх:** фильтры + quick controls.  
2. **Переключатель вида:** **Pipeline** (по умолчанию) · **Table** (массовые операции).  
3. **Основная зона:** pipeline-колонки **или** таблица.  
4. **Правый рейл (контекст):** выбранная сущность — текущее состояние, недостающее, **next action**, кнопки (без перегруза).

**Пример колонок (смысл, не только счётчики)**

- Не только `Docs (6)`, а **`Docs (6)`** + **`⚠ 2 stuck`** / **`⚠ 3 need action`** — это **заменяет** отдельные разделы «риски / SLA / проблемы» в навигации: состояние **встроено в процесс**.

**Inline-действия (без открытия полной карточки)**

- На строке/карточке в колонке: например **`⚠ No next action`** → **`[ Assign next step ]`**, **`[ Contact ]`** и т.д.

**Правый рейл**

- Только **текущее состояние + действия** (стадия, missing docs/barriers, next action, primary CTA — e.g. Send request, Assign).

**Убрать как отдельные экраны**

- ❌ «Без следующего действия», «SLA», «Риски» как самостоятельные страницы — всё **в pipeline / таблице / рейле** и на Dashboard (**NBA / Problems**).

**Связка с автоматизацией и монетизацией**

- В заголовке колонки или агрегате: **`⚠ 3 candidates need action`** + **`[ Fix automatically ]`** — кнопка = **апселл** (см. ниже paywall).

**Массовые действия (обязательно)**

- После multi-select: **`[ Contact all ]`**, **`[ Request docs ]`**, **`[ Assign automatically ]`** — ощущение «система ускоряет», не только по одному.

---

#### Dashboard (продаёт ценность и апгрейд)

**Цель:** не «показать данные», а **заставить действовать** и **апгрейдиться**. Минимум «аналитической свалки».

**Верх экрана — NBA (Next Best Actions)**

- Блок в духе: **🔥 Next best actions** — список карточек с **одной главной кнопкой** на действие (Contact all, Auto-assign, Send request и т.д.).  
- Агрессивный главный CTA-уровень: например **«Fix your process in 1 click»** + **`[ Fix all automatically ]`** — **главный paywall-якорь** (не страница Pricing).

**Встроенный апселл по плану**

- **SOLO:** текст уровня *You have N issues* → **Upgrade to:** auto-fix, auto-assign, reminders → **`🔒 Upgrade required`** на заблокированных действиях.  
- **TEAM+:** те же действия доступны или частично; границы по **`TenantLicense`** / продуктовым флагам.

**Минимальный набор блоков (не раздувать)**

1. **Next actions** (NBA).  
2. **Problems** — краткая сводка: без next action, stuck > N ч, unassigned и т.п.  
3. **Funnel** — компактно (например `100 → 60 → 30 → 12`), связка с **§2.12**.  
4. **Insights** — 1–2 детерминированных инсайта (conversion dropped, reason: slow response).

**Анти-паттерны Dashboard**

- ❌ Десяток графиков и полноэкранные таблицы — это не целевой **entry screen**.

---

#### Связка Dashboard ↔ Work

- Клик по NBA / проблеме (например **Contact 5 candidates**) → открывает **Work** с **уже применённым фильтром** (тот же контекст: overdue, стадия, тип сущности).

**Частично в коде:** на **`/app/overview`** после онбординга — **NBA** (**`components/nba/DashboardNbaSection.tsx`**, **`GET /next-actions`**, **`NbaNextActionsChips`**, playbook по первому лиду; при пустых очередях — блок «всё чисто», при сбое загрузки — сообщение + **Refresh**) и карточка **Meta auto-fix** (**`components/dashboard/DashboardLeadAutoFixCard.tsx`**) при очереди **needs_routing / failed** (по **`leads.view`**; ссылка «открыть список» через **`CRM_APP_DRILLDOWN_HREFS.leadsNeedsRouting`**); затем полоса быстрых ссылок на **`/app/work`** и **`/app/analytics`** (в реестре **`workHub`** / **`analyticsHub`**; карточка «Дашборд» на **`/app/analytics`** — **`dashboardOverview`** = **`ACTIVATION_PATHS.overview`**; по тем же правам, что и видимость хабов в навигации); хаб **`/app/analytics`** содержит карточку **Work hub** (симметрия с дашбордом). Операционные виджеты дашборда ведут в лиды с **`status` / `next_action`**, кандидатов без next action — **`/app/candidates?queue=no_next_action`** (редирект на страницу очереди; в реестре **`candidatesNoNextAction`**, канонический query — **`CANDIDATES_QUICK_VIEW_NAV_PATHS`**), **задачи** — **`/app/tasks`** с **`tab`**, **`t_due_bucket=overdue`**, **`t_entity=lead`** и др. (**`RemindersPage`**; legacy **`type=leads_no_next_action`** читается и вычищается из URL), счета с **`queue=overdue_unpaid`** при просрочке, открытые заказы — **`/app/orders?status=open`**, вакансии **`?status=open`** (**`VacancyList`**). **Канон** URL и drilldown — **`hostflow-frontend/src/app/crmAppPaths.ts`** (**§1.6**): **`CRM_APP_PATHS`**, **`CRM_APP_DRILLDOWN_HREFS`**; quick-view очереди кандидатов — **`CANDIDATES_QUICK_VIEW_NAV_PATHS`** (**`modules/candidates/constants.ts`**). Эти же значения используются в Work shell (**`WorkHubPage`**, **`WorkContextTabs`**, **`CandidatesListGate`**, **`agencyClients`** / **`clientsDirectory`**, **`invoiceNew`**, редирект заказов → **`services`**) и в ссылках дашборда / сущностей.

---

#### Где рождается апгрейд

- Не в первую очередь в **Pricing**.  
- В потоке: **`[ Fix automatically ]` / `[ Assign automatically ]`** → **`🔒 Upgrade required`** + короткое объяснение ценности.

---

#### Жёсткий вывод

- **Work:** процесс + действия, минимум экранов, максимум контекста в колонках и рейле.  
- **Dashboard:** проблемы + решения, агрессивный CTA, встроенный апселл; система **ведёт** пользователя.

#### Бэклог (внедрение)

- [ ] **Work:** единый shell с Pipeline/Table toggle; колоночные **health-бейджи** (need action, stuck, SLA) из одной модели с NBA.  
- [ ] **Work:** inline primary actions на элементах списка/kanban; правый контекст-рейл без дублирования полной карточки.  
- [ ] **Work:** bulk toolbar + действия согласованы с NBA / автоматизацией (**§2.3**, **§2.10**).  
- [ ] **Dashboard:** сверху NBA + главный CTA «fix in one click» — **частично:** **`DashboardNbaSection`** + **`DashboardLeadAutoFixCard`** на **`/app/overview`** (до хабов и операционной сетки); блоки Problems / Funnel / Insights без перегруза.  
- [ ] **Deep link:** query/state из Dashboard → Work (фильтр, выбор pipeline) — **частично:** лиды / счета / кандидаты (**`queue=no_next_action`**) / заказы (**`status=open`**) / задачи (**`t_*`** на **`/app/tasks`**). Остаётся: встроить очередь no-next-action кандидатов в основной список без отдельного экрана (если продуктово решим).  
- [ ] **Paywall:** единые точки для auto-fix / auto-assign на Dashboard и в колонках Work; копирайт SOLO vs TEAM.

### 2.15 Client Portal: операционный интерфейс клиента (не «доступ к CRM»)

**Цель продукта:** портал — не «посмотреть кандидатов из базы», а чтобы клиент **понял статус**, **принял решение** и **не задавал лишних вопросов** агентству. За это платят и это удерживает.

#### Главный принцип: Transparency + Action + Control

Клиент должен: **(1)** видеть, что происходит; **(2)** понимать, что от него требуется; **(3)** **действовать прямо в портале** (accept / reject / запрос уточнения и т.д.).

#### Главный экран (то, что клиент открывает первым)

- Заголовок уровня **Hiring status** / статус найма: агрегаты в духе *Active candidates*, *Ready for review*, *Waiting for decision* — **коротко**, без таблицы «как в CRM».  
- Блок **⚠ Action required**: например *N candidates need your decision* + **`[ Review now ]`**.  
- **Recent activity** — лента событий (добавлены, перешли на этап и т.п.), не полноэкранная таблица.

**Анти-паттерн:** первый экран = таблица всех полей или копия внутреннего pipeline.

#### Список кандидатов (упрощённый)

- Карточки/строки: имя, **понятный клиенту статус**, индикатор документов (**✔ complete** / **⚠ Missing:** перечень только нужного).  
- Первичные кнопки: **`[ View ]` `[ Accept ]` `[ Reject ]`** (или эквиваленты по продукту) — **только нужное**, без лишних полей.

#### Карточка кандидата (ключевой экран)

- Одна страница: имя, статус для клиента, чеклист документов/условий, **recruiter notes** (разрешённые к показу).  
- CTA: **`[ Accept candidate ]` `[ Reject ]` `[ Request clarification ]`** — **без обязательных переходов** на другие экраны для главного сценария.

#### Handoff (ключевая фича)

- После передачи клиенту явный блок: **Shared with you by {Agency}** + *N candidates awaiting your decision*.  
- Клиент понимает **зону своей ответственности** (это не «наблюдение за базой», а **его очередь решений**).

#### Коммуникация внутри портала

- В карточке: **Chat with recruiter** (или аналог) — поток в продукте, **не** замена на email/WhatsApp как основной канал для статуса по кандидату.

#### Уведомления (вне портала → обратно в портал)

- Каналы: email, **Telegram / WhatsApp** (по roadmap и интеграциям).  
- Смысл пуша: *You have N candidates waiting* + **`[ Open portal ]`** — доводят до **действия внутри** портала.

#### Ключевые UX-решения

1. **Без CRM-сложности:** не показывать клиенту **внутренний pipeline**, **внутренние коды стадий**, инструменты рекрутера.  
2. **Только релевантное:** статус (клиентский), документы/барьеры, действия.  
3. **Action-first:** на каждом экране с проблемой или решением — **явная кнопка**.

#### Ограниченный доступ (обязательно)

Клиент **не** видит: других клиентов, чужие сделки, **внутренние** заметки (если помечены как internal), «всю базу». Только **свой** контекст (scoped share / assignment).

#### Монетизация (ориентир)

| Уровень | Смысл |
|--------|--------|
| **Портал как платная фича** | Например: *Share candidates with clients* → **`🔒 Available in Team plan`** |
| **Advanced portal** | Брендированный портал, кастомные **клиентские** статусы, client-facing аналитика (позже) |
| **Per-client** | Включённые слоты и цена за доп. клиента — **§2.16** «Порталы» (**Team €7** / **Business €5** за доп. аккаунт; сверить с паками overage в той же секции) |

Согласовать с **§2.2** (paywall онбординга), **§2.16** (тарифы) и точками апселла **§2.14** (CTA в потоке, не только Pricing).

#### Конкурентное позиционирование

- Рынок по умолчанию: Excel, мессенджеры, хаос.  
- Продукт: **clear process, clear status, clear actions** → меньше вопросов, задержек и ошибок.

#### Связка с системой: Portal ↔ Pipeline ↔ NBA

- Поток: стадия / событие в **pipeline** (кандидат готов к клиенту) → появляется в **портале** → клиент **не реагирует** → у рекрутера в **NBA** (**§2.3**, **§2.14**): например **⚠ N candidates waiting client decision** + **`[ Remind client ]`**.

#### Ошибки, которых нельзя допустить

- ❌ Второй полноценный **CRM** для клиента.  
- ❌ Перегруз данными и полями.  
- ❌ Слишком широкий доступ.  
- ❌ Экраны без **действий** (только «посмотреть»).

#### Итоговая модель

**Pipeline → Handoff → Portal → Decision → обратно в систему** (статус, события, следующие задачи у агентства).

**Эффект:** клиент реже пишет «а где мы?» — **принимает решения в системе**.

#### Бэклог (внедрение)

- [ ] Клиентский **home**: статус + action required + activity (без CRM-таблицы как default).  
- [ ] Упрощённый список + карточка кандидата с CTA Accept / Reject / Request clarification.  
- [ ] Модель **handoff** (копирайт + данные: кто передал, сколько ждёт решения).  
- [ ] Встроенный **чат** рекрутер ↔ клиент по сущности (или интеграция с единым Comms — **§2.7**).  
- [ ] Уведомления + deep link **Open portal**; синхронизация с NBA **Remind client**.  
- [ ] RBAC / scope: только shared; скрытие internal notes.  
- [ ] Тарифы: флаг **Team+** для portal share; опционально branded / per-client billing — см. **§2.16**.

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
- До **1** pipeline, **1** source mapping, **1** интеграции типа lead source, **1** формы.  
- До **1** email channel, **1** Telegram, **1** WhatsApp.  
- До **100** исходящих уведомлений / мес из **разрешённых** на Solo автоматизированных сервисных событий (если такие вообще доступны на плане).

**Логика апселла:** Solo **рабочий**, но с **потолком** — упирается при: invite, второй компании, портале, auto-distribution, второй воронке, доп. источниках, счетах/услугах.

---

#### Team

| | |
|--|--|
| **Цена** | **€129**/мес (monthly) · **€109**/мес при годовой оплате |
| **Аудитория** | Агентства, работодатель + рекрутер/координатор, малые команды, бизнес, которому нужен **процесс**, не таблица |

**Включено (core+):** до **3** пользователей, **1** workspace, до **3** пресетов обработки / pipeline presets, **неограниченные базовые воронки** в рамках одного workspace (в пределах лимитов ниже), кандидаты / клиенты / лиды / вакансии / заказы, Work, Dashboard с **NBA**, Inbox / messages / email center, задачи, календарь, документы, ручная + assisted обработка лидов, **автообработка** по правилам, **auto-distribution**, SLA tracking, next action engine, **automation rules**, **candidate portal**, **client portal**, **3** клиентских доступа в портал, **300** активных candidate portal sessions / мес (или иная единица — **§2.16** «Порталы»), базовый handoff клиенту, базовая аналитика воронки / источников / команды, базовые уведомления, field mapping входящих лидов, кастомные поля в фильтрах и правилах, базовая история изменений, **3** формы лидов, **3** интеграции lead sources.

**Не включено:** advanced finance analytics, полный модуль услуг с инвойсингом, расширенный branded portal, white-label, расширенные аудиты, cross-workspace orchestration, кастомные SLA matrix, сложные versioned rulesets, enterprise support / SLA guarantees.

**Лимиты (ориентир):**

- До **1 500** новых лидов / мес.  
- До **2 000** активных сущностей.  
- До **50 GB** файлов.  
- До **50** кастомных полей.  
- До **10** automation rules.  
- До **3** lead forms, **3** источников рекламы/лидов, **3** client portal clients.  
- **3** seats включено.  
- До **3** email channels.  
- Telegram/WhatsApp: до **3** connections **суммарно** или **по типу** — **зафиксировать в оферте** (одно из правил).  
- До **1 000** автоматических системных уведомлений / мес.  
- До **5** pipeline templates.  
- **10** стадий на воронку в базовой конфигурации **или** без лимита на стадии, но с лимитом на число pipelines — **выбрать в политике продукта**.

**Смысл плана:** HF становится **системой управления процессом**, а не хранилищем.

---

#### Business

| | |
|--|--|
| **Цена** | **€249**/мес (monthly) · **€219**/мес при годовой оплате |
| **Аудитория** | Несколько пользователей и **несколько** workspace/брендов, активные порталы, услуги, счета, нагрузка, бизнес-аналитика |

**Включено:** всё из **Team** + до **10** пользователей, до **3** компаний / workspaces, полноценная работа с несколькими профилями бизнеса, расширенные client/candidate portal, **branded portal basic**, handoff с историей и статусами решений, модуль **услуг/сервисов**, заказы, привязка услуг к сущностям, **счета/фактуры**, банковские и юридические реквизиты, финучёт по услугам, базовая аналитика продаж / услуг / клиентов / причин остановок, расширенная воронка, срезы по источнику / менеджеру / компании / pipeline, team management, рабочие часы, отпуска/больничные/перерывы, подтверждение запросов руководителем, распределение по доступности/нагрузке/языку, расширенные правила распределения и workflow, доп. формы и источники, приоритетная поддержка.

**Лимиты (ориентир):** до **5 000** лидов / мес, **10 000** активных сущностей, **200 GB** файлов, **200** кастомных полей, **50** automation rules, **20** lead forms, **10** источников, **25** client portal-аккаунтов, **10** seats включено, **10** communication channels, **10 000** системных уведомлений / мес, до **20** pipelines. **Branded portal basic:** на **1** бренд/workspace **или** на каждый workspace — **выбрать в политике**.

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

**Принцип:** порталы нельзя воспринимать как «бесплатное приложение к CRM» — только через **планы + лимиты + оверейдж/апгрейд** (**§2.15**).

**Candidate portal**

| План | Включено |
|------|----------|
| **Team** | Базово с лимитом: до **300** портальных взаимодействий / мес **или** до **300** кандидатов с portal access / мес — **выбрать одну единицу учёта в оферте** |
| **Business** | До **2 000** активных портальных взаимодействий / мес (в той же метрике, что и Team) |

**Overage (candidate portal):** +500 interactions = **€15** **или** +500 active portal-enabled кандидатов = **€20** — задать **одну** метрику, не обе параллельно.  
**Рекомендация:** считать по **активным portal-enabled кандидатам** за расчётный период, **а не по кликам**.

**Client portal**

| План | Включено |
|------|----------|
| **Team** | До **3** активных клиентских portal-аккаунтов |
| **Business** | До **25** активных клиентских portal-аккаунтов |

**Доп. клиентский портал:** **Team +€7**/мес · **Business +€5**/мес за каждый активный доп. аккаунт.

**Брендированный портал:** **basic** — в **Business** (как в базовом плане); **full branded:** **+€49**/мес за workspace **или** только **Enterprise** — зафиксировать в политике.

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

**Рекомендация:** по умолчанию **A**; **B** — если сознательно поднимаем ARPU Team.

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

**Рекомендация:** **7 дней**, функционал уровня **Team или Business**, но **не** безлимит.

**Trial даёт:** **1** workspace, до **2** test seats, ограниченный test volume, demo/seeded data; **порталы, автоматизации, auto-distribution** — можно попробовать.

**Лимиты trial (ориентир):** до **50** тестовых лидов, **20** conversion actions, **2** portal test shares, **5** automation executions — **или** мягче, но с ограничением real sending.

**После trial:** выбор плана **или** read-only/restricted **или** хранение данных **X** дней — зафиксировать.

**Оферта:** trial **один раз** на выбранный критерий (пользователь / организация / домен / телефон / billing entity); HF может блокировать повторные trials; по окончании — ограничение функционала.

**Технический поток (Stripe, баннеры, read-only):** **§2.18**.

#### Overages / превышения

Режимы: **hard block** · **soft + upgrade** · **automatic overage billing** (только при **явном согласии** на автосписание).

| План | Рекомендация |
|------|----------------|
| **Solo** | **Hard block** / **forced upgrade** |
| **Team / Business** | Warning **~80%**, **100%** → upgrade **или** paid overage pack |

**Примеры паков:** +500 leads/mes **€15** · +2 000 active records **€20** · +50 GB **€10** · +10 automation rules **€15** · +5 client portal accounts **€20** (согласовать с per-client **€7/€5** — **одна** модель: пакеты vs per unit).

**Оферта:** без согласия на overage **не** включать неожиданные автосписания.

#### Архивация и активные сущности

В условиях разделить **active** и **archived**. **Рекомендация:** архив **вне** лимита активных; хранение в разумных пределах; удаление по **retention** при отмене плана / закрытии / превышении хранения. Описать: что такое **active record**, когда **archived**, срок данных после **cancellation**.

#### Upgrade / downgrade / cancellation

- **Upgrade:** сразу, оплата **пропорционально**.  
- **Downgrade:** со **следующего** billing cycle.

**После downgrade при превышении лимитов:** read-only, запрет новых сущностей, ограничение users/companies/rules/portals — **явно в оферте**.

#### Founder pricing

Первые **20–50** клиентов: **Team €99**/мес (вместо **€129**), **Business €199**/мес (вместо **€249**); только новые; скидка держится, пока подписка активна и перерыв не дольше **X** дней.

#### Сегменты: Agency / Employer / Services

**Одна** матрица цен; различаются **preset + exposure модулей** в UI, не три прайс-листа.

- **Agency:** кандидаты, client portal, handoff, вакансии, recruitment analytics.  
- **Employer:** кандидаты, teamwork, hiring funnel, SLA, internal processing.  
- **Services:** клиенты, услуги, заказы, invoices, sales analytics.

См. **`business_type`**, **§2.13**.

#### Меню по планам (связь с §2.13)

| План | Dashboard | Inbox | Work | Tasks | Finance | Analytics | Settings |
|------|-----------|-------|------|-------|---------|-----------|----------|
| **Solo** | basic | basic | leads, candidates, clients, **1** pipeline, без advanced automation | да | **нет** | basic | limited |
| **Team** | full operational | full | full core, automation, auto-distribution, portals basic | full | optional / нет (зависит от стратегии финансов) | operational | full team-level |
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
| Services / invoices | нет | только add-on **B** или нет | да | custom |

#### Дополнительные опции (единый реестр)

Extra user Team **€18** / Business **€15** · extra workspace Team **€25** / Business **€20** · extra source **€10** · +5 forms **€10** · +10 rules **€15** (+25 **€30**) · +50 GB **€10** · +5 client portal accounts **€20** (сверить с **€7/€5** per client) · branded portal **+€49**/workspace · finance add-on Team **+€49** · advanced analytics **+€39** (опционально).

#### Пользовательское соглашение — обязательный чеклист

**Определения:** аккаунт, пользователь, seat, workspace/company, active/archived record, source, communication channel, automation rule, portal account, portal interaction (если используется), form, storage, billing cycle.

**Биллинг:** периодичность, авто-продление, налоги/VAT, неуспешный платёж, заморозка.

**Лимиты и превышения:** поведение на лимите, overage, soft/hard, согласие на автосписание.

**Trial / downgrade / cancellation:** см. подразделы выше; данные после отмены.

**Third-party:** нет ответственности за стабильность внешних API; провайдеры могут менять контракты.

**Mapping / custom fields:** ответственность пользователя за настройки; HF не гарантирует корректность авто-логики при ошибочных правилах.

**Automation disclaimer:** исполнение по правилам пользователя; пользователь валидирует правила; HF не отвечает за последствия неверной настройки (**критично для юридической защиты**).

#### Запуск v1 pricing

Не усложнять: **Solo / Team / Business / Enterprise** + **extra users, workspaces, sources, branded portal** и при необходимости **finance add-on** для Team — достаточно для цены, договора и роста без демпинга.

#### Стратегия (итог в одном блоке)

**Дёшево:** Solo. **Дорого:** команда, multi-company, **порталы**, **автоматизация**, **финансы**, многоканальные коммуникации. **Не бесплатно:** auto-distribution, client portal, automation engine, multi-company, полноценный team management.

**HF** продаётся как **план + seats + workspaces + modules + usage**; **Terms** строятся на чётких определениях единиц и лимитов.

---

#### Связь с продуктом (NBA, портал, автоматизация)

- Paywall и CTA в приложении (**§2.14**) и **§2.15** (портал) должны ссылаться на **конкретные** строки этой таблицы (план + лимит).  
- Кодовые флаги (**`TenantLicense`**, `business_type`, module flags) — маппинг на **Plan + Modules + Limits** (**бэклог внедрения**).

#### Договор и биллинг (сводка)

Полный чеклист — подраздел **«Пользовательское соглашение — обязательный чеклист»** и блоки **Trial**, **Overages**, **Upgrade/downgrade**, **Архивация** выше. Дополнительно в оферте: **неоплата**, **grace period**, соответствие заявленных модулей UI/API.

#### Состояние в коде (лицензии и платформа)

- **`TenantLicense`** — **`backend/app/models/tenant.py`**; чтение лимитов — **`tenant_limits`**, **`profile_limits`**.  
- После успешной оплаты Stripe webhook **`billing._apply_license_limits`** подставляет лимиты из **`PLAN_LICENSE_LIMITS`** (черновик под планы, **не** полная матрица add-ons **§2.16**).  
- **Platform API:** **`backend/app/api/v1/platform/tenants.py`** — список тенантов, suspend, **PATCH …/license**, impersonate, модули.  
- **Superadmin UI:** **`hostflow-frontend/src/pages/admin/TenantsPage.tsx`** + **`src/api/tenants.ts`** (в приложении под ролью `superadmin`, **`routes.tsx`** `superadminOnly`) — не отдельный host из спеки **§2.17**.

#### Бэклог (внедрение)

- [ ] Расширить **Plan + аддоны** в Stripe и на **`TenantLicense`** поверх текущего **`_apply_license_limits`** и ручного **PATCH license** в Platform (workspace, seat, portal packs, metered — по **§2.16**).  
- [ ] Enforcement лимитов (лиды/мес, активные сущности, файлы, правила, формы, каналы, candidate portal metric, client portal accounts) на API и в UI.  
- [ ] Страница планов и **in-app** апселлы с ценами из **§2.16**.  
- [ ] Юридические шаблоны по чеклисту §2.16: trial, downgrade, overage (**согласие на автосписание**), retention, automation/mapping disclaimers.  
- [ ] Решения по политике: Telegram/WhatsApp (суммарно vs по типу); стадии vs число pipelines; branded portal на workspace; **candidate portal** — interactions vs portal-enabled candidates; **client portal** — пак +5 (**€20**) vs **€7/€5** per client.  
- [ ] **Trial** v1: 7 дней, лимиты + ограничение real sending; анти-абьюз.  
- [ ] **Founder pricing** (если запускаем): флаг + условия прерывания **X** дней.  
- [ ] **Сегментные пресеты** Agency/Employer/Services без дублирования прайса.  
- [ ] **UI биллинга и лимитов** по **§2.17** (tenant Settings + отдельный Platform Admin). Базовый экран и Checkout — см. **§2.18** «Состояние в коде».  
- [ ] **Stripe:** довести до спеки **§2.18** (остаток — в бэклоге там).

### 2.17 Подписка, пользователи, доступы и Platform Admin (логика + UI)

**Цель:** простота для владельца аккаунта **и** жёсткое соответствие модели **§2.16** (план, seats, workspaces, usage, модули). Цены в примерах ниже — из **§2.16**; при изменении прайса обновлять оба раздела. **Платежи (целевой провайдер):** Stripe — **§2.18** (Checkout, webhooks, статусы, VAT).

#### 1. Объект управления (иерархия)

**Account** → **Workspaces (companies)** → **Users (seats)** → **Roles & Permissions** → **Subscription (plan + usage)** → **Modules & Limits**.

В UI это не обязательно показывать как схему — но **данные и API** должны ей соответствовать.

---

#### 2. Settings → Billing & Subscription (главный экран тенанта)

**Состав (один экран, без разнесения «важного» по разделам):**

1. **Plan summary** — текущий тариф (например *Team — €129/month*), кратко что включено (**§2.16**).  
2. **Usage** — **всегда видимый** блок с **прогресс-барами**: Users *3/3*, Workspaces *1/1*, Leads this month *820/1500*, Active records *1200/2000* и т.д. по продукту.  
3. **Billing info** — next billing date, сумма, **VAT** (как в оферте).  
4. CTA: **`[ Upgrade plan ]`**, **`[ Change billing cycle ]`**, **`[ Manage add-ons ]`**.

**Принцип:** billing и usage **рядом** — пользователь видит **сколько платит** и **где упирается**.

---

#### 3. Upgrade / Change plan

- Список планов: **Solo / Team / Business** (+ Enterprise — contact).  
- Текущий план помечен.  
- Не длинный список фич, а **разница**: *Team includes …* / *Business adds …* → **`[ Upgrade to Business ]`**.  
- Согласовать с **§2.16** (downgrade со следующего цикла, upgrade с prorate).

---

#### 4. Add-ons (отдельный экран или шаг)

Таблица строк: Extra user, Extra workspace, Extra client portals (per client), Automation pack, Branded portal — **цены из §2.16**.

- Выбранные позиции + **Total add-ons** → **`[ Confirm changes ]`**.  
- После подтверждения — обновление **`TenantLicense`** / биллинга и **немедленное** отражение в Usage (где применимо).

---

#### 5. Settings → Team (пользователи и seats)

**Список:** *Team (3/3 seats used)*, пользователи с ролью и статусом → **`[ Invite user ]`**.

**Invite:** email, **Role** (Recruiter / Manager / Admin — набор из продукта), **Workspace access** (чекбоксы по компаниям — см. §7).

**Нет свободных seats:** *No available seats* → **`[ Add user (€18/month) ]`** (или цена **§2.16** для плана) / **`[ Upgrade plan ]`**.

**Связка с §2.16:** seat = правило из оферты (**viewer** и т.д.).

---

#### 6. Roles & Permissions

**Список ролей:** Admin, Manager, Recruiter, Viewer → **`[ Edit role ]`**.

**Экран роли:** матрица **granular**, но без перегруза — примеры секций: Candidates (view/edit/delete), Clients, Automation, Billing.  
**Billing** и критичные модули — только у ролей уровня Admin/владельца (как в политике продукта).

---

#### 7. Доступ к компаниям (multi-workspace)

На карточке пользователя (или в инвайте): **Company A ✓ / B ✗ / C ✗** → **`[ Save ]`**.

**Ключевая логика multi-tenant:** список сущностей и действий **скоупится** по выбранным workspace; несовпадение scope и роли — блокировать или предупреждать на API (**бэклог**).

---

#### 8. Settings → Companies / Workspaces

**Список** workspace с статусом → **`[ Add company ]`**.

**Создание:** имя + предупреждение *Additional workspace €25/month* (**§2.16**) → **`[ Create ]`**.  
Solo — без второй компании без апгрейда (**§2.16**).

---

#### 9. Ограничения и реакции системы (единый паттерн)

| Ситуация | UX |
|----------|-----|
| Лимит **пользователей** | *You reached your user limit* → **Add user €…/mo** · **Upgrade plan** |
| Лимит **лидов** / мес | *You reached monthly lead limit* → **Upgrade** · **Buy +500 leads (€15)** (или пак из **§2.16**) |
| Лимит **компаний** | *Additional workspace required* + цена |

Тот же паттерн для других лимитов (**§2.16**): всегда **действие с ценой**, не абстрактный баннер.

---

#### 10. Platform Admin (Super Admin) — отдельный интерфейс

**Не** внутри обычного Settings тенанта. Отдельный вход / host / приложение для операторов платформы.

**10.1 Список тенантов:** название, план, статус (Active / Trial / …), MRR, срок trial → **`[ Open tenant ]`**.

**10.2 Карточка тенанта:** план, users, workspaces, billing next charge → **`[ Change plan ]` `[ Add credits ]` `[ Suspend ]` `[ Impersonate ]`** (impersonate — по политике безопасности и аудита).

**10.3 Пользователи тенанта:** список, **`[ Reset password ]` `[ Remove access ]`**.

**10.4 Limits:** отображение лимитов плана → **`[ Override limits ]`** — **только** для platform admin, с **audit log**.

**10.5 Billing тенанта:** план + add-ons + total → **`[ Adjust billing ]`**.

**10.6 Audit log:** user added, plan upgraded, automation changed, overrides и т.д.

**10.7 Rulesets (advanced):** версии ruleset, active/archived → **`[ Rollback ]`** — если продукт вводит версионирование.

**10.8 Интеграции на уровне тенанта:** Meta, Google leads — **`[ Disable ]` `[ Reconnect ]`**.

---

#### 11. UX-принципы

1. Всё критичное для денег и лимитов — **на одном экране** (billing + usage).  
2. **Лимиты всегда видны** — пользователь чувствует границы плана.  
3. Апселл = **конкретное действие с ценой** (*Add user €18*), не голый *Upgrade now*.  
4. **Один** Settings для тенанта, **один** Platform Admin — не «админка внутри админки».

---

#### 12. Критические решения

**❌ Не делать:** отдельный экран на каждую сущность биллинга без связи; глубокую вложенную иерархию без поиска.

**✅ Делать:** простые списки, inline-действия, мгновенный апселл с привязкой к **§2.16**.

---

#### 13. Три уровня управления (итог)

| Уровень | Где | Что |
|---------|-----|-----|
| **1. Пользователь** | Work, Tasks, Inbox | Операционная работа (**§2.13–2.14**) |
| **2. Владелец** | Settings | Billing, Team, Roles, Workspaces (**§2.17**) |
| **3. Платформа** | Platform Admin | Tenants, limits override, billing adjust, аудит (**§2.17**) |

**Эффект:** пользователь понимает **сколько платит**, **за что** и **как увеличить** лимит легально и прозрачно.

#### Состояние в коде (честно)

- **Billing:** **`BillingWorkspacePage.tsx`**, **`billing.py`** — см. **§2.18**.  
- **Команда / seats (черновик):** панель **`TeamManagementPanel`** в **`BillingTeamPage.tsx`** (запросы мест, модули, обзор) — не полный сценарий **§2.17** п.5 (invite + matrix workspace).  
- **Platform admin:** **`TenantsPage.tsx`** — список тенантов, license, suspend, impersonate, модули; **отдельного** Platform Admin app нет.

#### Бэклог (внедрение)

- [ ] Экран **Billing & Subscription** + **usage** из метрик (**§2.16**) — довести до полной спеки. Черновик UI/API: **`BillingWorkspacePage.tsx`**; **`billing.py`**.  
- [ ] **Upgrade / compare**, **add-ons** и **Customer Portal** — расширить поверх текущего Checkout (**§2.18**).  
- [ ] **Team:** invite + seat gate + **workspace access** matrix поверх **`BillingTeamPage`** / **`UserFormInvite`**.  
- [ ] **Roles** editor с серверной валидацией.  
- [ ] **Companies** CRUD с предупреждением цены и enforcement **§2.16**.  
- [ ] Единые **limit reached** модалки → upgrade / buy pack.  
- [ ] **TenantsPage** (или отдельный app): **override limits**, billing adjust, **audit log** по **§2.17** п.10 — довести до спеки.  
- [ ] Аудит: plan change, override, invite, role change.

### 2.18 Stripe: единая цепочка trial → оплата → лимиты → UX

**Назначение:** связать **HF** со **Stripe** так, чтобы одна цепочка закрывала **trial**, **апгрейд**, **биллинг**, **лимиты**, **продуктовый UX** и **юридику** (**§2.16**, **§2.17**). Ниже — целевая архитектура; идентификаторы продуктов/цен — в конфиге и **Stripe Dashboard**, синхронизированы с **`TenantLicense`**.

#### 1. Общая архитектура

**User action** → выбор плана / add-on → **Stripe Checkout** (или **Customer Portal** / **Subscription update**) → **Webhook** Stripe → HF → обновление **subscription state** → применение **лимитов** / разблокировка **фич**.

Источник истины после активации: **Stripe Subscription** + зеркало в БД HF (**`stripe_customer_id`**, **`stripe_subscription_id`**, статус, текущий **price id**, add-ons как line items или отдельные подписки — **выбрать одну модель** в реализации).

#### 2. Состояния аккаунта (обязательно)

| Статус | Смысл | Продукт |
|--------|--------|---------|
| **trial** | Пробный период (**§2.16**): полный или частичный доступ по политике | До конца trial |
| **active** | Подписка оплачена, период действует | Полный доступ по плану |
| **past_due** | Платёж не прошёл (invoice failed) | Ограничения (**§11**) |
| **canceled** | Подписка отменена (конец периода или сразу — по политике) | Read-only / restricted (**§10**) |
| **incomplete** | Checkout / первый инвойс не завершён | Нет полного доступа до `active` |

При необходимости маппить **`incomplete_expired`** Stripe отдельно (истёк неоплаченный инвойс).

#### 3. Trial → conversion (UX)

**Во время trial:** на **Dashboard** — *Trial ends in N days*, контекст NBA (*N candidates waiting* …) → **`[ Continue with Team plan €129 ]`** (цена из **§2.16**).

**За ~48 ч до конца:** email, **in-app** banner, опционально Telegram/WhatsApp (**§2.15** / Comms).

**После окончания:** *Your trial has ended*; **данные сохранены**; **`[ Choose plan ]`**. **Work** (и создание сущностей): **read-only** или **нельзя создавать новые записи** — зафиксировать в оферте (**§2.16** Trial).

#### 4. UI оплаты: Stripe Checkout

CTA **`[ Upgrade to Team €129/month ]`** → **Stripe Checkout** (или встроенный flow, если позже).

**Параметры сессии (концептуально):** `plan_id` / **Price** id, **seats**, **add-ons**, **VAT / tax**, **billing cycle** (monthly/yearly), `client_reference_id` / metadata → **tenant_id**, success/cancel URLs обратно в HF.

**После успешной оплаты:** webhook **`checkout.session.completed`** / **`customer.subscription.updated`** → HF → **activate plan**, **unlock features**, обновить UI (**§2.17**).

#### 5. Экран в HF до редиректа в Stripe (рекомендуется)

Краткая сводка: план, users (included + extra), workspaces, строки add-ons, **Total** / month, переключатель **Monthly / Yearly** (скидка **§2.16**), поле **VAT ID** → **`[ Proceed to payment ]`**.

Снижает сюрпризы и согласуется с **§2.17** п.4–5.

#### 6. VAT (ЕС)

- С **VAT ID** (B2B): **reverse charge**, без начисления VAT с продавца — логика через **Stripe Tax** и/или **customer tax IDs** + проверка (**VIES** / аналог) в UI **Validate VAT** → *Valid (PL) — VAT will not be charged*.  
- Без VAT ID: начисление VAT по **стране** покупателя.

Детали — налоговый консалтинг; в **Terms** — кто отвечает за корректность реквизитов (**§2.16** чеклист).

#### 7. Инвойсы

**Settings → Billing → Invoices:** список (период, сумма, статус Paid/…), **`[ Download PDF ]`** (ссылка на **Stripe Hosted Invoice** или свой PDF).

В инвойсе: номер, дата, VAT, компания, адрес, разбивка услуг (**§2.16**).

#### 8. Управление подпиской (post-checkout)

Экран текущего плана: seats *included + extra*, workspaces *included + extra* → **`[ Add user ]` `[ Add workspace ]` `[ Change plan ]` `[ Cancel subscription ]`**.

Изменения, которые меняют MRR, вести через **Stripe** (update subscription / Checkout) с **proration** (**§9**).

#### 9. Изменение подписки и proration

Пример: *Add 1 user — €18/mo — Effective immediately — Prorated billing* → **`[ Confirm ]`** → **Stripe** применяет **prorate** (настройки `proration_behavior` в API).

То же для add-ons и смены цикла — явно в UI «следующий счёт / доплата сегодня».

#### 10. Отмена подписки

*Cancel subscription?* — *Access until {date}* · *After that: read-only* → **`[ Confirm cancel ]`**. Синхронизация с **`customer.subscription.deleted`** / `cancel_at_period_end` в webhook.

#### 11. Past due

**UI:** *Payment failed* — **`[ Retry payment ]`** (Stripe **Customer Portal** или обновление платёжного метода).

**Ограничения (ориентир):** нельзя создавать **новые лиды** / критичные сущности, нельзя **отправлять сообщения**; **Dashboard** и просмотр — доступны (политика может ужесточаться). Согласовать с **§2.16** неоплата / grace.

#### 12. Связка с лимитами

*You reached your limit* → **Upgrade** · **Add +500 leads (€15)** — кнопка открывает **тот же** Stripe-поток (новая подписка / subscription item / one-time — **выбрать модель**). Единый паттерн с **§2.17** п.9.

#### 13. Объекты Stripe

1. **Products** — HF Solo / Team / Business (и при необходимости Enterprise как custom).  
2. **Prices** — monthly / yearly на каждый план; отдельные Prices для **add-ons** (seat, workspace, packs) или **metered** — по выбору.  
3. **Subscription** — основной объект доступа.  
4. **Usage / metered** (если включите) — лиды, порталы и т.д. (**§2.16** overage); иначе overage как **разовые инвойсы** или **subscription items** — зафиксировать.

#### 14. Webhooks (обязательно обработать)

- `checkout.session.completed`  
- `customer.subscription.created`  
- `customer.subscription.updated`  
- `invoice.payment_succeeded` / **`invoice.paid`** (оба ведут в один обработчик)  
- `invoice.payment_failed`  
- `customer.subscription.deleted`  

Идемпотентность по **`event.id`**: таблица **`stripe_webhook_event_log`**, запись **после** успешной обработки (повтор доставки → `Duplicate webhook ignored`). Верификация подписи, при сбоях — ретраи Stripe. Актуальный код — **`billing.py`** `stripe_webhook`.

#### 15. Маппинг webhook → HF

- **`active` (+ оплаченный период)** → включить фичи по **§2.16**.  
- **`past_due`** → **restrict** (**§11**).  
- **`canceled` / окончание периода** → **read-only** / restricted (**§2.16** downgrade).  
- **`incomplete`** → не считать платящим; ограниченный доступ.

#### 16. Главная UX-логика

1. **Оплата = продолжение действия:** не «иди в биллинг», а **`[ Add user ]`** → оплата → пользователь добавлен (**§2.14** paywall в потоке).  
2. Апселл из контекста: *Assign leads automatically* **🔒** → **Upgrade to Team** → Checkout.  
3. **Минимум трения:** один переход в Stripe, **return URL** → HF уже с обновлённым состоянием после webhook (с учётом задержки — optimistic UI осторожно).

#### 17. Ошибки, которых нельзя допустить

Сложный checkout без сводки; отдельный «мир биллинга» без связи с действием; нет **VAT**; нет **prorate** при ожидании пользователя; нет **webhooks** (только client-side); блокировка **без объяснения** и CTA **Retry / Upgrade**.

#### 18. Итоговая модель

**Trial** → действие в продукте → **Upgrade** → **Stripe** → **Webhook** → **Unlock** → **Usage tracking** → **Renewal**.

**Эффект:** пользователь **не думает про биллинг** — **продолжает работать**; платформа остаётся в рамках **§2.16–2.17**.

#### Состояние в коде (честно)

- **Уже есть:** **`backend/app/api/v1/settings/billing.py`** — `checkout-session` (Stripe Checkout при настроенных ключах, иначе mock), **`webhook`** — `checkout.session.completed`, **`invoice.paid`** и **`invoice.payment_succeeded`**, **`invoice.payment_failed`** (статус **`past_due`** + email), **`customer.subscription.created` / `updated` / `deleted`**; **идемпотентность** по **`event.id`** — модель **`StripeWebhookEventLog`**, миграция **`202603251400_stripe_webhook_log`**; частично **Billing Portal**; хранение подписки на тенанте. Фронт: **`BillingWorkspacePage.tsx`**, **`billing.ts`**.  
- **Ещё нет / слабо:** сводка перед оплатой по **§2.16** (add-ons, seats); **Stripe Tax** / **VAT ID** / VIES; список **Invoices** в Settings; **trial** баннеры (Dashboard частично есть) и **полный** read-only после trial на всех write-API (сейчас — лиды + исходящие comms); **metered** / overage; при гонке двух вебхуков с одним `event.id` возможен кратковременный двойной side-effect до записи в лог.  
- **Частично past_due UX:** баннер + CTA **Retry payment** → **Customer Portal** (не новый Checkout), правка **`BillingWorkspacePage.tsx`**.  
- **past_due + expired trial API (лиды / исходящие):** **`backend/app/services/billing_restrictions.py`** — при **`past_due`** или **истёкшем trial** (`TenantLicense.plan == trial` и **`expires_at` < сегодня**, либо **`subscription.status == trial`** и **`trial_ends_at` в прошлом**): новый лид не создаётся (**`modules/leads/service.py`**) → **403** `billing_past_due` / `billing_trial_expired`; исходящие сообщения и **`dispatch/queued`** — **403** / no-op; **`GET /settings/billing/subscription|summary`** подставляет **`trial_ends_at`** из лицензии trial, если в **`settings.billing`** ещё нет даты.

#### Бэклог (внедрение)

- [ ] **Products/Prices** в Stripe под полную матрицу **§2.16**; стабильный metadata `plan_code`, `tenant_id`.  
- [ ] Webhook: при необходимости **`invoice.finalized`** и др.; **очередь** / ретраи внутри HF при ошибках после частичного commit.  
- [ ] Экран **summary** перед редиректом в Checkout; **Stripe Tax** / tax IDs + проверка VAT (EU).  
- [ ] **Settings → Billing → Invoices** (hosted invoice / PDF).  
- [ ] **Trial** (UI баннеры / post-trial messaging) и **post-trial** read-only на остальных write-API (частично: лиды + исходящие comms — **`billing_restrictions`**).  
- [ ] **Metered** overage или ручные инвойсы — решение и внедрение.

### 2.19 Порядок работ (зафиксировано)

1. **Этап — продукт и платформа:** последовательно закрывать **все** открытые **`[ ]`** в **§2** (включая **§2.16–§2.18**), пока каждый пункт не станет **`[x]`** или не будет явно снят как неактуальный.
2. **Этап — коммерция:** внешние продажи, маркетинг и публичный GTM — **после** этапа 1.

**Примечание:** чеклисты **§2.18** и **§2.16–§2.17** — часть общего бэклога **§2**, без отдельного «раньше времени» среза.

---

*Обновлено: 2026-03-26 — **§2.19** порядок: весь **§2** → коммерция; §2.12: **`lost_from_stage`** + **`lost_reason_breakdown`** в **`conversion-funnel`** + UI; **`lead_lost_reason_v1`** + модалка при **`lost`** (инбокс, деталь, **`PATCH /leads/bulk`**); **срезы** TEAM+; **dwell**; §2.11: **`GET /leads?q=`**; §2.10: NBA **Process batch**; paywall **field_mapping** + **Meta credential**; §2.6: **лиды** в **`GET /search`**. 2026-03-25 — §2.2 (onboarding i18n); §2.3 — NBA **candidates** + **`t_due_bucket`**; **gating** + **Do now**; **`GET /next-actions`**; **`GET /leads/stage-health`**; distribution **language_routing_v1**; inbox **assignment_lock**; DnD; round-robin; **`stage_contract_v1`**; **LeadOut** + playbook; **next_action** bulk **block**; **lead.pipeline.stage_changed**; §2.18; billing.*
