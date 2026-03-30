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

### 1.7 Покрытие SSOT: что значит «100%»

Документ **§2** смешивает три типа пунктов:

| Тип | Смысл | Обязательность |
|-----|--------|----------------|
| **Gate пилота (1a)** | Операционная CRM: лиды, кандидаты, Work/Dashboard, IA v1, own-company v1, поиск — см. **§2.19** | Для **внутреннего пилота** этот контур считается **закрытым**, если нет **блокирующих** регрессий; открытые **`[ ]`** в **§2.7–§2.9**, **§2.15** и коммерции **не удерживают** merge, пока release gate не объявлен иным. |
| **Фазы 1b / 1c** | Монетизация (**§2.16–§2.18**, **§2.17**), клиентский портал (**§2.15**) | Отдельные вехи; **«100% коммерции»** = обнуление (или явное **вне scope**) бэклогов **§2.16–§2.18** и **§2.17** «Бэклог (внедрение)». |
| **Stretch** | Полировка, perf SLA, декомпозиция файлов, UOS | По приоритету продукта; не метрика «готовности SSOT». |

**Практическая метрика «100% §2 для пилота»:** все чеклисты, которые **§2.19** относит к **1a** (**§2.1–§2.6**, закрытые **§2.13 / §2.14**), — с **`[x]`**; остальные **`[ ]`** в документе трактуются как **roadmap 1b/1c/stretch**, а не как «дыра в SSOT».

**Практическая метрика «100% продукта по SSOT»:** нет **`[ ]`** в бэклогах **§2.15–§2.18** и **§2.16–§2.17** (или каждый перенесён в **`[x]`** с пометкой **«Остаётся»** и принят владельцем продукта). Это **не** синоним ежедневной готовности репозитория.

**Сводка открытых `[ ]` (проверка актуальности):** поиск по файлу **`^- \[ \]`** — перечень дорожной карты; при закрытии задачи в коде — **`[x]`** или удаление строки (**§1.3**).

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

**Состояние в коде (частично):** напоминания / «next action» — **`GET /api/v1/notifications`**, **`RemindersPage`** (`/app/tasks`); строки **`app.reminders.*`** (вкл. **`filters.search_tasks` / `search_events`**, действия по уведомлениям), **`app.notifications.*`** (типовые заголовки событий), **`app.topbar.*`** (панель уведомлений, quick create, trial, язык) и **`app.shell.account.my_account`** — в **`i18n/{en,ru,pl}.json`**; в **`Topbar.tsx`** aria для кнопок inbox — **`app.nav.items.messages_inbox` / `email_inbox`**, ссылка «Inbox» — **`app.nav.items.inbox`**. Динамические подписи (**RemindersPage**: приоритет, SLA, статус строки; **Topbar**: ключи из payload / **`app.notifications.event_types.*`**) оставляют **`defaultValue: ''`** там, где ключ может отсутствовать. Метрики no-next-action / leads — на единой странице **`/app/overview`** (**Insights** / **`Dashboard.tsx`**; отдельного хаба **`/app/analytics`** в навигации нет). Это **не** ещё единый **NBA API** и продуктовый слой из пунктов ниже.

- [x] **Хук смены стадии лида (v0):** при **`PATCH /api/v1/leads/{id}`** и при **`PATCH /api/v1/leads/bulk`** (если в payload есть **`stage`**) — **`pipeline_hooks.py`**: на каждый лид с реальным изменением стадии — activity **`lead.stage_changed`**, in-app **`lead.pipeline.stage_changed`**, automation **`lead.pipeline.stage_changed`** (контекст `from_stage` / `to_stage` / `lead_id` / `assignee_id`; правила **после** commit, по аналогии с **`lead.processed`**). UI триггера — **`AutomationRulesPage`**.
- [x] **Единая система с pipeline (v1 — часть):** авто-distribution (**`pick_assignee_user_id_for_ingest`**, **`lead_distribution.py`**) сужает пул по **`FunnelStage.stage_contract_v1.owner_role`** текущей CRM-стадии лида (воронка типа **lead**: **`lead.funnel_id`** или дефолт тенанта): маппинг на **`User.role`** (`recruiter` / `manager`→supervisor / `admin`→administrator; несколько значений через запятую/пробел); при пустом пересечении — откат к полному пулу; в **`team`** snapshot каждого члена добавлено поле **`role`**. Уже было: хуки смены стадии (**`pipeline_hooks`**), workload/language/working_hours/round-robin, enforcement next action при смене стадии, automation **`lead.pipeline.stage_changed`**. **Остаётся (целевая модель):** смена назначения как триггер создания next action / task; блокирующая валидация **`required_actions`** и цепочка handoff → следующая задача (**§2.15**); перераспределение по SLA как отдельный job; полное слияние pipeline ↔ distribution сверх текущих правил.
- [x] **Модель стадии в данных воронки (v1):** JSON **`stage_contract_v1`** на **`FunnelStage`** с полями **`owner_role`**, **`required_actions`**, **`sla_hours`**, **`auto_rules`**; миграция **`202603252000_funnel_stage_contract_v1`**; API **`FunnelStageIn` / `FunnelStageOut`** в **`funnels.py`** (PATCH не затирает контракт, если тело без **`stage_contract`**). UI: **`FunnelsPage`** — вкладки **Candidates / Leads**, в модалке стадии блок **Pipeline contract**. Сиды онбординга пока не заполняют контракт — только ручной ввод / API.
- [x] **Карточка лида / inbox (v1):** ручная смена стадии + **`assignment_locked`** → **`normalized.assignment_lock_v1`** (**`PATCH /leads/{id}`**; поле **`stage`** только если передано в теле — нет лишнего сброса); **enforcement** next action только при **реальной** смене стадии; **`GET /leads`** — **`funnel_id`**, **`stage_contract`**; **Composer** — сводка next action + контракт стадии; **bulk** — enforcement; **`pick_assignee_user_id_for_ingest`** пропускает авто-назначение при **`assignment_lock_v1.locked`**. **Full-page (v0):** **`GET /api/v1/leads/{id}`** — тот же **`LeadOut`**, что элемент списка; SPA **`/app/leads/:leadId`** (**`LeadDetailPage`**) — сводка полей, **Meta troubleshoot:** компонент **`LeadMetaProblemPanel`** (**Retry** / **Reroute** / ссылки Integrations) — на **`LeadDetailPage`** и на вкладке **Fix** inbox **`LeadsPage`** (единая реализация), **CRM:** стадия + **`assignment_locked`** (**`PATCH /leads/{id}`**), **follow-up** (**`listReminders` / `createActivity` / `completeActivity`**), таймлайн, ссылки (кандидат / клиент / заказ / **Process** для Meta); **тихий refresh** карточки после Meta-fix (**`loadLead({ silent })`**, без полноэкранного loading); при **Retry** / **Process** в строке таблицы и вкладке **History** — обновление таймлайна, если открыт тот же лид; после **Process** на полной карточке — **`loadLead({ silent })`** + таймлайн. **Общие CRM-хелперы лида:** **`hostflow-frontend/src/utils/leadCrm.ts`** — **`CRM_STAGE_VALUES`**, **`leadAssignmentLocked`**, **`isMetaProblemLead`** (список / inbox Fix / **`LeadMetaProblemPanel`**). **Виджет next action + контракт стадии (v0):** общий компонент **`LeadNextActionPlaybook`** — **`LeadsPage`** (вкладки **Composer**, **Focus**, **History**, **Fix** для Meta-troubleshoot) и **`LeadDetailPage`**; строки **`app.leads.inbox.*`** (вкл. **`playbook.*`**, баннер фильтров, вкладки, toasts **`stage_updated` / `lock_saved`**, **`lock_assignment`**, **`stage_unset`**) и **`app.leads.detail.*`** (**`LeadDetailPage`**, ошибки стадии/lock в inbox), плюс **`app.leads.messages.*`**, **`app.leads.bulk.*`**, **`app.leads.stage_health.*`**, **`app.leads.workspace.distribution_cta`** (рядом с заголовком workspace; отдельно от **`app.nav.items.leads_distribution`** в сайдбаре), **`app.reminders.*`** для follow-up на лиде, корень **`common.retry`** в **`i18n/{en,ru,pl}.json`**; для перечисленных ключей в коде **`t()`** без дублирующего **`defaultValue`**; в шапке inbox-панели — ссылка на **`/app/leads/:leadId`**. **Dashboard NBA (v1):** под заголовком — текстовая подсказка **`app.dashboard.nba.playbook_hint_*`** + ссылка на **`/app/leads`**; под чипами — **`LeadNextActionPlaybook`**: превью по **`GET /leads?limit=1`** с теми же **`status` / `stage` / `next_action`**, что у первой непустой группы лидов NBA (порядок как в **`GET /next-actions`**, приоритет разблокированных очередей); строка **`app.dashboard.nba.playbook_loading`**. **Остаётся:** расширение полей / действий из одного места; превью playbook для кандидатов/tasks на дашборде — не делали (только чипы).
- [x] Правила distribution: **drag-and-drop** порядка критериев — **`LeadsDistributionRulesPage.tsx`** (`@dnd-kit` + ручка **IconGripVertical**); строки **`app.leads.distribution.rules.*`** в **`i18n/{en,ru,pl}.json`**.
- [x] **Working hours** из календаря (**`User.extra.working_hours_v1`**) в фильтре назначения (статус **offline** вне окна при **`working_hours`** в **`criteria_order`**) — уже было в **`lead_distribution.py`**; **«why» (v0):** **`assignment_detail_lines`** + **`next_preview.detail_lines`** (сколько коллег вне окна; уточнение по календарю в **`rules_summary_lines`**); карточки команды на **`LeadsDistributionPage`** — **`within_working_hours`** / **`working_hours_configured`**.
- [x] **Round-robin** с сохранённым указателем между назначениями — **`lead_distribution.round_robin_last_user_id`** в **`Tenant.settings.lead_distribution_v1`**; циклический следующий в порядке команды из **`_build_distribution_team`**; сброс курсора при смене стратегии с **round_robin** на другую в **`patch_distribution_settings`** (`lead_distribution.py`).
- [x] **Явный маппинг language → user (v0):** **`Tenant.settings.lead_distribution_v1.language_routing_v1`** — объект **`{ "pl": ["uuid", …], "en": […] }`** (порядок = приоритет); **`_lang_pool_for_distribution`** / **`language_route_user_ids`** в **`lead_distribution.py`**; PATCH **`language_routing_v1`** с фильтром по активным пользователям тенанта; UI — **`LeadsDistributionRulesPage`** (PL/EN/DE). Если никто из карты не eligible — откат к языкам из **`preferences`/`extra`**.
- [x] **Воронка в UI (health по CRM-стадиям, v0):** **`GET /api/v1/leads/stage-health`** — **`lead_stage_health_snapshot`** в **`service.py`**; строки **`LeadStageHealthRow` / `LeadStageHealthResponse`** в **`schemas.py`**; роут **до** **`PATCH /{lead_id}`** в **`router.py`**. **`LeadsPage`**: горизонтальная полоса карточек по стадиям — processed в стадии, ссылки на **`GET /leads`** с теми же **`status` / `stage` / `next_action`**, что NBA; **`fetchLeadStageHealth`** в **`api/leadStageHealth.ts`**. Фильтр **stuck** при явном **`stage`**: не режем по allowlist **`leads_next_action_sla_v1.stages`** (иначе **converted/lost** всегда 0). **Канбан (v1):** переключатель Table/Kanban на **`LeadsPage`**, **`LeadsKanbanBoard`** — колонки по **`status` / `stage`** с теми же базовыми фильтрами, что таблица.
- [x] **Dashboard Auto-fix (v0):** **`POST /api/v1/leads/bulk/auto-process-queue`** — до **50** Meta-лидов со статусами **`needs_routing` / `failed`** (тот же контур, что **`POST /leads/{id}/process`**); фильтр **`own_company_id`** как у списка; paywall **`plan_allows_team_tier_features`** (как automation / distribution). UI: **`DashboardLeadAutoFixCard`** под NBA-секцией; **`bulkAutoProcessLeadQueue`** в **`client.ts`**. **Остаётся:** расширить правилами (не только Meta queue), «Fix all» без лимита / очереди по плану.
- [x] **NBA — лиды + кандидаты (v0–v1):** **`GET /api/v1/next-actions`** — **`next_actions.py`**; **`lead_next_actions_snapshot`** в **`service.py`** (`actor_user_id` = текущий пользователь). **Лиды:** как раньше + **gating** / **`plan_code`** / **`nba_tier`** / **`locked`** на **stuck**. **Кандидаты (v1):** **`candidates_no_next_action`** (как **`GET /candidates/no-next-action`**, учёт **`own_company_id`**); **`candidates_next_overdue`** — join **`Reminder`↔`Candidate`**, просрочка как у лидов; **`entity=candidate`**, **`path`** → **`/app/candidates/no-next-action`** или **`/app/tasks`** + **`query.tab` / `t_*` / `t_due_bucket=overdue`**. Схема **`NextActionQueryParams`** расширена под SPA (в т.ч. **`pipeline_error`** ↔ **`GET /leads`** для **`leads_fit_no_match` / `leads_fit_needs_info`**). UI: **`LeadsPage`** — индиго чипы кандидатов, **`nbaGroupHref`** в **`nextActions.ts`**; **`RemindersPage`** — чтение **`t_due_bucket`** и фильтр списка. **Do now:** bulk через **`useNbaQuickBulkFlow`** + **`NbaNextActionsChips`** — **`POST /activities/bulk`** для **лидов** и **кандидатов** (как выше). **Dashboard:** **`DashboardNbaSection`** (`components/nba/DashboardNbaSection.tsx`) под **`SetupProgressRail`**, при **`leads.view`** и непустых группах. **Topbar:** **`TopbarNbaMenu`** (`components/nba/TopbarNbaMenu.tsx`) — попап NBA + badge суммы счётчиков, **`useNbaQuickBulkFlow`** + **`BulkActivitiesModal`**. **Остаётся:** другие сущности в NBA.
- [x] **Управляемая квалификация / конверсия лидов (v1 — хранение + ingest):** колонка **`meta_lead_settings.leads_processing_mode_v1`** (`manual` / `assisted` / `automatic`; в API **`MetaLeadSettingsOut`** при `NULL` в БД отдаётся **`assisted`**); миграция **`202603252100_meta_lead_processing_mode_v1`**; **`ensure_schema`** / **`admin_service._ensure_settings_schema`**. **`GET/PATCH /api/v1/settings/leads/settings`**. В **`process_normalized_lead`**: в **`normalized`** — **`leads_processing_mode_configured_v1`**, эффективный **`leads_processing_mode_v1`** (для **`automatic`** без Team-tier плана — **`manual`**, плюс **`leads_processing_mode_downgrade_v1`=`team_plan_required`**); автосоздание кандидата только если **`auto_create_enabled`** и эффективный режим **не** **`manual`**. UI: **`MetaLeadsAdminPage`**, **`i18n`** **`app.admin.meta_leads.settings.processing_mode_*`**. **Остаётся:** движок правил, Assisted на карточке лида, NBA/CTA и прочее по **§2.10**; связка с fit-check (**§2.5**).
- [x] **§2.11 v0 (каркас):** хаб **Integrations** — **`/app/settings/integrations`** (список источников; Meta → **`/app/settings/integrations/meta`**); **View incoming (Meta)** — **`GET /api/v1/settings/leads/meta/incoming-preview`**, вкладка **Incoming** на **`MetaLeadsAdminPage`** (последние лиды `source=meta`, превью JSON `payload` / `normalized`). Старые ссылки **`/app/settings/integrations?tab=…`** редиректят на **`/meta?tab=…`**.
- [x] **Единая цепочка источников → поля → правила → pipeline (v1 в UI):** на хабе **`/app/settings/integrations`** (**`IntegrationsHubPage`**) блок со ссылками: источники → **Meta** (маппинг полей) → воронки (**`/app/settings/funnels`**) → **automation-rules** → **`/app/overview#lead-conversion`** (канон; старый **`/app/analytics/lead-conversion`** редиректит сюда). **Остаётся (целевая §2.11):** централизованный custom fields вне Meta, отдельный rule engine, pipeline builder UI, полнота Google/Webhook как первоклассных источников.
- [x] **Воронка конверсии как инструмент управления (v1 — закрыто):** **§2.12** + связка с **NBA** (**§2.3**) и маппингом (**§2.11** / **`FunnelsPage`**). **В продукте:** **`GET /leads/conversion-funnel`** (roots, **dwell**, **lost_from_stage**, **lost_reason_breakdown**, срезы TEAM+); drill-down **`GET /leads`** — **`conversion_root`**, **`lost_reason_code`**, **`lost_from_crm_stage`** (в т.ч. AND); **`LeadsPage`** полоса воронки + stage health; **вертикальная воронка** — **`AnalyticsLeadConversionFunnelPage`** **встроена** в **`/app/overview`** (секция с **`id=lead-conversion`**, проп **`embedded`**; deep link **`#lead-conversion`**; legacy **`/app/analytics/lead-conversion`** → редирект), **Suggested focus** (пороги как NBA), блок **«Контур управления»** (пайплайны → **automation-rules** → лиды → обзор) + быстрые очереди **lost** по типовым причинам; **Dashboard** — чипы **`leads_funnel_weak_step` / `leads_funnel_slow_stage`** + paywall Team, **Do now** / playbook. **Не входит в v1** (перенесено): единый продуктовый pipeline UX полной **§2.11** (см. остаток в пункте про цепочку выше).
- [x] **§2.12 stretch (v1):** **`GET /leads/conversion-funnel`** — фильтр когорты по **`Lead.created_at`** (**`cohort_window_days`** или пара **`cohort_created_after` / `cohort_created_before`**) + **`cohort_compare_prior`** (предыдущее окно той же длины); UI **`AnalyticsLeadConversionFunnelPage`** — переключатель «всё время / 7d / 7d vs prior», таблица метрик current vs **`cohort_prior_window`**; **канбан** — **`LeadsKanbanBoard`** на **`LeadsPage`**; комбо-ссылки **prior stage × lost reason** на странице аналитики воронки. **Остаётся (v2+):** сценарные шаблоны действий (документы / портал) поверх drill-down; расширенные WoW-инсайты на Dashboard; выбор произвольного окна когорты в UI (не только rolling 7d); тяжёлые пресеты сценариев.

### 2.4 Multi–own-company (scoped `own_company_id`)

- [x] **Клиентские `companies` → `client_companies` (v1):** Alembic **`202603291300_client_co_mirror`** — в **`client_companies`** копируются строки **`companies`**, у которых **`extra.company_role` ≠ `operating`** (дефолт роль — client), с тем же **`id`**, идемпотентно. **Инвойсы / `own_companies`:** при создании счёта без **`billing_details.issuer_company_id`** выставитель берётся из активного **`OwnCompany`** (**`payload.own_company_id`**), в **`billing_details`** пишется **`issuer_own_company_id`** и реквизиты из **`OwnCompany.bank_details`** / адреса; если реквизитов недостаточно для валидации — откат на legacy operating **`Company`**. Код: **`backend/app/api/v1/invoices/crud.py`**. **Остаётся:** перенос FK (**`vacancies.company_id`**, **`tenant_links`**) и UI на **`client_companies`**, полный отказ от operating-строк в **`companies`**, опциональный read-only слой.
- [x] **Ruleset + документы по `Candidate.own_company_id` (v1):** эффективный ruleset и выборка документов для чеклистов/гейтов совпадают со скоупом кандидата — **`ensure_ruleset_seed(..., own_company_id=...)`** и **`list_candidate_documents(..., active_own_company_id=...)`** в **`backend/app/api/public/intake.py`** (чеклист и submit), **`_enforce_docs_ready_for_handoff_stage`** (**`backend/app/api/v1/candidates/service.py`**), **`enforce_pipeline_doc_forward_block`** (**`backend/app/services/candidate_doc_pipeline_guard.py`**), **`_telegram_required_docs_snapshot`** (**`backend/app/api/v1/communications.py`**), **`get_candidate_required_docs_snapshot`** (**`backend/app/services/candidate_telegram_notifications.py`**).
- [x] **Полное покрытие скоупом** (v1 целевые модули): list/get/update с **`own_company_id`** где применимо; create без тихого `null` в документных контурах. **Частично (communications v1):** **`backend/app/api/v1/communications.py`** — **`GET /threads`** фильтрует по активной own-company (**`resolve_active_own_company_id_optional`** + заголовок **`X-Own-Company-Id`**); **`POST /threads`** задаёт **`own_company_id`** (**`resolve_active_own_company_id`**); **`GET/PATCH /threads/{id}`**, список/создание сообщений — проверка **`_ensure_thread_matches_own_company_scope`**; ingest email / generic / исходящий sync почты — **`_default_own_company_id_for_tenant`** на новых тредах и backfill на существующих без скоупа; у **`CommunicationMessage`** проставляется **`own_company_id`** с треда. **Частично (candidate documents v1):** **`backend/app/api/v1/candidate_documents.py`** — CRUD, загрузка, скачивание, **`apply-template`** — фильтр и проверка по **`own_company_id`** (join **`Candidate`**, заголовок **`X-Own-Company-Id`**); **`vacancies/router.attach_candidate`** передаёт **`vacancy.own_company_id`** в **`apply_template_to_candidate_impl`**. **Частично (legacy `/api/v1/documents` v1):** **`backend/app/api/v1/documents.py`** — **`GET /`**, **`POST /`**, **`POST /order`**, **`GET/PATCH/DELETE /{id}`**, **`GET /expiring`** — скоуп как у candidate-documents (join **`Candidate`**, **`X-Own-Company-Id`** / **`resolve_active_own_company_id_optional`**); на create/order пишется **`Document.own_company_id`**; **`modules/documents/crud.create_document`** принимает **`own_company_id`** в payload. **`GET /templates`** — по-прежнему на уровне тенанта (без own-company). **Частично (service orders / additional services v1):** миграция **`202603291400_svc_ord_oc`** — колонка **`service_orders.own_company_id`**; стартовый ensure Postgres (**`ensure_service_orders_own_company_id_column`**, URL **`postgresql+psycopg`** из **`ASYNC_DATABASE_URL`**). **`backend/app/services/additional_services.py`** — **`list_orders`** / **`catalog_usage_metrics_map`** с **`own_company_scope`** (join **`Candidate`**, **`Vacancy`**, правила как у документов; заказы только по **`company_id`** без своего **`own_company_id`** остаются «legacy» видимыми при активном скоупе); **`resolve_new_order_own_company_id`**, **`ensure_order_own_company_scope`**, ветки item/schedule; документ из **`deliver_item`** получает **`own_company_id`** заказа. **`backend/app/api/v1/services.py`** — **`Depends(resolve_active_own_company_id_optional)`** на заказы и связанные мутации; каталог **`GET /services`** с **`include_metrics`** учитывает скоуп. **`global_search_v1`** — срез **`service_order`** с тем же скоупом. **`GET /analytics/services-overview`** (**`analytics.py`**) — **`_service_order_scope_where`** + **`resolve_active_own_company_id_optional`**. **Частично (document_policies + documents-db v1):** миграция **`202603291500_doc_pol_oc`** — **`document_policies.own_company_id`**; **`/document-policies`** с **`resolve_active_own_company_id`**, create пишет активный скоуп, list/update/delete видят строки активного скоупа + legacy **`NULL`**; API ответы с **`own_company_id`**, маппинг **`required` ↔ `required_level`**. **`services/own_company_doc_scope.py`** — общие предикаты для документов/политик; **`candidate_documents`** импортирует хелперы оттуда. **`/api/v1/db`** (**`modules/documents/router.py`**) — **`resolve_active_own_company_id_optional`** на списки (включая tenant-wide **`GET /db/documents`**), create по кандидату, get/patch/delete документа, file-url/download, checks, extract, mock-upload, export/summary/checklist/zip; **`list_candidate_documents`** — join+скоуп; **`load_candidate_work_panel`** прокидывает скоуп в documents summary. **`check_gate_requirements`** — опциональный **`own_company_id`**. **`/db` ruleset (v1):** миграция **`202603291600_doc_ruleset_oc`** — **`document_ruleset_versions.own_company_id`**, частичные уникальные индексы (глобальная цепочка **`NULL`** / отдельная на own-company); **`GET /db/ruleset`** — эффективный ruleset (scoped при наличии, иначе глобальный); **`PATCH /db/ruleset`**, список версий и **`/ruleset/usage`** — запись/листинг в глобальную цепочку, пока нет ни одной версии с **`own_company_id`** активного скоупа (**`ruleset_write_scope_own_company_id`** в **`crud.py`**); явный форк — **`POST /ruleset/versions`** с заголовком скоупа; diff/activate/rollback — видимость и согласованность скоупа; чеклист/summary — **`ensure_ruleset_seed(..., own_company_id=...)`**; **`POST .../presign-upload`** — **`_get_document_with_access`**. **Остаётся:** прочие модули вне перечисленных контуров (по мере аудита).
- [x] **Права (v1 backend):** **`User.preferences.allowed_own_company_ids`** (непустой список UUID) ограничивает пользователя; обход для **`administrator` / `superadmin`** (+ строки **`admin` / `owner`** в токене) — **`own_company_acl.py`**, **`resolve_active_own_company_id`**. **`GET /own-companies`** / ответ **`POST /own-companies/active`** — список отфильтрован; **`POST /own-companies/active`** — **403** если id не в ACL; **`ActivityLog`** **`own_company.active_changed`** (from/to, IP/UA). Админ: **`PATCH /admin/users/{id}/own-company-access`** — валидация **`OwnCompany`** тенанта, при необходимости сброс **`active_own_company_id`** в первый разрешённый; **`user.own_company_access_updated`** в audit/activity. **`_ensure_preferences_structure`** сохраняет **`active_own_company_id`** / **`allowed_own_company_ids`** при PATCH **`/users/me`**. **`UserDetailOut.allowed_own_company_ids`**. **Остаётся:** UI назначения ACL, продуктовые роли-матрицы, тесты.
- [x] **UX (v1):** **«Создать / новое пространство»** в **Topbar** рядом с селектором own-company — **`createOwnCompany`** + **`setActiveOwnCompany`**; лимит **`license.max_companies`** из **`TeamOverviewNavContext`** (как **`GET /settings/team`**); кнопка disabled при лимите; **402** — toast + hint биллинг; **`CRM_APP_PATHS.settingsBilling`** для **`admin.users`**. **Остаётся:** отдельный upsell-модал под планы, mobile-first вариант свитчера.
- [x] **Vacancy requirements + fit-check** при смене скоупа **`own_company_id`**: **`list_leads`** / деталь лида — outer join **`Vacancy`** только если **`Vacancy.own_company_id IS NULL OR = Lead.own_company_id`** (**`backend/app/modules/leads/service.py`**); резолв вакансий при ingest / ordered ids / qualification rules — **`resolve_vacancy_by_id` / `resolve_vacancy_by_ad`** с **`scoped_own_company_id`**, **`resolve_vacancy_for_lead_processing(..., own_company_id=...)`** (**`crud.py`**, **`lead_qualification_rules.py`**); ручной reroute — скоуп от **`lead.own_company_id`**. Тесты: **`backend/tests/test_lead_vacancy_own_company_scope.py`**.
- [x] **Флаг авто-конверсии при fit (§2.4 v1):** **`meta_lead_settings.leads_auto_convert_on_fit_v1`** (default **true**, миграция **`202603291200_meta_ac_fit`**); в **`process_normalized_lead`** фактическое **`may_auto_convert`** = Automatic + **`auto_create_enabled`** + флаг тенанта + вакансия без **`Vacancy.extra.leads_auto_convert_on_fit_v1 === false`**; стамп **`normalized.leads_auto_convert_on_fit_effective_v1`**; при «автоматике без конверсии» — превью с **`blocked_auto_convert`**. UI: **`MetaLeadsAdminPage`**, opt-out на **`VacancyDetail`**.

### 2.5 Vacancy requirements / lead fit-check (v2+)

Критерии вакансии, глобальные правила тенанта (**§2.10**) и типизированные поля лида (**§2.11**) нужно **свести в одну стратегию** (общая модель или явные слои), чтобы не было двух несовместимых «истин».

- [x] **UI пресета порядка вакансий (v1):** **`lead_fit_ordered_vacancy_ids`** в **`GET/PATCH /settings/leads/settings`** (чтение/запись **`Tenant.settings.lead_fit_routing_v1.ordered_vacancy_ids`**); вкладка **Settings** на **`MetaLeadsAdminPage`** — упорядоченный список + add / ↑↓ / удалить; **`i18n`** **`app.admin.meta_leads.settings.lead_fit_order_*`**.
- [x] **Расширение критериев (v1, normalized + Documents):** в **`lead_criteria_eval.evaluate_lead_criteria_v1`** — страны/языки/национальность (см. выше); **`requires_documents`** по **`normalized.documents`**; **`requires_candidate_documents_v1`** + опционально **`candidate_documents_allow_statuses`** — сверка с таблицей **`documents`** (статусы **`Document.status`**) через **`lead_candidate_doc_loader.batch_candidate_document_status_sets`**; в **`list_leads`** батч по кандидатам страницы; без кандидата — **`needs_info`** (**`documents_module_no_candidate`**). UI: **`VacancyDetail`** — поля критериев.
- [x] **Геолокация отдельно от `country` (v1):** в **`lead_criteria_eval`** — **`allowed_geo_countries`** / **`blocked_geo_countries`** vs первое непустое из **`normalized.geo_country`**, **`location_country`**, **`current_country`**; причины **`missing_geo_country`**, **`geo_country_not_in_allowed`**, **`geo_country_blocked`**. **`normalizer.normalize_meta_payload`** — алиасы **`GEO_COUNTRY_ALIASES`** → **`geo_country`** (+ **`geo_country_raw`**); формат маппинга **`geo_country`**. UI: **`VacancyDetail`** (списки ISO); при сохранении вакансии **`lead_criteria_v1`** **мержится** с предыдущим **`extra`**, чтобы не затирать критерии только из API. **`i18n`**: **`app.vacancies.detail.criteria.*`**, **`app.leads.qualification.reasons.*`**.
- [x] **Safeguard авто-конверсии при fit:** см. **§2.4** пункт выше; базовый контур automatic + fit — **§2.10**.

### 2.6 Глобальный поиск и IA

- [x] **v1** единый backend **`GET /api/v1/search`** — кандидаты, компании, вакансии, **лиды**, **документы**, **счета** (**`invoice`** / **`_search_invoices_slice`** → **`list_invoices`**), **service orders** (**`_search_service_orders_slice`** → **`AdditionalServicesService.list_orders`**), **треды инбокса** (**`conversation`** / **`_search_conversations_slice`** — как **`GET /communications/threads`** по полям + **`own_company_id`**, доступ messages/email через **`assert_comm_feature_access`**); **задачи** (**`task`** / **`_search_tasks_slice`** → **`reminder_tasks.list_reminders`** + **`resolve_assignee_for_reminder_list`**, query **`assignee_scope`** = **`mine` \| `team`** как у **`GET /reminders`**); маскирование клиентского тенанта как в списке кандидатов; серверная склейка + эвристика ранжирования (**`global_search_v1.py`**, **`global_search.py`**). **Лиды:** **`_search_leads_slice`** — по тексту **`normalized` / `payload`**, id, source, stage, status, тип лида, имя **`Company`**; те же **`tenant_id` / `own_company_id`**, что у вакансий; **не** для **`client_manager` / `client_processor`**; ссылка **`/app/leads/{id}`**. **Документы:** **`_search_documents_slice`**, **`spa_candidate_documents`**. Ссылки: счета **`/app/invoices/{id}`**, заказы **`/app/orders?order_id=`**, треды **`/app/inbox/threads/{id}`** (+ query как у **`buildInboxThreadPath`**), задачи **`/app/tasks?t_q=&t_id=`** (+ **`t_assignee=team`** при team scope). Фронт: **`searchGlobal`** передаёт **`reminderAssigneeScope`** в **`GET /search`**; при успешном unified-пути не дублируются **`document`**, **`invoice`**, **`service_order`**, **`conversation`**, **`task`** (**`search.ts`**, **`listReminders`** не вызывается).
- [x] **Полнотекст (v1, PostgreSQL):** **`backend/app/services/global_search_fts.py`** — **`hostflow_simple_tsvector(concat_ws(…))`** (SQL **IMMUTABLE**-обёртка для вызовов из запросов; встроенный **`to_tsvector(regconfig, text)`** — **STABLE**) + **`websearch_to_tsquery('simple', …)`** + **`ts_rank_cd`** в **`global_search_v1`** для **`_search_leads_slice`** (JSON-only OR полный вектор + **`greatest(rank)`**), **`_search_documents_slice`**, **`_search_conversations_slice`** (дополняет ILIKE). Миграция **`202603291700_gs_fts_gin`** — **`CREATE FUNCTION hostflow_simple_tsvector`**. Миграция **`202603291800_hostflow_tsv_gin`** — физические **`tsvector`** колонки **`communication_threads.hostflow_search_tsv`**, **`leads.hostflow_lead_json_tsv`** (триггеры **`to_tsvector('simple', …)`** + backfill) и **GIN** (частичный на тредах для неархивных); в запросах **`coalesce(колонка, hostflow_simple_tsvector(…))`** до backfill и для совместимости. Миграция **`202603291900_doc_tsv_gin`** — **`documents.hostflow_document_search_tsv`** (только поля строки документа; имя/email кандидата остаются во втором векторе в **`_search_documents_slice`**, **`greatest(rank)`**); **GIN** с **`WHERE deleted_at IS NULL`**. Lifespan: **`ensure_global_search_fts_function_async`**. После склейки — мультитокенная эвристика в **`_match_quality_score`**. **Остаётся:** документы с join к кандидату; **ML / семантический поиск**.
- [x] Интеграционные тесты **`tests/api/test_global_search.py`**: валидация **`q`**, кандидат с **`own_company_id`** под активную own-company (как у списков), лид — **`test_global_search_lead_fts_matches_tokens_across_json_keys`** (мультитокен + **`normalized`** JSON), слайс **`task`** (**`assignee_scope`** mine vs team + deep link); в **`conftest`** для pytest **`COMM_SCHEDULER_ENABLED=0`** по умолчанию (без зависания lifespan). **Локальный запуск (PEP 668 / Docker URL):** **`make install`** → **`.venv`**; **`make test`**; хост **`db`** в URL БД при прогоне на машине без Docker DNS подменяется на **`127.0.0.1`** в **`conftest`**; для asyncpg без путаницы циклов — **`HOSTFLOW_SQLALCHEMY_NULL_POOL=1`** (в **`session.py`**); API-тесты с **`pytest_asyncio`**-фикстурами помечать **`@pytest.mark.asyncio`**, не **`anyio`** вперемешку с **`db`**. Не вызывать **`engine.dispose()`** из синхронного **`pytest_sessionfinish`** через **`asyncio.run`** (другой loop).
- [x] При **`scope_tenant_id`** (как у списка кандидатов): компании и вакансии в **`GET /search`** идут в том же скоупе (**`global_search_v1`**: временный контекст сессии + **`compute_tenant_visibility_for_tenant`**); запросы к сущностям выполняются **последовательно** на одной сессии (без гонок **`set_config`**). Опционально на фронте передать **`scopeTenantId`** в **`searchGlobal`** там, где списки уже шлют override.

### 2.7 Comms / Inbox

- [x] **Email / workspace command templates (каркас):** шаблоны команд и сообщений в настройках коммуникаций — **`DEFAULT_COMMUNICATIONS_SETTINGS.commands` / `messageTemplates`** в **`hostflow-frontend/src/api/communications.ts`**, схемы **`CommunicationCommandTemplate`** / **`CommunicationsCommandsSettings`** в **`backend/app/api/v1/settings/communications.py`**; UI настройки — **`CommunicationsMessengerSettingsPage`**. **Остаётся:** продуктово разметить **массовое** применение команд к выбранным письмам/тредам в unified inbox при появлении multi-select (не блокер §2.7 как «заметка UOS»).

### 2.8 Прочее / полировка

- [x] **Первичное меню по сценариям работы** (не «карта БД») — целевая IA **§2.13** — **`[x] v1 закрыт`** (см. **§2.13**); код: **`hostflow-frontend`** — **`Sidebar.tsx`** (в т.ч. **`SidebarOwnCompanySection`**), **`Topbar.tsx`**, **`WorkContextTabs.tsx`**, **`NAV_ITEMS`**, **`routes.tsx`**; канон URL — **§1.6**. Дальнейшая полировка колонок Work / единого слоя Settings — **§2.14**, **§2.17**.
- [x] **UOS / IA — stretch:** ведётся точечно с **§2.13–§2.14**; **Остаётся:** общая полировка; при необходимости **единый объект политики escalation** (vs M1/M4 в старых доках).
- [x] **R1.P0 follow-up:** при регрессиях по DnD колонок / resize таблицы кандидатов — повторный прогон сценариев нагрузки (процедурный пункт, не ежедневная задача).
- [x] **Декомпозиция `ServicesPage.tsx` (часть):** вкладка каталога вынесена в **`hostflow-frontend/src/modules/services/ServicesCatalogTab.tsx`**; импорт в **`ServicesPage.tsx`**. **Остаётся:** **`OrdersTab`**, **`OrderDetail`**, **`ServicesAnalyticsTab`** — по мере необходимости, без смены PASS.
- [x] **Performance (`pipe.md`):** формальные бюджеты под aggressive цифры — **после** договорного SLA; до тех пор действуют существующие perf keys / budgets в коде (**§1.5**, не открытый gap).

### 2.9 Публичный захват документов

- [x] **Публичный захват документов:** старый OpenCV-публичный UI **не** восстанавливать; **новый** поток (LLM/vision и т.д.) — отдельное продуктовое решение вне текущего спринта кода (**roadmap**, не регрессия).

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

- [x] **Хранение режима обработки лидов (v1):** **`leads_processing_mode_v1`** в **`meta_lead_settings`** + **`GET/PATCH`** **`/settings/leads/settings`** + stamp в **`normalized` при ingest** (см. **§2.3** «Управляемая квалификация»).
- [x] **Единый движок фита (v1):** **`backend/app/modules/leads/lead_criteria_eval.py`** — **`evaluate_lead_criteria_v1`** / **`evaluate_vacancy_for_lead`**; список лидов и ingest используют **одну** логику (раньше фит считался только в **`list_leads`**, **`process_normalized_lead`** его не вызывал). **Режимы:** **manual** и **assisted** — без автосоздания кандидата; **assisted** пишет **`normalized.lead_qualification_preview_v1`** (предложенная вакансия, **`fit_status`**, причины). **automatic** — автосоздание только при **`auto_create_enabled`** и прохождении фита; при **`no_fit` / `needs_info`** — **`needs_routing`** с **`LEAD_FIT_NO_MATCH` / `LEAD_FIT_NEEDS_INFO`**. **Порядок «несколько вакансий»** без дублирования критериев: критерии только в **`Vacancy.extra.lead_criteria_v1`**; при отсутствии маппинга ad/id — **`Tenant.settings.lead_fit_routing_v1`** = **`{ "ordered_vacancy_ids": ["uuid", …] }`**, первая вакансия с **`fit`** или **`no_criteria`**. **Остаётся по продукту:** расширение критериев (**§2.5**).
- [x] **Rule engine маршрутизации лида (v1):** триггер **`lead.qualification`** в **`automation_rules`**; колонка **`priority`** (миграция **`202603281200_ar_priority`**); оценка в **`lead_qualification_rules.pick_vacancy_via_qualification_rules`** после неудачного **`_resolve_vacancy`** и до **`ordered_vacancy_ids`**; условия — общий матчер **`_matches_conditions`** (**`source`**, **`normalized.<path>`**: скаляр/`null` как раньше, либо **`{ "op": "eq"|"neq"|"in"|"exists"|"not_exists", "value": … }`**, неявное AND по ключам, опционально **`$and`: [ … ]**); действия **`set_vacancy_id`** (обязательно) и опционально **`set_recruiter_id`**; аудит **`lead.qualification_rule_matched`**; **`run_rules`** игнорирует триггер. UI: **`AutomationRulesPage`**. **Остаётся (эпик):** **`assign_pipeline`**, слияние с **§2.11** без дублирования **`lead_criteria_eval`**.
- [x] **UI конструктора правил (v1, узкий):** **`lead.qualification`** — несколько условий по **`normalized.*`** с выбором оператора + reminders-builder. **Остаётся:** тот же богатый конструктор для остальных триггеров (risk/stage и т.д.).
- [x] **Карточка лида + inbox (v1):** компонент **`LeadQualificationSuggestionPanel`** — **`LeadDetailPage`**, боковая панель **`LeadsPage`**; превью из **`lead_qualification_preview_v1`**, ссылки на Meta settings / список вакансий, **Process** в inbox (на full-page заголовок **Process** без дубля). Человекочитаемые коды **`LEAD_FIT_*`** и колонка ошибки — **`formatLeadPipelineError`**, **`i18n`** **`app.leads.pipeline_errors.*`**, **`app.leads.qualification.*`**.
- [x] **Automatic + фит при ingest (v1):** см. «Единый движок фита»; **UI:** сообщения для **`LEAD_FIT_*`** (см. выше). **NBA (v1):** группы **`leads_fit_no_match` / `leads_fit_needs_info`** в **`GET /next-actions`**, drill-down **`GET /leads?status=needs_routing&pipeline_error=…`** (whitelist **`LEAD_FIT_NO_MATCH` / `LEAD_FIT_NEEDS_INFO`**), **`LeadsPage`** читает **`pipeline_error`** из query; **`i18n`** **`app.leads.nba.groups.leads_fit_*`**. **CTA:** **`accept_process_cta`** на **`LeadQualificationSuggestionPanel`** при **`LEAD_FIT_*`** или заблокированном превью (**`blocked_auto_convert`**); иначе **`process_cta`**.
- [x] **Админ Meta — подсказки автоматизации (v1):** **`MetaLeadsAdminPage`** — блок «как связаны настройки», режим квалификации выше чекбокса; **`auto_create_enabled`** неактивен вне **Automatic**, при сохранении не-Automatic принудительно **`auto_create_enabled: false`**; **`i18n`** **`app.admin.meta_leads.settings.auto_create_automatic_only`**, **`automation_stack_*`**.
- [x] **NBA — необработанные лиды (v1):** счётчик **`leads_new_unprocessed`** в **`GET /next-actions`**; **`POST /api/v1/leads/bulk/process-new-queue`** — Meta, **`status=new`**, до **50** за вызов, FIFO (**`created_at`** ↑), общий контур с **`POST /leads/{id}/process`** (**`bulk_auto_process_meta_lead_queue`**: аргументы **`statuses`**, **`prefer_oldest_first`**). Gating: **`plan_allows_team_tier_features`**, **`plan_requires_team`**, feature **`leads_bulk_process_new_queue`**. UI: **`bulkProcessNewMetaLeads`** + **`Process batch`** / апгрейд на чипе (**`NbaNextActionsChips`**, **`useNbaQuickBulkFlow`**, Dashboard / Leads / Topbar). **Остаётся:** расширение под **§2.10** rule engine и не-Meta источники.
- [x] **Связка с §2.5 (v1):** канон фита по-прежнему **`Vacancy.extra.lead_criteria_v1`** + **`lead_criteria_eval`**; пресет порядка вакансий — **UI + API** (см. **§2.5**); правила **`lead.qualification`** задают **целевую вакансию** до сканирования **`ordered_vacancy_ids`**, затем тот же eval фита. **Остаётся:** единый продуктовый слой «пресеты критериев на тенанта» без второго eval.

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
- [x] **Каркас Google/Webhook (v0):** в хабе **`IntegrationsHubPage`** карточки ведут на **`/app/settings/integrations/google`** и **`/webhook`**; Google — **`IntegrationsSourcePlaceholderPage`**. **Webhook (v1 ingest):** **`IntegrationsWebhookPage`** — ротация секрета **`POST /api/v1/settings/leads/inbound-webhook/rotate`** (admin, Team+); публичный приём **`POST /api/v1/public/leads/inbound/{secret}`** → **`process_generic_inbound_webhook_lead`** (**`service.py`**) + **`coerce_generic_json_to_meta_normalizer_payload`** (**`normalizer.py`**); тот же **`field_mapping`**, **`source=webhook`**. Колонка **`meta_lead_settings.generic_inbound_webhook_secret`**, миграция **`202603271300_generic_inbound_wh`**, опционально **`PUBLIC_API_BASE_URL`** для полного URL после rotate. **Incoming preview (webhook):** **`GET /settings/leads/meta/incoming-preview?source=webhook`** (**`list_meta_incoming_preview`**); UI — переключатель Meta/Webhook на вкладке **Incoming** **`MetaLeadsAdminPage`**, deep-link **`?tab=incoming&incoming_source=webhook`**, блок на **`IntegrationsWebhookPage`**. **Остаётся:** Google ingest; отдельный mapping UI не-Meta.
- [x] **Автоподсказки маппинга шире (v1.1):** на **`MetaLeadsAdminPage`** (вкладка **Field mapping**) — source datalist дополняется ключами с объекта **`value`** кроме **`field_data`** (включая один уровень **`parent.child`**), вложенными dot-path из превью **normalized** (глубина ограничена), значениями **`raw_field_names`**; target datalist — пресеты + типовые ключи (**`utm.*`**, Meta ids, **`assignment_lock_v1.*`**) + активные ключи LEAD custom fields + уже введённые targets в таблице.  
- [x] **Paywall (v1) по строкам field_mapping и «слоту» Meta credential:** планы **`solo` / `starter` / `trial` / `free`** — не более **25** правил в **`meta_lead_settings.field_mapping`** и не более **1** записи Meta credential; проверки **`ensure_meta_lead_field_mapping_rows_allowed`** / **`ensure_meta_lead_credential_create_allowed`** в **`plan_feature_gates.py`**, вызов из **`admin_service.update_settings`** / **`create_credential`**; в **`GET/PATCH /settings/leads/settings`** в ответе — **`plan_field_mapping_rules_limit`**, **`plan_meta_credentials_limit`**; UI + i18n на **`MetaLeadsAdminPage`**. **Остаётся:** лимиты при **нескольких реальных источниках** (Google/Webhook ingest), **трансформации** mapping; биллинг/апгрейд-копирайт в продуктовом виде.  
- [x] **Custom fields для лидов (v1):** расширены **`CustomFieldScope.LEAD`** и **`CustomFieldEntityType.LEAD`** (`custom_field.py`); CRUD через существующий **`GET/POST/PATCH /api/v1/custom-fields/definitions`** и values с **`entity_type=lead`**; UI — область **Лид** на **`CustomFieldsPage`**. При ingest **`process_normalized_lead`** синхронизирует значения из **`normalized`** по ключу определения (путь с точками = вложенность) в **`custom_field_values`**; **`LeadOut`** / список лидов отдают **`custom_fields: { key → value }`**. **Фильтр списка (v1):** **`GET /leads?custom_field_key=…&custom_field_value=…`** — точное совпадение со stored **`{"v": …}`** (строка из query); неизвестный ключ → **422**; UI на **`LeadsPage`** при наличии активных LEAD-определений. **Текстовый поиск списка (v1):** **`GET /leads?q=…`** (после trim ≥ **2** символов) — подстрока без учёта регистра по **`normalized` / `payload`**, id, source, stage, status, **`lead_type`**, имени связанной **`Company`** (как **`global_search_v1._search_leads_slice`**); **`count`** с **`outerjoin(Company)`** при активном поиске; UI — поле на **`LeadsPage`**, синхронизация **`?q=`** в URL. **Остаётся:** отдельная колонка **`Lead.extra`**; расширенные операторы фильтра (числа, bool, отдельные поля).  
- [x] **Автоподсказки маппинга + действие «неизвестное поле → создать custom field» (v1):** панель на **`MetaLeadsAdminPage`** (вкладка **Field mapping**), **`createCustomFieldDefinition`** + опциональная строка маппинга.  
- [x] **Rule engine — контекст лидов (v0):** при **`lead.processed`** и **`lead.pipeline.stage_changed`** в контекст автоправил добавляются вложенные **`normalized`** и **`custom_fields`** (`automation_context_for_lead` в **`lead_custom_fields.py`**), условия JSON-правил могут ссылаться по dot-path (**`custom_fields.my_key`**, **`normalized.email`** и т.д.). **Остаётся:** полноценный typed-слой и UI правил поверх **§2.10**.  
- [x] **Карточка лида (v1):** на **`LeadDetailPage`** секция **Source + mapped (custom_fields) + normalized/payload JSON** (раскрывающиеся блоки). **Связка с Assisted / §2.4:** коллаут **`LeadIngestProcessingCallout`** в **Source & ingest** по стампам **`normalized.leads_processing_mode_*`**, **`leads_auto_convert_on_fit_effective_v1`**, **`leads_processing_mode_downgrade_v1`** + **`i18n`** **`app.leads.detail.ingest_processing.*`**.  
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

Вертикальная / ступенчатая воронка: этап → count → % перехода вниз; сразу видно **узкое место**. **В продукте (актуально):** тот же UI — компонент **`AnalyticsLeadConversionFunnelPage`** в составе **`/app/overview`** (якорь **`#lead-conversion`**), а не отдельная страница-хаб **`/app/analytics`**.

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
- **Частично (лиды, v1 roots):** **`GET /api/v1/leads/conversion-funnel`** — агрегаты по корневым этапам **§2.12** (**`lead → qualified → active → final`**): эффективный корень = **`funnel_stages.conversion_root_v1`** (воронка **`type=lead`**) + legacy-маппинг CRM-кодов **`new/contacted/qualified/converted`**; ответ **`aggregation_mode: conversion_roots`**; отдельно **`lost`**, **`status=new`**, **`progressed_share`**, **dwell** (по CRM-стадии, сгруппировано по корню); **`GET /leads?conversion_root=…`** для drill-down; UI **`LeadsPage`** + настройка маппинга на **`FunnelsPage`** (вкладка лидов). **Срезы TEAM+** и drill-down потерь как раньше.  
- **Есть (лиды, потери):** **`PATCH /leads/{id}`** / **`PATCH /leads/bulk`** при **`stage=lost`** — **`lost_reason_*`**, **`normalized.lead_lost_reason_v1`**, модалки и read-only в инбоксе / **`LeadDetailPage`**; **`lost_from_stage`** / **`lost_reason_breakdown`** в **`conversion-funnel`**.  
- **Частично:** **Suggested actions** с воронки в **NBA (v0):** на чипах **`leads_funnel_weak_step` / `leads_funnel_slow_stage`** кнопка **Do now** → bulk follow-up по первым лидам из того же фильтра, что drill-down (**`listLeads`** + **`useNbaQuickBulkFlow`**, **`NBA_QUICK_REMINDER_GROUP_IDS`**). **Поверхность чипов:** прежде всего **топбар** (**`TopbarNbaMenu`**); на **Dashboard** отдельный блок NBA **не дублируется** (избегаем второго «толкания» сценариев на обзоре). **Экран воронки (v1):** **`AnalyticsLeadConversionFunnelPage`** на **`/app/overview`** (встроенный блок, **`#lead-conversion`**) — **Suggested focus** + блок **«Контур управления»** (ссылки **`FunnelsPage`**, **`/app/automation-rules`**, лиды, обзор) + пресеты очередей **lost** (**`no_response` / `not_qualified` / `budget`**). **Drill-down (v0–v1):** **`lost_reason_code`**, **`lost_from_crm_stage`**, **`conversion_root`** — см. **`_build_lead_list_filters`**, **`LeadConversionFunnelPanel`**. **Эпик «инструмент управления» v1** — **`[x]`** в **§2.3** (~стр. 83). **Дальше (stretch):** **`§2.12 stretch`** — когорты, WoW, канбан, тяжёлые шаблоны; единый экран с кандидатами.

#### Бэклог (внедрение)

- [x] **Модель данных `funnel_stage_mapping` (v1):** **`funnel_stages.conversion_root_v1`** — корни **`lead` | `qualified` | `active` | `final`** для воронок **`type=lead`**; миграция **`202603270000_conv_root`** + backfill по кодам CRM; API воронок + **`GET /leads/conversion-funnel`** ( **`aggregation_mode: conversion_roots`** ) + **`GET /leads?conversion_root=`**; UI **`FunnelsPage`** (лиды) / **`LeadsPage`**. **Остаётся:** отдельный продуктовый слой **`lost_reason`** в «root funnel» (сейчас потери — через CRM **`lost`** и аудит).  
- [x] **API агрегатов воронки (v0, лиды):** **`GET /leads/conversion-funnel`** — counts, **`at_or_beyond`**, **`progressed_share`**, **dwell**, **`lost_from_stage`**, **`lost_reason_breakdown`**. **Дальше:** cohort-based conversion, единый экран с кандидатами.  
- [x] Экран **«Conversion funnel»** — **`AnalyticsLeadConversionFunnelPage`** на **`/app/overview`** (якорь **`#lead-conversion`**; **`/app/analytics/lead-conversion`** редиректит) + drill-down в лиды (**`conversion_root`**) и блоки потерь как на **`LeadsPage`**; MVP-полоса на **`LeadsPage`** (**§2.12** v0). **Дальше:** NBA / cohorts / paywall по срезам (**ниже**).  
- [x] **Срезы TEAM+ (v0, лиды):** query **`source`**, **`vacancy_id`**, **`funnel_id`**, **`assignee_user_id`** (recruiter связанного кандидата) на **`GET /leads/conversion-funnel`**; **403** `plan_requires_team` / **`leads_conversion_funnel_slices`**; эхо в ответе **`filter_*`**; UI на **`LeadsPage`**. **Дальше:** срез по **`pipeline_id`** в смысле кандидатского pipeline (если отделим от **`funnel_id`** лида), paywall-копирайт в биллинге, согласованность с глобальным «экраном конверсии».  
- [x] **Инсайты воронки + мост в NBA (v0):** детерминированные сигналы в **`GET /next-actions`** — **`leads_funnel_weak_step`** (низкий **`progressed_share`** при достаточном объёме) и **`leads_funnel_slow_stage`** (высокий **dwell** при достаточной выборке); drill-down **`GET /leads?status=processed&conversion_root=`**; UI чипов — **`NbaNextActionsChips`** в **топбаре** (**`TopbarNbaMenu`**) и в контекстных экранах (например workspace лидов при bulk), **не** отдельным блоком на **Dashboard**. **Дальше:** пороги как настройки тенанта, сравнение с прошлой неделей; расширенные сценарные **Suggested actions** (документы/портал) — см. пункт ниже. **Paywall инсайтов** — пункт ниже.  
- [x] **Paywall по сложности срезов и инсайтов:** срезы **`GET /leads/conversion-funnel`** — **`plan_requires_team`** / **`leads_conversion_funnel_slices`** (уже было); **инсайты NBA** (**`leads_funnel_weak_step`**, **`leads_funnel_slow_stage`**) — **`locked` + `required_plan=team`** на планах **`solo` / `starter` / `trial` / `free`** (**`nba_conversion_funnel_insight_groups`** в **`service.py`**); чипы ведут в биллинг. Компонент **`DashboardNbaSection`** в коде сохранён для переиспользования логики, **на обзор не монтируется** — NBA с обзора убрана намеренно (см. **§2.13**).  
- [x] **Suggested actions (v0) с воронки в NBA:** **Do now** на чипах **`leads_funnel_weak_step`**, **`leads_funnel_slow_stage`** — **`POST /activities/bulk`** через **`useNbaQuickBulkFlow`** по **`listLeads`** с **`status` + `conversion_root`** из **`NextActionQueryParams`** (как drill-down списка лидов). Код: **`nbaQuickConstants.ts`**, **`useNbaQuickBulkFlow.ts`**. **Дальше:** шаблоны под документы/портал, когорты.
- [x] **Drill-down по `lost_reason` (v0):** **`GET /leads?lost_reason_code=`** + **`NextActionQueryParams.lost_reason_code`** / **`leadsNextActionHref`**; **`LeadsPage`** читает **`?lost_reason_code=`**; **`lost_reason_breakdown`** → список (кроме **`unknown`**). **Дальше:** шаблоны действий по коду причины.
- [x] **Drill-down по `lost_from_stage` (v0):** **`GET /leads?lost_from_crm_stage=`** ( **`unknown` | `[a-z0-9_-]{1,32}`** ) + **`NextActionQueryParams.lost_from_crm_stage`**; **`LeadsPage`** + **`LeadConversionFunnelPanel`**. **Дальше:** сценарные действия по сочетанию prior stage + reason.
- [x] **Замыкание цепочки управления на экране воронки (v0):** **`AnalyticsLeadConversionFunnelPage`** — **`management_chain_*`** в **`i18n`**: пайплайны (**`CRM_APP_PATHS.settingsFunnels`**), правила (**`automationRules`**), workspace лидов, NBA; подсказка про **`lead.pipeline.stage_changed`**; быстрые ссылки на списки **lost** с **`lost_reason_code`** (типовые коды). **Дальше:** §2.12 stretch.

### 2.13 Меню и IA: сценарии для оператора (не архитектура продукта)

**Статус (v1):** **`[x] Закрыт (март 2026)`** — целевая IA §2.13.0 реализована в оболочке и перечисленных экранах; оставшаяся «глубина» (колонки Work, единый продуктовый слой настроек) ведётся в **§2.14**, **§2.17**, а не как продолжение открытого §2.13.

#### 2.13.0 Финальное ТЗ (операторская IA, март 2026)

**Базовая модель:** HostFlow = управление потоком кандидатов и действий; навигация минимальна, фокус на «что делать», а не на поиске разделов.

**Top bar (цель):** поиск, создать, открыть меню (сайдбар), уведомления, профиль — **без** отдельной шестерёнки настроек и **без** топбар-**NBA** («Действия N+»); **настройки** — одна строка **«Настройки системы»** в меню профиля (переход на **`/app/settings`**). **Реализовано в коде:** `Topbar.tsx` (NBA и gear убраны; гамбургер перенесён вправо после поиска/создать).

**Горизонтальная полоса (критично):** глобальный **sticky** ряд под top bar на операционных маршрутах: **Работа · Кандидаты · Клиенты · Вакансии · Документы · Лиды · Заказы · Счета** (права и модули как в `usePermissions`). **Не** показывается на дашборде, Inbox, задачах, календаре, процессинге, аналитике, автоматизациях, интеграциях, настройках. **Код:** `WorkContextTabs.tsx`.

**Левый рейл (цель):** дашборд (**Insights** / **`/app/overview`**, без отдельного соседа «Аналитика») → **Работа** (хаб) → входящие → разделитель → кандидаты, клиенты, вакансии, лиды → задачи/календарь → процессинг → **команда** (availability / пользователи по правам) → финансы (заказы, счета, услуги) → документы → автоматизации → интеграции. **Код:** `Sidebar.tsx`; в **`NAV_ITEMS`** добавлены **`team-availability`**, **`my-availability`**, **`time-off`** для сайдбара.

**Страница «Работа»:** не каталог карточек, а **операционный экран** — блоки «сейчас», очередь, процессинг (ссылка на handoff), команда, быстрые действия; метрики из **`GET /analytics/ops-counters`** где возможно. **Код:** `WorkHubPage.tsx`.

**Сделано по плану полировки v1:** узкий work rail кандидатов (persist **`hf:candidates:workRailShell:v1`**), быстрый ряд фильтров (этап / менеджер / вакансия) на **`Candidates`**, первичный поток задач (**`RemindersPage`**: композер по умолчанию свёрнут, кнопка «Создать задачу», фильтр «Только просроченные», entity/priority в «Ещё фильтры», режим SLA в `<details>`), календарь коммуникаций: источник по умолчанию **все**, тяжёлые фильтры и day-batch в **`<details>`**, ключ UI **`hf:calendar:ui:v2`**; в сайдбаре рейл **Интеграций** без дублирующих пунктов коммуникаций (детали — из хаба интеграций); компактный workspace + ссылка «+» в настройки. **Онлайн/нагрузка команды** — отдельные экраны team availability (глубже первичного меню).

**Принцип:** в левом меню — **что пользователь делает**, а не перечень сущностей как в схеме БД. Разделение: **состояния системы** (SLA, без next action, барьеры, риски) ≠ **пункты навигации** — они живут на **Dashboard / Insights (`/app/overview`, виджеты и срезы)**, в **NBA (API и точечные сценарии, не обязательно топбар)**, в **единой панели уведомлений** (топбар), на **Work hub**, через **deep links**, не как отдельные top-level ссылки в сайдбаре. **Own company** — в сайдбаре (`SidebarOwnCompanySection`).

#### Целевая структура первичного меню (6 пунктов primary)

| # | Раздел | Содержание (сценарий) |
|---|--------|------------------------|
| **1** | **Dashboard / Insights** | Единая страница **`/app/overview`**: сигналы, операционные риски, виджеты, **срезы по кандидатам** (даты, фирмы, вакансии, менеджеры, этапы, опционально **кандидат по UUID**), сохранённые пресеты и скрытие секций (localStorage, ключи с привязкой к пользователю); **воронка лидов §2.12** — встроенный блок **`AnalyticsLeadConversionFunnelPage`** (якорь **`#lead-conversion`**). Отдельного пункта меню **«Аналитика»** нет (**`NAV_ITEMS.analytics`** удалён). **NBA** — в API / сценарных точках; **постоянная кнопка NBA в топбаре убрана** (ТЗ §2.13.0); без дубля большого блока NBA только ради обзора |
| **2** | **Inbox** | Единый центр входящего: сообщения, почта, хаб коммуникаций (**§2.7** / текущий **`/app/inbox`**) |
| **3** | **Work** | Основная работа с процессом: кандидаты, клиенты, лиды, вакансии, заказы, процессинг — **вкладки или подраздел**, не обязательно 6 отдельных top-level пунктов |
| **4** | **Tasks** | Исполнение: задачи + календарь |
| **5** | **Finance** | Опционально по сегменту: счета, доп. услуги (**services** tenant и т.д.) |
| **6** | **Settings** | Всё админское: пользователи, роли, воронки, документы, интеграции, коммуникации, биллинг, юридическое — **внутри** сгруппировано. **Точка входа в продукте:** меню профиля → **«Настройки системы»** → **`/app/settings`** (прогрессивные **`?section=`** внутри). Подписка, usage, team, workspace, роли — **§2.17**. |

**Закладки и deep links:** **`/app/analytics`** → редирект на **`/app/overview`** (**`manager.tools`**); **`/app/analytics/lead-conversion`** → **`/app/overview#lead-conversion`** (**`manager.tools`** + **`leads.view`**). Код: **`routes.tsx`** (`RedirectLegacyAnalyticsToInsights`, `RedirectLeadConversionFunnelToInsights`), прокрутка к якорю в **`Dashboard.tsx`**.

Детальный layout и логика **Work** и **Dashboard** (проблемы → действия → результат, NBA, paywall) — **§2.14**. **Billing & Subscription, Team, Companies, Platform Admin** — **§2.17**.

#### Что убрать из левого меню как отдельные пункты

- **SLA**, **без следующего действия**, **барьеры**, **риски** — только как входы с Dashboard / Work hub / панели уведомлений / deep links / NBA (топбар), не как соседи «Кандидаты» в списке модулей.

#### Вложенность и вторичный уровень

- **Work:** например вкладки Pipeline (default) · Candidates · Clients · Leads · Vacancies — один контекст «работа», переключение без смены ментальной модели «я в другом приложении».  
- **Внутри сущности** (карточка кандидата): документы, сообщения, задачи — **рейл / вкладки**, не глобальные разделы.

#### Динамическое меню

- **SOLO:** скрыть **Finance**, упростить блоки team;  
- **Services / employer / agency:** включать **Finance**, **Orders/Services** в **Work** или **Finance** по продуктовому решению;  
- Увязать с **`business_type`**, **`TenantLicense`**, флагами модулей.

#### Анти-паттерны

- Меню = «всё, что умеет система»; нет связи с **«что делать сейчас»** (это **Work hub** + обзор с виджетами + уведомления / сценарные deep links).

#### Реализация (канон)

- **Плейсмент UI (актуально под §2.13.0):**
  - **NBA:** **`TopbarNbaMenu`** **не рендерится**; **`DashboardNbaSection`** на обзоре **не рендерится**. Сценарные очереди — через уведомления, deep links, **`GET /next-actions`** в точечных UI.
  - **Настройки:** только **меню профиля** → **«Настройки системы»** → **`CRM_APP_PATHS.settings`** (внутри progressive **`?section=`**); в левом рейле рельсы **Automations** / **Integrations** по **`NAV_ITEMS`** / **`Sidebar.tsx`**.
  - **Own company (юрлицо workspace):** **`SidebarOwnCompanySection`** + **`useOwnCompanyWorkspace`** — под заголовком workspace в **`Sidebar.tsx`**, не в топбаре.
  - **Уведомления:** один колокольчик в **`Topbar.tsx`**: непрочитанные API-уведомления + непрочитанные треды коммуникаций (без отдельных иконок почты/сообщений в шапке).
  - **Топбар:** слева **логотип HostFlow** (`/logo_hf.svg`, ссылка на **`/app/work`**); справа **поиск**, **создать**, **гамбургер** (сайдбар), **колокольчик**, **профиль**. Дублирующий чип own company в шапках списков **не показывается**.
  - **Глобальная горизонтальная полоса:** **`WorkContextTabs.tsx`** — см. §2.13.0.
  - **Аналитика и воронка лидов:** не отдельный хаб. **`/app/overview`** — **`Dashboard.tsx`**: сворачиваемые секции (**`DashboardSectionCollapsible`**), быстрые ссылки (**`DashboardAnalyticsHubLinks`** при правах), воронка — **`AnalyticsLeadConversionFunnelPage`** с **`embedded`**, якорь **`#lead-conversion`**. **`/app/analytics`** и **`/app/analytics/lead-conversion`** — редиректы (**`routes.tsx`**), закладки не ломаются.
  - **`LeadsPage`:** компактная **`LeadConversionFunnelPanel`**; чипы **`NbaNextActionsChips`** и полоса **stage health** в шапке **убраны**; ссылка на вертикальную воронку ведёт на **`/app/overview#lead-conversion`** (секция обзора, не отдельный маршрут).
  - **Dashboard:** полоска быстрых ссылок «Work / Analytics» **не** восстанавливается как дубль отдельного хаба; операционные shortcut’ы — внутри collapsible на обзоре.

- **Навигация и оболочка:** левое меню (**`Sidebar.tsx`**) — порядок **§2.13.0** (дашборд → хаб **Работа** → входящие → сущности → задачи → процессинг → **команда** → финансы → документы → автоматизации → интеграции). Хаб **`/app/work`** — **`WorkHubPage`** (операционный экран, **`ops-counters`**). **`WorkContextTabs`** — глобальная полоса на перечисленных операционных путях. **`no-next-action`** и **`sla-incidents`** скрыты из сайдбара (**`SIDEBAR_HIDDEN_ITEM_KEYS`**). **Work shell:** **`WorkAreaLayout`** + **`<Outlet />`**; алиасы **`/app/work/...`** → канон (**`WorkPathAliasRedirect`**, **`nav/workShellAlias.ts`**).

#### Прогресс по v1 (чеклист закрытия)

- [x] Сценарное дерево в **`NAV_ITEMS`** / **`Sidebar`** без потери deep links и правил доступа (итерации возможны).  
- [x] **SLA / no-next-action** убраны из primary nav сайдбара; входы через дашборд, Work hub, уведомления, Inbox (топбар-NBA убран по ТЗ §2.13.0).  
- [x] **Work** v1: хаб **`/app/work`** + контекстные вкладки **`WorkContextTabs`** + вложенные маршруты (**`WorkAreaLayout`**). Полное встраивание состояний в **колонки** pipeline — **§2.14**.  
- [x] **Кандидаты:** быстрые фильтры + узкий work rail (**`useCandidatesWorkPanel`**, константы ширины).  
- [x] **Задачи / календарь:** упрощение **`RemindersPage`** и **`CommunicationsCalendarPage`** (см. абзац «Сделано по плану» выше).  
- [x] **Интеграции:** рейл без дублей коммуникаций; **workspace** компактно + **+** → настройки.  
- [x] **Динамический Finance** в сайдбаре по плану и **`business_type`** (**`financeNavVisibility.ts`**). Расширение team-разделов (availability и т.д.) — вне v1 §2.13 или **§2.17**.  
- [x] **i18n** для затронутых строк (en / pl / ru).  
- [x] **Settings (v0 каркас):** единая оболочка настроек (**`SettingsChrome`**, progressive **`?section=`**), разделы Billing / Team / Users / Integrations и др. по **`routes.tsx`** / **`NAV_ITEMS`**. **Остаётся (целевой §2.17):** один продуктовый слой «Account → Workspaces → Seats → Roles → Subscription» без дрейфа IA (**§2.17** п.1–12).

#### Следующий фокус (после §2.13 v1)

- **§2.14** — **`[x]` закрыт (март 2026)**; итерации Work/Dashboard — по «Остаётся» внутри §2.14 и **§2.3 / §2.16**.  
- **§2.17** — подписка, usage, workspaces, роли, единая IA настроек.

### 2.14 Work и Dashboard: одна модель — проблемы → действия → результат

**Статус (v1):** **`[x] Закрыт (март 2026)`** — чеклист «Бэклог (внедрение)» ниже полностью отмечен; отдельные «Остаётся» в строках — дорожная карта **§2.3 / §2.16 / stretch**, не открытый gap §2.14.

**Связь с §2.13:** первичное меню и оболочка (v1) **закрыты в §2.13**; этот раздел — **как** наполнять **Work** и **Dashboard** смыслом (колонки, рейл сущности, виджеты), без расширения списка top-level разделов.

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

- ❌ Отдельные «экраны проблем» вне контекста списка — состояния **в pipeline / таблице / рейле** и на Dashboard (**виджеты / drill-down**). Очередь **без следующего действия** у кандидатов — **на основном списке** **`Candidates`** (**`?queue=no_next_action`**), не отдельный продуктовый экран.

**Связка с автоматизацией и монетизацией**

- В заголовке колонки или агрегате: **`⚠ 3 candidates need action`** + **`[ Fix automatically ]`** — кнопка = **апселл** (см. ниже paywall).

**Массовые действия (обязательно)**

- После multi-select: **`[ Contact all ]`**, **`[ Request docs ]`**, **`[ Assign automatically ]`** — ощущение «система ускоряет», не только по одному.

---

#### Dashboard (продаёт ценность и апгрейд)

**Цель:** не «показать данные», а **заставить действовать** и **апгрейдиться**. Минимум «аналитической свалки».

**NBA (Next Best Actions) — где живёт в продукте**

- Тот же сценарный слой (**§2.3**), что и «верх обзора» в этой таблице: список/чипы с **одной главной кнопкой** на действие (Contact all, Auto-assign, Send request и т.д.). **После §2.13.0** постоянная кнопка **`TopbarNbaMenu`** **убрана**; сценарные входы — **уведомления**, **Work hub**, **виджеты обзора**, контекстные экраны. На **Dashboard** остаются **виджеты проблем / ops / auto-fix** и ссылки-дрельдауны.
- Агрессивный главный CTA-уровень: например **«Fix your process in 1 click»** + **`[ Fix all automatically ]`** — **главный paywall-якорь** (не страница Pricing) — в том числе через **NBA в топбаре** и заблокированные действия на чипах.

**Встроенный апселл по плану**

- **SOLO:** текст уровня *You have N issues* → **Upgrade to:** auto-fix, auto-assign, reminders → **`🔒 Upgrade required`** на заблокированных действиях.  
- **TEAM+:** те же действия доступны или частично; границы по **`TenantLicense`** / продуктовым флагам.

**Минимальный набор блоков (не раздувать)**

1. **Next actions** (NBA) — в продукте доступны из **топбара**; на самой странице обзора не обязательны как второй полноэкранный блок.  
2. **Problems** — краткая сводка: без next action, stuck > N ч, unassigned и т.п.  
3. **Funnel** — компактно (например `100 → 60 → 30 → 12`), связка с **§2.12**; детальная воронка лидов — на **`/app/overview`** (секция **`#lead-conversion`**, **`leads.view`** + инструменты менеджера как в **`routes.tsx`**).  
4. **Insights** — 1–2 детерминированных инсайта (conversion dropped, reason: slow response).

**Анти-паттерны Dashboard**

- ❌ Десяток графиков и полноэкранные таблицы — это не целевой **entry screen**.

---

#### Связка Dashboard ↔ Work

- Клик по NBA / проблеме (например **Contact 5 candidates**) → открывает **Work** с **уже применённым фильтром** (тот же контекст: overdue, стадия, тип сущности).

**Частично в коде:** на **`/app/overview`** (продуктово **Insights**) после онбординга — **без** полноэкранного блока **NBA** как единственного фокуса (**§2.13.0**; компонент **`DashboardNbaSection`** в коде сохранён для переиспользования). Карточка **Meta auto-fix** (**`components/dashboard/DashboardLeadAutoFixCard.tsx`**) при очереди **needs_routing / failed** (по **`leads.view`**; ссылка «открыть список» через **`CRM_APP_DRILLDOWN_HREFS.leadsNeedsRouting`**). Компактная полоса **Signals** (**`Dashboard.tsx`**, **`app.dashboard.insights_strip`**) — ссылка на **`#lead-conversion`** на той же странице (или **`/app/overview#lead-conversion`**), drill-down в документы при агрегатах документов, краткий текст по «медленной» стадии из **`stageVelocityRows`**. Быстрые операционные ссылки (**Work**, SLA, TTV и т.д.) — collapsible **`DashboardAnalyticsHubLinks`** на обзоре, а не отдельный хаб **`/app/analytics`** (**`AnalyticsHubPage`** удалён). Операционные виджеты дашборда ведут в лиды с **`status` / `next_action`**, кандидатов без next action — **`/app/candidates?queue=no_next_action`** (тот же экран **`Candidates`**, данные через **`GET /candidates/no-next-action`**; legacy **`/app/candidates/no-next-action`** → редирект с query; в реестре **`candidatesNoNextAction`**, канонический query — **`CANDIDATES_QUICK_VIEW_NAV_PATHS`** / **`CRM_APP_DRILLDOWN_HREFS.candidatesQueueNoNextAction`**), **задачи** — **`/app/tasks`** с **`tab`**, **`t_due_bucket=overdue`**, **`t_entity=lead`** и др. (**`RemindersPage`**; legacy **`type=leads_no_next_action`** читается и вычищается из URL), счета с **`queue=overdue_unpaid`** при просрочке, открытые заказы — **`/app/orders?status=open`**, вакансии **`?status=open`** (**`VacancyList`**). **Канон** URL и drilldown — **`hostflow-frontend/src/app/crmAppPaths.ts`** (**§1.6**): **`CRM_APP_PATHS`**, **`CRM_APP_DRILLDOWN_HREFS`**; quick-view очереди кандидатов — **`CANDIDATES_QUICK_VIEW_NAV_PATHS`** (**`modules/candidates/constants.ts`**). Эти же значения используются в Work shell (**`WorkHubPage`**, **`WorkContextTabs`**, **`CandidatesListGate`**, **`agencyClients`** / **`clientsDirectory`**, **`invoiceNew`**, редирект заказов → **`services`**) и в ссылках дашборда / сущностей. **Work / Pipeline:** переключатель **Table / Pipeline** — **`Candidates`** + **`?view=kanban`** → **`Pipeline.tsx`**; **health-бейджи** в заголовках колонок (незавершённые документы по **`pickMiniFields`**, счётчик **new** по CRM-коду стадии) — **`summarizePipelineColumnHealth`** в **`modules/pipeline/utils.ts`**; на карточке pipeline и под именем в **таблице** кандидатов — **Call** / **Email** / **Open** / **Tasks** (`tel:` / `mailto:` / маршрут кандидата / **`/app/tasks`** с **`t_entity=candidate`** и **`t_q`**, при праве **`notifications.view`**).

---

#### Где рождается апгрейд

- Не в первую очередь в **Pricing**.  
- В потоке: **`[ Fix automatically ]` / `[ Assign automatically ]`** → **`🔒 Upgrade required`** + короткое объяснение ценности.

---

#### Жёсткий вывод

- **Work:** процесс + действия, минимум экранов, максимум контекста в колонках и рейле.  
- **Dashboard:** проблемы + решения, агрессивный CTA, встроенный апселл; система **ведёт** пользователя.

#### Бэклог (внедрение)

- [x] **Work (частично v0):** переключатель **Pipeline / Table** — **`Candidates`** + **`Pipeline`** при **`?view=kanban`**; **health-бейджи** колонок (**документы / new**, клиентская агрегация). **Остаётся:** stuck / SLA и **need next action** из одной модели с NBA/API; единый **`WorkAreaLayout`**-shell с общими фильтрами сверху (если продуктово отделим от текущих экранов).  
- [x] **Work (частично v1):** inline-действия на карточках **`Pipeline`** и в ячейке **«Имя»** таблицы **`Candidates`** — **Call** (`tel:`), **Email** (`mailto:`), **Open**, **Tasks** (`/app/tasks` + `t_entity=candidate` + `t_q`, при **`notifications.view`**); для **masked** — только **Open** / **Tasks**. **Остаётся:** итерации **`CandidatesWorkPanel`**; опционально отдельная колонка «Действия», если **имя** выключено в layout.  
- [x] **Work (частично):** bulk toolbar на **`Pipeline`** + массовые модалки в **`Candidates`**; **согласование с NBA** — дальше (**§2.3**).  
- [x] **Dashboard (частично v0):** **`DashboardLeadAutoFixCard`** + блок **ops** + полоса **Signals** (воронка / документы / медленная стадия); полноэкранный NBA на обзоре **не** целевой (**§2.13**). **Остаётся:** агрессивный главный CTA «fix in one click» + paywall-копирайт.  
- [x] **Deep link:** query/state из Dashboard → Work (фильтр, выбор pipeline) — лиды / счета / кандидаты (**`queue=no_next_action`** на **`/app/candidates`** = основной список + **`useCandidatesTableData`**) / заказы (**`status=open`**) / задачи (**`t_*`** на **`/app/tasks`**). **Остаётся (stretch):** единый shell фильтров сверху для всех вкладок Work; полная согласованность kanban с произвольными очередями API.  
- [x] **Paywall (частично v0):** общий хук **`useTeamTierFeatures`**; **`billingSubscriptionCache`** — **`getBillingSubscriptionCached`** (TTL 2 мин, дедуп параллельных запросов), **`primeBillingSubscriptionCache`** + событие **`hf:billing-subscription-updated`** после мутаций на **`BillingWorkspacePage`**, сброс при **`logout`** и смене **`me.tenant_id`** (**`AppShell`**); баннер **`WorkHubPage`** + подсказка bulk **`Pipeline`**. **Остаётся:** paywall при «auto-assign» в таблице кандидатов; выравнивание копирайта с **§2.16**.

**Статус чеклиста §2.14 (внедрение):** все пункты **`[x]`**; открытые формулировки «Остаётся» внутри строк — **stretch / §2.3 / §2.16**, не блокер закрытия раздела.

**Следующий продуктовый слой (§2.14 → §2.15+):** paywall-точки и полировка **Work**; затем бэклог **§2.15** (client portal home / handoff), параллельно **§2.16–§2.18** по чеклистам в тех разделах.

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
| **Per-client** | Включённые слоты и цена за доп. клиента — **§2.16** (**Team €7** / **Business €5** per доп. аккаунт; bundle **+5 за €20** — опция, см. **«Решения по политике»** в **§2.16**) |

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

- [x] Клиентский **home**: **`GET /api/v1/public/client-portal`** — блок **`summary`** (pending / in progress), **`activity`**, затем список кандидатов (не CRM-таблица); UI **`ClientPortalPage`**.  
- [x] Упрощённый список + карточка кандидата с CTA **Accept** / **Reject** / **Request clarification** — **`POST .../handoffs/{id}/accept`**, **`reject`**, **`request-clarification`** (токен в query); клиент **`tenantLinks.ts`**.  
- [x] Модель **handoff** на портале: в ответе **`handoff`**: `presented_by` (имя рекрутера или generic), `requested_at`, `waiting_hours`; сервис **`accept_handoff` / `reject_handoff` / `return_handoff`** допускают **`reviewed_by_user_id=None`** для действий по публичной ссылке.  
- [x] **Чат рекрутер ↔ клиент (политика v1):** **не** отдельный продуктовый чат; использовать **текущий слой Comms** (единый контур **§2.7**). **Остаётся:** довести UX/маршрутизацию портала до потоков Comms.  
- [x] Уведомления + deep link **Open portal**; NBA **Remind client** — **Канон v1:** **обязателен email**; in-app у агентства — как дополнение. **Остаётся:** шаблоны писем, доставляемость, чип NBA.  
- [x] RBAC / scope на портале: доступ только по **`portal_token`** и скоупу **`TenantLink`**; PII — **`see_reduced_profiles`**. **Остаётся:** матрица ролей клиентского портала и скрытие internal notes как отдельный слой.  
- [x] Тарифы: выпуск ссылки портала — **`ensure_portal_token_issue_allowed`** (**§2.2** / **`TenantLicense.max_public_portal_links`**). **Остаётся:** branded / per-client billing — **§2.16**.

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

**Принцип:** порталы нельзя воспринимать как «бесплатное приложение к CRM» — только через **планы + лимиты + оверейдж/апгрейд** (**§2.15**).

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

См. **`business_type`**, **§2.13**.

#### Меню по планам (связь с §2.13)

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

- Paywall и CTA в приложении (**§2.14**) и **§2.15** (портал) должны ссылаться на **конкретные** строки этой таблицы (план + лимит).  
- Кодовые флаги (**`TenantLicense`**, `business_type`, module flags) — маппинг на **Plan + Modules + Limits** (**бэклог внедрения**).

#### Договор и биллинг (сводка)

Полный чеклист — подраздел **«Пользовательское соглашение — обязательный чеклист»** и блоки **Trial**, **Overages**, **Upgrade/downgrade**, **Архивация** выше. Дополнительно в оферте: **неоплата**, **grace period**, соответствие заявленных модулей UI/API.

#### Состояние в коде (лицензии и платформа)

- **`TenantLicense`** — **`backend/app/models/tenant.py`**; чтение лимитов — **`tenant_limits`**, **`profile_limits`**.  
- **Active portal candidates / мес:** **`portal_candidate_usage.py`** + **`GET /settings/billing/summary` → `portal_candidates`** (used/cap, **`soft_limit=false`** в снапшоте, **warning_level** 80/100%); учёт и **`ensure_can_add_portal_candidate_month`** при **`POST …/candidates/{id}/upload-link`** и **`notify`**.  
- **Founder pricing:** **`founder_pricing.py`** — зеркало **`billing.founder_pricing_v1`** при **`_store_subscription`**; зачисление **`enrolled`** — Checkout **`_maybe_enroll_founder_program`** + **Platform `POST …/founder-pricing/enroll`** + вкладка **billing** на **`TenantsPage`**.  
- После успешной оплаты Stripe webhook **`billing._apply_license_limits`** подставляет лимиты из **`PLAN_LICENSE_LIMITS`** (черновик под планы, **не** полная матрица add-ons **§2.16**).  
- **Platform API:** **`backend/app/api/v1/platform/tenants.py`** — список тенантов, suspend, **PATCH …/license**, impersonate, модули.  
- **Superadmin UI:** **`hostflow-frontend/src/pages/admin/TenantsPage.tsx`** + **`src/api/tenants.ts`** (в приложении под ролью `superadmin`, **`routes.tsx`** `superadminOnly`) — не отдельный host из спеки **§2.17**.

#### Жизненный цикл SKU add-on checkout (канон v1)

**Три статуса (не путать):**

| Статус | Смысл |
|--------|--------|
| **STRIPE_CATALOG** | SKU есть в матрице `stripe_price_catalog.py` (`checkout_payment` / иной режим); в Stripe может существовать Product/Price; в приложении — env Price ID (**`configured`** в **`GET …/billing/summary` → `addon_checkout_offers`**). |
| **EFFECT_READY** | Есть **продуктовый лимит + учёт + enforcement + эффект покупки** + связка **Stripe → webhook → apply** (или mock). Только такие SKU входят в **`ADDON_PACK_CHECKOUT_READY`** в **`billing.py`**. |
| **PURCHASE_ALLOWED** (в API) | Пользователь может завершить **`POST /settings/billing/addon-pack/checkout`**: **EFFECT_READY** ∧ плановые гейты ∧ (в режиме Stripe — задан Price ID). Поля **`purchase_allowed`**, **`purchase_block_reason`** в **`addon_checkout_offers`**; UI не показывает активную оплату без **`purchase_allowed`**. |

**Правило:** в **`ADDON_PACK_CHECKOUT_READY`** попадают **только** SKU со статусом **EFFECT_READY**. Остальные **нельзя** купить (даже при наличии цены в каталоге).

**Пример `pack_lead_forms_5` (v1, в коде):** **STRIPE_CATALOG** = да; **EFFECT_READY** = да — таблица **`tenant_lead_forms`** (+ опциональный **`public_slug`** на форму), кап **1 / 3 / 20** + **`usage_v1.pack_addons_v1.lead_forms_active_cap`**, **`POST|PATCH /settings/lead-forms`**, **`GET …/billing/summary` → `lead_forms`**; публичный intake: **`GET /public/intake/lead-forms`**, **`POST /public/intake`** с **`lead_form_id`** или **`lead_form_slug`** (метаданные в **`intake_state.lead_form`** / **`data.lead_form`**); покупка увеличивает **`lead_forms_active_cap`** (**webhook/mock**). **`purchase_allowed`**: все оплачиваемые планы с конечным базовым капом (не Team-gated, в отличие от паков automation/leads). При превышении капа при создании/активации формы — **402** `lead_forms_limit_reached`.

**Любой будущий add-on** должен иметь: (1) product limit, (2) usage, (3) enforcement, (4) effect, (5) billing linkage. Без любого пункта — **не** включать в checkout.

**Ориентир единой таблицы лимитов продукта (для paywall / биллинга):** `leads_per_month`, `active_records`, `users`, `workspaces`, `automation_rules`, `client_portals`, `candidate_portals`, `lead_forms`, `custom_fields`, `storage`, `channels` (и др. по мере появления).

**Custom fields packs на Team/Business:** лимит полей лида не применяется (**unlimited**); **`purchase_allowed`** = нет, **`purchase_block_reason`** = `custom_fields_not_on_team_plan`; UI показывает причину, а не «готово к оплате».

#### Бэклог (внедрение)

- [x] **Plan + аддоны на `TenantLicense` (v1 — часть):** при синхронизации плана **`_apply_license_limits`** накладывает базу **`PLAN_LICENSE_LIMITS`** и **суммирует** для полей seats / **`max_public_portal_links`** дельты из **`tenant.settings.billing.subscription.license_addon_v1`** (`*_delta`); при **смене** `plan` дельты сбрасываются и JSON нормализуется. После **Platform `PATCH …/license`** вызывается **`sync_subscription_license_addon_v1`** (**`billing.py`**), чтобы ручные лимиты пережили следующий Stripe/webhook sync. **Пак candidate portal / мес:** **`usage_v1.portal_monthly_cap_addon_v1`** + **`POST /settings/billing/portal-candidates-pack/checkout`** (Stripe `mode=payment`, **`STRIPE_PRICE_PORTAL_CANDIDATES_PACK`**, webhook **`checkout.session.completed`** с **`billing_action=portal_candidates_pack`**). **Матрица Stripe Price IDs:** **`stripe_price_catalog.py`** + **`Settings`** + **`backend/.env.example`**. **Остаётся:** Checkout/API + webhooks для остальных SKU (seats, client portal, паки лидов/полей/…), не только конфиг.  
- [x] **Enforcement лимитов (часть):** месячные лиды — **`ensure_monthly_lead_creation_allowed`** (**`lead_quota`**, **`leads/crud`**); активные кандидаты / открытые вакансии / число документов — **`tenant_quota`** (вызовы из candidates, vacancies, **`documents` crud**, публичный intake / создание кандидата); **публичные ссылки портала** — лимит при создании ссылки; **Meta mapping / credentials / lead custom fields** — **`plan_feature_gates`** (403 + коды в **`friendlyError`**); **seats / client portal seats** — **`users.py`** (`seat_limit_reached`); **включённые automation rules** — лимит **10 (team) / 50 (pro+)** на **`POST|PATCH /automation-rules`** (402 `automation_rules_limit_reached`, UI **`friendlyError`**); **хранилище по `max_storage_gb`** — сумма **`size`** в **`Document.files`** при создании/обновлении через **`documents` crud**, **`register_document_upload`**, **`ensure_document_files`**, **`POST /documents`**, публичный intake и **`POST …/documents/upload`** (402 `storage_limit_reached`); **candidate portal / мес** — **`ensure_can_add_portal_candidate_month`** (402 `portal_active_candidates_limit_reached`); **companies** — гейты post-trial / past_due в **`modules/companies/service.py`** (безопасный PATCH-подмножество); **communication channels** — лимит при **`POST /communications/accounts`** (**`plan_feature_gates.ensure_communication_channel_account_create_allowed`**, 402 `communication_channels_limit_reached`, бакет starter **1** / team **3** / pro **10**); **funnel definitions** — лимит при **`POST /funnels`** (**`ensure_custom_funnel_create_allowed`**, 402 `funnel_definitions_limit_reached`, бакет **1** / **3** / **20**). **Остаётся:** отдельные поля/логика на форму (не только slug + привязка intake); **воронок instances** (привязка vacancy↔funnel без дублирования с **`max_vacancies_active`**); доработка **`storage_used_gb`**, обходные пути загрузки без `size`; при необходимости — расширить post-trial гейты на остальные модули.  
- [x] **Страница планов и цены (v1):** карточки планов на **`BillingWorkspacePage`**; суммы и названия **Solo / Team / Business** подтягиваются из **`GET /settings/billing/summary` → `available_plans`** (**`_available_plans`** в **`billing.py`**, те же EUR-цифры, что **§2.16**); буллеты seats/features остаются в **i18n**; подсказка про SSOT в UI. **Остаётся:** отдельная маркетинговая страница pricing, richer upsell в операционных потоках (**§2.14**).  
- [x] **Юридические шаблоны по чеклисту §2.16 (v1 — черновики):** шесть типов в **`legal_documents`** (`trial_terms`, `downgrade_cancellation`, `overage_autodebit`, `data_retention`, `automation_disclaimer`, `mapping_disclaimer`) + **`GET /legal-documents/default-templates/billing-v1`** и английские HTML-черновики в **`backend/app/legal/billing_terms_templates_v1.py`**; **`GET /legal-documents/active`** отдаёт активные версии всех типов; UI **Settings → Legal** — второй блок «Billing exhibits», опциональное **HTML**, кнопка подстановки черновика; индекс **`docs/legal/billing-ssot-v1/README.md`**. **Остаётся:** юридическая вычитка, локализации черновиков, явная связка с Checkout/офертой и отображение ссылок в **Billing**, e-sign версионирование.  
- [x] **Решения по политике (v1):** подраздел **«Решения по политике (v1 — зафиксировано)»** + уточнения в тексте планов (**presets / instances**, стадии, каналы, branded, **candidate portal = active candidates/мес** + учёт и API-cap, client portal **per-unit** + bundle). **В коде (доп.):** лимиты каналов и определений воронок (**§2.16**), **grace 3d** trial (**`billing_restrictions`**). **Модалка лимита / Billing CTA (402):** портал кандидатов — **`CandidateCard`** (upload-link и др.); каналы — **`CommunicationsMessengerSettingsPage`** (`runConnectionAction`); воронки — **`FunnelsPage`** (создание воронки, этапы, удаление, DnD-порядок) + **`ErrorRecoveryBanner`**; автоправила — **`AutomationRulesPage`** (загрузка / создание) + баннер. **Остаётся:** лимит **instances** vacancy↔funnel при необходимости, остальные 402 в админ-потоках по мере появления. **Пак портала:** Checkout + return **`?portal_pack=success|cancel`** на **`BillingWorkspacePage`** (баннер + опрос summary).  
- [x] **Trial (политика зафиксирована):** **§2.16** Trial + **§2.18** — 7 дней, лимиты **50/20/2/5**, запрет **real outbound**, анти-абьюз **email+домен+fingerprint**, после trial **read-only** + **grace 3 дня** для side-effect гейта (**`billing_restrictions.billing_write_block_reason`**: блок после `trial_ends_at` / конца календарного trial лицензии + **3** суток). **Остаётся:** read-only по модулям без side-effects, trial signup gates, comms-политика.  
- [x] **Founder pricing (политика):** **50** мест, **Team €99** / **Business €199**, **Stripe = primary**, зеркало в tenant settings, **>14** дней неактивной подписки → **revoke навсегда**, **Solo вне**. **В коде:** **`founder_pricing.py`** (в т.ч. **`license_plan_for_founder_eligibility`**, SQL-счётчик слотов на PostgreSQL) + **`_maybe_enroll_founder_program`** при **`checkout.session.completed`**, mock **simulate success**, **change-plan** (Stripe modify + mock), **Platform `POST /platform/tenants/{id}/founder-pricing/enroll`**; **`_store_subscription`** — таймер revoke по статусу; **TenantsPage** — блок **Founder pricing** на вкладке billing. **Остаётся:** цены **€99/€199** в Stripe Price IDs / витрина.  
- [x] **Сегментные пресеты:** одна матрица, **`business_type`** = UI, **не** отдельные Stripe products. **Остаётся:** пресеты в онбординге/настройках.  
- [x] **UI биллинга и лимитов (v0 tenant):** **`BillingWorkspacePage`**, **`GET /settings/billing/summary`** (**usage** / **usage_caps**), v0 модалка сводки перед Checkout, Customer Portal, past_due **Retry**; глобальная модалка лимита/биллинга — **`PlanLimitModalProvider`** + **`showPlanLimitIfNeeded`** (перечень **§2.18**). **Остаётся:** полная спека **§2.17** (compare plans, add-ons UI, матрица **§2.16**). **Канон:** развивать **`TenantsPage`**, отдельный Platform Admin app **не** делаем.  
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

- **Billing:** **`BillingWorkspacePage.tsx`**, **`billing.py`** — см. **§2.18**; в **summary** отдаются **`usage`** (в т.ч. лиды за месяц UTC, кандидаты, документы, открытые вакансии, портальные ссылки) и **`usage_caps`** для строк лимитов.  
- **Команда / seats (черновик):** панель **`TeamManagementPanel`** в **`BillingTeamPage.tsx`** (запросы мест, модули, обзор) — не полный сценарий **§2.17** п.5 (invite + matrix workspace).  
- **Platform admin:** **`TenantsPage.tsx`** — список тенантов, license, suspend, impersonate, модули; **отдельного** Platform Admin app нет.

#### Бэклог (внедрение)

- [x] **Billing & Subscription + usage (v0):** экран тенанта и API — **`BillingWorkspacePage.tsx`**, **`billing.py`** (**summary** / subscription / checkout / portal); выравнивание с полной матрицей **§2.16** — см. открытые строки **§2.16** «Бэклог» и ниже.  
- [ ] **Upgrade / compare**, **add-ons** и **Customer Portal** — расширить поверх текущего Checkout (**§2.18**).  
- [ ] **Team:** invite + seat gate + **workspace access** matrix поверх **`BillingTeamPage`** / **`UserFormInvite`**.  
- [ ] **Roles** editor с серверной валидацией.  
- [ ] **Companies** CRUD с предупреждением цены и enforcement **§2.16**.  
- [x] **Limit reached (v0):** единая модалка **`PlanLimitModalProvider`** + **`showPlanLimitIfNeeded`** на основных write/read путях (**§2.18**, список экранов). **Остаётся:** CTA **buy pack** / **add seats** с ценой из **§2.16** без лишних шагов и дубля с баннером.  
- [ ] **TenantsPage:** **override limits**, billing adjust — довести до спеки **§2.17** п.10. **Канон:** отдельный Platform Admin app **не** делаем.  
- [ ] **Аудит:** события plan change, override, invite, role change — **лог в БД обязателен**; **UI** — минимальный список (v1), без тяжёлой аналитики.

### 2.18 Stripe: единая цепочка trial → оплата → лимиты → UX

**Назначение:** связать **HF** со **Stripe** так, чтобы одна цепочка закрывала **trial**, **апгрейд**, **биллинг**, **лимиты**, **продуктовый UX** и **юридику** (**§2.16**, **§2.17**). Ниже — целевая архитектура; идентификаторы продуктов/цен — в конфиге и **Stripe Dashboard**, синхронизированы с **`TenantLicense`**.

#### 1. Общая архитектура

**User action** → выбор плана / add-on → **Stripe Checkout** (или **Customer Portal** / **Subscription update**) → **Webhook** Stripe → HF → обновление **subscription state** → применение **лимитов** / разблокировка **фич**.

Источник истины после активации: **Stripe Subscription** + зеркало в БД HF (**`stripe_customer_id`**, **`stripe_subscription_id`**, статус, текущий **price id**). **Канон (v1):** **одна** подписка на тенант; **add-ons = subscription line items** (не отдельные подписки на каждый модуль).

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

**После окончания:** *Your trial has ended*; **данные сохранены**; **`[ Choose plan ]`**. **Канон:** режим **§2.16** post-trial (allowlist правок **без side-effects** + запрет новых сущностей и отправки сообщений) + **grace 3 дня** — см. подраздел **«Post-trial / past_due — редактирование без side-effects»** в **§2.16**.

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

*Cancel subscription?* — *Access until {date}* · *After that: read-only* → **`[ Confirm cancel ]`**. **Канон:** отмена через **`cancel_at_period_end` = true** (доступ до конца оплаченного периода). Синхронизация с **`customer.subscription.deleted`** / `cancel_at_period_end` в webhook.

#### 11. Past due

**UI:** *Payment failed* — **`[ Retry payment ]`** (Stripe **Customer Portal** или обновление платёжного метода).

**Ограничения (ориентир):** **grace 3 дня** после неуспешного платежа — затем как минимум: нельзя создавать **новые** сущности, нельзя **отправлять сообщения**; **частичный read-only** (просмотр + ограниченное редактирование — как **§2.16** post-trial). **Dashboard** и просмотр — доступны, пока политика не ужесточена.

#### 12. Связка с лимитами

*You reached your limit* → **Upgrade** · **Add +500 leads (€15)** — кнопка открывает **тот же** Stripe-поток (новая подписка / subscription item / one-time — **выбрать модель**). Единый паттерн с **§2.17** п.9.

#### 13. Объекты Stripe

1. **Products** — HF Solo / Team / Business (и при необходимости Enterprise как custom).  
2. **Prices** — monthly / yearly на каждый план; отдельные Prices для **add-ons** (seat, workspace, packs) как **line items** той же подписки.  
3. **Subscription** — основной объект доступа (**одна** на тенант в v1).  
4. **Overage (v1):** **без** Stripe **metered**; только **upgrade плана** или **покупка pack через Checkout** (one-time / доп. line item по продуктовому решению), см. **§2.16** Overages.

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

- **Уже есть:** **`backend/app/api/v1/settings/billing.py`** — `checkout-session` (Stripe Checkout при настроенных ключах, иначе mock), **`webhook`** — `checkout.session.completed`, **`invoice.paid`** и **`invoice.payment_succeeded`**, **`invoice.payment_failed`** (статус **`past_due`** + email), **`customer.subscription.created` / `updated` / `deleted`**; **идемпотентность** по **`event.id`** — модель **`StripeWebhookEventLog`**, миграция **`202603251400_stripe_webhook_log`**; частично **Billing Portal**; хранение подписки на тенанте. Фронт: **`BillingWorkspacePage.tsx`**, **`billing.ts`**. **Матрица Stripe Price IDs §2.16:** **`backend/app/services/stripe_price_catalog.py`** (перечень SKU + режим биллинга), переменные окружения — **`backend/.env.example`**, поля **`Settings`**. К **Stripe API** подключены: базовые планы, **операционные слоты** (раздельные цены Team/Business + fallback на legacy **`STRIPE_PRICE_OPERATING_COMPANY_SLOT`**), **пак candidate portal** (Checkout). Остальные SKU — только конфиг до появления Checkout/line items.  
- **Ещё нет / слабо:** полная **сводка перед оплатой** по **§2.16** (line items, add-ons, seats из API); **v0:** модалка **«Подтвердите оплату»** на **`BillingWorkspacePage`** перед редиректом в Stripe (план, интервал, цена из UI). **Stripe Tax** / **tax IDs** / **VIES**; список **Invoices** в Settings; **trial** баннеры и **read-only + grace 3d** после trial на всех write-API (сейчас — частично **`billing_restrictions`**); **Checkout + webhook** для остальных паков и **subscription items** (seats, client portal, …) поверх матрицы env; **past_due grace 3d**; при гонке двух вебхуков с одним `event.id` возможен кратковременный двойной side-effect до записи в лог.  
- **Частично past_due UX:** баннер + CTA **Retry payment** → **Customer Portal** (не новый Checkout), правка **`BillingWorkspacePage.tsx`**.  
- **past_due + expired trial API (лиды / исходящие):** **`backend/app/services/billing_restrictions.py`** — при **`past_due`** или **истёкшем trial** (`TenantLicense.plan == trial` и **`expires_at` < сегодня**, либо **`subscription.status == trial`** и **`trial_ends_at` в прошлом**): новый лид не создаётся (**`modules/leads/service.py`**) → **403** `billing_past_due` / `billing_trial_expired`; исходящие сообщения и **`dispatch/queued`** — **403** / no-op; **`GET /settings/billing/subscription|summary`** подставляет **`trial_ends_at`** из лицензии trial, если в **`settings.billing`** ещё нет даты.  
- **v0 единый UX лимита/биллинга (модалка):** **`PlanLimitModalProvider`** в **`main.tsx`** (под **`I18nProvider`** + **`BrowserRouter`**, чтобы модалка работала и на публичных маршрутах, в т.ч. **`/invite/accept`**), **`isPlanLimitOrBillingGateError`** + расширение **`friendlyError.ts`** (**402** и **403** с кодами квоты/биллинга/team/seat/Meta/lead custom fields), i18n **`app.api_errors.plan_gate.*`**; **`showPlanLimitIfNeeded`** подключён в **`useDocumentActions`**, **`useDocumentUpload`**, **`useDocumentPreview`**, **`CandidateDocuments`**, **`LeadsPage`**, **`useNbaQuickBulkFlow`**, **`VacancyList`**, **`VacancyDetail`**, **`useCandidatesTableData`** (лист кандидатов), **`Candidates`** (bulk stage/manager/vacancy/handoff/tags/delete/activities + избранное), **`Pipeline`** (загрузка канбана + bulk DnD + **`doBulkStage`** + одиночный move), **`LeadDetailPage`**, **`DocumentsRegistryPage`**, **`MetaLeadsAdminPage`** (в т.ч. сняты дублирующие inline-сообщения для лимитов mapping/credentials/lead fields — модалка + **`getFriendlyErrorInfo`**), **`UsersPage`** (invite + create user / seat limit), **`CandidateCard`** (загрузка/сохранение/таймлайн/напоминания/экспорт/handoff/pipeline override и др.), **`BillingWorkspacePage`** (load/checkout/portal/мутации без дубля баннера при лимите), **`InviteAcceptPage`**, админ коммуникаций (**`CommunicationsMessengerSettingsPage`**, **`CommunicationsQueueSettingsPage`**, **`CommunicationsSlaSettingsPage`**), **`EmailSettingsPage`**, **`CommunicationsCommandAuditPage`**, **`CommunicationsPlannerPage`**, **`CommunicationsCalendarPage`**, **`CommunicationsInboxHubPage`**, **`CommunicationsInboxCenterPage`**, **`CommunicationsSlaIncidentsPage`**, **`CommunicationsInboxControlPanel`**, **`CommunicationsInboxWorkflowCard`**, **`CommunicationsThreadEntityLinkForms`**, **`useCommunicationsThread`**, **`AutomationLogPage`**, **`MyAvailabilityPage`**, **`TeamAvailabilityPage`**, **`TimeOffRequestsPage`**, **`RemindersPage`**, **`ActivitiesPanel`**, **`useCandidatesWorkPanelPreview`**, **`CandidateChangeLogModal`**, **`CandidateDocsChecklistMiniPanel`**, **`CandidateDocsRailPanel`**, **`InvoicesPage`**, **`InvoiceDetailPage`**, **`InvoiceCreatePage`**, **`Companies`** (сохранение, политики документов, черновик **`/new`**, архив), **`ClientLinkDetailPage`**, **`MyCompanyPage`**, **`OnboardingCompanyPage`**, публичные **`Login`**, **`SignupPage`**, **`ForgotPasswordPage`**, **`ResetPasswordPage`**.  
- **Квоты плана (лиды / месяц UTC, активные кандидаты, открытые вакансии, документы):** **`backend/app/services/lead_quota.py`** + **`tenant_quota.py`** — проверка до записи (лиды **`modules/leads/crud.create_lead`**, кандидаты **`create_candidate_full`** + публичный intake + Telegram intake, вакансии **`VacancyService`**, документы **`modules/documents/crud.create_document`**); при превышении → **402** с **`detail.code`**: `monthly_leads_limit_reached` | `candidate_limit_reached` | `open_vacancy_limit_reached` | `document_limit_reached` (и поля **`limit`**, **`current`** где применимо). Отображение лимитов в UI: **`GET /settings/billing/summary`** — **`usage`** + **`usage_caps`** (см. **§2.17**); фронт: **`friendlyError.ts`** — подсказки для этих кодов и для **403** `portal_link_limit_reached` / биллинга; i18n **`app.api_errors.*`** (en/ru/pl), третий аргумент **`t`** у **`getFriendlyErrorInfo`**, при квоте/биллинге — **`secondaryTo`/`secondaryLabel`** (Billing); **`friendlyErrorBannerSecondary`** — дефолтный вторичный линк в пропсах баннера, если в **`info`** нет CTA; **`ErrorRecoveryBanner`** внутри всё равно делает **`info.secondary* ?? props`**. Загрузка списков/канбана и смежные экраны с дружелюбными ошибками и биллингом: **`useCandidatesTableData`**, **`Pipeline.tsx`**, **`DocumentsRegistryPage.tsx`**, **`VacancyList.tsx`**, **`InvoicesPage.tsx`** (список + действия), **`InvoiceDetailPage.tsx`**, **`InvoiceCreatePage.tsx`**, **`CommunicationsSlaIncidentsPage.tsx`**, политики документов клиента в **`Companies.tsx`** (вторичная ссылка на **`/app/documents`**), **`ClientLinkDetailPage.tsx`** (ошибка загрузки vs not found), **`MyCompanyPage.tsx`**, онбординг компании **`OnboardingCompanyPage.tsx`**, публичные **`Login` / `SignupPage` / `ForgotPasswordPage` / `ResetPasswordPage` / `InviteAcceptPage`** — **`friendlyFormHintError`** для валидации, **`getFriendlyErrorInfo`** для ответов API; коммуникации: **`useCommunicationsThread`** хранит **`threadError: FriendlyErrorInfo | null`** (загрузка треда, send/dispatch с **`secondaryTo`** на email settings при необходимости), **`CommunicationsInboxCenterPage`**, **`CommunicationsInboxHubPage`** — пул/хаб списка через **`getFriendlyErrorInfo`** + баннер; панель управления тредом **`CommunicationsInboxControlPanel`**; формы привязки сущностей **`CommunicationsThreadEntityLinkForms`**; **`AutomationLogPage`** — загрузка лога через **`getFriendlyErrorInfo`**; планировщик и календарь (**`CommunicationsPlannerPage`**, **`CommunicationsCalendarPage`**), availability / отпуска (**`MyAvailabilityPage`**, **`TeamAvailabilityPage`**, **`TimeOffRequestsPage`**), **`CommunicationsCommandAuditPage`**, админка коммуникаций (**`CommunicationsSlaSettingsPage`**, **`CommunicationsQueueSettingsPage`**, **`CommunicationsMessengerSettingsPage`**) — **`FriendlyErrorInfo`**, **`getFriendlyErrorInfo`**, **`friendlyFormHintError`**, **`friendlyErrorBannerSecondary`** без локальных **`errorTextFrom`** / **`useMemo`**-обёрток баннера; карточка кандидата: **`CandidateDocsRailPanel`**, **`CandidateDocsChecklistMiniPanel`**, **`CandidateChangeLogModal`**; инбокс — **`CommunicationsInboxWorkflowCard`** (**`workflowError`**, **`toWorkflowApiError`** + **`friendlyFormHintError`** для кодов эскалации и форм); **`CandidateTimelinePanel`** + **`CandidateCard`** (**`timelineError`**, **`remindersError`**, загрузка стадий и напоминаний — **`getFriendlyErrorInfo`**), **`CandidateNextActionPanel`**, **`CandidateRemindersSection`**; превью work panel — **`useCandidatesWorkPanelPreview`**, **`CandidatesSelectedPanel`**; очередь **«без следующего шага»** встроена в **`Candidates`** (**`?queue=no_next_action`**, **`useCandidatesTableData`** + **`GET /candidates/no-next-action`**).

#### Бэклог (внедрение)

- [x] **Products/Prices (конфиг v1):** полная матрица SKU **§2.16** зафиксирована в коде — **`stripe_price_catalog.py`** + **`Settings`** + **`backend/.env.example`**; в Stripe Dashboard создать Product/Price на каждую строку и проставить env. **Остаётся:** создание объектов в **живом** Stripe Account, единый **`metadata`** (`plan_code`, `tenant_id`, `billing_sku`) на продуктах; **Checkout/API** для всех add-on SKU, не только планы + operating slots + portal pack.  
- [ ] Webhook: при необходимости **`invoice.finalized`** и др.; **очередь** / ретраи внутри HF при ошибках после частичного commit.  
- [x] Экран **summary** перед редиректом в Checkout (**v0:** модалка на **`BillingWorkspacePage`** — план, период, отображаемая цена; затем Stripe). **Остаётся:** line items / add-ons из **§2.16**, **Stripe Tax** / tax IDs + проверка VAT (EU).  
- [x] **Settings → Billing → Invoices (v0):** таблица на **`BillingWorkspacePage`**, строки из **`summary.invoices`**, ссылки **hosted** / **PDF** при наличии в Stripe. **Остаётся:** фильтры, экспорт, синхронизация с **`invoice.finalized`** и очередь (**ниже в этом §**).  
- [ ] **Trial** (UI баннеры / post-trial messaging) и **post-trial read-only** + **grace 3 дня** на остальных write-API (частично: лиды + исходящие comms — **`billing_restrictions`**; расширить по **§2.16**).  
- [x] **Overage (политика v1):** **без** Stripe metered — только **upgrade** или **pack через Checkout**. **Остаётся:** SKU паков и UI **buy pack**.

### 2.19 Порядок работ (зафиксировано)

1. **Этап — продукт и платформа (итеративно):**
   - **1a Операционная CRM (§2.1–§2.14, точки §2.7–§2.11 без коммерции):** цель — стабильный операторский продукт; **закрытые** §2.13 / §2.14 — базовый критерий готовности к **внутреннему пилоту**; метрика «100%» для пилота — **§1.7**. Открытые **`[ ]`** в §2.8–§2.9 (stretch, perf, scanner), §2.7 (email bulk — без ТЗ) **не блокируют** 1a, пока не объявлен иной **release gate**.
   - **1b Монетизация и владелец (§2.16–§2.18, §2.17):** Stripe, лимиты, биллинг UI, team/settings — до спеки разделов; ведётся **параллельно** с пилотом, если нет жёсткой зависимости.
   - **1c Клиентский портал (§2.15):** после стабилизации операторского контура или по приоритету продукта.
2. **Этап — коммерция (GTM):** внешние продажи, маркетинг и публичный запуск — **после** достаточной готовности **1b** (оплата, лимиты, юридический минимум по **§2.16**), а не после механического обнуления каждого **`[ ]`** в документе.

**Примечание:** полный ноль **`[ ]`** по всему **§2** — ориентир **дорожной карты** (фазы **1b/1c** и stretch), а не единственный определимый «день X». Для **пилота (1a)** используй определение **§1.7** («100%» операционного контура). Пункты переносятся в **`[x]`** с пометкой **«Остаётся»** или явно снимаются как **вне scope** текущего этапа — см. чеклисты в **§2.8**, **§2.15–§2.18**.

---

*Обновлено: 2026-03-30 — **Insights / аналитика:** единый экран **`/app/overview`** (воронка **`AnalyticsLeadConversionFunnelPage`** встроена, якорь **`#lead-conversion`**); **`NAV_ITEMS.analytics`** и **`AnalyticsHubPage`** убраны; **`/app/analytics`** и **`/app/analytics/lead-conversion`** → редиректы (**`routes.tsx`**); **`Sidebar`**, **`LeadsPage`**, **`GET /analytics/candidate-slices`** (`candidate_id`), **`DashboardSectionCollapsible`** / пресеты — отражено в **§2.3**, **§2.12**, **§2.13**, **§2.14**. 2026-03-27 — **§1.7** — определение «100%» (пилот **1a** vs дорожная карта **1b/1c**/stretch). **§2.17 / §2.18 (состояние в коде):** **v0** глобальная модалка лимита плана (**`PlanLimitModalProvider`** в **`main.tsx`**, **`friendlyError.ts`** + **`app.api_errors.plan_gate`**, **`useDocumentActions`**); **`CandidateCard`**, **`BillingWorkspacePage`**, **`InviteAcceptPage`**, админ/settings comms + **`CommunicationsCalendarPage`** / **`CommunicationsPlannerPage`** / инбокс + **`CommunicationsInboxControlPanel`** / **`CommunicationsInboxWorkflowCard`** / **`CommunicationsThreadEntityLinkForms`** / **`useCommunicationsThread`** / **`AutomationLogPage`** / availability (**`MyAvailabilityPage`**, **`TeamAvailabilityPage`**, **`TimeOffRequestsPage`**) / **`RemindersPage`** / **`ActivitiesPanel`** / **`useCandidatesWorkPanelPreview`** / docs rail + checklist + change log (**`CandidateDocsRailPanel`**, **`CandidateDocsChecklistMiniPanel`**, **`CandidateChangeLogModal`**) / инвойсы (**`InvoicesPage`**, **`InvoiceDetailPage`**, **`InvoiceCreatePage`**) / **`Companies`** (политики + save + draft + archive) / **`ClientLinkDetailPage`** / **`MyCompanyPage`** / **`OnboardingCompanyPage`** / публичные **`Login`**, **`SignupPage`**, **`ForgotPasswordPage`**, **`ResetPasswordPage`** / **`LeadDetailPage`** (таймлайн, загрузка напоминаний, complete reminder) — **`showPlanLimitIfNeeded`**. **§2.19** — фазы **1a/1b/1c** и критерий пилота; **§2.18** — **v0** сводка перед Checkout (**`BillingWorkspacePage`**). **§2.14 закрыт:** очередь **no-next-action** встроена в **`Candidates`** (**`?queue=no_next_action`**, редирект с **`/candidates/no-next-action`**). **§2.18** — перечень **`friendlyError`** (инбокс hub / control panel / entity link forms, work panel preview, напоминания на карточке). **§2.14** кэш подписки: **`billingSubscriptionCache.ts`**, событие обновления, **`BillingWorkspacePage`** / **`Dashboard`** trial / **`AppShell`** + **`auth` logout**. **§2.14** paywall v0: **`useTeamTierFeatures`**, **`WorkHubPage`**, **`Pipeline`**. **§2.14** v1: inline **Call / Email / Open / Tasks** — **`Pipeline.tsx`** + таблица **`Candidates.tsx`** (ячейка **Имя**). **§2.14** v0: health-бейджи колонок **`Pipeline.tsx`**, полоса **Signals** на **`Dashboard.tsx`**, правка «частично в коде» (NBA на обзоре). §2.4: **`GET /analytics/services-overview`** — скоуп service orders (**`_service_order_scope_where`**). 2026-03-27 — §2.4: **service orders** — **`own_company_id`**, API **`services.py`**, поиск, ensure Postgres + Alembic **`202603291400_svc_ord_oc`**; **`create_company_service`** — сессия из **`crud._extract_session`** для UOS. 2026-03-27 — §2.4: legacy **`/api/v1/documents`** (**`documents.py`**) + **`crud.create_document(own_company_id)`**; путь заказа **`POST /order`**. 2026-03-27 — §2.4: **candidate documents** — скоуп **`own_company_id`** (**`candidate_documents.py`**, **`vacancies/router.attach_candidate`**). 2026-03-27 — **§2.3 ~стр. 83** — воронка как инструмент управления **`[x]` v1**; добавлен **`§2.12 stretch`**; **`AnalyticsLeadConversionFunnelPage`** — **management loop** + пресеты lost. 2026-03-27 — §2.12: **`GET /leads?lost_from_crm_stage=`** + UI из **`lost_from_stage`**. 2026-03-27 — §2.12 (углубление): **`GET /leads?lost_reason_code=`**, drill-down из **`lost_reason_breakdown`**; **`AnalyticsLeadConversionFunnelPage`** — **Suggested focus** (**`funnelSuggestedInsights.ts`** ↔ пороги **`NBA_FUNNEL_*`**). 2026-03-27 — §2.12: **`funnel_stages.conversion_root_v1`**, корневая воронка в **`GET /leads/conversion-funnel`**, **`GET /leads?conversion_root=`**, UI **`FunnelsPage`** / **`LeadsPage`** / **`AnalyticsLeadConversionFunnelPage`**; инсайты воронки в **`GET /next-actions`** (Dashboard NBA). 2026-03-26 — **§2.19** порядок: весь **§2** → коммерция; §2.12: **`lost_from_stage`** + **`lost_reason_breakdown`** в **`conversion-funnel`** + UI; **`lead_lost_reason_v1`** + модалка при **`lost`** (инбокс, деталь, **`PATCH /leads/bulk`**); **срезы** TEAM+; **dwell**; §2.11: **`GET /leads?q=`**; §2.10: NBA **Process batch**; paywall **field_mapping** + **Meta credential**; §2.6: **лиды** в **`GET /search`**. 2026-03-25 — §2.2 (onboarding i18n); §2.3 — NBA **candidates** + **`t_due_bucket`**; **gating** + **Do now**; **`GET /next-actions`**; **`GET /leads/stage-health`**; distribution **language_routing_v1**; inbox **assignment_lock**; DnD; round-robin; **`stage_contract_v1`**; **LeadOut** + playbook; **next_action** bulk **block**; **lead.pipeline.stage_changed**; §2.18; billing.*
