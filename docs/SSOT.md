# HostFlow SSOT (Single Source of Truth)

This file is the **only source of truth** for:

- current product readiness status
- remaining work (backlog)
- evidence of completion (kept inline here)

Rules:

- **All** progress updates and status changes go to this file.
- No new “tracker” markdown files should be added elsewhere.
- Supporting docs like specs/blueprints may exist, but they are **not trackers**.

### Working from any git branch

`docs/SSOT.md` is **one file in the repo** — the same path on **every** branch. Treat it like shared code: edit it on your feature branch, merge/rebase as usual; there is no separate “SSOT branch” or secret tracker.

- **Wording:** describe **product/code state** in branch-neutral terms (what is shipped, what is open, which paths). Avoid “only on `feature/…`” unless you also state whether it is merged to the integration branch you care about.
- **Backlog / checkboxes:** open work is **global** to the product, not owned by a branch. Add or tick items here instead of leaving status only in PR descriptions.
- **Merge conflicts:** resolve by **keeping both** substantive updates when possible (combine backlog lines, preserve distinct `[ ]` items). Do not drop the other side’s factual changelog or open tasks without reading them. Prefer **dated** statements over “latest wins” guessing.
- **Change log:** **append** new dated bullets; do not rewrite or delete historical entries to “clean up” during a merge — that breaks auditability across branches.
- **Code pointers:** use **stable paths** (e.g. `hostflow-frontend/src/...`) so the doc stays valid after merges; avoid line-number-only references when the surrounding section is volatile.

---

## Requirements sources (non-tracker)

- Product blueprint (workflow/UX principles): `docs/pipe.md`
- Landing/SEO/design direction: `docs/pipedesign.md`
- Module specs (reference): `docs/specs/**`

---

## Current status (2026-03-28)

### Product readiness

- **Overall**: **READY**
- **Primary remaining release-pass**: **none** — **R0.1** PASS recorded (see **Expanded backlog → R0.1 — Evidence**). **R1.5** product sign-off **PASS `2026-03-23`** (see **§ R1.5 — Evidence**). **R3.3** Services module v2 — **PASS `2026-03-23`** (see **§ R3.3 — Evidence**). **R3.4** Risk intelligence v1 — **PASS `2026-03-23`** (see **§ R3.4 — Evidence**). **Recent:** **Unified Inbox** — single surface **`/app/inbox`** with **`?channel=`** (all / messages / email), **`?folder=`** + IMAP-style rail + **Sync** + auto-poll in email scope, hub filters (**in work** / **later** / pinned sort), URL **`q`** search; **`/app/messages`** and **`/app/email`** redirect (OAuth redirect URI **`/app/email`** preserved). Legacy **public document scanner** removed (**`2026-03-25`**); uploads via **`/public/apply`** + **`?mode=documents`**. **Manual Inbox escalation bridge (`2026-03-26`):** first **`ops.mode=escalated`** on a thread → **`ActivityLog`** **`communications.thread.ops_escalated`**, in-app **`communications_thread_escalated`** (bell **Urgent (SLA)**), **`communications_thread_escalated`** task for recipients — **`communications.py`** **`_emit_manual_thread_escalation_bridge`**. **Vacancy recruiting → Activity (`2026-03-26`):** **`uos_auto_activities`** **`ensure_vacancy_recruiting_follow_up_task`** on **create** (open vacancy) and when a vacancy **enters** recruiting (**closed→open** / **`is_open`**); type **`uos_vacancy_recruiting_follow_up`**, toggle **`vacancy_recruiting_follow_up`**; wired from **`VacancyService.create`/`patch`**. **Bell → Inbox deep links (`2026-03-26`):** **`Topbar.tsx`** — **`buildInboxThreadPath`** for **`payload.thread_id`** + optional **`channel`**; **Urgent (SLA)** rows with a thread → **Open in Inbox** (before SLA incidents list); **Messages** group → unified Inbox thread URL (fallback **`/app/communications/threads/…`** if no comms license); notification drawer footer → **Inbox** when messages/email licensed; **`communications_thread_escalated_title`** + **`open_in_inbox`** i18n **en/pl/ru**. **Sidebar IA (`2026-03-26e`–**`f`**):** **`Sidebar.tsx`** — **Core / Business / System**; **Business** = one SSOT-aligned key order (Candidates → Clients → **do-procesowania** → Vacancies → Orders → Services → Invoices → Documents → Leads); **Account** mini-section (**profile**); **Settings** collapsible = admin + **communications-setup** + **command-audit**; client flat primary list. **Bell drawer (`2026-03-27a`):** **`Topbar.tsx`** — **Critical** / **High** / **Normal** tier chip per row (**`getNotificationAttentionTier`**). **Pipeline-completed candidates (`2026-03-27`–`28`):** canonical finals **`employed` / `probation_ok` / `rejected` / `declined`** — no operational doc-gate / next-step pressure on the card; **risk_model_v1** zeroed + list/detail/work-panel fast paths + **`constants/stages.is_pipeline_completed_stage`**; **`docs/pipe.md` §25**. **Next focus (backlog):** **UOS / IA — stretch** (notification **`priority`**, полный каталог **event→Activity**, нарратив **escalation** в *Operating model*); **Expanded backlog** — party / **own-company** и др. **`[ ]`** ниже. **Performance (R4)** и **hygiene uploads** — summary **`[x]`** по состоянию на **`2026-03-28`**.

### Evidence (latest)

- **R3.3 Services module v2 (`2026-03-23`):** workspace `/app/services` (sell → fulfill → invoice → collect + analytics/KPIs) — **PASS** по критериям SSOT **§ Services module v2** + shipped slice; зафиксировано в **§ R3.3 — Evidence** (Expanded backlog).
- **R3.4 Risk intelligence v1 (`2026-03-23`):** Phases A–D v1 + team settings UI + telemetry — **PASS** по чеклисту **§ R3.4 — Product sign-off** vs SSOT **§ Risk intelligence v1**; зафиксировано в **§ R3.4 — Evidence** (Expanded backlog).
- **R1.5 Product sign-off (`2026-03-23`):** Candidates command center v2 — **PASS** по чеклисту **§ R1.5 — Product sign-off** vs **`docs/pipe.md`**; зафиксировано в **§ R1.5 — Evidence** ниже.
- **R0.1 Production PASS (`2026-03-23`):** Scenario A (**services**) on tenant slug **`victoria-services`** — **PASS** per run-sheet **Expanded backlog → R0.1**; sign-off recorded in **§ R0.1 — Evidence** below.
- **Party + client workspace + services scoped URLs** (see section *Party model + client workspace + services deep links* below): shipped in app code; treat as canonical CRM/services UX for client companies until SSOT says otherwise.
- **Frontend static gate**: `npm --prefix hostflow-frontend run qa:static` → **PASS**
- **Frontend unit tests (CI)**: `.github/workflows/frontend-static-qa.yml` runs `npm run test` (Vitest) before `qa:static` — see Change log **`2026-03-28a`**
- **Pipeline-completed candidates (ops UX)**: finalized stages **`employed` / `probation_ok` / `rejected` / `declined`** — no doc-gate pressure on the card, zeroed list/detail risk scoring, no operational “advance” hints (**Change log `2026-03-27`–`2026-03-28`**); product philosophy bridge in **`docs/pipe.md` §25**
- **Repo hygiene — upload trees (`2026-03-28`):** **`git rm -r --cached backend/uploads backend/app/uploads`** (291 paths untracked); **`git ls-files`** → **0** under those prefixes; files stay on disk; **`.gitignore`** already excludes new local uploads
- **Production `vite build`**: default `npm run build` sets **`HOSTFLOW_LOW_MEM_BUILD=1`** + **`NODE_OPTIONS=--max-old-space-size=2048`**, no `experimentalMinChunkSize`. **`manualChunks`** only isolates **`@tabler/icons*`** (safe for React). Lazy bundles: CRM split into **`routeBundleCrmCore` / `routeBundleServices` / `routeBundleCrmMore`** plus other `src/app/routeBundles/*` — снижает пик RAM при `rendering chunks`. Для мощной машины: `npm run build:fast` (без low-mem I/O cap).
- **Staging scenario automation (A/B/C)**: Playwright+API run artifacts exist (local evidence used during stabilization).
- **Risk intelligence v1 — Phase A + B (ops leads) + Phase C (candidate surfaces)**:
  - Backend: `backend/app/services/risk_intel_v1.py` (decay + weighted `risk_model_v1`; hourly job `run_risk_intel_hourly_job`; `compute_candidate_risk_map_for_ids` for list/detail batches; tables `risk_intel_tenant_hourly`, `risk_intel_entity_shadow`; migration `202603221400_risk_intel_hourly_shadow`).
  - Scheduler: `communications_scheduler` — throttled hourly pass per tenant (`RISK_INTEL_HOURLY_ENABLED`, `RISK_INTEL_HOURLY_SECONDS`); disable per tenant: `Tenant.settings.risk_model_v1.hourly_job_enabled: false`.
  - API (superadmin / administrator / supervisor only): `GET /api/v1/analytics/risk-intelligence`, `.../trends`, `.../validation` (shadow cohort forward-stage proxy).
  - UI: Overview (`Dashboard.tsx`) — risk block visible only to **administrator / supervisor / superadmin**; live aggregate + hourly trend chart + validation panel.
  - Phase C: candidates list `include_risk` + `GET /api/v1/candidates/{id}` return the same `risk_model_v1` fields (`risk_score`, `risk_band`, `risk_drivers`, …); when the stored stage is **pipeline-completed**, responses use **synthetic zero risk** without **`compute_candidate_risk_map_for_ids`** / **`compute_candidate_risk_scores`** (entire list page terminal-only, or single-candidate detail / **`GET .../work-panel`** — **`2026-03-28c`–`d`**). Work panel (`CandidatesSelectedPanel`) shows drivers and an elevated-risk nudge (score ≥ 35). List filter **`shadow_bucket_start`** (+ optional **`shadow_bucket_min_band`**) restricts rows to `risk_intel_entity_shadow` for that hourly bucket (SQL subquery in `candidates/repo.py`); UI deep link **`/app/candidates?shadow_bucket=<ISO>&shadow_min_band=<low|medium|high|critical>`** (alias **`shadow_bucket_min_band`**) from Overview digest table; band floor adjustable in-list via query + banner select.
  - Phase D (automations v1): trigger `candidate.risk_band` in `automation_rules` + UI; hourly job calls `run_candidate_risk_band_rules` when `Tenant.settings.risk_model_v1.automations.enabled` is true (`dedupe_hours`, `min_band`); per-rule dedupe via `activity_log`; assignee = `recruiter_id` or `manager`.
  - Phase D (stage gate): `backend/app/services/candidate_risk_stage_gate.py` — `PATCH /candidates/:id` + bulk stage forward blocked when `risk_model_v1.stage_gate.enabled` and risk band ≥ `min_band` (default `critical`) and no active reminder (`new`/`pending`/`overdue`); skipped for client tenants, when moving into **terminal** stages, and when **`old_stage`** is **pipeline-completed** (**`is_pipeline_completed_stage`**, no risk map fetch — **`2026-03-28d`**).
  - Phase D (digest): `GET /api/v1/analytics/risk-intelligence/shadow-snapshot` (ops roles) — latest or `?bucket_start=` hourly `risk_intel_entity_shadow` bucket, top rows by score with links + `recruiter_id` for handoff; Overview **Manager digest queue** + cohort table **Latest hourly at-risk (shadow cohort)** with row + **bulk** **Remind** (`POST /reminders` / `POST /reminders/bulk`, `source=risk_intel.shadow_digest`) and **Assign to me** (`PATCH /candidates/:id` `recruiter_id`).
  - Phase D (manager digest queue): `GET /analytics/risk-intelligence/manager-digest-queue` (recent buckets, `unread` vs last `POST .../ack`, query `min_band`); `POST /analytics/risk-intelligence/manager-digest-queue/ack` — `activity_log` `risk_intel.manager_digest_ack` (per user); Overview UI: band selector + **Show** filter (all / unread / reviewed buckets) + **Mark through latest** + **Mark reviewed**; `list_shadow_digest_bucket_summaries` in `risk_intel_v1`.
  - Phase D (digest email, opt-in): after hourly persist, `maybe_send_risk_shadow_digest_email` (`backend/app/services/risk_intel_digest_email.py`) — `Tenant.settings.risk_model_v1.digest_email` (`enabled`, `to`, `to_roles`, `min_band`, `max_rows`, `skip_if_empty`); recipients = explicit `to` ∪ active users with `user_memberships` for `to_roles` (aliases: admin→administrator, manager→supervisor, …); uses tenant SMTP / webhook (`send_email_for_tenant`); dedupe + `activity_log` action `risk_intel.digest_email_sent` per `bucket_start`. Requires `FRONTEND_URL` (or `settings.frontend_url`) for deep links in the body.
- **Key fixes implemented** (high-level):
  - module visibility gating enforced via tenant module flags + effective role-module matrix
  - communications readiness verified (inbox, send, templates/signatures, scheduler/worker/audit depth checks); **email poll worker** — tenant load + commit on Sent ingest + client backoff on silent poll errors (`2026-03-23`)
  - leads path validated (source → lead → assignment → action) + retry semantics
  - SPA fallback for local E2E routing
  - mock email delivery mode for safe staging/local verification

---

## Audit vs requirements docs

### `docs/pipe.md` (product blueprint)

- **Implemented / aligned**
  - Shell layout (Topbar/Sidebar/Workspace); empty states; global search (**typed** results: candidates, clients, **vacancies**, documents, **conversations** (`GET /communications/threads?q=` + **`buildInboxThreadPath`** (+ optional **`channel=`**) — **`2026-03-24u`**, **`2026-03-26`**), **tasks** (**`GET /reminders?q=`**, assignee **mine** or **team** (manager roles) — **`2026-03-24v`** + **`2026-03-24w`**; deep link **`/app/tasks?t_q=`** + **`t_id=`** + optional **`t_assignee=team`**), **invoices**, **service orders** — parallel APIs; **`2026-03-24t`**) + **client-side merged ranking** (**`mergeSearchResultsHeuristic`** — title/subtitle match tiers + cap consecutive same type — **`2026-03-24x`**) + **⌘K quick jump** tiles incl. **Calendar**, **SLA**, **Automations** when gated — **`2026-03-24s`**) + **Topbar Create** menu to new-entity routes — **not** a single unified in-bar composer without navigation). **Unified Inbox:** **`/app/inbox`** = hub + center for **all** licensed channels; legacy **`/app/messages`** / **`/app/email`** → redirect (**`2026-03-26`**). **Public candidate capture:** **`/public/scan`** removed (**`2026-03-25`**); uploads via **`/public/apply`** + **`?doc=`** (**`2026-03-25a`**). **Still not:** single backend relevance score / unified search endpoint — *Screen contracts* **Global search**.
  - Next action: reminders + leads follow-up; candidates **list preview** (work panel) with Composer/Focus/**History** (`GET /candidates/{id}/timeline`); **`/app/candidates/no-next-action`** view.
  - Document intelligence + compliance rulesets; stage-aware pipeline gates and overrides (see **§3) Stage-based pipeline blockers** below). **Pipeline-completed** stages (**`employed` / `probation_ok` / `rejected` / `declined`**) — document forward gate off server-side + UI; ops/risk alignment per **Change log `2026-03-27`–`28`** and **`docs/pipe.md` §25**.
- **Still open vs pipe.md (tracked in Backlog)**
  - **Command center v2** (R1.5): **shipped + product sign-off PASS `2026-03-23`** (см. **§ R1.5 — Evidence**). Список-превью по дизайну остаётся **triage** (не полный паритет с карточкой по сценариям глубокой работы).
  - **Perf evidence** vs aggressive numeric targets in `pipe.md` (baseline exists; formal budgets — see R4).

### `docs/pipedesign.md` (landing/SEO/design system)

- **Implemented / aligned**
  - Public routes, SEO meta (`useSeoMeta`), sitemap in static gate.
  - **Tokens:** Tailwind `brand.*` + typography aligned to `pipedesign.md` (primary `#3FA3A8`, accent `#2E6F74`, section bg `#F4F8F9`; Inter canonical). Further drift checks = optional visual regression pass.

---

## Backlog (what’s left)

### Release-pass

- [x] **Production run: Scenario A (`services`) on `victoria-services`** — **PASS `2026-03-23`**. Evidence: **Expanded backlog → R0.1 — Evidence**; run-sheet **§ R0.1 — Run-sheet**.

### Product / architecture gaps (summary)

- [x] **UOS / IA — core (`2026-03-28`):** **Messages + Email** → unified **`/app/inbox`** (**`2026-03-26`**); **sidebar** **Core / Business / System** (**`2026-03-26e`–`f`**); **bell → Inbox** deep links + manual **escalation** bridge (**`2026-03-26b`**, **`d`**); **notification** drawer **tier** chips (**`2026-03-27a`**); **event→Activity** для **vacancy recruiting** (**`26c`**) и **candidate stage** (**`2026-03-24f`**). Дневной операционный контур закрыт; остаток — **stretch** (строка ниже).
- [ ] **UOS / IA — stretch:** поле **`priority`** у уведомлений (API + UI); исчерпывающий **каталог event→Activity** в SSOT; **нарратив escalation** в *Operating model*; прочая полировка IA.
- [x] **Candidates command center v2** (R1.5 below): **PASS `2026-03-23`** — engineering (Phases A–D) + product sign-off vs **`pipe.md`** daily loop; evidence **§ R1.5 — Evidence**.
- [x] **Services module v2** (R3.3): sell → fulfill → invoice → collect + analytics — **PASS `2026-03-23`**; evidence **§ R3.3 — Evidence**.
- [x] **Performance (R4) — policy (`2026-03-28`):** формальное расширение evidence / CI под жёсткие цифры **`pipe.md`** **не требуется**, пока эти цели не стали **договорным SLA**; при появлении SLA — отдельный проход.
- [x] **Risk intelligence v1** (R3.4): **PASS `2026-03-23`** — Phases A–D v1 (ops analytics, hourly job + shadow cohorts, candidate surfaces, opt-in automations / **stage_gate** / digest / manager queue / digest email) + **Settings → Risk intelligence** + telemetry; evidence **§ R3.4 — Evidence**; spec **Risk intelligence v1**.

### Marketing/SEO/design vs `pipedesign.md`

- [x] **Design tokens** baseline aligned (see Audit section).

### Hygiene / repo policy (must stay enforced)

- [x] Ensure **no** `.venv/` content is tracked by git — **verified `2026-03-23`** (`git ls-files` → 0 under `.venv/`)
- [x] Ensure **no** `node_modules/` content is committed — **verified `2026-03-23`** (`git ls-files` → 0 under `node_modules/`)
- [x] **Runtime uploads / local artifact trees out of git (`2026-03-28`):** **`git rm -r --cached backend/uploads backend/app/uploads`** — **291** path removed from index; **`git ls-files`** → **0** under those prefixes (verified same day). Файлы на диске сохранены. Не коммитить новые загрузки — **`.gitignore`**. Скриншоты/JSON для ручных чеклистов — **`docs/manual-checklist/_artifacts/`** (gitignored) или вне репозитория.

**Detailed tickets:** *Expanded backlog (R0–R4)* later in this file.

---

## Change log (SSOT-managed)

- `2026-03-28` (**SSOT / repo hygiene — upload index clean + backlog 100% summary slice**): **`git rm -r --cached backend/uploads backend/app/uploads`** — сняты с индекса **291** путь (файлы локально остаются); **`git ls-files`** **`backend/uploads/`**, **`backend/app/uploads/`** → **0**. **Backlog (summary):** **UOS/IA core** → **`[x]`**; **stretch** → отдельный **`[ ]`**; **Performance (R4)** → **`[x]`** по политике «до договорного SLA»; **hygiene uploads** → **`[x]`**. **Current status** — *Next focus* обновлён. Snapshot **2026-03-28e**.
- `2026-03-28` (**Candidates — pipeline completed: doc gate + stage rail**): **`PIPELINE_COMPLETED_STAGE_CODES`** (**`constants/stages.py`**, публичный **`__all__`**) — документы **не** блокируют пайплайн в UI и на сервере: **`hiring_pipeline_gates.docs_pipeline_blocks_forward_resolved`** ранний выход; **`candidateStageDocPolicy.docsPipelineBlocksForwardResolved`** (фронт); **`CandidateCard`** — **`effectiveStageForDocPolicy`** / **`canonicalStageForOps`** с приоритетом сохранённой стадии при финале; **`CandidateStageDecisionPanel`** — без барьеров / «следующего шага» для финала; **`stageOperationalHints.operationalHintForStage`** — **`null`** для финальных стадий (не подсказывать «двигать вперёд» для **`employed`/`probation_ok`**). **Backend tests** — **`tests/test_hiring_pipeline_gates.py`**. **Frontend tests** — **`candidateStageDocPolicy.test.ts`**, **`stageOperationalHints.test.ts`**; **`vitest.config.ts`** — **`mergeConfig`** с **`vite.config`**. **CI** — **`.github/workflows/frontend-static-qa.yml`** шаг **`npm run test`** перед **`qa:static`**. **`GET /candidates` + `include_risk`:** если все кандидаты на странице в **`PIPELINE_COMPLETED_STAGE_CODES`**, **`candidates/router.py`** отдаёт нулевой risk без **`compute_candidate_risk_scores`**. **`GET /candidates/{id}`** и **`GET /candidates/{id}/work-panel`** (**`candidate_work_panel._profile_ops`**) — при **`is_pipeline_completed_stage(stage)`** нулевой risk без **`compute_candidate_risk_map_for_ids`**. Хелпер **`constants/stages.is_pipeline_completed_stage`**. **`candidate_risk_stage_gate`:** не вызывает risk map при **`is_pipeline_completed_stage(old_stage)`**. Snapshot **2026-03-28a** (доп. **28c**–**28d**: list + detail/work-panel risk fast-path + stage gate).
- `2026-03-28` (**Infra — Compose/Caddy: legacy scanner service removed**): **`docker-compose.yml`** — удалён сервис **`scanner-api`** (контекст **`./scanner-backend`** отсутствует в репозитории после вывода публичного сканера). **`Caddyfile`** — убраны отдельные **`reverse_proxy`** для **`/scan/*`** и **`/api/uploads/scanner/*`**; трафик **`/api/*`** идёт в **`backend`**. **`.gitignore`** — **`backend/.venv-ci/`** (локальный venv для прогона узких pytest без загрязнения корня). Snapshot **2026-03-28b**.
- `2026-03-27` (**Candidates — pipeline completed: no next-step UX + ops/risk exclusion**): **`PIPELINE_COMPLETED_STAGE_CODES`** = **`TERMINAL_STATUSES`** ∪ **`employed`** (**`constants/stages.py`**) — финал успеха или отказа; **`risk_intel_v1`** — нулевой score + исключение из **hourly baseline**; **`ops-counters`**, **goals**, **`GET /candidates/no-next-action`** — только активный пайплайн. **Frontend:** **`candidatePipelineCompleted.ts`**, **`CandidateNextActionPanel`**, превью без **Risk (v1)**; i18n **`pipeline_completed_*`**. **Tests** — **`test_score_single_candidate_pipeline_completed_zero`**. Snapshot **2026-03-27b** (расширено **27c**: +**`employed`**, **`probation_ok`**, переименование константы).
- `2026-03-27` (**UOS / IA — notification drawer attention tiers**): **`Topbar.tsx`** — each notification row shows **`NotificationAttentionTierChip`** (**Critical** / **High** / **Normal**) alongside existing UOS **group** chip; mapping reuses **`getNotificationAttentionTier`** (same heuristic as bell **CRITICAL**/**HIGH**). i18n **`app.topbar.notifications.tier.{critical,high,normal}`** **en/pl/ru**. SSOT *Honest gap* **Notification badge…** row; snapshot **2026-03-27a**.
- `2026-03-26` (**UOS / IA — sidebar: SSOT Business order + Account**): **`Sidebar.tsx`** — **Business** primary keys follow § *Target sidebar* (Candidates, Clients, **do-procesowania**, Vacancies, Orders, Services, Invoices, Documents, Leads) for **all** tenant **`business_type`** values (no per-type reorder). **Profile** → non-collapsible **Account** block (label **`app.shell.sidebar.account`** **en/pl/ru**) above **Settings**; **Settings** group no longer lists **profile**. Snapshot **2026-03-26f**.
- `2026-03-26` (**UOS / IA — sidebar: Core / Business / System + Settings merge**): **`Sidebar.tsx`** — primary nav split **Core** (Overview, Inbox, Tasks, Calendar, SLA), **Business** (module order by **`businessType`**: services / employer / agency), **System** (**Automations** only); **client tenant** — flat list (no duplicate **SLA** collapsible). **Settings** group: **`profile`**, existing admin keys, then **`communications-setup`** + **`command-audit`** after **`settings-communications`** (removed separate **Communications workspace** group). Inbox row: compact **Messages** / **Email** chips (**`flex-wrap`**, **`text-[11px]`**). i18n **`app.shell.sidebar.core_workspace`**, **`business`** **en/pl/ru**. *Navigation (shipped vs target)*; backlog UOS line; snapshot **2026-03-26e**.
- `2026-03-26` (**UOS / IA — bell notification → unified Inbox**): **`Topbar.tsx`** — **`notificationThreadId`** / **`notificationThreadChannel`**; **`canInboxDeepLink`** (**`useCommunicationsAccess`** messages/email); **`buildInboxThreadPath`** for **Messages** group + **SLA** group when **`thread_id`** present (**Open in Inbox**); footer shortcut **`/app/inbox`**; **`notificationRank`** boost **`communications_thread_escalated`**; **`getNotificationTitle`** localized escalated title. i18n **`app.topbar.notifications.open_in_inbox`**, **`app.notifications.communications_thread_escalated_title`** **en/pl/ru**. SSOT *Honest gap* **Notification badge…** row; **Current status**; snapshot **2026-03-26d**.
- `2026-03-26` (**UOS — event→Activity: vacancy recruiting**): **`uos_auto_activities`** — **`vacancy_is_recruiting`**, **`ensure_vacancy_recruiting_follow_up_task`** (**`uos_vacancy_recruiting_follow_up`**, **`vacancy_recruiting_follow_up`** tenant flag); **`VacancyService.create`** / **`patch`** + **`vacancies/router.py`** (**`actor_user_id`** from **`get_current_user`**); **`reminders_v2`** **`_SLA_REMINDER_TYPES`**. **Tests** — **`tests/api/test_uos_vacancy_recruiting_auto_activities.py`**. SSOT *Honest gap* event→Activity row; *Current code pointers* (Vacancies); snapshot **2026-03-26c**.
- `2026-03-26` (**UOS — manual Inbox escalation → Tasks + bell + audit**): **Backend** — on **first** **`PATCH /communications/threads/:id`** merge where **`thread_meta.ops.mode`** becomes **`escalated`** (validated reason + target): **`log_activity`** **`communications.thread.ops_escalated`**; **`create_notification`** **`communications_thread_escalated`** per resolved recipient (**`user_id`** / **`role`** via **`user_memberships`** / **`queue`** → **supervisor** + **administrator**); **`create_reminder`** type **`communications_thread_escalated`** (SLA projection via **`reminders_v2`** **`_SLA_REMINDER_TYPES`**); dedupe notifications (**`dedupe_key`**) + skip duplicate open reminders per assignee+thread. **Frontend** — **`Topbar.tsx`** **`getNotificationUosGroup`** treats **`communications_thread_escalated`** like SLA for bell grouping. **Tests** — **`tests/api/test_communications_ops_escalation_bridge.py`**. SSOT *Honest gap* escalation row; *Current code pointers* (workflow card); snapshot **2026-03-26b**.
- `2026-03-26` (**UOS / IA — Unified Inbox 100% single surface**): **Frontend** — **`/app/inbox`** hub + **`/app/inbox/threads/:id`** center share **`fetchInboxThreadPool`** (**`utils/inboxThreadLoad.ts`**); URL state **`inboxUrlQuery`** (**`channel`**, **`folder`**, **`q`**, **`candidateId`**, **`assignedToMe`**, **`hasAssignee`**, **`unlinked`**); email **folder rail** (**`InboxEmailFolderRail.tsx`**), **Sync** + **`useEmailInboundSync`** (auto poll); hub filters **in work** / **later**, **pinned-first** sort in **`InboxUnifiedThreadList`**; **`inboxDeepLinks`** passes optional **`channel`** on thread/hub paths; **`search.ts`** conversation links scope by channel. **`CommunicationsMessagesPage`** / **`CommunicationsEmailInboxPage`** → **`<Navigate>`** to Inbox (**`useLayoutEffect`** stash **`code`** on **`/app/email`** for OAuth). **Topbar**, **Sidebar** (nested **Messages** / **Email** + active state from **`channel`**), **`WorkspaceTopNav`**, **`CandidatesSelectedPanel`**, **`activationRoutes`**, **`useCommunicationsThread`** default list path, **`CommunicationsThreadPage`** link. i18n **`communications_inbox_hub.*`** **en/pl/ru**. SSOT *Honest gap* **Unified Inbox** → **shipped**; new gap note **email bulk command templates**; *Navigation*, *Code pointers*, *Backlog* UOS line; snapshot **2026-03-26a**.
- `2026-03-25` (**Public intake — `doc` query deep focus**): **`PublicIntakeNew.tsx`** — on **documents** step, after the license branch is resolved, **`?doc=<DocumentType>`** selects the matching index in **`documentFlow`** (pairs with Telegram/backend links **`/public/apply/{token}?mode=documents&doc=`**). SSOT *Honest gap* row *Public candidate documents*, snapshot **2026-03-25a**.
- `2026-03-25` (**Public document scanner — removed as product artifact**): **Frontend** — удалены **`PublicScanPage`**, **`src/components/public-scanner/*`**, **`src/modules/public-scan/*`**, **`src/modules/public-intake/scan/*`**, **`src/api/scanner.ts`**, **`scannerPresets.ts`**; **`App.tsx`** — **`/public/scan`** и **`/public/scan-sessions`** → редирект на **`/public/intake`**; **`PublicApplyPage`** — убран неиспользуемый вызов сессии сканера. **`robots.txt`** — убраны **`Disallow`** для scan (маршрут не существует). **Backend** — **`main.py`**: роутеры **`api.v1.scanner`** и **`api.public.scanner`** **не монтируются** (пакет **`backend/app/scanner`** и **`services/scanner.py`** остаются в коде/БД до отдельного решения — например **LLM/vision**). **Telegram** — **`communications.py`**, **`candidate_telegram_notifications.py`**: ссылки «сканер» заменены на **`/public/apply/{token}?mode=documents`**. **Тесты** — удалён **`test_public_scanner_flow`**; поправлены presign/upload в **`test_public_magic_link_flow`** / **`test_public_intake_matches_phone_*`**. **Репо** — удалены **`HFSCANNER_SPEC.md`**, **`TEST_SCANNER.md`**, **`docs/scanner/*`**, **`docs/specs/tasks/document_scanner*.md`**, **`documents_scaner.md`**, **`scanner-backend/`**, корневые и **`backend/test_scanner*.py`**, **`backend/tests/test_scanner_module.py`**, **`backend/scripts/test_scanner.py`**, **`backend/app/scanner/test_scanner.py`**. **`docs/specs/core.md`**, **`candidate-intake-via-telegram-execution-plan.md`** — актуализированы. **План:** новый захват документов — отдельная инициатива (**LLM** / обучение), не восстанавливать текущий OpenCV-публичный UI без явного решения.
- `2026-03-25` (**Product — guided execution vs manager bypass**): SSOT **§3) Stage-based pipeline blockers** — new paragraph **Guided execution & manager bypass (operator UX)** (soft guidance, no hard-lock dogma; exceptions via manager-approved waiver/override + audit).
- `2026-03-24` (**IA — global search: client merged ranking heuristic**): **`search.ts`** — after parallel fetches, **`mergeSearchResultsHeuristic`**: **`matchQualityScore`** on **`title`/`subtitle`** (exact → prefix → substring / word boundary); sort by score then title; **`interleave`** with **`MAX_CONSECUTIVE_SAME_TYPE`** (**2**) so results are not one solid block per module. No unified **`/search`** API. SSOT *Global search* honest-gap row, **`pipe.md` audit**, snapshot **2026-03-24x**.
- `2026-03-24` (**IA — global search: task deep links + team reminder scope**): **`search.ts`** — **`SearchGlobalOptions.reminderAssigneeScope`**; managers/admins (**`Topbar`** role heuristic, aligned with **`RemindersPage`**) pass **`team`** → **`listReminders`** **`assignee_scope=team`**; task result links **`t_q`**, **`t_id`**, and **`t_assignee=team`** when applicable. **`RemindersPage`**: query **`t_id`** — pin row in client filter, **`loadReminders`** fetches **all statuses** while **`t_id`** present (so completed tasks resolve), auto-switch to **Tasks** tab, **scroll** + **ring** highlight, strip **`t_id`** after focus; if target is **done/cancelled** and filter was **active**, temporarily widen to **all** for **SLA flat** visibility. SSOT *Global search* honest-gap row, **`pipe.md` audit**, snapshot **2026-03-24w**.
- `2026-03-24` (**IA — global search: tasks / reminders**): **Backend** — **`reminder_tasks.list_reminders`**: optional **`q`** (**`ILIKE`** on **`title`**, **`description`**, **`message`**), optional SQL **`limit`**; **`reminders_v2`** **`GET /reminders`**: query **`q`**, **`limit`** (1–200; default cap **80** when **`q`** set without **`limit`**). **Frontend** — **`client.listReminders`** **`q`** / **`limit`** / **`signal`**; **`search.ts`** **`searchGlobal`** — **`listReminders({ q, limit: PER_TYPE, assigneeScope: 'mine', signal })`**, **`GlobalSearchResult`** **`task`**, link **`/app/tasks?t_q=`** (Tasks page filter); **`MAX_RESULTS`** **24**. **`Topbar`** **`RESULT_LABEL_KEYS.task`**; i18n **`app.topbar.search.results.task`**, **`placeholder`** **en/pl/ru**. SSOT *Global search* honest-gap row, **`pipe.md` audit**, snapshot **2026-03-24v**.
- `2026-03-24` (**IA — global search: inbox threads / conversations**): **`search.ts`** — **`listCommunicationThreads({ q, signal })`** in **`searchGlobal`** (same **`q`** as **`GET /communications/threads`** — subject / last preview / ref; backend already shipped); links **`buildInboxThreadPath`** (optional **`candidateId`** when **`linked_candidate_id`**). **`communications.ts`** — **`listCommunicationThreads`** accepts **`signal`** (abort). **`GlobalSearchResult`** **`conversation`** + **`Topbar`** **`RESULT_LABEL_KEYS`**; i18n **`app.topbar.search.results.conversation`**, **`placeholder`** **en/pl/ru**; **`MAX_RESULTS`** **21**. SSOT *Global search* honest-gap row, **`pipe.md` audit**, snapshot **2026-03-24u**.
- `2026-03-24` (**IA — global search: vacancies + invoices + orders**): **`hostflow-frontend/src/api/search.ts`** — **`searchGlobal`** parallel loads **vacancies** (`GET /vacancies?q=`), **invoices** (`GET /invoices?q=`), **service orders** (`GET /service-orders?q=`) alongside existing candidates/companies/documents; **`GlobalSearchResult`** types + **`Topbar`** **`RESULT_LABEL_KEYS`**; i18n **`app.topbar.search.results.*`**, **`placeholder`** **en/pl/ru**. **Backend** — **`invoices/crud.py`** **`list_invoices`**: optional **`q`** — **`invoice_number`** ILIKE or **`company_id`** in companies **`name`** ILIKE (**`invoices/router.py`** query **`q`**); **`additional_services.py`** **`list_orders`**: optional **`q`** — order **`id`** or **`notes`** ILIKE; **`services.py`** **`list_service_orders`**: query **`q`**, cap **80** rows when **`q`** set. **`client.ts`** **`listInvoices`** accepts **`q`**; **`listVacancies`** sends **`params.q`** (fixes **`search`** → API **`q`**). SSOT *Screen contracts* **Global search**, **`pipe.md` audit**, snapshot **2026-03-24t**.
- `2026-03-24` (**IA — Topbar ⌘K quick jumps: Calendar, SLA, Automations**): **`Topbar.tsx`** — **`quickTargets`** adds **`/app/calendar`** (**`notifications.view`** + **`useCommunicationsAccess('calendar')`**), **`/app/sla-incidents`** (**messages** or **email**), **`/app/automations`** (**`notifications.view`**, **`!isClientTenant`** — same visibility as primary **`Sidebar`**). Reuses **`app.nav.items.*`** labels; **`appendSearchQueryParam`** unchanged. SSOT *Honest gap* **Top bar quick jump**, **`pipe.md` audit** shell, **Progress**, snapshot **2026-03-24s**.
- `2026-03-24` (**Ops counters — open service orders**): **`backend/app/api/v1/analytics.py`** — **`OpsCountersOut`** + **`GET /analytics/ops-counters`**: **`open_service_orders`** (tenant-wide count where **`service_orders.status`** not **`completed`** / **`cancelled`**). **Frontend** — **`api/analytics.ts`**; **`Dashboard.tsx`** operational strip tile (**`services.view`**) → **`/app/orders`**; i18n **`app.dashboard.ops.open_service_orders*`** **en/pl/ru**. **`canServicesOpsWidgets`** rename (was invoice-only) for shared **`services.view`** gates. SSOT *Dashboard ops summary* row, **Progress**, snapshot **2026-03-24r**.
- `2026-03-24` (**Ops counters — open vacancies + pipeline count**): **`backend/app/api/v1/analytics.py`** — **`OpsCountersOut`** + **`GET /analytics/ops-counters`**: **`open_vacancies`**, **`open_vacancies_candidates`** (**`resolve_restricted_acl`**, **`Vacancy.status=open`**, **`is_archived=false`**, candidate rows with **`vacancy_id`** in scoped vacancies). **Frontend** — **`api/analytics.ts`** **`OpsCounters`**; **`Dashboard.tsx`** **Open vacancies** widget prefers **`getOpsCounters`** (exact totals), else **`listVacancies`** fallback (**200** cap). SSOT *Dashboard ops summary* row, **Progress**, snapshot **2026-03-24q**.
- `2026-03-24` (**IA — standalone `/app/orders` route**): **`routes.tsx`** — **`APP_ROUTES`** **`orders`** → **`OrdersStandaloneRedirect`** (**`useSearchParams`** → **`/app/services?tab=orders`** + preserved query); **`NAV_ITEMS`** **`service-orders`** → **`/app/orders`**. **`modules/services/utils.ts`** — **`buildServicesWorkspaceUrl`**: **Orders** tab → **`/app/orders`** (no redundant **`tab`** on canonical URL). **`ServicesPage.tsx`**, **`Sidebar.tsx`** (**`ordersNavActive`** includes **`/app/orders`**), **`Topbar`**, **`AutomationsHubPage`**. SSOT *Navigation (shipped)*, *Honest gap* *Orders + Invoices…*, **Progress**, snapshot **2026-03-24p**.
- `2026-03-24` (**IA — Dashboard open vacancies ops tile**): **`Dashboard.tsx`** — operational strip adds **Open vacancies** (**`listVacancies`**, **`status=open`**, limit **200**) for **`vacancies.view`**: main **count** ( **`200+`** when capped), subtitle **sum `candidate_count`** on loaded rows, hint when capped; drill **`/app/vacancies?status=open`**; **Refresh** reloads ops counters + invoice widget + vacancy summary. i18n **`app.dashboard.ops.open_vacancies*`** **en/pl/ru**. SSOT *Honest gap* **Dashboard ops summary (recruitment strip)** row, **Progress**, snapshot **2026-03-24o**.
- `2026-03-24` (**IA — Topbar quick create menu**): **`Topbar.tsx`** — **Create** (`IconPlus`) dropdown (**`quickCreateItems`**) routes to **SSOT quick-create** targets: **`/app/candidates/new`** (**`candidates.manage`**), **`/app/clients/new`** (**`companies.manage`**), **`/app/vacancies/new`** (**`vacancies.view`**), **`/app/orders`** (**`services.view`** + **`services.orders.manage`**), **`/app/tasks`** (**`notifications.view`**), **`/app/calendar`** (**`notifications.view`** + **`useCommunicationsAccess('calendar')`**), **`/app/invoices/new`** (**`services.view`**). Click-outside + **Esc**; **⌘K** closes menu. i18n **`app.topbar.quick_create.*`** **en/pl/ru**. SSOT *Honest gap* **Top bar quick create** row, **`pipe.md` audit** shell line, **Progress**, snapshot **2026-03-24n**.
- `2026-03-24` (**IA — Topbar ⌘K quick jumps + Automations execution shortcuts**): **`Topbar.tsx`** — global search modal **quick** tiles are **`usePermissions`**-gated: **candidates, clients, vacancies, orders (**`/app/orders`**), invoices, leads, documents, tasks, inbox**; **`appendSearchQueryParam`** appends **`q=`** without breaking paths that already have a query. **`AutomationsHubPage.tsx`** — section **Fulfillment & billing (execution)** → **Orders** + **Invoices** when **`services.view`**. i18n **`app.automations.hub.ops_*`** **en/pl/ru**. SSOT *Honest gap* (quick jump row, *Automations* row), **`pipe.md` audit** shell line, **Progress**, snapshot **2026-03-24m**.
- `2026-03-24` (**IA — first-class Orders nav**): **`routes.tsx`** — **`NAV_ITEMS`** **`service-orders`** → **`/app/services?tab=orders`** (**`services.view`**), placed before **Services** in **`Sidebar`** business order (agency / employer / services tenant layouts). **`Sidebar.tsx`** — **`ordersNavActive`** vs **`servicesModuleNavActive`** from **`tab`** query (**`IconClipboardList`** vs checklist for **Services**); **`moduleByItemKey`** maps **`service-orders`** → **services** module. i18n **`app.nav.items.orders`** **en/pl/ru**. SSOT *Navigation (shipped)*, *Honest gap* *Orders + Invoices…*, **Progress**, snapshot **2026-03-24l**.
- `2026-03-24` (**Vacancy headcount target — API + list/detail UI**): **Backend** — Alembic **`202603241200_vacancy_headcount`** adds **`vacancies.headcount_target`** (nullable **`Integer`**); **`Vacancy`** model; **`VacancyIn`** / **`VacancyOut`** / **`VacancyPatch`** + **`vacancy_to_out`** / **`VacancyService`** create + patch (**`model_fields_set`** clears on **0** / **null**). **Frontend** — **`api/vacancies.ts`**, **`vacancyUtils.buildVacancyPayload`**; **`VacancyDetail`** form + ops strip (**`current` / `target`**); **`VacancyList`** column **Headcount** (**`candidates/target`**, sort, CSV, column picker); i18n **en/pl/ru**. SSOT *Honest gap* *Vacancy…*, **Progress**, snapshot **2026-03-24k**. **Deploy:** run **`alembic upgrade head`** (revision chains from **`202603221400_risk_intel_hourly_shadow`** — adjust if your DB uses a different Alembic tip).
- `2026-03-24` (**UOS / IA — Dashboard invoice money + invoices nav permission + queue deep link**): **`Dashboard.tsx`** — operational strip widget **Open invoice balance** (**`listInvoices`**, limit **200**, **`invoiceOutstandingAmount`** / **`invoiceDaysPastDue`**) for **`services.view`**; refresh reloads ops counters + invoice summary; drill-down **`/app/invoices`** or **`?queue=overdue_unpaid`**. **`InvoicesPage.tsx`** — URL **`queue`** syncs queue filter (**`delivery_failed`**, **`missing_recipient`**, **`overdue_unpaid`**, **`needs_correction`**, **`all`**). **`routes.tsx`** — **`NAV_ITEMS`** **`invoices`** + invoice CRUD routes use **`services.view`** (repl. **`admin.users`** placeholder). i18n **`app.dashboard.ops.invoice_*`** **en/pl/ru**. SSOT *Honest gap* *Orders + Invoices…*, **Progress**, snapshot **2026-03-24j**.
- `2026-03-24` (**UOS / IA — Client receivables on company overview + default home migration**): **`CompanyReceivablesOverview.tsx`** — **`listInvoices({ company_id, limit: 100 })`**, **`invoiceOutstandingAmount`** / **`invoiceDaysPastDue`** (same heuristics as **`InvoicesPage`**); **Overview** card on **client** companies (**`Companies.tsx`**). **`defaultAppHome.ts`** — **`maybeMigrateDefaultAppHomeToTasks`** + **`hf:default_app_home:legacy_v1_tasks`** (one-time: unset **`hf:default_app_home`** → **Tasks** when user has **`notifications.view`**); **`AppShell.tsx`** runs migration on authed shell load. i18n **`app.companies.detail.overview.receivables.*`** **en/pl/ru**. SSOT *Honest gap* rows *Default post-login…*, *Clients…*, snapshot **2026-03-24i**.
- `2026-03-24` (**UOS / IA — Tasks default SLA queue + Automations policy hub**): **`RemindersPage.tsx`** — default **`taskListMode`=`sla_queue`** for **new** users; **legacy** persisted state **without** `taskListMode` → **`by_due`**. **`AutomationsHubPage.tsx`** — section **Policy & enforcement (settings)** with deep links (**`/app/settings/risk-intel`**, **`hiring-pipeline-gates`**, **`ruleset`**, **`docs`**, **`communications/sla`**, **`/app/settings`**), permission-gated; i18n **`app.automations.hub.policy_*`** **en/pl/ru**. SSOT *Honest gap* rows *Tasks…*, *Automations…*, *Hygiene* note, backlog **UOS / IA**, snapshot **2026-03-24h**.
- `2026-03-24` (**UOS / IA — Unified Inbox deep links + candidate scope**): **Frontend** — **`utils/inboxDeepLinks.ts`**; **`InboxUnifiedThreadList`** **`linkedCandidateId`** + scoped thread URLs; **`CommunicationsInboxHubPage`** / **`CommunicationsInboxCenterPage`** **`?candidateId=`** filter + banner. **`RemindersPage`**, **`ActivitiesPanel`**, **`CommunicationsSlaIncidentsPage`**, **`CandidateCommunicationSection`** (email included in linked list), **`CandidateCard`**, **`CandidatesSelectedPanel`** — routes to **`/app/inbox`** / **`/app/inbox/threads/…`**. i18n **en/pl/ru**. SSOT *Honest gap* row *Unified Inbox…*, snapshot **2026-03-24g**.
- `2026-03-24` (**UOS — candidate stage → Activity v1**): **`uos_auto_activities`** — **`ensure_candidate_stage_follow_up_task`** (**type** **`uos_candidate_stage_follow_up`**, 72h due, refresh open row on re-advance; skip **terminal** stages via shared **`_tenant_funnel_stage_code_is_terminal`**); tenant flag **`candidate_stage_follow_up`**. **`candidates/service.py`** — after successful stage change (**`update_candidate_full`**, **`bulk_update_stage`**). **`reminders_v2`** **`_SLA_REMINDER_TYPES`**. Tests: **`tests/api/test_uos_candidate_stage_auto_activities.py`**. SSOT *Honest gap* first row + snapshot **2026-03-24f**.
- `2026-03-24` (**Rollout 9 — Scheduling absorb: profile + Calendar (IA)**): **Frontend** — **`ProfilePage.tsx`**: **Scheduling & availability** section (`md:col-span-2`), gated by **`notifications.view`** + **`useCommunicationsAccess`** (**calendar**, **myAvailability**, **teamAvailability**, **timeOffRequests**); **`Link`**s to **`/app/calendar`**, **`/app/my-availability`**, **`/app/team-availability`**, **`/app/time-off`**; **team** link suppressed when **solo workspace** (**`getTeamOverview`** for admin/supervisor, same **`isSoloWorkspace`** heuristic as **`Sidebar`**). i18n **`app.profile.scheduling.*`** **en/pl/ru**; scheduling link labels reuse **`app.communications.calendar.scheduling.*`**. SSOT *Honest gap* row *Calendar / scheduling*, rollout **(9)** progress, snapshot **2026-03-24e**.
- `2026-03-24` (**Rollout 8 — Automations as dedicated module (IA)**): **Frontend** — **`AutomationsHubPage.tsx`** at **`/app/automations`** (hub cards → rules + log). **`routes.tsx`**: **`NAV_ITEMS`** **`automations`**; removed duplicate nav entries for **`automation-rules`** / **`automation-log`** (routes unchanged). **`Sidebar.tsx`**: **Automations** in primary row after **Documents**; **`automationsNavActive`** for **`/app/automation*`**; dropped empty **System** collapsible that only held automations. **`AutomationRulesPage`** / **`AutomationLogPage`**: back link to hub. **`LeadsPage`**: Meta admin tab CTA → hub. **`routeBundleCrmMore`**, **`appRoutePages`**. i18n **`app.nav.items.automations`**, **`app.automations.hub.*`** **en/pl/ru**. SSOT *Navigation (shipped)*, *Honest gap*, rollout **(8)**.
- `2026-03-24` (**Rollout 7 — Orders + Invoices: process + money control (UI)**): **Frontend** — **`modules/services/utils.ts`**: **`resolveServiceOrderNextAction`**, **`invoiceOutstandingAmount`**, **`invoiceDaysPastDue`** (shared heuristics). **`ServicesPage.tsx`** (**Orders** tab): each order row shows **Next** line (fulfillment + billing heuristic); **order detail** **ops strip** — next step, **blocking** count, **missing docs** count, **invoice days past due** (when outstanding), **updated** relative (**`date-fns`**). **`InvoicesPage.tsx`**: table columns **Days overdue** + **Outstanding** (balance due). i18n **`app.services.orders.next_action`**, **`app.services.orders.ops`**, **`app.services.orders.list.next_step`**, **`app.invoices.col_days_overdue`** **en/pl/ru**; PL **`app.invoices.fields.outstanding`** corrected. SSOT *Honest gap* + rollout **(7)**.
- `2026-03-24` (**Rollout 6 — Clients list + card: pipeline + recruitment + money**): **API** — **`CompanyOut`** **`recruitment_vacancies_active`**, **`recruitment_candidates_total`**; **`company_recruitment_metrics_for_list`** in **`counters.py`** (batch, same candidate scope as list); **`GET /companies/`** query **`include_recruitment_metrics`**; **`GET /companies/{id}`** optional **`include_service_metrics`** + **`include_recruitment_metrics`**. **Frontend** — **`Companies.tsx`**: list load passes both include flags; table columns **Active vacancies** (→ **`/app/vacancies?company=`**) + **Candidates** (→ **`/app/candidates`**); client **hero** badges **Party role** + **client stage**; **KPI** row adds live recruitment + service order counts/revenue; grid **`lg:grid-cols-4`** for client cards. **`api/types/company.ts`**. i18n **en/pl/ru**. **Routing** — CRM list at **`/app/clients/directory`** (**`NAV_ITEMS`**, **`Companies` `listBasePath`**, **`LegacyCompaniesRedirect`**, **`activationRoutes`**, Dashboard/Services/Leads CTAs); removed duplicate **`APP_ROUTES`** **`clients`** row; **`Sidebar`** treats **`/app/clients/*`** as active for **Clients**; **`AgencyClientsPage`** header link **`app.clients.crm_directory_link`**. SSOT *Honest gap* + rollout **(6)**.
- `2026-03-24` (**Rollout 5 — Vacancy list + card operational layer**): **API** — **`VacancyOut`** **`last_candidate_activity_at`**; **`VacancyRepo.list`** correlated **`max(Candidate.updated_at)`** per vacancy; **`include_archived`** query + **`status=archived`** → **`is_archived`** (archived tab no longer relies on **`status` column = archived**); default list excludes archived. **`VacancyRepo.get`** returns **`candidate_count`** + **`last_candidate_activity_at`**. **Frontend** — **`VacancyList.tsx`**: columns **Candidates** / **Profile** / **Last candidate activity** (relative **`date-fns`**), CSV export extended; hero tiles — **matching total** vs **status mix (this page)** + caption; **`ErrorRecoveryBanner`** retry → **`refresh()`**; count cell links **`/app/vacancies/:id/candidates`**. **`VacancyDetail.tsx`**: URL **`…/:tab`** syncs tabs; hero **ops strip** — linked count, last activity, pipeline **bottleneck** (largest column), **Candidate queue** CTA. i18n **en/pl/ru**. SSOT *Honest gap* + rollout **(5)** note.
- `2026-03-24` (**UOS / IA — Calendar as Activity view + scheduling off first-level nav**): **`CommunicationsCalendarPage.tsx`** — **`useCommunicationsAccess`**; **`hf:calendar:ui:v1`** restores **source filter** + **view mode** (default source **`reminders`** = **Tasks & deadlines**); subtitle + **Open full task queue** → **`/app/tasks`**; optional inline links **`/app/my-availability`**, **`/app/team-availability`**, **`/app/time-off`** when comm features allow. **`Sidebar.tsx`** — **Communications** collapsible no longer lists team/my availability or time-off (**setup** + **command audit** only). **`routes.tsx`** — **`NAV_ITEMS`** drops those three keys (**`APP_ROUTES`** unchanged for bookmarks). **`WorkspaceTopNav.tsx`** — non-messages views: **Calendar** + **Tasks** only; **`TeamAvailabilityPage`** / **`MyAvailabilityPage`** use **`active="calendar"`**. i18n **`app.communications.ia`**, **`app.communications.calendar`** (**`tasks_queue_link`**, **`scheduling.*`**, filter label **Tasks & deadlines**) **en/pl/ru**. SSOT *Navigation (shipped)* + *Honest gap* updated.
- `2026-03-24` (**UOS / IA — sidebar target order + Tasks SLA flat queue**): **`Sidebar.tsx`** — main nav order aligned with SSOT **Core workspace** (**Dashboard → Inbox → Tasks → Calendar → SLA**) then **Business** (incl. **`documents`** in primary row for agency/employer/services); removed duplicate **Operations** / **Leads** collapsibles that repeated main links; new collapsible **System** (**`app.shell.sidebar.system`**) for **Automations** (**`automation-rules`**, **`automation-log`**); **Communications** section no longer lists **Calendar** (already in core). **`RemindersPage.tsx`** — **`View`** selector **Group by due date** vs **SLA priority queue (flat)** (`taskListMode`, persisted + URL **`t_layout=sla_queue|by_due`**); flat mode merges open tasks into one SLA-sorted list; **Reset** restores **`by_due`**. Shared row UI: **`ReminderTaskRow`**. i18n **en/pl/ru**. **`.gitignore`:** **`backend/app/uploads/`**. SSOT *Honest gap* (**Tasks sorted…**, *Navigation (shipped)*) updated.
- `2026-03-24` (**UOS — client pipeline auto activities v1**): **`uos_auto_activities`** — **`ensure_client_company_intro_task`** (client party only, deduped **`uos_client_intro`**, 48h due, assignee owner→manager→actor) after **`POST /companies`**; **`ensure_client_stage_follow_up_task`** on **`client_stage`** change for client companies (**`uos_client_stage_follow_up`**, refresh open row on re-advance, 72h due; skip when new stage is terminal via **`funnel_stages.is_terminal`** or heuristic codes). Tenant flags **`uos_auto_activities_v1.client_company_intro`** / **`client_stage_follow_up`**. **`update_company_service`** reads prior stage; **`PUT`/`PATCH /companies/:id`** pass **`actor_user_id`**. **`refresh_open_typed_reminder_due`** — optional **`new_title`** / **`payload_merge`**. Tasks SLA projection: **`reminders_v2`** **`_SLA_REMINDER_TYPES`**. Tests: **`tests/api/test_uos_client_company_auto_activities.py`**. SSOT *Honest gap* (**Client pipeline…**) updated.
- `2026-03-24` (**Comms — unlinked outbound policy**): **`POST /communications/threads/{id}/messages`** and **`POST /communications/messages/{id}/dispatch`** — **removed** mandatory-link **400** for outbound; **`POST /communications/dispatch/queued`** **no longer skips** unlinked threads. **Frontend:** **`CommunicationsMessagesPage`** send reply **not** gated on unlinked (banner remains). **Tests:** **`test_outbound_thread_message_allowed_without_mandatory_link`**. SSOT *Honest gap* row (**Unlinked…**) updated.
- `2026-03-24` (**Comms — inbox hub + Topbar unread + email workspace UX**): **`/app/inbox`** — minimal hub (no **`WorkspaceTopNav`**), no channel marketing grid; unified thread list with filters **All / Unread / Unlinked / SLA** + sort **Last activity** / **SLA due**; hub load calls **`reconcileCommunicationThreadUnread`** before **`listCommunicationThreads`**. **`Topbar.tsx`** — reconcile unread **every** poll cycle (no one-shot gate), **`99+`** cap on message/email badges, **`visibilitychange` → visible** bumps poll so returning to tab refreshes counts. **`communicationThreadDecision.ts`** — **`threadSlaOverdue`**, **`threadNeedsOutboundReply`**, **`threadDecisionTier`**, **`threadHoursWaitingForReply`** (aligned with **`communicationsOpsMode`**). **`CommunicationsEmailInboxPage`** — no **`WorkspaceTopNav`**; compact list toolbar (search + **Sync** icon); folders sidebar **Inbox / Unread / Archive** + **More folders** (Sent, Trash, All, custom); filter chips **Without candidate / Assigned to me / Has assignee**; row badges (channel, unlinked, SLA/reply dots, **Xh without reply**); preview **Bind / Assign**; reply/forward **not** disabled when unlinked (amber banner only); **`sessionStorage`** **`hf:email:foldersCollapsed`**. i18n **en/pl/ru** (**`app.communications_inbox_hub`**, **`app.communications.email`** in `en.json` / `pl.json` / `ru.json`).
- `2026-03-24` (**UOS — Communication Center on shared inbox grid**): **`CommunicationsInboxWorkspaceGrid`** variant **`inbox_center`** — **`xl:grid-cols-[minmax(280px,20rem)_minmax(320px,1fr)_minmax(260px,20rem)]`**; **`CommunicationsInboxCenterPage`** uses the same wrapper as Messages/Email (list + main + rail); right rail **`20rem`** cap aligned with **Messages** rail; empty rail copies **`channel_rail_empty`**. SSOT *Navigation (shipped)* tightened.
- `2026-03-24` (**UOS — inbox workspace shell + IA + OAuth deep link**): **`CommunicationsInboxWorkspaceGrid`** — shared **`grid gap-4`** templates for **`messages_with_rail`** / **`email_with_rail`** (**`CommunicationsMessagesPage`**, **`CommunicationsEmailInboxPage`**). **Sidebar** — under **Inbox**, nested **Messages** / **Email** links (comm feature gates). **`CommunicationsSetupPage`** — scroll to **`#step-2`** (aliases **`#email`**, **`#email-oauth`**, **`#step-email`**) after load; **Email** poll auth banner **Reconnect email (setup)** → **`/app/setup/communications#step-2`**. i18n **en/pl/ru**.
- `2026-03-24` (**UOS — Messages / Email: narrow viewports → Inbox center + poll OAuth hint**): **`CommunicationsMessagesPage`** / **`CommunicationsEmailInboxPage`** — **`xl:hidden`** link **`/app/inbox/threads/:id`** (**`app.communications.actions.open_inbox_center`**) when the channel **control rail** is hidden below **`xl`**; **Email** poll banner **`pollAuthReconnectSuggested`** when poll row **`error`/`status`** suggests **401** / **UNAUTHENTICATED** / **invalid_grant** / **invalid credential** → **`app.communications.email.poll.reconnect_oauth_hint`** **en/pl/ru**.
- `2026-03-24` (**Comms — Gmail/Graph 401 → refresh + retry**): **`OAuthMailboxPollError` / `OAuthMailboxSendError`** carry **`status_code`**; **`_poll_gmail`** raises **401** on message-detail failure (not only list). **`_refresh_oauth_tokens_in_settings_json`** centralizes refresh; **`run_email_poll_worker`** on **401** refreshes once per folder and retries; **`_dispatch_email_message_via_tenant_smtp`** on **401** refresh + resend once.
- `2026-03-24` (**Comms — email poll worker: async MissingGreenlet**): **`run_email_poll_worker`** — after **`commit()`** / **`rollback()`** ORM rows are **expired**; reading **`account.settings_json`** (or other columns) triggered implicit load → **`sqlalchemy.exc.MissingGreenlet`**. **`await db.refresh(account)`** at loop start, after fetch branches, after IMAP/OAuth error handlers, per ingest message, and before mock-queue persist; **`account_id_str` / `account_inbox_snap` / `account_label_snap`** for result rows after commits.
- `2026-03-24` (**Comms — email poll worker: long RFC822 headers**): **`POST /communications/email/worker/poll`** — IMAP (and some OAuth) payloads can carry **From/To/Message-ID** strings longer than **VARCHAR(255)** / **`EmailIngestRequest`** limits; building **`EmailIngestRequest`** in the poll loop then raised **Pydantic `ValidationError`** (unhandled → **500**). **`_clamp_db_str`** + clamping before **`EmailIngestRequest`** and inside **`_ingest_email_outbound_from_mailbox`**.
- `2026-03-24` (**UOS — Messages / Email: three-column + control rail**): **`CommunicationsMessagesPage`** and **`CommunicationsEmailInboxPage`** — on **`xl+`**, fourth grid column (Email) / third column (Messages) mounts **`CommunicationsInboxChannelSideRail`** → **`CommunicationsInboxControlPanel`** via **`useCommunicationsThread`** with **`reloadSignal`** (parent list refresh) and **`backListPathOverride`** **`/app/messages`** / **`/app/email`**; archive/delete clears selection + refreshes list. **`useCommunicationsThread`** options **`reloadSignal`**; i18n **`channel_rail_empty`**, neutral **`folder_exit_hint`** **en/pl/ru**. SSOT *Honest gap* (**Unified Inbox…**) updated.
- `2026-03-24` (**UOS — Inbox center: archive / trash / restore**): **Communication Center** control panel — **Archive**, **Delete** (trash), **Unarchive / Restore** via same `PATCH …/threads/:id` as Email inbox; **`onAfterArchiveOrDelete`** refreshes hub list + **`navigate('/app/inbox')`** after archive/delete. **Status** row in Operations; i18n **en/pl/ru**.
- `2026-03-24` (**UOS — Inbox control panel: service order + workflow**): **Communication Center** — **Service order** block (`listServiceOrders` by linked candidate/client, manual UUID + `getServiceOrder`, `thread_meta.uos`); **`CommunicationsInboxWorkflowCard`** — ops mode (**in work** / **later** modal / **escalated** modal), **no reply needed**, **SLA** mute + snooze 1h/4h (aligned with `CommunicationsMessagesPage`). i18n **en/pl/ru**; SSOT *Honest gap* updated.
- `2026-03-23` (**UOS — Inbox control panel: link candidate / client**): **Communication Center** — search + link/unlink **candidate** (`searchCandidates` + `linked_candidate_id` + `thread_meta.linked_candidate_name`) and **client** (`listCompanies` + `linked_company_id` + `thread_meta.linked_company_name`); **`service order`** remains **Messages** UOS. i18n **en/pl/ru**; SSOT *Honest gap* updated.
- `2026-03-23` (**UOS — Inbox control panel: follow-up task**): **Communication Center** right rail — **Create task** form (`createReminder`): title / due / notes; **`entity_type`/`entity_id`** from linked candidate or client, else **custom/manual** with **`source=communications.inbox_control_panel`** + **`payload.communication_thread_id`**. i18n **en/pl/ru**; SSOT *Honest gap* row (**Unified Inbox…**) updated.
- `2026-03-23` (**Comms — email poll worker 500 fix**): **`POST /communications/email/worker/poll`** — **`run_email_poll_worker`** loads **`tenant`** via **`_get_tenant_or_404`** for **`_ingest_email_outbound_from_mailbox`** (Sent-folder path); **`await db.commit()`** after successful outbound-from-mailbox ingest (parity with **`ingest_email`** internal commit); **`db.rollback()`** on per-message ingest failure in the poll loop. **Frontend** **`CommunicationsEmailInboxPage`**: after **silent** auto-poll failure, **2 min** cooldown ref so React effects do not hammer the API when **`lastPollAt`** stays unchanged.
- `2026-03-23` (**UOS — Communication Center v1**): Route **`/app/inbox/threads/:threadId`** — **three-column** layout on **`xl+`** (unified thread list + timeline/compose + control panel: linked candidate/client, SLA due, Tasks / SLA / classic thread links). Hub unified list links into Center; **`useCommunicationsThread`** + **`CommunicationsThreadWorkArea`** refactor; **`communications-inbox-center`** comm gate. SSOT *Honest gap* (**Unified Inbox**) + *Navigation (shipped)* + *Current code pointers* updated.
- `2026-03-23` (**R3.4 — close PASS**): Пункт **R3.4** и summary **Risk intelligence v1** переведены в **`[x]`**; добавлены **§ R3.4 — Evidence** и **§ R3.4 — Product sign-off**; **Current status**, **Backlog**, **Roadmap**, **§ Where we are not yet → problem 1**, **§ Risk intelligence v1 → Tracker**, **§ Global next-action rule** — **R3.4** PASS; следующий фокус **UOS / IA** + **Performance**/**Hygiene** по **`[ ]`**. **Navigation (shipped vs target)** — nav **Inbox** → **`/app/inbox`**. **Hygiene:** **`git ls-files`** — нет путей под **`.venv/`** и **`node_modules/`** → пункты отмечены **`[x]`**.
- `2026-03-23` (**UOS — unified Inbox hub v1.1**): **`CommunicationsInboxHubPage.tsx`** — **merged thread list** on **`/app/inbox`** (**All / Unread / Unlinked**), sorted by latest activity, **Email** vs **Messages** badges, link to **`CommunicationsThreadPage`**; **`listCommunicationThreads`** limit **400**; i18n **`communications_inbox_hub.unified_*`** + **`channel_badge_*`** **en/pl/ru**; hub **subtitle** updated. SSOT *Honest gap* (**Unified Inbox…**) updated.
- `2026-03-23` (**UOS — comm gates script**): **`scripts/check-communications-gates.mjs`** — **`EXPECTED_COMM_GATES`** includes **`communications-inbox-hub`** (`withCommAnyFeature` **messages** + **email**), restoring **`npm run comm:gates:check`** / **`qa:static`** parity with **`routes.tsx`**.
- `2026-03-23` (**UOS — mandatory link v1, backend**): **`POST /communications/threads/{id}/messages`** — **400** **`communication_thread_unlinked_outbound_blocked`** for **outbound** when thread has no **`linked_candidate_id`**, **`linked_company_id`**, or **`thread_meta.uos.linked_service_order_id`** (same definition as frontend **`communicationThreadUnlinked.ts`**); **internal notes** exempt. **`POST /communications/messages/{id}/dispatch`** — same rule. **`POST /communications/dispatch/queued`** (and **`/email/worker/dispatch`**) — **skip** such queued messages **without** incrementing batch **`processed`** (stay **queued**). **Not** applied to IMAP **sent**-folder ingest (provider copy). SSOT *Honest gap* (**Unlinked…**) updated.
- `2026-03-23` (**UOS — mandatory link v1, frontend**): **Unlinked** threads — block **outbound** compose (**Messages**, **Email** preview, **`CommunicationsThreadPage`**), allow **internal notes**; block **Dispatch now** on **queued outbound** for that thread when unlinked. Server **`dispatch/queued`** skips unlinked rows without consuming batch slots (see backend changelog). **`?unlinked=1`** on **`/app/messages`** / **`/app/email`**; **Inbox hub** unlinked counts link to those URLs. i18n **`mandatory_link`** + **`app.communications_api.thread_unlinked_outbound_blocked`** (**en/pl/ru**) for API **`communication_thread_unlinked_outbound_blocked`**. SSOT *Honest gap* row (**Unlinked…**) updated.
- `2026-03-23` (**UOS — Inbox hub v1**): Route **`/app/inbox`** (`CommunicationsInboxHubPage.tsx`), nav **Inbox** → hub (was **`/app/messages`**); **WorkspaceTopNav** on hub; counts from **`listCommunicationThreads`**; i18n **`app.communications_inbox_hub`** **en/pl/ru**; **Sidebar** active state includes **`/app/inbox`**. SSOT *Honest gap* (**Unified Inbox…**) updated.
- `2026-03-23` (**UOS — optional default landing Tasks**): **`utils/defaultAppHome.ts`**, **`App.tsx`** (`AuthedDefaultAppNavigate`, `AppShellIndexNavigate`), **`ProfilePage`** (preference + i18n **en/pl/ru**). Storage **`hf:default_app_home`**; **Tasks** only if **`notifications.view`**. SSOT *Honest gap* row (**Default post-login…**) updated.
- `2026-03-23` (**UOS — Topbar bell = CRITICAL+HIGH**): **`Topbar.tsx`** — bell badge counts **SLA-tier** notifications + **`reminder_overdue`** + handoffs (**`max(pendingHandoffsCount, unread handoff_requested)`** to avoid double count). **`aria-label`** **`app.topbar.actions.notifications_with_urgent`**. SSOT *Honest gap* row (**Notification badge…**) updated.
- `2026-03-23` (**UOS — Tasks SLA sort within sections**): **Tasks** `/app/tasks` (`RemindersPage.tsx`) — within each open due-date group, sort by **SLA severity** → SLA deadline → due/remind → title; **Completed** group by **updated_at** descending. i18n **`app.reminders.sla_sort_hint`** (**en/pl/ru**). SSOT *Honest gap* row (**Tasks sorted by SLA…**) updated.
- `2026-03-23` (**UOS — Unlinked queue v1**): **Messages** — filter **All dialogs** / **Unlinked** (`CommunicationsMessagesPage.tsx`, `utils/communicationThreadUnlinked.ts`). **Email** — system folder **Unlinked** (`CommunicationsEmailInboxPage.tsx`). Definition: no `linked_candidate_id`, no `linked_company_id`, no `thread_meta.uos.linked_service_order_id`. i18n **en/pl/ru**; SSOT *Honest gap* row updated.
- `2026-03-23` (**R3.4 — telemetry v1**): Perf **`dashboard.risk_intel.core.load`** / **`shadow_snapshot.load`** (`Dashboard.tsx`), **`settings.risk_intel.page.load`** (`RiskIntelSettingsPage.tsx`); **`candidates.list.load`** meta (**`include_risk`**, shadow cohort flags); budgets in **`analytics.py`** `PERF_BUDGETS_P95_MS`; hourly job **`logger.info`** `risk_intel.hourly_job` with **duration_ms** + counts (`risk_intel_v1.py`).
- `2026-03-23` (**R3.4 — risk_model_v1 team settings**): API **`GET/PATCH /settings/team/risk-model-v1`** (`backend/app/api/v1/settings/team.py`, merge via `tenant_service.patch_risk_model_v1_settings`); UI **`RiskIntelSettingsPage`** (`/app/settings/risk-intel`) + settings landing card; i18n **en/pl/ru**. SSOT **R3.4** — закрыт пробел «config только JSON».
- `2026-03-23` (**R3.3 — close PASS**): Пункт **R3.3** и gap **Product → Services module v2** переведены в **`[x]`**; добавлен **§ R3.3 — Evidence**; **Current status**, **Backlog**, **Roadmap**, **§ problem 1 / 5**, **M3** — следующий фокус **R3.4** / UOS. Ранее по slice: deep links, Billing, CRM, **VacancyDetail** + **`company_id`/`vacancy_id`**.
- `2026-03-23` (**R3.3 — Services v2 UX**): **`company_id` + `vacancy_id`** с карточки вакансии; **`orderQuery.companyId`** на **`GET /service-orders`** при scoped URL; **`vacancy_id`** читается из query даже при **`company_id`**. **Phase B** (SSOT) — пункт про endpoints без смены контракта отмечен **`[x]`**. Ранее: **Vacancy detail → Services**, **candidate_id**, **Analytics → Billing**. SSOT: **§ R3.3 — Shipped slice & plan archive**.
- `2026-03-23` (**R1.5 — product sign-off PASS**): Пункт **R1.5** и **Product gaps → Candidates command center v2** переведены в **`[x]`**; добавлен **§ R1.5 — Evidence**; **Current status** — следующий фокус **R3.3** / **R3.4**; **Audit → pipe.md** и **§ problem 1** обновлены под закрытый R1.5.
- `2026-03-23` (**R1.5 — product sign-off checklist**): Под заголовком плана **R1.5** добавлена секция **«Product sign-off (порядок проверки)»** — пошаговый чеклист для закрытия **`[ ]` R1.5** после приёмки vs **`pipe.md`**. В **Audit → pipe.md** уточнено: инженерная часть R1.5 сдана, открыт только sign-off.
- `2026-03-23` (**R0.1 — production PASS**): Пункт **R0.1** и **Release-pass** отмечены **`[x]`**; добавлен блок **§ R0.1 — Evidence**; **Current status** — release-pass закрыт, следующий внешний gate: **R1.5** product sign-off.
- `2026-03-23` (**R0.1 — run-sheet + Scenario A filter**): В **SSOT** добавлен пошаговый **run-sheet** для **R0.1** (прод `victoria-services`, Scenario A / **services**) и ссылка из **Release-pass**. В **`scripts/f7-e2e-local-actions.mjs`**: переменная **`E2E_SCENARIOS=a`** (через запятую `a,b,c`) для прогона подмножества; блок **`communications/commands/audit`** перенесён **после** создания inbound thread (исправлен порядок относительно `inbound`).
- `2026-03-23` (**SSOT / roadmap alignment**): Секции **Product gaps**, **Where we are not yet → problem 1**, **Roadmap** и пункт **R1.5** в **Expanded backlog** приведены к одному смыслу: **R1.P0** — verified shipped; **R1.5** — инженерно сдан по плану, **`[ ]`** остаётся до **product sign-off** «daily loop».
- `2026-03-23` (**R1.5 / Candidates list — table customize crash**): Исправлен **`ReferenceError: Cannot access 'setDraggingColumn' before initialization`**: эффект сброса DnD при выключенном **«Настроить таблицу»** вызывал **`setDraggingColumn` / `setDragOverColumn`** до **`useCandidatesTableColumnsDnDResize`**; эффект перенесён **ниже** хука в **`Candidates.tsx`**.
- `2026-03-23` (**R1.5 Phase D / perf budgets**): **`PERF_BUDGETS_P95_MS`** в **`backend/app/api/v1/analytics.py`** дополнен **`candidate.card.open`: 1200ms** — тот же ключ, что шлёт фронт **`recordPerfMeasurement`** с **`CandidateCard`** (рядом с уже заданными **`candidates.list.load`**, **`candidates.work_panel.load`**).
- `2026-03-23` (**R1.5 Phase B / Overview drill-down**): Виджет **«No next action»** на Overview ведёт по **`CANDIDATES_QUICK_VIEW_NAV_PATHS.no_next_action`** (`Dashboard.tsx`), без дублирования строки пути.
- `2026-03-23` (**R1.5 Phase B / Quick Views — nav presets + SSOT paths**): Префиксы **`no_next_action`** и **`overdue_next_action`** обрабатываются в **`useCandidatesQuickViews`** через **`navigate(..., { replace: true })`** (без записи **`qv`** на целевом маршруте); при открытии **`/app/candidates?qv=`** с этими значениями — тот же редирект после **`filtersHydrated`**. Единые URL: **`CANDIDATES_QUICK_VIEW_NAV_PATHS`** в **`hostflow-frontend/src/modules/candidates/constants.ts`** (использует хук). **`CandidatesQuickViewsBar`** вызывает один **`onApplyQuickViewFilters`** для всех пресетов; проп **`onQuickViewNavigate`** удалён.
- `2026-03-23` (**R1.5 Phase A / Candidate card — Activity stage focus**): В **`CandidateTimelinePanel`** на карточке кандидата (prop **`stageHistoryShortcut`**) в шапке **Activity** — ссылка **«Только смены этапа»**: разворачивает ленту и включает фильтр только **Stage** (замена отдельной модалки истории стадий). i18n: **`app.candidate_card.timeline.stage_changes_only`**.
- `2026-03-23` (**R1.5 Phase C / table customize mode**): Candidates list — **DnD порядка колонок** и **resize по правому краю заголовка** только при включённой кнопке **«Настроить таблицу»** в правом рейле (`tableLayoutCustomize`, persist **`localStorage`** `hf:candidates:tableLayoutCustomize`); над таблицей — краткая подсказка; чекбоксы колонок остаются в **⋯**. i18n: **`app.candidates.table.customize_layout`** / **`customize_layout_done`** / **`customize_layout_title`** / **`customize_banner`**.
- `2026-03-23` (**R1.5 Phase A / Candidate card — services in work rail**): **`CandidateServicesSection`** is rendered in the **sticky right rail** (after **Messages**, before **RODO/contact**) when the user has **`services.view`** and the candidate is not masked; **`services.orders.manage`** controls the **Open services** link. Section styling matches the rail (**`rounded-2xl`**, scroll-capped order table). Removed unused **section nav** `useMemo` / **`handleScrollTo`** and dead **Tabler** icon imports from **`CandidateCard.tsx`**.
- `2026-03-23` (**R1.5 / product — no list “Next action” column**): **Candidates table** will **not** add a **«Next action»** column. Next action remains in the **work panel**, row **context menu**, dedicated **`/app/candidates/no-next-action`** view, and **quick views**. **R1.5 plan** (`Target UX` + **Phase C**) updated to match.
- `2026-03-23` (**R1.5 Phase A / Candidate card rail order**): **`CandidateCard`** sticky work rail: **`CandidateTimelinePanel`** moved **directly under** **`CandidateNextActionPanel`** (then docs → notes → messages → RODO/contact). **Activity** in header still scrolls/expands the same **`#candidate-card-timeline-rail`** anchor — **scan next action → immediate context** without a top-level Timeline tab.
- `2026-03-23` (**R1.5 / Candidates row context menu**): Restored **“preview + expand next action”** as a **context-menu** item (not in the name cell): opens work panel, **`bumpNextActionDetailsOpen`** → **`CandidateNextActionPanel`** `detailsOpenTrigger`. i18n: **`app.candidates.context.preview_next_action`** / **`preview_next_action_hint`**.
- `2026-03-23` (**UX / Modal close control**): Shared **`Modal`** (`components/Modal.tsx`) adds a visible **close (X)** in the top-right plus top padding so large embedded content (e.g. Activities from Candidates insights) is always dismissible without hunting for backdrop gaps. **`aria-label`** uses **`common.actions.close`**.
- `2026-03-23` (**R1.5 / Candidates name column**): Removed row chips **Open** and **Remind** from the name cell; **full card** opens via the **name link** only. **Preview** is a single **sidebar icon** (`IconLayoutSidebarRight`) **on the same line** as the name inside `group/name`: subtle opacity on desktop, full visibility on touch and on row/name hover (`CandidatesTableRowNamePreview`). Dropped **`nextActionDetailsOpenTrigger` / `bumpNextActionDetailsOpen`** (was only used by the removed Remind chip). i18n: **`app.candidates.actions.preview_panel_hint`**.
- `2026-03-23` (**R1.P0 / Candidates preview rail — docked grid column**): Replaced **`pr-[352px]` + absolutely positioned** `CandidatesWorkPanel` with a **two-column CSS grid** (`minmax(0,1fr)` + `352px`) when the work panel is open, so the rail **does not overlay** the table’s hit targets. **`CandidatesWorkPanel`** is now a **normal flex column** in that grid cell (no outer `pointer-events-none` / `absolute inset-y-0 right-0`). List root `data-hf-ui` → **`candidates-native-table-v7-grid-rail`**. **Manual prod verification** of the original click-blocker still required before closing **R1.P0**.
- `2026-03-23` (**UX / Candidates list polish**): **Bulk bar** + **search card** use shared **rounded-xl / gradient / shadow** styling. **Stage** column: **`StageTag` only** — no inline **`select`**. **Work panel**: **`previewVisible={Boolean(selectedCandidate)}`** — no **`flex-1`** preview block without a row; **no `mt-auto`** on controls (that caused a **large empty flex gap** between overview and list controls). **Rail column wrapper** without preview: **`self-start` + `max-h-full`**, **`aside` `h-auto`** so the rail **does not stretch** to full grid row height (avoids white tail under controls). With preview: wrapper + aside **`h-full min-h-0`** for scrollable **`CandidatesSelectedPanel`**. Rail **views**: quick **`select`**, **Save as view**, saved chips. i18n **`save_needs_filters_hint`**.
- `2026-03-23` (**UX / Candidates rail + table toolbar**): **`CandidatesWorkPanel`** = **`summaryHero` \| `previewSlot` \| `controlsSlot`** (KPI strip → scrollable **`CandidatesSelectedPanel`** → docked **`CandidatesLeftRailPanel`**). **Search** is in the **card above the table** (same **`searchRef`**, ⌘/Ctrl+K); **favorites + doc quick filters** use **`CandidatesQuickViewsBar` `variant="tableToolbar"`** next to the search; **quick view presets** in the rail are a **`<select>`** (**`app.candidates.views.quick_views_placeholder`**); **saved views** remain compact chips under the select. Rare filters (**handoff, contact attempts, ops mode**) under **`<details>`** (**`app.candidates.filters.more_filters_summary`**). **Stage column**: compact **`StageTag` `size="sm"`** next to inline **`<select>`** for color coding. **Preview** icon **toggles** closed for the active row (**`aria-pressed`**, **`app.candidates.actions.preview_close`** / **`preview_close_hint`**). Defaults: **`reasons`** column **on**, ordered after **`docsStatus`**.
- `2026-03-23` (**R1.5 Phase C / Candidates row — inline stage**): **`CandidatesTableRowStageCell`** in the list **Stage** column: compact **`<select>`** for users who can manage candidates (masked / no permission → read-only **`StageTag`**). Uses **`meta.reason_choices`**: keeps reasons valid for the target stage, auto-applies the only reason when a stage has exactly one, otherwise **alert** to open the card or use bulk stage if multiple reasons apply. **RODO 409** → confirm + **`sendRodo`** + retry; **risk gate** / **handoff docs incomplete** surfaced like on **`CandidateCard`**. i18n: **`app.candidates.messages.row_stage_reason_required`**, **`row_stage_select_hint`**.
- `2026-03-23` (**R1.5 / list work panel — comms from bundle**): **`useCandidatesWorkPanelPreview`** persists **`comms`** from **`GET .../work-panel`** (`CandidatesWorkPanelCommsLinks`). **`CandidatesSelectedPanel`** adds a **Comms** block with **Messages** + **Email** (`useNavigate` to API relative URLs, with local fallbacks if `comms` is missing).
- `2026-03-23` (**R1.5 Phase D / work panel — assignee_scope**): List preview passes **`assignee_scope`** (`mine` \| `team`) into **`getCandidateWorkPanel`**, aligned with reminders list rules. Managers/supervisors see a **My tasks / Team tasks** toggle in **`CandidatesSelectedPanel`**; choice persists per tenant in **`localStorage`** (`hf:candidates:workPanelAssigneeScope`). Perf meta **`candidates.work_panel.load`** includes **`assigneeScope`**.
- `2026-03-23` (**R1.5 Phase D / work panel — documents summary in bundle**): **`GET /api/v1/candidates/{id}/work-panel`** adds optional **`documents_summary`** (same rules as **`GET .../documents/summary`**: `fetch_candidate_documents_summary_response` in `documents/router.py`). List preview seeds **`docsBlockers`** from the bundle; **`docsBlockersLoading`** stays false while the rail refetches if the bundle already seeded blockers (`docsRailLoading && !docsSeededFromWorkPanel`). On summary failure the field is omitted; rail still loads via **`getSummary`**.
- `2026-03-23` (**R1.5 Phase D / list docs rail — skip duplicate getSummary**): **`CandidateDocsRailPanel`** accepts optional **`embeddedDocumentsSummary`** `{ ready, summary }` from the work-panel hook (`previewDocumentsSummarySnapshot` + `!previewRemindersLoading`). When **`ready`** and non-null **`summary`**, the rail hydrates from the bundle and does **not** call **`getSummary`** on mount; **`refreshTrigger` > 0** or missing embedded summary still triggers network load. **`CandidateCard`** omits the prop (unchanged). **`useCandidatesWorkPanelPreview`** keeps **`previewDocumentsSummarySnapshot`** in sync with **`documents_summary`**.
- `2026-03-23` (**R1.5 Phase D / work panel API + perf**): **`GET /api/v1/candidates/{id}/work-panel`** — one response with `profile` (contact policy + risk v1), **`reminders`** (same assignee rules as list: `assignee_scope` query `mine|team`), **`timeline`** (shared builder with `GET .../timeline` via `fetch_candidate_timeline_events`), **`comms`** relative URLs (messages / email / documents). Frontend **`useCandidatesWorkPanelPreview`** loads this bundle instead of three calls; emits **`candidates.work_panel.load`** perf event. Backend **`PERF_BUDGETS_P95_MS`** adds **`candidates.work_panel.load`: 800ms**. List **`compact=true`** remains the lightweight row shape (no schema change).
- `2026-03-23` (**R1.5 Phase C / Candidates table**): Default visible columns — **`risk` off by default** (enable via column picker); default column order = name → stage → docsStatus → vacancy → manager → risk → … **Name** cell: link opens full card; **preview** = sidebar icon on the same row (`CandidatesTableRowNamePreview`). **Stage** column: inline stage **`select`** (`CandidatesTableRowStageCell`). *(Earlier row chip “Remind” + `nextActionDetailsOpenTrigger` removed 2026-03-23 — use work panel next-action UI.)*
- `2026-03-23` (**R1.P0 + R1.5 Phase B / Candidates list**): Work panel overlay fixed width `352px`; main table column gets `pr-[352px]` when the work panel is open so list content does not sit under the rail (reduces mistaken hit targets). **Quick Views** + favorites + doc quick filters + **saved views chips** rendered as a **standalone bar above the table** (always visible in table mode); rail reuses shared `CandidatesQuickViewsBar`. Removed duplicate saved-views block from the right rail. **Full reset** clears URL `qv`; quick-view apply sets `qv` **after** reset so deep links work. i18n: `app.candidates.views.saved_inline_title`. *(Superseded for toolbar vs rail: **UX / Candidates rail + table toolbar** same date — search above table; quick/saved views in rail.)*
- `2026-03-23` (**R1.5 Phase A / Candidate card**): Activity timeline removed from full-screen modal; embedded in sticky work rail (`CandidateTimelinePanel` + controlled expand), header **Activity** scrolls to rail and expands. Stage history + timeline reminders load on candidate open / stage change; reminder mutations refresh timeline list. `CandidateTimelinePanel` supports optional controlled `expanded` / `onExpandedChange`; collapsed preview cap raised to 50 rows for `collapsedCount` up to 15.
- `2026-03-22` (**Product / engineering**): Party + client workspace + services deep links; **UOS v1** — Tasks hub, Inbox context rail + linking, `/activities` + SLA projection, Topbar notification groups, `uos_auto_activities` + inbound reply task (+ refresh/dedupe). SSOT: Operating model + Screen-by-screen architecture. **Email:** `incomingEnabled` wired from setup; inbox banner + sync; threads `channel=email` → `/app/email` (not Messages); IMAP default `UNSEEN`.
- `2026-03-22` (**SSOT maintenance**): Deduplicated UOS (single nav/UX pointer to Screen-by-screen), compressed shipped Steps 1–7 + M1–M4 into snapshots, merged contradictory pipe.md/preview backlog items, collapsed stage-gate implementation treatise into shipped summary + code pointers, removed duplicate Pipedrive-audit checklist, aligned Roadmap with Expanded backlog.
- `2026-03-22` (**SSOT policy**): Added **Working from any git branch** — same `docs/SSOT.md` on all branches; neutral wording; merge-conflict + append-only changelog rules.
- `2026-03-22` (**SSOT maintenance**): Linked **Risk intelligence v1** to backlog (**R3.4** + summary item), **Roadmap** focus line, and UOS *Global next-action rule*; fixed R1.P0 “Implemented so far” indentation.
- `2026-03-22` (**Risk intelligence v1 / R3.4**): **Phase A** — `risk_intel_v1` service, `GET /api/v1/analytics/risk-intelligence`, Overview widget; tenant overrides via `Tenant.settings.risk_model_v1`.
- `2026-03-22` (**Risk intelligence v1 / R3.4**): **Phase B** — DB tables + hourly scheduler job, shadow rows for high/critical, `GET /api/v1/analytics/risk-intelligence/trends` + `/validation`, ops-only API + Overview (trend chart + validation); env `RISK_INTEL_HOURLY_*`.
- `2026-03-22` (**Risk intelligence v1 / R3.4**): **Phase C** — unified `risk_model_v1` for list (`risk_scoring` → `compute_candidate_risk_map_for_ids`), refactor shared metric bundle + row scorer in `risk_intel_v1`; `GET /candidates/{id}` risk fields; work panel risk block + nudge.
- `2026-03-22` (**Risk intelligence v1 / R3.4**): **Phase D (automations v1)** — `candidate.risk_band` trigger, `run_candidate_risk_band_rules` from hourly risk job (opt-in `risk_model_v1.automations`), dedupe on `automation.rule_fired`; Automation rules UI hint + risk band field.
- `2026-03-22` (**Risk intelligence v1 / R3.4**): **Phase D (stage gate)** — opt-in `risk_model_v1.stage_gate` blocks forward pipeline stage changes when risk ≥ `min_band` and no active candidate reminder; API `409` `stage_blocked_by_risk_gate`; Candidate card + bulk stage messaging.
- `2026-03-22` (**Risk intelligence v1 / R3.4**): **Phase D (digest)** — `list_latest_shadow_snapshot` + `GET /analytics/risk-intelligence/shadow-snapshot`; Overview ops block with cohort table + deep links to candidate cards.
- `2026-03-22` (**Risk intelligence v1 / R3.4**): **Phase D (digest email)** — `risk_intel_digest_email.maybe_send_risk_shadow_digest_email` from hourly job; `Tenant.settings.risk_model_v1.digest_email`; dedupe `risk_intel.digest_email_sent`.
- `2026-03-22` (**Risk intelligence v1 / R3.4**): **Phase D (digest email — `to_roles`)** — merge explicit `to` with active tenant members matching canonical roles (`user_memberships`); aliases aligned with user invite / RBAC strings.
- `2026-03-22` (**Risk intelligence v1 / R3.4**): **Phase D (manager digest queue)** — `GET/POST .../manager-digest-queue`; shadow-snapshot `bucket_start`; Overview queue UI + `risk_intel.manager_digest_ack`.
- `2026-03-22` (**Risk intelligence v1 / R3.4**): **Phase D (digest → list drill-down)** — `GET /candidates?shadow_bucket_start=` + `shadow_bucket_min_band`; UI `?shadow_bucket=&shadow_min_band=`; Overview **Open cohort in list** passes snapshot `min_band`.
- `2026-03-22` (**Risk intelligence v1 / R3.4**): **Phase D (digest queue UX)** — Overview band floor selector for queue + shadow table; **Mark through latest** ack without opening a bucket.
- `2026-03-22` (**Risk intelligence v1 / R3.4**): **Phase D (digest queue — read filter)** — **Show** all / unread / reviewed; cohort chip selection clears when the active bucket is not in the filtered list.
- `2026-03-22` (**Risk intelligence v1 / R3.4**): **Phase D (shadow digest — row handoff)** — API adds `recruiter_id` on shadow items; Overview **Remind** + **Assign to me** on cohort rows.
- `2026-03-22` (**Risk intelligence v1 / R3.4**): **Phase D (shadow digest — assignee picker)** — per-row **Remind → auto** vs teammate from tenant managers list; `payload.risk_intel_digest.assignee_choice` when explicit.
- `2026-03-22` (**Risk intelligence v1 / R3.4**): **Phase D (shadow digest — bulk handoff)** — cohort checkboxes, **Remind selected** / **Assign selected to me**; `createBulkReminders` extended (`assignee_id`, `source`, `payload`).
- `2026-03-22` (**Risk intelligence v1 / R3.4**): **Phase D (shadow digest — bulk outcomes)** — banner with ok/fail + error samples; partial success keeps row selection; typed `BulkReminderCreateResponse`.
- `2026-03-17`: Consolidated SSOT created; single tracker policy.

---

## System audit report (goal: better than Pipedrive)

### North Star (what “better than Pipedrive” means for HostFlow)

Pipedrive wins because it reduces friction in daily work. HostFlow must **match** that usability baseline and then **surpass** it by being a specialized “Recruitment Operations CRM”:

- **Pipedrive-like**: fast scanning, minimal clicks, clear next action, simple automation, operational visibility.
- **HostFlow advantage**: candidate readiness/compliance, document intelligence, recruitment-specific workflow, and domain automations that generic CRM cannot do without heavy customization.

Success definition:

- A new team can run their core recruitment workflow end-to-end **without training**.
- The system **prevents operational risk** (missing docs, expirations, stuck candidates) rather than merely storing records.
- The system remains **fast** and **predictable** under real load and real team usage.

---

## What is already strong (current strengths)

- **Core CRM loop:** candidates, companies, vacancies, leads, documents, communications, Tasks (`/app/tasks`), billing — wired with permissions and module gating.
- **Differentiator:** document/requirements engine, readiness meta, rulesets + versions UI.
- **Operator UX:** empty states, global search, `qa:static` gate; many Pipedrive-parity items shipped — see **Expanded backlog** `[x]` rows and **Party model** section.

---

## Where we are not yet “Pipedrive-level” (gaps & problems)

This list is written as “problem → why it matters → what we do”.

### 1) Candidates “command center” vs `pipe.md`

**Shipped (v1):** list **work panel** (preview) with next action, docs summary, **History** = unified **timeline** API (`GET /candidates/{id}/timeline`), handoff shortcuts; **`/app/candidates/no-next-action`**.

**Shipped (R1.5 v2, product sign-off `2026-03-23`):** command-center loop on list + card (quick views, **`qv`**, work-panel bundle, table customize mode, Activity in card rail) — **§ R1.5 — Evidence**.

**Remaining (candidates surface):** summary backlog **perf / hygiene / UOS core** — **`[x]` `2026-03-28`**; **UOS stretch** + **Expanded backlog** (party / own-company и т.д.) — см. **`[ ]`**. **R3.4** risk intelligence v1 — **shipped + PASS `2026-03-23`** (**§ R3.4 — Evidence**). **R3.3** Services v2 — **shipped + PASS `2026-03-23`** (**§ R3.3 — Evidence**). **R1.5** command center v2 — **shipped + sign-off `2026-03-23`**. **R1.P0** preview click-blocker — **verified shipped** (docked grid rail; backlog **R1.P0**).

### 2) Next action + SLA (leads + candidates)

**Partially shipped:**

- Leads-first next action loop:
  - Leads list exposes `next_action_status` (`scheduled` / `overdue` / `no_next_action`) and `next_action_due_at`.
  - Leads list supports drill-down filter via query param `next_action` (e.g. `/app/leads?status=processed&next_action=no_next_action`).
  - Dashboard ops counters include processed leads compliance counters (`leads_no_next_action`, `leads_overdue`, `leads_with_next_action`, `leads_total`).
  - Dashboard ops counters include recruitment strip metrics (`open_vacancies`, `open_vacancies_candidates`) — ACL-aligned with vacancy list (`2026-03-24q`).
  - Dashboard ops counters include **`open_service_orders`** (non-terminal service orders; **`2026-03-24r`**).
- Enforcement setting (tenant):
  - `Tenant.settings.next_action_enforcement_v1 = { mode: 'off' | 'warn' | 'block' }`
  - Applied to lead stage changes (`PATCH /api/v1/leads/{id}`): in `warn` logs an ops signal, in `block` rejects stage change when there is no active reminder for the lead.

**SLA nudges (current)**

- Background scheduler runs tenant-scoped SLA checks (same loop as communications SLA/docs deadlines).
- Config:
  - `Tenant.settings.leads_next_action_sla_v1 = { enabled?: bool, noNextActionAfterHours?: number, createNotifications?: bool, createReminders?: bool, limit?: number }`
  - Env kill switch: `COMM_SCHEDULER_LEADS_NEXT_ACTION_SLA_ENABLED=true|false`
- Behavior (Leads-first):
  - For `Lead.status == 'processed'` with **no active reminders** for `N` hours (default 24h), create a best-effort nudge for ops assignee:
    - in-app notification `lead_no_next_action` (deduped daily)
    - internal reminder `type='leads_no_next_action'` assigned to ops recipient (idempotent: only one active per lead+assignee)
- Stuck detection (Leads-first):
  - We log `lead.stage_changed` into `ActivityLog` on stage updates.
  - For `Lead.status == 'processed'` in active stages (default: `new/contacted/qualified`), if **no stage change** for `D` days (default 7d), create:
    - in-app notification `lead_stuck_stage` (deduped daily)
    - internal reminder `type='leads_stuck_stage'` assigned to ops recipient (idempotent per lead+assignee)
  - Config (same namespace): `Tenant.settings.leads_next_action_sla_v1.stuckAfterDays` and optional `stages: string[]`.
- Ops visibility:
  - `GET /api/v1/analytics/ops-counters` includes `leads_sla_no_next_action_reminders` (active assigned SLA reminders).
  - `GET /api/v1/analytics/ops-counters` includes `leads_sla_stuck_stage_reminders` (active assigned stuck-stage reminders).

### 3) Stage-based pipeline blockers (documents & gates) — **shipped**

**Principle:** stage-scoped requirements (not global doc blocking on `new`); overrides with approval + audit; non-overridable legal types; vacancy + contact-attempt gates; soft vs hard doc stages.

**Guided execution & manager bypass (operator UX):** The product **nudges** users along the happy path (obvious “next step”, checklist + upload where documents live, client-side hints aligned with server gates) so someone new can follow the process **without training**. Real-world operations are **not always perfect**; the UI does **not** enforce a fictional ideal by hard-locking every alternative. **Exceptions** are legitimate when taken through **manager-confirmed** paths (e.g. document pipeline **waiver** — recruiter request → manager approve; **override** flows with reason + audit). **Default:** clear guidance; **escape hatch:** accountable bypass via manager approval, not silent rule-breaking.

**Code entry points:** `candidateStageDocPolicy.ts`, `stageOperationalHints.ts`, `candidate_doc_pipeline_guard.py`, `pipeline_overrides_*`, `hiring_pipeline_gates`, **`GET/PATCH .../hiring-pipeline-gates`**.

| Hiring OS plan area | Status |
|---------------------|--------|
| §1–2 Stage-based doc blockers | Done |
| §3 Gates in data (`hiring_stage_gates_v1`) | Done; hints still mostly code (`stageOperationalHints.ts`) |
| §4–6 Stage panel + next action | Done |
| §7–11 Overrides / audit / badges | Done |
| §12–13 Non-overridable + soft stages | Done |

**Stretch:** tenant-editable **stage → hints** matrix; richer custom requirements beyond gates.

### 4) Automation explainability

**Shipped:** automation log API/UI + DB rules builder + triggers (see R2.1–R2.2). **Remaining:** deeper “why” on every surface (e.g. comms threads), richer actions, guardrails.

### 5) Operational reporting

**Shipped:** ops counters + drilldowns, stage metrics, goals/share (Overview + public share). **Services / M3:** модуль **`/app/services`** + services analytics/KPIs — **R3.3** **`[x]`** (**§ R3.3 — Evidence**). **Risk intelligence v1 / M3:** ops + candidate risk surfaces — **R3.4** **`[x]`** (**§ R3.4 — Evidence**). **Remaining:** optional extra widgets per `pipe.md` beyond текущего scope.

### 6) Performance governance

**Shipped:** perf events, baseline + budgets on Overview, breach signals (R4). **Policy (`2026-03-28`):** расширение evidence / CI под более жёсткие числа **`pipe.md`** — только если цели становятся **договорным SLA**; иначе пункт summary backlog **закрыт** как неприменимый.

---

## Roadmap (phases R0–R4)

Phases map 1:1 to **Expanded backlog** below. **R0.1** release-pass **done**; **R1** (включая **R1.5** product sign-off) **done**; **R3.3** Services v2 **done**; **R3.4** Risk intelligence v1 **done** (**§ R3.4 — Evidence**); summary **Backlog** — **perf**, **hygiene uploads**, **UOS/IA core** помечены **`[x]` `2026-03-28`**; дальше — **UOS/IA stretch** и подробные **`[ ]`** в **Expanded backlog** (party / own-company и др.).

---

## Expanded backlog (R0–R4)

`[x]` = shipped; `[ ]` = open. (Pipedrive-audit extras — hovercards, stage-time, documents rail v2, bulk activities, templates — are covered by the `[x]` rows in **R1–R2** and candidate modules.)

### R0

- [x] **R0.1 Production PASS: scenario A (`services`) on `victoria-services`** — **PASS `2026-03-23`**.

#### R0.1 — Evidence (production PASS)

- **UTC date:** `2026-03-23`
- **Tenant slug:** `victoria-services`
- **Scope:** Scenario A — business type **services** (checklist **§ R0.1 — Run-sheet** below).
- **Result:** **PASS** (operator sign-off).
- **Artifacts:** any screenshots / JSON — **outside git** per **Hygiene / repo policy** (optional).

#### R0.1 — Run-sheet (Scenario A, business type **services**, tenant **`victoria-services`**)

**Automation mirror (staging / local, not a prod substitute):** `scripts/f7-e2e-local-actions.mjs` runs Playwright + API flows; **Scenario A** = `{ scenario: 'a', businessType: 'services' }`. To run **only A**:

`E2E_SCENARIOS=a BASE_URL=https://<api+spa-host> node scripts/f7-e2e-local-actions.mjs`

Artifacts: `OUT_DIR` (default `docs/manual-checklist/_artifacts/f7-local-actions`) — PNGs + `runs-*.json`. Requires Playwright, reachable **`BASE_URL`**, and (for billing step) environments where **`checkout-session/.../simulate`** is allowed — **production usually skips that** and uses real billing state instead.

**Production PASS (operator checklist — порядок):**

1. Войти в тенант со slug **`victoria-services`** под ролью, достаточной для CRM + настроек (как минимум administrator).
2. **Биллинг:** подписка / план активны (без dev-simulate); при необходимости зафиксировать план в evidence.
3. **Тип workspace:** услуги (**services**) — онбординг и operating company завершены, модульные флаги позволяют сценарий.
4. **Клиентская компания (client):** создать тестовую или открыть существующую; убедиться, что карточка клиента открывается (**`/app/clients/:id`**).
5. **Вакансия:** для маршрутизации лида (как в скрипте) — при необходимости одна открытая вакансия у этого клиента.
6. **Лид:** появление лида (Meta / ручной импорт — по политике прода) или минимум **Leads** список + открытие карточки без ошибок.
7. **Кандидат:** создать кандидата, привязанного к client (и менеджеру); открыть **`/app/candidates/:id`**.
8. **Напоминание / задача:** создать reminder; открыть **`/app/reminders`** — запись видна.
9. **Почта / коммуникации:** поток писем по политике прода (входящий тред или хотя бы **Email** inbox без 5xx). Глубина (ingest, dispatch) — по возможности среды.
10. **Команда:** **`/app/settings/users`** открывается, список пользователей консистентен.
11. По желанию: **Messages**, **mobile** smoke — как в скрипте (best-effort).

**Evidence:** зафиксировано в **§ R0.1 — Evidence** выше.

**Следующий по бэклогу:** **UOS / IA** gaps (см. **Honest gap** + **Screen-by-screen**), опционально **R4** если бюджеты станут контрактными (см. **Current status** и **Backlog**).

### R1

- [x] **R1.P0 Preview rail click-blocker (CRITICAL)** — **verified 2026-03-23** (operator: no longer reproduces after docked grid rail).  
  **Implemented:** **CSS grid** second column **`352px`** when the rail is open — table and rail are **siblings**, no absolute overlay on the table; **`CandidatesWorkPanel`** fills the docked column (`flex` + `overflow-y-auto`).  
  **Follow-up:** re-validate column DnD (drag, resize, persisted order) under load if any regression reports return.

- [x] **R1.1 Candidates quick preview side panel** (implemented in Candidates right sidebar: select row → Composer/Focus/History + reminders)
- [x] **R1.2 Candidate unified timeline v1** (Candidates list preview side panel `History` tab: unified view of `ActivityLog` (candidate events) + reminders (created/completed), via `GET /api/v1/candidates/{id}/timeline`)
- [x] **R1.3 Next action contract + “no next action” operational view** (next action = active reminder; added `/api/v1/candidates/no-next-action` + UI page `/app/candidates/no-next-action`)
- [x] **R1.4 Leads qualification “fit-check” v1 (vacancy requirements → lead match)** (see “Vacancy requirements presets + lead fit-check v1” section below)
- [x] **R1.5 Candidates command center v2 (table + candidate card redesign)** — **PASS `2026-03-23`** (engineering Phases A–D + product sign-off vs **`pipe.md`**). *(Efficiency-first table + card; timeline in rail; work-panel API; quick views.)*

#### R1.5 — Evidence (product sign-off PASS)

- **UTC date:** `2026-03-23`
- **Scope:** чеклист **§ R1.5 — Product sign-off** (daily loop Candidates list + card vs **`docs/pipe.md`**).
- **Result:** **PASS** (product sign-off).
- **Note:** превью списка остаётся **triage** по продуктовому дизайну R1.5 — не баг.

#### R1.5 Plan — Candidates command center v2 (efficiency-first)

**Goal**

Turn Candidates into the primary “work surface” (not a registry), with a clear loop: **scan → pick → act → verify**. CandidateCard becomes a “case file” optimized for operations (stage changes, docs readiness, reminders/comms, handoff) with **timeline always visible** and without tab-hopping.

**What’s wrong today (observed)**

*Note (2026-03-23): this was the starting diagnosis for R1.5; most gaps below are addressed in **Phased implementation** / changelog — kept for product sign-off context.*

- **Candidates table (current)**:
  - Too much control surface at once (many columns + DnD + resize + filters + bulk tools + keyboard shortcuts + side panel) → high cognitive load, slow to find “what to do next”.
  - Column system is powerful but not efficient by default: users must curate; the “best default” isn’t opinionated enough for daily ops.
  - “Preview sidebar” exists, but “work loop” is split: some actions live in preview, others require opening the full card; the transition is not designed as a primary flow.
  - Filters are capable but not structured as **Quick views** (Saved views / KPI drill-down) → users re-build mental context each time.
  - Performance risk: the page is a large monolith (state + localStorage orchestration + virtualization + DnD) → higher chance of regressions and longer time-to-interact.

- **Candidate card (current)**:
  - Information architecture is “tabs first” (Personal / Docs / Timeline / Services). The **Timeline tab** is a dead-end: timeline is context, not a destination.
  - Actions are scattered across places (header + quick panel + per-section UI) and the layout doesn’t reflect the operational priority: stage/docs/next action/comms should dominate the right rail.
  - Timeline is duplicated/fragmented (stage history modal + timeline tab + notes + reminders), which increases “where do I look?” cost.

**Design principles (hard rules)**

- **Timeline is always visible** (right rail / work panel). It should never require a dedicated top-level tab.
- **One primary surface per intent**:
  - list = scanning + triage + bulk
  - card = deep work on one candidate
- **Default beats configurability**: keep power features, but ship a ruthless default layout that works day 1 without customization.
- **Two-click rule** from list to key action (stage change on **card**, create reminder / docs / handoff from **preview rail** or context menu where applicable).

**Target UX (v2)**

- **Candidates list** becomes a 3-part layout:
  - **Left**: table/kanban toggle + search + quick filters + saved views (opinionated).
  - **Center**: virtualized table with a compact, consistent row layout (name + stage + docs readiness + vacancy + assignee/manager + optional signals such as reasons/risk). **Product decision (2026-03-23):** **no dedicated “Next action” column** in the table — next action lives in the **work panel** (row preview), **context menu** (“preview + next action”), **`/app/candidates/no-next-action`**, and **quick views**; avoids list **N+1** / row bloat.
  - **Right “Work panel”** (persistent): when a row is selected, show:
    - next action editor (create/snooze/complete reminder)
    - docs readiness summary + missing critical docs
    - comms composer (quick message/email entry point)
    - mini-timeline (last 15 events; expandable)
    - quick actions (handoff, stage change, tag, favorite)

- **Candidate card** becomes a **2-column case file**:
  - **Main column**: structured sections (Personal, Status/Eligibility, Experience, Custom fields, Employer/vacancy).
  - **Right rail (sticky)**: “Work panel” identical to list preview, plus:
    - docs checklist block (embedded, not a separate tab)
    - **Shipped:** **Services orders** summary (`CandidateServicesSection` in **`CandidateCard`** sticky rail when **`services.view`**; compact table + **Open services** for **`services.orders.manage`**)
  - Remove top-level **Timeline tab**; timeline exists in the right rail and can expand to a full-height overlay if needed.

**Phased implementation**

- **Phase A — “Timeline tab removal” + unified Work Panel (UI-only, safe refactor)**
  - CandidateCard:
    - Replace tabs with: `Personal`, `Docs` (optional), `Services` (optional). Remove `Timeline` top-level tab.
    - Move unified timeline rendering into the right rail (sticky), default-collapsed with “Show more”.
    - Keep StageHistory modal only if it adds unique value; otherwise merge into timeline.
  - Candidates list:
    - Promote Work panel to first-class: improve selected-row affordance and make “act in panel” the default path.
  - **Shipped (card rail):** **Service orders** embedded in **`CandidateCard`** work rail (`services.view`); dead **sectionNavItems** scaffold removed from **`CandidateCard.tsx`**.
  - **Shipped (list):** when the work panel is open, the active row gets a **brand left bar** + **tinted cells** (checkbox + body) and **`aria-current`**, so the table visually matches “действуй в панели”.

- **Phase B — Opinionated defaults: Quick Views + KPI drill-down**
  - Introduce “Saved views” as first-class UI (not hidden settings):
    - `My work today`, `Overdue next action`, `No next action`, `Docs incomplete`, `Ready for handoff`, `New this week`.
  - Views must be shareable (URL params) and persist per user (existing `UserSavedView` concept).
  - **Shipped:** list-filter presets persist **`qv`**; **`no_next_action`** / **`overdue_next_action`** navigate via shared **`CANDIDATES_QUICK_VIEW_NAV_PATHS`** (also used for hydration when `qv` is present on `/app/candidates`).

- **Phase C — Table v2 row model (efficiency + fewer columns)**
  - Create a **default compact row schema** and relegate niche fields to optional columns.
  - **Shipped:** **Stage** column = compact **`StageTag`** + inline **`<select>`** for users who can manage candidates (**`CandidatesTableRowStageCell`**): **`meta.reason_choices`**, RODO / risk gate / handoff messaging aligned with **`CandidateCard`**; read-only **`StageTag`** when masked or no permission. **Preview** icon beside **name**; **full card** = name link; **preview + expand next action** = row **context menu**.
  - **Non-goal:** **«Next action» table column** — **out of scope** (confirmed); do not extend **`compact`** list payload for per-row reminder titles/due dates for this purpose.
  - Keep power features (DnD/resize/custom columns) but make them secondary (via “Customize” mode).
  - **Shipped:** **«Настроить таблицу»** в правом рейле (список кандидатов): по умолчанию **без** ручек ⋮⋮ и **без** ресайза границ заголовков; в включённом режиме — прежний DnD порядка колонок + resize, полоса-подсказка над таблицей; видимость колонок по-прежнему в **⋯**.

- **Phase D — Data shaping + performance**
  - Lightweight list row: **`GET /candidates` with `compact=true`** (existing); heavy profile fields omitted unless needed.
  - **Shipped:** single **`GET /candidates/{id}/work-panel`** — profile ops + reminders (**`assignee_scope=mine|team`**, mirrored in list preview toggle) + timeline + comms relative URLs + optional **`documents_summary`** (blockers / readiness mirror **`documents/summary`**); list preview uses it (**one round trip**). Timeline SQL shared with **`GET .../timeline`** (`candidate_timeline.fetch_candidate_timeline_events`).
  - Perf budgets:
    - `candidates.list.load` p95 ≤ 2500ms (already tracked)
    - **`candidates.work_panel.load` p95 ≤ 800ms** (backend budget + frontend `recordPerfMeasurement`)
    - **`candidate.card.open` p95 ≤ 1200ms** — **frontend shipped:** `recordPerfMeasurement` in **`CandidateCard`** when первичная загрузка завершена (`GET /candidates/{id}` + awaited **`loadProfileFromVacancy`**); в `meta`: `candidateId`, `isNew`, `outcome` (`ok` | `not_found` | `error`); при смене `id` устаревший запуск не пишет метрику и не трогает `loading`. **Backend:** **`PERF_BUDGETS_P95_MS`** включает тот же ключ (**1200ms**) для **`GET /analytics/perf-budgets`** / сводок.

**Acceptance (measurable)**

- From Candidates list, for a selected candidate:
  - create a reminder OR start handoff in **≤ 2 clicks** without leaving the page; **stage / journey** on the **full card** (list preview stays triage-only by design).
- On CandidateCard:
  - user can see: stage, docs readiness, next action, and a **collapsed Activity preview** (then expand for full history) **without switching tabs**.
- Timeline:
  - no dedicated timeline tab exists; timeline is visible in right rail and expandable.

#### R1.5 — Product sign-off (порядок проверки)

**Статус:** выполнено **`2026-03-23`** — см. **§ R1.5 — Evidence**.

**Назначение (архив):** чеклист, по которому закрыт пункт **R1.5** (`[x]`) после приёмки «daily loop» vs **`docs/pipe.md`**.

**Чеклист (все пункты OK → PASS):**

1. **Список:** выбрана строка → **work panel** виден; **создать reminder** или **открыть handoff** за **≤ 2 клика** без смены страницы (смена stage / причин в строке или на **полной карточке** — по дизайну R1.5).
2. **Quick views:** пресеты в рейле/панели применяют фильтры и **`qv`** где положено; **No next action** и **Overdue next action** уводят на маршруты из **`CANDIDATES_QUICK_VIEW_NAV_PATHS`** (в т.ч. при **`?qv=`** на списке).
3. **Saved views:** сохранить / применить вид; полный сброс снимает **`qv`**.
4. **Таблица:** **«Настроить таблицу»** — DnD и resize только в включённом режиме; переключение режима без падений UI.
5. **Карточка:** **Activity** в правом рейле, без отдельной вкладки Timeline; при необходимости — **«Только смены этапа»**; next action и docs в рейле доступны.
6. **Services** (если модуль доступен): блок заказов в рейле карточки при **`services.view`**.
7. **Мини-сессия 10–15 мин:** типичный цикл **scan → pick → act** без сюрпризов; расхождения с **`pipe.md`** — в тикет, не в «тихий» FAIL.

**После PASS (выполнено):** **`[x]`** выставлен; **Evidence** — **§ R1.5 — Evidence**; запись в **Change log**.

**Implementation notes (where to change)**

- **Frontend:** `Candidates.tsx` + `hostflow-frontend/src/modules/candidates/components/*` — work panel hooks (`useCandidatesWorkPanel*`), left rail (`CandidatesLeftRailPanel`), keyboard nav, insights hero; list preview = **triage only** (no stage **PATCH** from rail — `app.candidates.preview.stage_scope_hint`). **Candidate card:** `CandidateCard.tsx` — **Timeline** только в правом рейле (**`CandidateTimelinePanel`**); отдельной вкладки Timeline нет.
- **Backend:** list insights aggregate `GET /candidates?include_insights=true`; extend **`/candidates/{id}/timeline`**; optional single **work panel** payload to cut N+1.

### R2

- [x] **R2.1 Automation log (rule fired → actions)** (ActivityLog-based; reminders emit `automation.*`; added API `/api/v1/automation-log` + UI `/app/automation-log`)
- [x] **R2.2 Minimal rules builder (candidate created/stage changed/doc expiring/lead processed)** (DB-backed rules + API `/api/v1/automation-rules` + UI `/app/automation-rules`; execution wired for `candidate.created`, `candidate.stage_changed`, `lead.processed`)
  - Operational hardening:
    - `GET /api/v1/automation-rules` now degrades safely to empty list if `automation_rules` table is missing (no 500 on page open).
    - Added deploy/dev command: `make ensure-automation-schema` to bootstrap `automation_rules` in environments where Alembic is unavailable.
    - Recommended rollout order:
      1) `make upg` (preferred, full migrations),
      2) fallback `make ensure-automation-schema` (SQLite/dev safety net),
      3) smoke check `GET /api/v1/automation-rules` returns `200` with `items`.

### R3

- [x] **R3.1 Dashboard operational widget set (8–10) + drill-down** (added ops counters API + Operational widgets block on Overview with drilldowns)
- [x] **R3.2 Stage time + conversion + readiness analytics** (added `/api/v1/analytics/stage-metrics` + Overview block with readiness/stage-time/transitions)
- [x] **R3.3 Services module v2 (sell → fulfill → invoice → collect) + analytics** — **PASS `2026-03-23`** (workspace `/app/services`, Billing tab, deep links, CRM round-trips, KPI strip + Analytics; evidence **§ R3.3 — Evidence**).
- [x] **R3.4 Risk intelligence v1 (response-delay decay model)** — **PASS `2026-03-23`** (см. **§ R3.4 — Evidence** + **§ R3.4 — Product sign-off**). **Phases A–C** + **Phase D v1** (hourly `candidate.risk_band` rules + opt-in **stage_gate** + **shadow snapshot digest** + **manager digest queue** on Overview + opt-in **digest email** incl. **`to_roles`**). **Config:** `GET/PATCH /api/v1/settings/team/risk-model-v1` (effective + overrides JSON) + workspace UI **Settings → Risk intelligence** (`/app/settings/risk-intel`). **Telemetry (v1):** perf keys `dashboard.risk_intel.core.load`, `dashboard.risk_intel.shadow_snapshot.load`, `settings.risk_intel.page.load` (+ budgets in `PERF_BUDGETS_P95_MS`); `candidates.list.load` **meta** includes `include_risk`, `shadow_cohort`, `shadow_min_band`; structured **`logger.info`** line on completed hourly `risk_intel.hourly_job` (duration, shadow row count, evaluated count). **Queue UX:** read-state filter; shadow bulk handoff + **result banner** (ok/fail, sample errors, dismiss; selection kept on partial remind/claim).

#### R3.4 — Evidence (PASS `2026-03-23`)

- **UTC date:** `2026-03-23`
- **Scope:** SSOT **§ Risk intelligence v1** (decay model, bands, ops + candidate surfaces, Phase D v1) и перечень shipped в **Current status → Evidence (latest)** (risk block).
- **Result:** **PASS** — критерии v1 закрыты на shipped-коде; опциональная калибровка весов/порогов и расширение метрик — вне PASS.
- **What shipped (code pointers):**
  - **Backend:** `backend/app/services/risk_intel_v1.py`, `risk_intel_digest_email.py`, `candidate_risk_stage_gate.py`; migration `202603221400_risk_intel_hourly_shadow`; models `risk_intel.py`; scheduler hooks in `communications_scheduler.py`; analytics routes risk-intelligence + shadow-snapshot + manager-digest-queue; tests `backend/tests/test_risk_intel_v1.py`, `test_automation_rules_risk.py`.
  - **Frontend:** Overview risk widgets (`Dashboard.tsx`); **Settings → Risk intelligence** (`RiskIntelSettingsPage.tsx`); candidates list/work panel risk + shadow cohort deep links; perf keys as in пункт **R3.4** выше.
- **Build / gate hygiene:** `npm --prefix hostflow-frontend run qa:static` — **PASS** на момент закрытия тикета в SSOT. Рекомендуемая бэкенд-проверка в dev/CI: `pytest tests/test_risk_intel_v1.py tests/test_automation_rules_risk.py`.

#### R3.4 — Product sign-off (порядок проверки)

**Статус:** выполнено **`2026-03-23`** — см. **§ R3.4 — Evidence**.

**Назначение:** чеклист для закрытия **`[x] R3.4`** после приёмки vs SSOT **§ Risk intelligence v1** (не замена калибровки модели в проде).

**Чеклист (все пункты OK → PASS):**

1. **Overview (administrator / supervisor / superadmin):** блок risk intelligence загружается без ошибок; при наличии данных — агрегаты + тренд; панель validation / shadow cohort / manager digest queue — в соответствии с ролью и флагами.
2. **Shadow digest:** строки когорты с deep link в список кандидатов (`shadow_bucket` / `shadow_min_band`); **Remind** / **Assign to me** (в т.ч. bulk) — осмысленный отклик API (без массовых 5xx).
3. **Candidates:** при **`include_risk`** в списке и в work panel видны **`risk_score` / `risk_band` / drivers** (как в контракте API); фильтр hourly shadow cohort работает с бэкендом.
4. **Opt-in stage gate:** при включённом `risk_model_v1.stage_gate` попытка смены stage вперёд при высоком band без активного reminder даёт **409** `stage_blocked_by_risk_gate` и понятное UI-сообщение (карточка + bulk).
5. **Settings → Risk intelligence:** `GET/PATCH /settings/team/risk-model-v1` отражается в UI; сохранение не ломает tenant settings.
6. **Telemetry:** события `dashboard.risk_intel.*`, `settings.risk_intel.page.load`, `candidates.list.load` meta — не падают консолью; при необходимости — сверка с `PERF_BUDGETS_P95_MS`.

**После PASS (выполнено):** **`[x]`** в **Backlog** и **Expanded backlog**; запись в **Change log**.

#### R3.3 — Evidence (PASS `2026-03-23`)

- **UTC date:** `2026-03-23`
- **Scope:** SSOT **§ Services module v2** (целевой поток + фазы A–D) и **deep links** в **§ Party model + client workspace + services deep links** / **Frontend — Services workspace**.
- **Result:** **PASS** — продуктовые критерии «pipeline + money loop + analytics за ~10 с» считаются закрытыми на shipped-коде; остаётся опциональная декомпозиция монолита **`ServicesPage.tsx`** без отмены PASS.
- **What shipped (code pointers):**
  - **Frontend:** `hostflow-frontend/src/pages/ServicesPage.tsx` — вкладки Overview / Orders / Catalog / Analytics / Billing; компактный hero + KPI strip с drill-down; **Revenue path**; заказы + fulfillment; Billing + счета; **`onOpenServicesBilling`** с Analytics.
  - **URL / CRM:** `hostflow-frontend/src/modules/services/utils.ts` — **`servicesWorkspacePath`**, **`servicesOrdersTabPath`**, **`serviceOrderWorkspacePath`**; **Orders** tab canonical **`/app/orders`** (остальные вкладки — **`/app/services?tab=…`**); query **`order_id`**, **`status`**, **`candidate_id`**, **`vacancy_id`**, **`company_id`**, **`billing_filter`**; ссылки из **CandidateCard**, **VacancyDetail**, Companies / Dashboard / Communications / invoices (см. Change log R3.3).
  - **API (без смены контракта списка):** `GET /api/v1/service-orders` с фильтрами **`company_id`**, **`vacancy_id`**, **`candidate_id`**, **`status`**; `GET /api/v1/analytics/services-overview`; инвойсы / payments — как в Phase C SSOT.
- **Build hygiene:** `npm --prefix hostflow-frontend run build` и **`i18n:check`** — **PASS** на момент закрытия тикета в SSOT.

#### R3.3 — Shipped slice & plan archive

- **Shipped slice (`2026-03-23`, UX):** на **Overview** — **«Revenue path»** (`app.services.overview.flow.*`); в списке заказов — **Open invoice** → `/app/invoices/:id`. **Billing** — колонка **Service order**, пустое состояние, **Outstanding** в детали заказа. **URL sync:** **`tab`**, **`order_id`**, **`status`**, **`candidate_id`**, **`vacancy_id`**, **`company_id`** (список заказов: **`GET /service-orders`** с **`company_id`** при scoped URL и опционально **`vacancy_id`** / **`candidate_id`** по правилам UI), **`billing_filter`**; **`setCandidateIdInUrl`**, **`setVacancyIdInUrl`**, **`setBillingStatusFilterAndUrl`**. **Analytics:** **Overdue** / **Outstanding** → **Services → Billing**. **`servicesWorkspacePath`**; **CandidateCard**, **VacancyDetail** (**`company_id`+`vacancy_id`** при наличии компании вакансии). **Catalog** — empty CTA **«Go to orders»**.

**План (архив — пункты закрыты в рамках R3.3 / предшествующих итераций):**

1. **Инвентаризация:** экраны **`/app/services`**, заказы, **invoices** / **payments** — отражены в Evidence выше.
2. **Целевой поток:** **sell → fulfill → invoice → collect** — CTA Overview, Orders, Billing, hero actions.
3. **Связка данных:** service order ↔ invoice ↔ payment в UI (в т.ч. Billing, order detail, create invoice).
4. **Аналитика:** KPIs в модуле (**Analytics** tab) + **services-overview**; hero strip (invoiced / paid / outstanding / overdue).
5. **Приёмка:** выполнена — этот блок **§ R3.3 — Evidence**.

### R4

- [x] **R4.1 Perf baseline capture (p50/p95) for key actions** (added `analytics.perf.measured` events via `/api/v1/analytics/events`, baseline report `GET /api/v1/analytics/perf-baseline`, and Overview block “Performance baseline”)
- [x] **R4.2 Perf budgets + regression response workflow** (added `GET /api/v1/analytics/perf-budgets` + budget breach signal `analytics.perf.budget_breached`; Overview highlights p95 regressions vs budget; playbook below)

#### R4.2 Playbook (regression response)

**Signals**
- Baseline table on `/app/overview`: p95 highlighted red when it exceeds budget.
- `ActivityLog` action `analytics.perf.budget_breached` indicates a live budget breach (contains `metric_key`, `duration_ms`, `budget_p95_ms`, `route`).

**Workflow**
- **Triage**: confirm the metric key and route; check if breach is widespread (many samples) vs isolated spike.
- **Reproduce**: open the same route with similar filters/data size; repeat 3–5 times to reduce variance.
- **Profile**: capture a short CPU profile around the action; identify the hottest functions (render loops, expensive selectors, large table work).
- **Fix**: prefer data shaping (compact payloads, pagination), memoization, virtualization, and avoiding repeated fetches.
- **Verify**: re-run the action and ensure p95 is back under budget; keep the budget stable unless product requirements changed.

**Budgets (current, p95 ms)**
- `leads.list.load` ≤ 1500
- `candidates.list.load` ≤ 2500

---

## Vacancy requirements presets + lead fit-check v1 (qualification accelerator)

Goal: speed up Leads Inbox processing by making “requirements” explicit, reusable, and automatically evaluated on incoming leads.

### What we implemented (v1)

- **Vacancy requirements stored explicitly**: `Vacancy.extra.lead_criteria_v1` (no schema migration; rides on existing `extra` JSON field).
- **Lead list returns match result**:
  - `LeadOut.fit_status`: `fit | no_fit | needs_info | no_criteria`
  - `LeadOut.fit_reasons`: list of strings explaining what’s missing / failing
- **UI**:
  - Vacancy detail now has a criteria editor (MVP) for:
    - min EU experience years
    - required documents (comma-separated codes)
  - Leads list shows a **Fit** badge with tooltip (reasons)
- **Presets (reusable requirements)**:
  - stored in `Tenant.settings["vacancy_requirements_presets_v1"]`
  - API (team settings):
    - `GET /api/v1/settings/team/vacancy-requirements-presets`
    - `PUT /api/v1/settings/team/vacancy-requirements-presets/{preset_id}`
    - `DELETE /api/v1/settings/team/vacancy-requirements-presets/{preset_id}`
  - Vacancy UI can select a preset and **Apply** it (copies criteria into vacancy form fields; then save vacancy).

### Criteria schema (v1, stored in `lead_criteria_v1`)

Current MVP supports:
- `min_experience_eu_years: int` → compared against `lead.normalized.experience_eu_years`
- `requires_documents: string[]` → compared against `lead.normalized.documents[]` (if present)

Fit semantics:
- **fit**: all criteria satisfied
- **no_fit**: hard mismatch (e.g. experience below minimum, missing required doc)
- **needs_info**: cannot evaluate because required lead data is missing (e.g. experience/documents not provided)
- **no_criteria**: vacancy has no requirements configured

### Design decisions (why this shape)

- **Copy-on-apply presets (MVP)**: vacancy “Apply preset → save” is intentionally simple and stable.
  - Pros: requirements always visible on vacancy; no hidden indirection; fit-check uses only vacancy row → fast.
  - Later: add “linked preset” mode if we need global edits to propagate.
- **No hard dependency on Documents module yet**: v1 reads `lead.normalized` only.
  - Next: integrate with Documents to compute `documents[]` from real candidate/lead evidence.

### Next steps (v2+)

- **Preset manager UI**: create/edit/delete presets from UI (not only via API).
- **Expand criteria**:
  - nationality/citizenship (from `lead.normalized.country` and/or dedicated field mapping)
  - location / in Poland (`lead.normalized.in_poland`)
  - language (requires lead field mapping + normalization)
  - document policies: integrate with Documents module (real document statuses vs free-form codes)
- **Automation: auto-convert lead→candidate** (opt-in / feature-flagged):
  - trigger: on lead ingestion or manual processing when `fit_status=fit`
  - safeguards: rate limits, idempotency, audit log “why”, ability to disable per vacancy/preset

---

## Multi-own-companies inside one tenant (own vs client) — v1

Goal: allow **multiple “my companies” (legal entities/brands)** inside a single tenant, with a **global context switch** (no re-login), while keeping **client companies** separate.

### What we implemented (v1)

- **New entities**:
  - `own_companies` (our legal entities / brands)
  - `client_companies` (client/employer entities; kept separate to avoid mixing semantics)
- **Scoping for ops data**: added `own_company_id` and backfilled existing rows (default own-company per tenant) for:
  - `vacancies`, `candidates`, `leads`, `documents`, `invoices`, `communication_threads`, `communication_messages`
- **Active own-company resolution** (backend):
  - `X-Own-Company-Id` header → `User.preferences.active_own_company_id` → first own-company
  - if no own-company exists: APIs that require scope respond with `OWN_COMPANY_REQUIRED`
- **API**:
  - `GET /api/v1/own-companies`
  - `POST /api/v1/own-companies` (enforces `TenantLicense.max_companies`)
  - `PATCH /api/v1/own-companies/{id}`
  - `POST /api/v1/own-companies/active` (stores `active_own_company_id` in user preferences)
- **Frontend switcher**:
  - topbar dropdown to switch active own-company
  - persists to localStorage and sends `X-Own-Company-Id` automatically on requests
- **Onboarding (updated)**:
  - “Create company” now creates an **own-company** and sets it active
  - onboarding status now uses **own-companies** as the “company_created” step (legacy `companies` remains for now)
- **Alembic**:
  - heads were merged into a single head revision; migrations are now upgradeable with `alembic upgrade head`

### Next steps (v2+)

- [ ] **Legacy `companies` migration plan**:
  - [ ] define mapping rules: which legacy rows become `client_companies` (and which remain as legacy until removed)
  - [ ] migrate references: replace usage of legacy “operating company” semantics in invoicing/billing to use `own_companies`
  - [ ] add read-only compatibility layer if needed during transition
- [ ] **Complete scoping coverage**:
  - [ ] audit remaining modules and ensure list/get/update endpoints filter by `own_company_id` consistently
  - [ ] tighten writes: enforce `own_company_id` set on create for all ops entities (no silent nulls)
- [ ] **Permissions & safety**:
  - [ ] decide whether recruiters/managers can be restricted to a subset of own-companies (optional ACL)
  - [ ] add audit events for switching active own-company (who/when/from/to)
- [ ] **UX polish**:
  - [ ] “Create new own-company” action in switcher (respect plan limit; show upsell path when limit reached)
  - [ ] show active own-company label in key screens (Vacancies, Leads, Candidates)
- [ ] **Requirements/fit-check integration**:
  - [ ] ensure vacancy requirements + fit-check remain correct under scoping
  - [ ] optional: feature-flag `leads_auto_convert_on_fit_v1` (auto lead→candidate) per tenant (+ per vacancy override)

---

## Services module v2 (Catalog → Sell → Fulfill → Invoice → Collect → Analytics)

Goal: make `/app/services` a **fast operational workspace** for selling services (to clients or candidates), fulfilling them, and collecting payments via invoices — with **clear analytics** (revenue, margin, paid, overdue, pipeline).

**R3.3 status (`2026-03-23`):** **PASS** — зафиксировано в **Expanded backlog → § R3.3 — Evidence**. Ниже — исходная постановка и фазы (исторический контекст).

### Current problems (why it feels “сложно и перегружено”)

- **One mega-page**: catalog + order creation + fulfillment + attachments + schedules + analytics are mixed in one screen and one mental model.
- **No clear “money loop”**: users can create orders but the **invoice/payment** connection is not first-class inside Services (even though invoices exist).
- **Analytics is partially placeholder**: labels like “Company ab12cd34”, manager labels are not human; no paid/overdue picture.
- **Hero blocks are decorative/huge**: large gradient panels take space but do not drive next action.

### Target UX (v2)

#### IA / navigation

- `/app/services` becomes a workspace with 4 focused areas:
  - **Overview**: KPIs + alerts + quick actions
  - **Orders**: list + filters + drill-down + fulfillment actions (schedule, deliver, attach)
  - **Catalog**: service definitions (pricing/costs/SLA/required docs)
  - **Billing**: invoices linked to service orders (issue → send → paid → overdue)

#### Primary workflows

- **Sell**:
  - select owner (client company / candidate / vacancy)
  - pick catalog item(s), qty, price, cost source (estimated/confirmed)
  - result: **Service order** (quote/approved)
- **Fulfill**:
  - schedule (if needed), collect attachments/docs, mark delivered
  - result: ready to invoice (or auto-create invoice if enabled)
- **Invoice & collect**:
  - create invoice from order (line items), send, track paid/overdue
- **Analyze**:
  - revenue / profit / margin
  - paid vs invoiced vs outstanding
  - top clients / top services
  - pipeline by status and aging

### Implementation plan (phased)

#### Phase A — Make analytics real and connected to money (fast win)

- [x] Improve `/api/v1/analytics/services-overview`:
  - real labels for client/candidate/vacancy + manager (no placeholders)
  - include invoice aggregates: invoiced / paid / outstanding / overdue
  - add trends: revenue vs paid, conversion to delivered, cancellation rate
  - fixed overdue-invoice aggregation bug (timezone `now` was referenced before initialization in the pre-aggregation pass)

#### Phase B — UI v2 shell + compact functional hero

- [x] Replace huge hero with compact header + KPI strip:
  - 4–6 KPIs max; each KPI is clickable (filter/drill-down)
  - quick actions: “New order”, “New service”, “Create invoice”
- [x] Split Services UI into smaller components (Overview/Orders/Catalog/Billing tabs)
- [x] Deep links on Services: URL sync for `tab`, `order_id`, `company_id` (scoped orders + banner + client card round-trip)
- [x] Keep existing endpoints; focus on UX and clarity first (endpoints extended where needed: `include_metrics`, company filters — see Party section)

#### Phase C — Billing inside Services (invoice-first integration)

- [x] “Create invoice from order” (1-click):
  - prefill invoice items from order items, set `service_order_id`
  - enforce recipient rules (client vs candidate) depending on business type
- [x] Payment tracking: show invoice status & paid amount inside Orders
- [x] Overdue automation: reminder + notification for overdue invoices (optional)  
  Implemented via communications scheduler invoice SLA pass:
  - env kill switch: `COMM_SCHEDULER_INVOICES_OVERDUE_SLA_ENABLED=true|false`
  - tenant settings: `Tenant.settings.invoice_overdue_sla_v1 = { enabled?: bool, overdueAfterDays?: number, createNotifications?: bool, createReminders?: bool, limit?: number }`
  - creates in-app notification `invoice_overdue` and internal reminder `type='invoice_overdue_payment'` (idempotent per invoice+assignee active reminder)

#### Phase D — Productization & analytics depth

- [x] Roles: agency vs services vs employer terminology and defaults
- [x] Data quality guidance:
  - cost coverage warnings (estimated vs confirmed)
  - missing docs/schedule alerts
- [x] Reporting exports (CSV) + saved filters

### Acceptance criteria

- Services feels like a **sales+delivery pipeline** (not a form dump).
- User can: **create catalog → sell → fulfill → invoice → mark paid** without hunting UI.
- Analytics answers in 10 seconds:
  - “How much revenue/profit last 30/90 days?”
  - “What’s paid vs outstanding?”
  - “Which services/clients drive revenue?”

#### Catalog usage metrics (API + UI)

- `GET /api/v1/services?include_metrics=true` adds per–catalog-row aggregates from `service_items` ⨝ `service_orders`:
  - **`metrics_orders_count`**: `COUNT(DISTINCT order_id)` where order status ≠ `cancelled` and line status ≠ `cancelled`
  - **`metrics_revenue_completed`**: `SUM(line.amount)` where order status = `completed` and line status ≠ `cancelled`  
  (numeric sum only; mixed currencies on one tenant are summed as numbers — documented on the schema.)
- HostFlow UI: **Services → Catalog** requests metrics by default; table columns **Orders** / **Revenue (completed)**.

---

## Party model + client workspace + services deep links (implemented 2026-03-22)

Single **Party** record for a client lives in **`companies`** (no duplicate client/employer tables). Recruiting and **additional services** revenue attach to the same company where applicable.

### Data model (Alembic / ORM)

- **`companies`**: `party_entity_type` (`company` | `person`), `party_business_roles` (`employer` | `service_client` | `both`), `client_stage` (pipeline codes, e.g. `new_lead` … `lost`), `client_source` (free text).
- **`leads`**: `lead_type`; `company_id` required when type implies candidate-employer link (validated in API).
- **`service_orders`**: canonical statuses `draft`, `confirmed`, `in_progress`, `completed`, `cancelled`, `on_hold`; optional `start_date` / `end_date`; legacy status values normalized at API boundary where needed.
- **`invoices`**: optional `service_order_id` → `service_orders` (when present).

### API — companies list & metrics

- `GET /api/v1/companies` supports filters: `party_business_roles`, `client_stage`, `owner_user_id`, plus existing list filters.
- `GET /api/v1/companies?include_service_metrics=true` adds per company (where implemented): **`service_active_orders`**, **`service_revenue_completed`** (from service orders for that `company_id`).

### Frontend — client company card (`/app/clients/:id`, not operating profile)

- **Workspace tabs** (query param **`ctab`**; default = overview when omitted):
  - **`overview`**: relationship summary, vacancies widget, blocking service orders widget.
  - **`orders`**: **Additional services** orders for this company (`GET /service-orders?company_id=`) + legacy **CRM / staffing order lines** editor (stored on company profile).
  - **`invoices`**: `ClientInvoicesBlock` (list/create for this `company_id`).
  - **`activity`**: created/updated metadata + shortcuts (invoices list with `company_id`, **Services** with `company_id`, vacancies list with `company` filter).
  - **`profile`**: full company editor — base & Party fields, billing, contacts, legal, contracts, document policies, system block, etc.
- Deep links **`?section=legal|billing|bank_accounts|branding`** force **`ctab=profile`** and scroll to matching `section-*` anchors.
- i18n: `app.companies.party.*`, `app.companies.client_stage.*`, `app.companies.detail.workspace.*`, catalog metric labels under `app.services.catalog.table.*`.

### Frontend — Services workspace (`/app/services`)

- **`?tab=`** (`overview` | `orders` | `catalog` | `analytics` | `billing`) and **`?order_id=`** are read from the URL on load so shared links open the right tab and selected order.
- **`?company_id=<uuid>`** (with **`tab=orders`** in links from CRM):
  - applies **client drilldown** (company-scoped order list),
  - prefills **new order** owner as that company,
  - shows a **scope banner** (name from `GET /companies/:id`) with link back to **`/app/clients/:id`** and **Clear filter** (removes `company_id` from the query),
  - clearing order-list drilldown to “all” while `company_id` is present also strips **`company_id`** from the URL to avoid hidden filters.
- **`?candidate_id=<uuid>`** (without **`company_id`**): filters the **orders** list to that candidate, hydrates the **new order** form owner, and stays in sync when the user picks or clears a candidate; **CandidateCard → Services** uses **`servicesWorkspacePath('orders', { candidateId })`**.
- **`?vacancy_id=<uuid>`** (only when **`candidate_id`** is absent for list filter; with **`company_id`** both are sent to **`GET /service-orders`** as AND filters): hydrates the new-order **vacancy** owner. **`VacancyDetail` → Services** adds **`company_id`** (employer/client) when known so the list matches backend **`company_id` + `vacancy_id`**. URL helpers: **`candidate_id`** xor **`vacancy_id`** in the query string (not both); **`company_id`** can combine with **`vacancy_id`**. **Vacancy detail** header: **Services & orders** when **`services.view`**.
- **`?billing_filter=`** on **`tab=billing`**: invoice status filter (values aligned with the Billing tab UI; **`all`** omits the param).
- Client card **Orders** panel and **Activity → Services** use these query params consistently.

### Spec cross-reference

- Additional services domain tables and flows: `docs/specs/modules/additional_services.md` (status enum names in prose may lag; **SSOT + migration + API** win for canonical enums).

---

## Live audit: Pipedrive (public sources, 2025–2026)

This section is based on Pipedrive’s official public documentation and feature pages (not guesses). It is here to make our plan implementable: we must know exactly which “Pipedrive-grade” mechanics we’re competing with.

### 1) Activities are the operational backbone (not “tasks” on the side)

Source: Pipedrive KB “Activities” (updated **Mar 11, 2026**) `https://support.pipedrive.com/en/article/activities`

What matters (patterns to copy):

- **Activities are first-class** and can be created from many contexts: pipeline cards, detail views, Leads Inbox, calendar/list, contacts timeline, mobile.
- **Linking model**: activities link to person/org/lead/deal/project; visibility depends on visibility into linked items.
- **Scheduling UX**: “Schedule an activity” shows calendar context to prevent double booking; supports guests, location, busy/free semantics.
- **Fields that power “next”**:
  - “Next activity date”, “Last activity date”
  - “Update time” used as an operational signal
- **Bulk activity creation** from list views (deals/contacts/leads/sent).
- **Emails can be added as activities automatically**, reducing reporting gaps.

HostFlow takeaway:

- We must treat “next action” as a **core entity contract**, not a reminders-only feature.
- Our recruitment equivalent must cover candidate-centric actions (call, docs request, verify doc, schedule interview, permit check, arrival planning).

### 2) Leads Inbox is a separate qualification space (pipeline stays clean)

Source: Pipedrive KB “Leads Inbox” (updated **Feb 26, 2026**) `https://support.pipedrive.com/en/article/leads-inbox`

What matters:

- Leads Inbox exists to store **unqualified leads**; conversion moves to pipeline later.
- **Lead detail is a panel**, not a full page jump: left = structured data (org/person/lead fields); right = work surfaces.
- Right side includes:
  - **Composer** (notes/activities/email/files)
  - **Focus** (upcoming activities, pinned notes, drafts, scheduled emails)
  - **History** (notes, completed activities, sent emails, files)
- Lead lifecycle features:
  - archive vs delete
  - merge duplicates
  - convert single or bulk to deals
  - bulk edit key lead fields

HostFlow takeaway:

- Our “Leads” should behave like an operational inbox with an embedded work panel and explicit conversion outcomes (services: lead→company; agency/employer: lead→candidate/vacancy context).

### 3) Email is centralized as “Sales Inbox” with visibility controls + AI helpers

Source: Pipedrive KB “Email sync” (updated **Feb 9, 2026**) `https://support.pipedrive.com/en/article/email-sync`

What matters:

- Central **Sales Inbox** to view/send/reply without app switching.
- **Linking**: conversations auto-link or can be manually linked to deals/leads/projects.
- **Visibility model**: private/shared; team account vs personal account rules.
- Inbox organization via labels/filters.
- AI helpers: suggested replies, email creation, summarization.
- Automation templates exist specifically for email (action or date based).

HostFlow takeaway:

- We already have inbox + templates/signatures, but we need the Pipedrive-grade combination of:
  - reliable linking and visibility semantics
  - “focus” layer (upcoming + drafts + scheduled)
  - explainable automation around outreach
  - optional AI layer (later phase)

### 4) Detail view: progress bar, changelog, hovercards reduce navigation cost

Source: Pipedrive KB “Detail view” (updated **Feb 9, 2026**) `https://support.pipedrive.com/en/article/detail-view`

What matters:

- Deal detail has a **progress bar** showing current stage and days spent per stage.
- **Changelog**: chronological list of all changes (default + custom fields) since creation.
- **Hovercards** for owners/people/orgs/deals reduce context switching.

HostFlow takeaway:

- For recruitment, we need stage-time visibility and a changelog/timeline that is not “optional”.
- Hovercards are a cheap but high-impact speed feature for daily ops.

### 5) Insights: dashboards + goals + reports (with sharing and AI report generation)

Source: Pipedrive KB “Insights feature” (updated **Jul 15, 2025**) `https://support.pipedrive.com/en/article/insights-feature`

What matters:

- Three pillars:
  - **Reports** (visual builder + filters)
  - **Dashboards** (drag/drop of reports/goals)
  - **Goals** (deal/activity/forecast)
- Share dashboards via public link (view-only).
- AI-assisted report generation exists (prompt → report).
- Visibility/permissions are explicit and tied to data visibility.

HostFlow takeaway:

- Our reporting must become operational and drill-down capable; goals should include “activity/next action compliance” and “readiness/compliance” metrics.

### 6) LeadBooster: lead-gen is a product surface, not an integration footnote

Source: Pipedrive KB “LeadBooster add-on” (updated **Dec 11, 2025**) `https://support.pipedrive.com/en/article/leadbooster-add-on`

What matters:

- Lead generation is packaged: web forms, chatbot, live chat, prospector.
- All feeds into Leads Inbox.

HostFlow takeaway:

- We don’t need to copy Prospector, but we must treat “lead source → inbox → qualification → conversion” as a coherent product surface.

---

## How HostFlow becomes “Pipedrive+” (explicit deltas)

### Copy (parity) targets

- **Activities system**: unified activity types + schedule UX + bulk creation + link/visibility semantics.
- **Inbox panels**: lead/candidate/communications side panel with Composer/Focus/History structure.
- **Detail view utilities**: changelog + hovercards + stage-time visualization.
- **Reporting shell**: dashboards + reports + goals (with drill-down).

### Surpass (recruitment-native advantages)

- **Readiness/compliance-first** reporting and automation:
  - missing docs, expiring soon, compliance blockers
  - time-to-ready and readiness score distribution
- **Next action enforcement** tied to stage requirements:
  - “no next action” is a managed operational risk
  - stuck detection and recruitment-specific playbooks
- **Document intelligence** integrated into the daily command center, not a separate module.

---

## Unified Operations System (target architecture)

**Status:** product north star — not fully implemented in navigation/data model yet.  
**Intent:** one operational center for attention, actions, and money — not a pile of disconnected screens.

### Core model (three primitives)

1. **Activity** — what must be done (SLA is a property of Activity, not a separate domain object).
2. **Conversation** — where the interaction lives (replaces fragmented “Messages” + “Email” mentally; may remain multiple channels technically).
3. **Notification** — what demands attention now (no full-page module; top bar: badge + grouped dropdown).

**Calendar** is a **view** over Activities (meetings, calls, deadlines), not a second source of truth.

### Navigation (shipped vs target)

- **Target IA** (full sidebar: Dashboard, Core work, Business incl. Vacancies/Invoices/Documents/Leads, System Automations, unified Inbox, …): **Screen-by-screen system architecture** → § *Target sidebar + shell* + consolidation table.
- **Shipped (v1):** **Tasks** `/app/tasks` (optional **SLA priority queue (flat)** list + URL **`t_layout`**); **Inbox** (nav) → **`/app/inbox`** — hub + **Communication Center** **`/app/inbox/threads/:threadId`**: merged threads, URL state **`channel`** (all/messages/email), email **`folder`** rail + **Sync** + assignee chips, **`q`** search, filters **in work** / **later**, pinned-first sort (**`2026-03-26`**). Sidebar nested **Messages** / **Email** → **`/app/inbox?channel=messages|email`** (active state from **`channel`** query). Legacy **`/app/messages`**, **`/app/email`** redirect into Inbox (**OAuth** still uses **`/app/email`** as redirect URI). On **`xl+`**, **`CommunicationsInboxWorkspaceGrid`** **`inbox_center`**: list + timeline/compose + control panel; narrow viewports: **«All threads»** preserves list query. **Sidebar** (**`2026-03-26e`–`f`**) — **Core** / **Business** / **System**; **Business** = SSOT key order (incl. **do-procesowania** after Clients); **Account** = **profile** (flat); **Settings** = admin + **communications setup** + **command audit**. **Calendar** default **Tasks & deadlines**; availability / time-off routable, not first-level nav. **SLA** incidents; Topbar **notification groups**.
- **Still target:** **email bulk command templates** (multi-select + saved batch commands) not ported from legacy email workspace — restore if ops need (**Honest gap**).

### Activity types (canonical)

`call` | `message` | `email` | `meeting` | `task` | `follow_up` | `document_request`

**Fields (target):** `related_to` (candidate | client | order), `assigned_to`, `status`, `due_date`, `sla_due_at`, `sla_status`, `priority`, plus provenance (manual / automation / comms).

### Per-surface UX

Target contracts (filters, columns, control room): **Screen-by-screen** § *Screen contracts (summary)*. **v1:** Messages page matches a **subset** (3-col + link rail); Tasks = my/team + SLA chip + filters; SLA page not yet full “Activity-derived control room” (see gap table).

### Quick actions (everywhere)

On Candidate / Client / Order surfaces: Call, Message, Request document, Create task, Schedule meeting — **all create Activities** (same pipeline as Tasks).

### Automation (critical)

System-generated Activities examples:

- Candidate created → task: call candidate.
- Inbound message → task: reply.
- Order created → task: confirm.
- Invoice created → task: follow payment.

### UOS Steps 1–7 — v1 shipped (2026-03-22)

**Reminder** = persisted Activity; **`GET /activities`** + **`assignee_scope`**; Inbox **3-column** + link company/order; IA **redirects** (planner/reminders/activities → calendar/tasks); **Tasks** hub; **`sla_due_at` / `sla_status`** + UI chip; Topbar **notification groups**; **`uos_auto_activities`** + inbound **`uos_inbound_reply`** (dedupe/refresh). **Remaining work** = *Honest gap* table + Screen-by-screen rollout (not re-listing steps here).

### Current code pointers (today)

- Nav items: `hostflow-frontend/src/app/routes.tsx` (`NAV_ITEMS` — incl. **Orders** **`service-orders`** → **`/app/orders`**, redirect → **`/app/services?tab=orders`**), shell grouping: `hostflow-frontend/src/components/nav/Sidebar.tsx` (**`ordersNavActive`** / **`servicesModuleNavActive`** from **`tab`** + **`/app/orders`**). **Automations** hub: `AutomationsHubPage.tsx` (`/app/automations` — rules + log + **Policy & enforcement** settings shortcuts); rules/log: `AutomationRulesPage`, `AutomationLogPage`.
- Inbox hub + Communication Center: `CommunicationsInboxHubPage` (`/app/inbox`, URL **`inboxUrlQuery`** — **`channel`**, **`folder`**, **`q`**, **`candidateId`**, **`assignedToMe`**, **`hasAssignee`**, **`unlinked`**), `CommunicationsInboxCenterPage` (same query parity + email folder rail in list column); **`utils/inboxDeepLinks.ts`**, **`utils/inboxThreadLoad.ts`**, **`utils/emailInboxFolders.ts`**; **`InboxEmailFolderRail.tsx`**; **`useEmailInboundSync.ts`**; shared list **`InboxUnifiedThreadList.tsx`** (**hub filters** incl. **in_work** / **later**, **`listQuery`** on thread links); thread body `CommunicationsThreadWorkArea.tsx` + `useCommunicationsThread.ts` (**default back** **`/app/inbox?channel=…`**); control panel `CommunicationsInboxControlPanel.tsx` + `CommunicationsInboxWorkflowCard.tsx` (manual **escalated** → backend **`_emit_manual_thread_escalation_bridge`**). Legacy routes **`CommunicationsMessagesPage`** / **`CommunicationsEmailInboxPage`** → **`<Navigate>`** to Inbox (email stashes OAuth **`code`**). Classic thread: `CommunicationsThreadPage` (`/app/communications/threads/:threadId`).
- Client pipeline UOS hooks: `backend/app/services/uos_auto_activities.py` (**`ensure_client_company_intro_task`**, **`ensure_client_stage_follow_up_task`**); wired from `backend/app/modules/companies/service.py` after create / `client_stage` update; **candidate hiring stage** — **`ensure_candidate_stage_follow_up_task`** from `backend/app/api/v1/candidates/service.py` (**`update_candidate_full`**, **`bulk_update_stage`**); SLA chips include **`uos_client_intro`** / **`uos_client_stage_follow_up`** / **`uos_candidate_stage_follow_up`** in `backend/app/api/v1/reminders_v2.py`.
- Tasks hub IA: `hostflow-frontend/src/pages/RemindersPage.tsx` — **`taskListMode`** **`by_due`** | **`sla_queue`**, **`hf:inbox:reminders:v2`** persistence + **`t_layout`** query; **`ReminderTaskRow`**.
- Messages / email entry: **redirect** components only — unified **`/app/inbox`**; work queue: `RemindersPage` at **`/app/tasks`**; **Calendar** `CommunicationsCalendarPage` — **`hf:calendar:ui:v1`**, links to **`/app/tasks`** + scheduling deep links.
- Vacancies: list `hostflow-frontend/src/components/vacancies/VacancyList.tsx`; detail `VacancyDetail.tsx` (tabs sync **`vacancies/:id/:tab`**); API **`backend/app/api/v1/vacancies/`** — list/get include **`candidate_count`**, **`last_candidate_activity_at`**, **`include_archived`** query; **UOS** — **`VacancyService`** create/patch → **`ensure_vacancy_recruiting_follow_up_task`** when vacancy **enters** recruiting (**`vacancy_is_recruiting`**).
- Clients (companies): list + card `hostflow-frontend/src/pages/Companies.tsx` (**`/app/clients`**); API **`backend/app/modules/companies/`** — **`include_service_metrics`**, **`include_recruitment_metrics`**, **`company_recruitment_metrics_for_list`**.
- SLA: `CommunicationsSlaIncidentsPage`, settings `CommunicationsSlaSettingsPage`.

### Relationship to Pipedrive+ milestones

**M1–M4** are reference labels; much of **M1/M2/M3** scope is already in production (see **Expanded backlog** `[x]`). **M4** import/prefs/dedupe still open in places — see milestone snapshot below.

### Operating model — full system interaction logic (target, production-ready)

**How work is driven** and **how revenue path ties together**. **UOS Steps 1–7 v1** shipped; gaps = table below + IA in *Screen-by-screen*.

**North-star principle:** the system is judged by **actions enforced**, not only by data stored. The baseline chain:

`Event → Activity → SLA → Notification → Action → Outcome → Money`

**Four cores (conceptual):**

1. **Entity** — Candidate, Client (company), Order, Invoice, …
2. **Conversation** — thread + channel (messages, email as integrated surface over time)
3. **Activity** — persisted work item with owner, due, provenance (today: **`Reminder`** / activities API)
4. **Control** — SLA + notifications + escalation policies

**Event → Activity (target rule):** meaningful events (message, new candidate/client, order, invoice, stage change, …) should **materialize or refresh** an Activity so the queue never depends on the manager “remembering”.

**Activity (target invariant):** always has **assignee**, **deadline**, and **SLA projection** (OK / warning / breach) where the type is time-bound.

**If Activity is not completed:** SLA warning → breach → **notification** → **escalation** (per tenant policy); surfaced in **Tasks**, **SLA dashboard**, and **bell**.

**Reference workflows (targets):**

- **Lead / candidate:** create entity → auto Activities (e.g. call, intro) with **short SLA**; breach surfaces in Tasks + notifications.
- **Manager opens Tasks:** sees overdue, SLA risk, today — **work is assigned**, not discovered by browsing Candidates/Clients/Orders (those screens support execution, not queue discovery).
- **Completion:** mark Activity done → **next Activity** / pipeline update where rules apply.
- **Inbox:** not “just chat”; each dialog should be **linked** to an entity, have **ops/SLA state**; message → conversation → **reply Activity**. **Unlinked** conversations are a **first-class queue** until linked (target UX).
- **Order → money:** order → Activities (confirm, assign, schedule, …) → delivery → invoice → payment follow-up Activity; unpaid → SLA → notification → escalation.
- **Client:** not only a directory — **pipeline + Activities + SLA** (e.g. “offer sent” → follow-up in N days).

**SLA (target):** levels **OK / warning / breach** drive **sort order** (hotter = higher), notifications, escalation — not only color.

**Notifications (target attention model):** tiered **CRITICAL** (SLA breach, unpaid invoice) / **HIGH** (overdue tasks, waiting reply) / **NORMAL** (new lead, new message); **badge** emphasizes critical+high; dropdown shows full feed.

**Automation (target):** prefer **behavior** over screens — rule engine expresses: if *event* then *create/update Activity* with *SLA* (today: **`uos_auto_activities`**, communications scheduler, `automation_rules`, comms SLA — **converge** toward one explicit policy model).

**Honest gap — target vs shipped (snapshot 2026-03-26a):**

| Target | Today |
|--------|--------|
| Every meaningful event → Activity | **Partial (`2026-03-26`):** candidate, service order, invoice, inbound thread, **vacancy enters recruiting** (**`uos_vacancy_recruiting_follow_up`**, **`ensure_vacancy_recruiting_follow_up_task`**, **`vacancy_recruiting_follow_up`** toggle) via **`uos_auto_activities`**; **candidate hiring stage** → **`uos_candidate_stage_follow_up`** (**`update_candidate_full`** + **`bulk_update_stage`**). Still **not** exhaustive (e.g. all email-only flows, every domain event). |
| Unified Inbox including email | **Shipped (`2026-03-26`):** **`/app/inbox`** hub + **`/app/inbox/threads/:id`** center — **all** licensed channels; **`?channel=`** (all / messages / email), email **`?folder=`** + sidebar rail (inbox/unread/archive/sent/custom/…), **`q`** search (API), **Sync** + auto **email poll** in email scope, assignee chips (**assigned to me** / **has assignee**), hub filters **in work** / **later** + **SLA** / unread / unlinked, **pinned** threads sorted first. **`/app/messages`** / **`/app/email`** → redirect ( **`/app/email`** keeps **Google OAuth** redirect URI). Deep links: **`inboxDeepLinks`** + **`inboxUrlQuery`** on thread URLs; **Topbar** / **Sidebar** / **global search** updated. **Still not re-shipped:** legacy **email bulk command templates** (multi-select + batch command runner) — was on old **`/app/email`** page; restore only if product needs. |
| Inbox “Unlinked” queue + link guidance | **Shipped (2026-03-24):** **Unlinked** filter + **`?unlinked=1`** on **`/app/inbox`** (legacy Messages/Email URLs redirect and preserve query). **Outbound** not blocked by link state (**API** / **`dispatch/queued`**). |
| Tasks sorted by SLA severity first | **Shipped (`2026-03-24`) for default UX:** **new** browser profiles (no **`hf:inbox:reminders:v2`** snapshot) default **`taskListMode`=`sla_queue`** (**`RemindersPage.tsx`**); **legacy** snapshots **without** `taskListMode` stay **`by_due`**; URL **`t_layout`** + explicit saved mode still override. **by_due** groups retain within-group SLA sort (**`app.reminders.sla_sort_hint`**). Flat queue: **`app.reminders.sla_flat_hint`**. |
| SLA breach → unified escalation from Activities | **Partial (`2026-03-26`):** scheduler **SLA overdue** path + **manual Inbox ops escalation** now **bridges to Tasks + bell** (see **Current status → Recent**); **still not** one merged escalation **policy** object across all domains (**M1/M4** narrative). |
| Client pipeline auto Activities | **Partial (`2026-03-24`):** **`uos_auto_activities`** creates **`uos_client_intro`** on **client** company create and **`uos_client_stage_follow_up`** when **`client_stage`** advances (terminal stages skipped; one open follow-up per company, due refreshed on further moves). Toggle via **`Tenant.settings.uos_auto_activities_v1`**. Still **not** exhaustive vs full “every client event → Activity” target. |
| Notification badge = critical+high only | **Partial (`2026-03-26` + **`2026-03-27`**):** Bell badge counts **CRITICAL** (SLA / invoice / lead SLA group) + **HIGH** (`reminder_overdue`, handoffs via `max(pending, unread handoff notif)`); **reminder_due** and routine **messages/system** do not inflate the bell (see **Messages** / **Email** unread badges). **Drawer:** UOS **group** chip + **`NotificationAttentionTierChip`** (**Critical** / **High** / **Normal**) from **`getNotificationAttentionTier`** (**`Topbar.tsx`**); i18n **`app.topbar.notifications.tier.*`** **en/pl/ru**. Thread-backed SLA + **Messages** deep-link **`buildInboxThreadPath`**; escalated title **`app.notifications.communications_thread_escalated_title`**. **Still not:** unified **backend** priority/tier on notification rows (client derives tier from **`event_type`** / group). |
| Default post-login = Tasks | **Partial (`2026-03-24`):** **Profile** → «After sign-in, open» (`hf:default_app_home`); redirects **`/`**, **`/app`**, authed **`/login`** respect **Tasks** if user has **`notifications.view`**, else **Overview**. **One-time migration** (**`maybeMigrateDefaultAppHomeToTasks`**, **`hf:default_app_home:legacy_v1_tasks`**) sets **Tasks** when the key was **never** set and **`notifications.view`** holds — **`AppShell.tsx`** on load. |
| Calendar = Activity time view; scheduling not daily nav | **Shipped (`2026-03-24`):** Calendar defaults to **Tasks & deadlines** (`sourceFilter` **`reminders`**); **`hf:calendar:ui:v1`** persists filter + month/week/day; primary CTA to **`/app/tasks`**. **My / team availability** + **time off** removed from **`NAV_ITEMS`**, **Communications** sidebar section, and **`WorkspaceTopNav`**; routes **`/app/my-availability`**, **`/app/team-availability`**, **`/app/time-off`** remain in **`APP_ROUTES`** with **Calendar** inline links when gated. **`ProfilePage.tsx`** — **Scheduling & availability** block (**`useCommunicationsAccess`** + **`notifications.view`**), links to **Calendar** + the three routes; **team** link hidden for **solo workspace** (same heuristic as **`Sidebar`**). i18n **`app.profile.scheduling.*`** **en/pl/ru**. |
| Vacancy list & card = recruitment container ops | **Partial (`2026-03-24`):** List shows **`candidate_count`**, **`last_candidate_activity_at`**, optional **profile** column; honest **hero** totals vs page mix; detail **ops strip** (counts, bottleneck from pipeline columns, queue CTA); deep link **`/vacancies/:id/candidates`**. **`headcount_target`** on **`vacancies`** (**API** + list column **candidates/target** + detail form + ops line). **Dashboard** ops strip adds **open vacancies** count + pipeline sum (see **Dashboard ops summary** row). Still **not** full **blockers** / hired-vs-target automation / unified “next action” object — see *Screen contracts*. |
| Dashboard ops summary (recruitment strip) | **Partial (`2026-03-24`):** **`Dashboard.tsx`** **Open vacancies** tile — primary path **`GET /analytics/ops-counters`** fields **`open_vacancies`** + **`open_vacancies_candidates`** (ACL-aligned with **`list_vacancies`**, no **200** cap); legacy API → fallback **`listVacancies`** (**`status=open`**, limit **200**, capped hint). Drill **`/app/vacancies?status=open`**; **Refresh** with ops batch. **Open service orders** tile (**`open_service_orders`** from same endpoint, **`services.view`**) → **`/app/orders`**. Still **not** the full **~5s command center** (*Screen contracts* **Dashboard**). |
| Clients list & card = party + pipeline + money | **Partial (`2026-03-24`):** List **`include_recruitment_metrics`** + existing service metrics; columns **active vacancies** / **candidates** (scoped); card **hero** shows **party role** + **client stage**; KPIs add **live** recruitment + **service orders / completed revenue**; **`GET /companies/:id`** can hydrate same metrics. **Company overview** (**client** workspace) adds **Receivables** card — **`CompanyReceivablesOverview`** (**outstanding** + **past-due** count / oldest aging, link **`/app/invoices?company_id=`**). Still **not** full role-specific layout (employer vs service client only) — see *Screen contracts*. |
| Orders + Invoices = process + money control | **Partial (`2026-03-24`):** **Services → Orders** list shows **next step** (status + items + linked invoice summary); **detail** **ops strip** (blocking, missing docs, overdue chip, updated). **Invoices** list adds **outstanding** + **days overdue** columns; **Dashboard** ops strip adds **open invoice balance** + **overdue unpaid** hint (**`services.view`**); **Invoices** nav + routes gated by **`services.view`** (not **`admin.users`**); deep link **`/app/invoices?queue=…`**. **Sidebar** — first-class **Orders** → **`/app/orders`** (redirect → **`/app/services?tab=orders`**; same **`ServicesPage`** shell; active state distinct from **Services** default tabs). **Deep links** from **`servicesWorkspacePath('orders', …)`** / **`servicesOrdersTabPath`** use **`/app/orders`**. Still **not** unified order-level SLA object or automated follow-up Activities from these fields alone — see *Screen contracts*. |
| Top bar quick jump (⌘K search modal) | **Partial (`2026-03-24`):** **`Topbar`** search modal tiles include **vacancies, leads, orders (**`/app/orders`**), invoices, **Calendar**, **SLA**, **Automations** (non–client tenants), tasks, inbox** (plus **candidates / clients / documents**) when **`usePermissions`** + **`useCommunicationsAccess`** match **`Sidebar`** / route gates; typed **`q`** merges with existing query strings (**`2026-03-24s`** extends **`2026-03-24m`**). |
| Global search (typed results, Topbar) | **Partial (`2026-03-24`):** **`searchGlobal`**: candidates, companies, vacancies, documents, inbox **conversations** (threads `q` → `/app/inbox/threads/…`, `2026-03-24u`), **tasks** (**`GET /reminders?q=`** — **`assigneeScope: 'mine'`** or **`'team'`** for manager/admin roles — `2026-03-24v` + `2026-03-24w`; link **`/app/tasks`** with **`t_q`**, **`t_id`**, optional **`t_assignee=team`**; **`RemindersPage`** focuses row), invoices, service orders (substring `q`; 403 / no-comms omits threads / reminders). **Merged list:** client **`mergeSearchResultsHeuristic`** — match quality on shown fields + max **2** consecutive same type (**`2026-03-24x`**). **Still not:** single **backend** relevance model / unified **`/search`** endpoint — *Screen contracts* **Global search** (`2026-03-24t` + `u` + `v` + `w` + `x`). |
| Top bar quick create | **Partial (`2026-03-24`):** **`Topbar`** **Create** menu (**`app.topbar.quick_create.*`**) links to **new candidate / client / vacancy / service order (orders tab) / task queue / calendar (planner form) / new invoice**, permission- and feature-gated (**`usePermissions`**, **`useCommunicationsAccess('calendar')`** for meetings). Still **not** a **unified in-bar composer** (create without leaving context) — see *Target sidebar + shell*. |
| Automations = unified policy cockpit | **Partial (`2026-03-24`):** **`AutomationsHubPage`** — **Automation rules** + **log** cards; **Policy & enforcement** settings shortcuts; **Fulfillment & billing (execution)** shortcuts (**Orders** tab, **Invoices**) for **`services.view`** (**`ops_*`** i18n). **Policy** shortcuts gated by **`usePermissions`** / **`useCommunicationsAccess`**. **Not** a single merged builder UI — rules + log routes unchanged. |
| Public candidate documents (portal) | **Shipped / simplified (`2026-03-25`):** file upload via **`/public/apply/{token}`** with **`?mode=documents`**; optional **`?doc=`** jumps to matching card in **`PublicIntakeNew`** document flow when the type exists (**`2026-03-25a`**). **Removed:** product **`/public/scan`** camera/OpenCV page + mounted public scanner APIs (**`2026-03-25`**). **Future:** LLM/vision capture — separate initiative (see **Change log**). |

**Intended shift:** from “screens for each module” to **operations control** — the system proposes and pressures work; the manager **executes** the queue.

### Screen-by-screen system architecture (target, final)

This subsection is the **IA + screen contract** companion to *Operating model* above: same north star (**process engine** for recruitment, clients, services, money), but **route-by-route** so engineering and design do not ship unrelated pages.

**Principle:** HostFlow is not a CRM directory or a pile of forms — it is a **process engine**. The universal spine:

`Event → Activity → owner → due / SLA → surfaces in Tasks / Inbox / Calendar → pipeline advances`

**Four cores (IA-facing names):**

1. **Entity** — Candidate, Client/employer (party), Vacancy, Order, Invoice (and related).
2. **Process** — pipeline stage, blockers, next action, overrides/approvals.
3. **Work** — Activities, Inbox, Tasks, Calendar (Calendar = **view** over timed work, not a second truth).
4. **Control** — SLA, notifications, approvals, automation.

#### Consolidation — remove duplicate “daily” modules

**Problem (to eliminate):** Messages, Email, Planner, Reminders, Availability, Time off, Activity, and Calendar partially duplicating planner each feel like separate products.

**Target:** absorb into **Inbox**, **Tasks**, **Calendar**, **SLA**, and **settings** (user/team scheduling context). Standalone routes may remain technically but **must not** be first-class daily nav.

| Remove as first-class module | Becomes part of |
|-----------------------------|-----------------|
| Planner, Reminders, Activity list | **Tasks** (+ Calendar as time view) |
| Messages + Email as peers | **Inbox** (Communication Center) |
| My / team availability, time off | **User profile**, **Calendar** filters, team workload — not top-level ops nav |
| Weak standalone “SLA incidents” feel | **SLA dashboard** as **control room** over Activities |

#### Target sidebar + shell (canonical)

**Sidebar — Core workspace**

1. Dashboard  
2. Inbox  
3. Tasks  
4. Calendar  
5. SLA  

**Sidebar — Business**

6. Candidates  
7. Clients  
8. Vacancies  
9. Orders  
10. Services  
11. Invoices  
12. Documents  
13. Leads  

**Sidebar — System**

14. Automations  
15. Settings (sub-areas: communication, workspace, users/roles; profile entry)

**Top bar:** global search, notifications, **quick create**, workspace switcher, user menu.

**Quick create (top bar):** Candidate, Client, Vacancy, Order, Task, Meeting, Invoice.

**Reconciliation:** § *Navigation (shipped vs target)* above is the **minimal shipped slice**; this subsection is the **full target IA**. Until shipped, some routes stay combined (e.g. **Finance** vs **Invoices**) — track in top **Backlog**.

#### Screen contracts (summary)

- **Dashboard** — operational summary in ~5s: what is on fire, where money is, bottlenecks, first action. Sections: my urgent work (overdue, SLA breach, waiting replies, unpaid due), recruitment + client/revenue pipeline summaries, KPI cards, quick actions, recent activity / approvals / expiring docs / overdue invoices.
- **Inbox** — single **Communication Center** (replaces separate Messages vs Email mental model). Three columns: list + filters (**Unassigned**, **Waiting reply**, **New**, **SLA risk**, **Closed**, **Linked / Unlinked**), thread + notes, **control panel** (linked entity, owner, status, SLA, quick actions: link, task, docs, order, schedule, escalate, close). No separate “email app” vs “messages app” for daily work.
- **Tasks** — **primary execution engine** (not “reminders”). Filters: My, Team, Today, Overdue, Upcoming, High priority, SLA risk. Table: type, title, entity, stage/context, assignee, due, SLA, priority, status (`planned` / `in_progress` / `waiting` / `done` / `cancelled`). Actions: complete, reassign, snooze, open entity, escalate; optional drawer for quick creates.
- **Calendar** — **only** a view of Activities (meetings, calls, deadlines, timed tasks, time off). Filters by user, type, entity, priority; scheduling respects availability. **Does not** duplicate Tasks as a second queue.
- **SLA dashboard** — **control room** for ops/leads: overdue, at-risk, breached conversations, unassigned urgent, ignored critical; KPIs; table with actions (assign, reassign, escalate, resolve, open entity).
- **Candidates list** — flow control, not a dumb table: table + pipeline counters + saved filters; columns include next action, blocking, docs, time in stage; **right preview** with summary, blockers, quick actions.
- **Candidate card** — hero (stage, next step, move forward/back, override blocker); main: key info, timeline; sticky rail: next action, documents, blockers, quick actions, notes, related comms; tabs Overview / Documents / Services·Orders / History; stage-aware blockers and **approval** for overrides.
- **Vacancies list & card** — same **operational** bar as candidates (vacancy = recruitment container): columns for pipeline distribution, blockers, last activity; card links candidates scoped to vacancy, headcount, bottleneck, next action.
- **Clients list & card** — **party** with roles (employer, service client, both); pipeline + money signals; card emphasizes vacancies+candidates for employers, orders+invoices for service clients, both when mixed.
- **Leads** — strong standalone **qualification** before Candidates/Clients; types candidate vs client; convert / reject / assign.
- **Services catalog** — **templates** only (code, price, margin, usage, scheduling/VAT); not the execution surface.
- **Orders** — full **process module** (status draft → confirmed → in progress → completed / cancelled); list + card with next action, invoice/payment blocks, SLA.
- **Invoices** — **money control**: amounts, due, delay, follow-ups; Activities + SLA on overdue; quick actions (send, mark paid, follow-up, escalate).
- **Documents** — **center** across candidate, client/legal, and generated service/invoice docs; expiring/missing filters; approve/reject/replace.
- **Automations** — system **spine**: rules, hiring gates/stage requirements, notification rules, SLA policies, templates — not a peripheral screen.
- **Communication settings** — under **Settings**: channels, accounts, templates, signatures, routing, assignment, SLA policies (not daily nav).
- **Availability / time off** — **profile** + calendar/scheduling consumption; optional HR-lite requests — not top-level modules.
- **Notifications** — **center only** (top bar): groups Urgent, Tasks, Messages, System, Finance; priority critical/high/normal; actions open, read, snooze, assign.
- **Global search** — grouped results: candidates, clients, vacancies, orders, invoices, conversations, documents, tasks.

#### Global next-action rule

Every entity surface (table, preview, card) should expose **state, blockers, next action, owner, deadline/SLA** consistently.

**Predictive layer:** aggregate + hourly `risk_score` (v1) + shadow cohorts for ops leads; list/detail/work-panel fields + hourly **risk → reminder** automations + **shadow snapshot** digest + **manager digest queue** (per-user ack) on Overview; opt-in **stage_gate**; opt-in **hourly digest email** (`to` and/or `to_roles`) — **Risk intelligence v1** (**R3.4** **`[x]`** **§ R3.4 — Evidence**).

#### Reference scenarios (cross-screen)

1. **Candidate path:** Lead → convert → auto call task → SLA → notification → stage/doc gates → Activities.  
2. **Client + money path:** Lead → client → qualify → offer → contract → order → invoice → payment follow-up + SLA if overdue.  
3. **Inbound comms:** thread in Inbox → unlinked queue → link + assign → Activity + SLA → escalate if stuck.

#### Rollout order (IA / product)

1. Lock **sidebar architecture** (this doc).  
2. **Unified Inbox** (messages + email one center).  
3. **Tasks** as execution hub (behaviors + sort/priority).  
4. **Calendar** strictly as Activity view.  
5. Strong **Vacancy** list + card.  
6. **Clients** around pipeline + money.  
7. **Orders + Invoices** as process + money control.  
8. **Automations** as dedicated system module.  
9. Remove **availability / time off** from first-level nav (absorb per above).

**Progress (`2026-03-24`–**`26`):** (4) Calendar oriented to **Tasks & deadlines** + persistence + Tasks queue link; (9) availability / time off **off** first-level nav + **profile** absorb (**`ProfilePage`** scheduling block + Calendar parity) — **Honest gap** row *Calendar / scheduling* **shipped** for IA slice. (5) Vacancy list + card — **operational columns** + **detail ops strip** + **`headcount_target`** — **Honest gap** row *Vacancy…*; **Dashboard** **open vacancies** — **`ops-counters`** **`open_vacancies` / `open_vacancies_candidates`** (**2026-03-24q**), list fallback (**2026-03-24o**). (6) Clients — **list + card** recruitment + service **metrics** + **company overview** **Receivables** card (**`CompanyReceivablesOverview`**) — **Honest gap** row *Clients…*. (7) Orders + Invoices — **next step** + **ops strip** on service orders; invoices table **outstanding** + **aging**; **Dashboard** invoice balance widget + **`open_service_orders`** ops tile → **`/app/orders`** (**2026-03-24r**); **Invoices** **`services.view`** gate + **`?queue=`**; **Sidebar** **Orders** → **`/app/orders`** (redirect shell; snapshot **2026-03-24p**) — **Honest gap** row *Orders + Invoices…*. (8) **Automations** — **`/app/automations`** hub + primary sidebar + **policy shortcuts** (snapshot **2026-03-24h**) + **execution shortcuts** (**Orders** / **Invoices**, snapshot **2026-03-24m**). **Tasks** — **default SLA flat queue** for new profiles (**`RemindersPage`**, snapshot **2026-03-24h**); **default post-login** — one-time **Tasks** when **`hf:default_app_home`** never set (**`maybeMigrateDefaultAppHomeToTasks`**, **`AppShell`**); **global search** — reminders **`GET /reminders?q=`** (**mine** + **team** for managers, **`2026-03-24v`** + **`2026-03-24w`**); **`t_id`** deep focus on **Tasks** page (**2026-03-24w**). **Inbox** — **`2026-03-24g`** deep links + **`?candidateId=`**; **`2026-03-26`** — **single surface** **`/app/inbox`** (**`channel`**, **`folder`**, **`q`**, email rail + sync, **in work** / **later**, pinned sort); **`/app/messages`** / **`/app/email`** redirect (**OAuth** URI unchanged). **Topbar** — **⌘K** quick-jump + **typed global search** + **Create**; badge shortcuts → scoped Inbox. **Public intake (`2026-03-25`):** **`/public/scan`** removed; **`?doc=`** focus (**2026-03-25a**). Latest honest-gap snapshot label: **2026-03-26a**. Prior: **2026-03-25a** — public intake doc param + scanner removal; **2026-03-24x** — merged search ranking; **2026-03-24w** — task deep links + team scope in search; **2026-03-24v** — tasks in search; **2026-03-24u** — inbox threads in search; **2026-03-24t** — entity search expansion; **2026-03-24s** — quick tiles; **2026-03-24r** — **`open_service_orders`** ops tile; **2026-03-24q** — **open vacancies** ops-counters; **2026-03-24p** — **`/app/orders`**; **2026-03-24o** — Dashboard **open vacancies** list tile; **2026-03-24n** — Topbar **Create**; **2026-03-24m** — quick jump + Automations execution.

---

## Milestones M1–M4 (reference snapshot)

Original milestone specs are archived in git history if needed. **Current truth:**

| Milestone | Intent | Status |
|-----------|--------|--------|
| **M1** Activities | Pipedrive-grade activity spine + calendar/list | **Largely shipped** via **Reminder** + `/activities` + Tasks + calendar + bulk/templates; optional future rename/evolve model. |
| **M2** Leads inbox | Qualification workspace + convert + SLA | **Partially shipped** — side panel, fit-check, enforcement/SLA nudges; **duplicate merge** / heavy bulk still open. |
| **M3** Reporting | Operational dashboards + drill-down | **Largely shipped** — ops counters, stage metrics, goals/share; **Services** workspace + module analytics — **R3.3** **`[x]`** (**§ R3.3 — Evidence**); **Risk intelligence v1** — **R3.4** **`[x]`** (**§ R3.4 — Evidence**). |
| **M4** Hygiene | Import/export, dedupe, notification prefs | **Partial** — taxonomy/groups v1; **CSV import**, dedupe UX, digests/mute prefs TBD. |

---

## Landing (public) audit + plan (make it a selling landing)

Current public entry is `hostflow-frontend/src/pages/public/CrmLandingPage.tsx` (routes `/` and `/pricing` for non-auth users). It already has hero, pricing, comparison, objections, FAQ, audience, final CTA, and CTA tracking, but it is missing key conversion mechanics: strong proof, product visualization, a focused narrative per persona, and a measurable funnel.

### Landing vNext — positioning & narrative

- **Clarify 1 primary ICP per page**: keep `/` focused on “recruitment operations CRM” (managers + ops); move secondary narratives to dedicated use-case pages (already present) and link them with stronger “choose your path” blocks.
- **Make the promise measurable**: replace generic “Launch in minutes” with quantified outcomes we can defend (e.g. “reduce ‘no next action’ to < 5%”, “cut time-to-ready by X%”) once reporting is in place.
- **Differentiate vs Pipedrive** (recruitment-native): readiness/compliance + document control + SLA nudges as primary differentiators.

### Landing vNext — sections to add/upgrade (UI/UX)

- **Hero**
  - Add 1–2 product visuals (screenshots / short looping video) showing: Leads inbox panel + next action + ops dashboard drill-down
  - Add trust strip (logos / “used by” once available) or “early access” proof alternative (numbers, case study snippets)
- **Problem → solution**
  - Insert a short “Before/After” block: chaos (spreadsheets, missed follow-ups) → HostFlow command center (next action, SLA, compliance)
- **Feature proof blocks (3–5)**
  - Each with: headline, 1 sentence outcome, visual, and “See example” link to existing guide pages
- **Social proof**
  - Testimonials/case studies section + lightweight “results cards”
- **Pricing**
  - Add FAQ below pricing that answers purchase friction: migration, seats, security, cancellation
  - Make CTA consistent: primary CTA = “Start trial”, secondary = “Book demo” (if we support it)
- **Conversion surface**
  - Add sticky CTA on scroll (desktop) + bottom mobile CTA
  - Add “Request demo”/“Talk to us” capture (email) if self-serve is not enough

### Landing vNext — tracking, experimentation, and SEO

- **Funnel tracking**
  - Define events: `landing.view`, `cta.click` (already), `signup.view`, `signup.submit`, `onboarding.complete`
  - Track CTA placement keys: hero/pricing/final/sticky; and page variants `/` vs `/pricing`
- **A/B readiness**
  - Simple variant flag (query param or remote config) to test hero copy + CTA + visual
- **SEO**
  - Ensure each public page has: unique title/description, canonical, structured data (already), internal linking map, and keyword-targeted headings
  - Add comparison pages into a “Learn” hub section and improve cross-linking with clear next steps

### Landing vNext — acceptance (what “better landing” means)

- **Conversion metrics**
  - Baseline and target: \(CVR_{landing \to signup}\), \(CVR_{signup \to onboarding\_complete}\)
  - Track by source/UTM and by locale
- **Performance**
  - p95 LCP < 2.5s on mid-tier mobile (or explicit budget we set) and no heavy JS regressions
- **Quality**
  - Content is consistent with product truth (no claims we can’t demonstrate inside the app)

---

## Risk intelligence v1 (response-delay decay model)

**Tracker:** **R3.4** — **`[x]` PASS `2026-03-23`** (*Expanded backlog* **§ R3.4 — Evidence** + *Backlog* summary). **Phases A–C + Phase D v1** are shipped in code (hourly job + ops analytics + candidate surfaces + opt-in `candidate.risk_band` rules + opt-in **stage_gate** + **shadow-snapshot** digest API/UI + **manager digest queue** + opt-in **digest email** via `to` / `to_roles`). Queue UX: read-state **Show** filter; shadow cohort **Remind** + **Assign to me** (row + **bulk** select); bulk remind uses **`/reminders/bulk`** when one assignee chosen, else per-row **`POST /reminders`**. This section stays the full product/engineering spec; further model calibration is **not** a blocker for the closed PASS.

### Why this matters now

HostFlow already enforces next action and SLA nudges, but we still mostly answer "what is overdue?" and not "what is likely to fail soon?".  
For recruitment and sales-like workflows, delay itself is a strong predictive signal:

- if a candidate was not contacted on day 0/1, motivation and conversion probability decay each day;
- if a client did not receive a timely response, deal-close probability drops and cycle length increases.

The goal of this section is to define a practical, rollout-safe way to move from rule-based alerts to risk-aware operations.

### Conceptual model (simple and useful)

Treat risk as a probability of negative outcome over a time horizon, updated whenever key events happen.

- For candidates: risk of "won't reach target stage in X days" (e.g., not hired/not ready).
- For leads/clients: risk of "won't close/won't advance to next milestone in X days".

Minimum viable framing:

- `p_success_now`: estimated probability to reach target outcome from current state.
- `risk_score`: normalized urgency score 0..100 where higher means "intervene now".
- `risk_drivers`: human-readable top reasons (e.g., "no first response for 36h", "7d in stage without movement", "2 overdue actions").

### Core metric family (start here)

Use a small metrics set first; each metric must be explainable and actionable.

1. **Response latency metrics**
   - `first_response_minutes`: time from entity creation/inbound event to first human response.
   - `last_response_gap_hours`: now - last meaningful outbound/bi-directional touch.
   - `inbound_unanswered_hours`: unanswered inbound age.

2. **Action discipline metrics**
   - `has_next_action` (bool)
   - `next_action_overdue_hours`
   - `overdue_actions_count_7d`

3. **Flow stagnation metrics**
   - `days_in_stage`
   - `days_since_stage_change`
   - `stage_reopen_count_30d` (stage ping-pong as friction signal)

4. **Outcome context metrics**
   - `current_stage` / `funnel_position`
   - `owner_workload_open_items`
   - `interaction_count_7d` (too low can indicate cold process)

5. **Quality metrics (later, optional)**
   - communication sentiment/quality proxy (if available)
   - profile/data completeness index

### Time-decay logic (the heart of the model)

Use explicit decay curves so the system "understands" that each day of silence hurts odds.

For each delay-sensitive signal, define a half-life:

- `candidate_first_response_half_life_hours` (example: 24-36h)
- `client_inbound_reply_half_life_hours` (example: 8-24h)
- `stage_stagnation_half_life_days` (example: 5-10d depending on stage)

Apply decay factor:

- `decay(t, h) = 0.5^(t / h)` where `t` is delay and `h` is half-life.
- As `t` grows, contribution to success falls smoothly and predictably.

Practical interpretation:

- at `t = h`: signal contribution drops by 50%;
- at `t = 2h`: by 75%;
- the model encodes "each day late reduces chance" without hard cliffs.

### Risk score design (v1 transparent scoring, not black box)

Start with weighted scoring instead of a complex ML model.

Example v1 score:

- `risk_score = clamp(0..100, w1*response_risk + w2*stagnation_risk + w3*action_risk + w4*context_risk)`
- each component is normalized 0..100 and uses decay/time thresholds.
- initial weights can be expert-defined, then calibrated on historical outcomes.

Severity bands:

- `0-34`: low (normal monitoring)
- `35-64`: medium (show warning + suggested next best action)
- `65-84`: high (escalate to owner + manager digest)
- `85-100`: critical (immediate intervention workflow)

### Suggested initial thresholds (to be tuned)

These are rollout defaults, not final truth:

- Candidate first response:
  - medium risk after 24h
  - high risk after 48h
  - critical after 72h
- Client inbound unanswered:
  - medium after 4h (working hours)
  - high after 12h
  - critical after 24h
- Stage stagnation:
  - per-stage baseline SLA (e.g., qualified max 5d, interview max 7d, offer max 3d)
  - risk grows after baseline breach, then accelerates with decay

### Validation strategy when metrics are not finalized yet

You can start now without perfect schema by using an iterative evidence loop.

1. **Define target outcomes**
   - Candidate: reached target stage/hired within horizon.
   - Client/lead: advanced/closed-won within horizon.

2. **Backfill baseline from existing logs**
   - Use `ActivityLog`, reminders, stage changes, communication timestamps.
   - Build a retrospective dataset for last 60-180 days.

3. **Measure signal power**
   - For each candidate signal, compute success rate by delay buckets:
     - 0-24h, 24-48h, 48-72h, 72h+.
   - If success declines monotonically with delay, keep the signal.

4. **Calibrate thresholds and weights**
   - Choose cutoffs that separate "healthy" vs "at risk" cohorts.
   - Prefer stable, interpretable settings over overfitted precision.

5. **Run shadow mode**
   - Compute risk silently for 2-4 weeks.
   - Compare predicted high-risk cohorts vs real outcomes before enforcement.

### Product integration (where risk must appear)

1. **List surfaces (Candidates/Leads/Services)**
   - Add `risk_badge` (Low/Med/High/Critical) and sortable `risk_score`.
   - Provide quick filter: `risk>=high`.

2. **Work panel / Candidate card**
   - Show top 3 `risk_drivers` with plain language.
   - Add "recommended next action" generated from strongest driver.

3. **Dashboard widgets**
   - "Critical risk entities now"
   - "Risk trend 7d/30d"
   - "Intervention success rate" (high-risk rescued after action)

4. **Automation log linkage**
   - Every risk escalation must create a visible audit entry:
     - why score changed,
     - what rule triggered,
     - what action was suggested/executed.

### Automation policy (graduated response)

Map risk bands to interventions:

- Medium:
  - owner notification + suggested playbook action
- High:
  - auto-create reminder with due soon + manager visibility
- Critical:
  - escalation to backup owner / team lead queue
  - optional SLA breach incident counter

Guardrails:

- strict deduping windows to avoid alert spam;
- cooldown after manual action;
- "snooze with reason" to capture operator intent and improve model later.

### Data contract additions (minimal)

Add risk fields to key API outputs:

- `risk_score: number (0..100)`
- `risk_band: low|medium|high|critical`
- `risk_updated_at: datetime`
- `risk_drivers: string[]` (max 3-5)
- `risk_version: string` (for traceability)

Analytics additions:

- `risk_distribution_by_stage`
- `high_risk_volume`
- `high_risk_success_rate` (rescued vs not rescued)
- `time_to_first_response_distribution`

### Governance and quality controls

- **Versioned model configs** per tenant or segment (`risk_model_v1`, `risk_model_v1.1`).
- **Explainability required**: no score without drivers.
- **Fairness checks**: ensure risk is not proxying protected attributes.
- **Operational KPI coupling**:
  - `% entities with first response within SLA`
  - `% high-risk touched within 24h`
  - conversion uplift on previously high-risk cohort.

### Phased rollout plan

Phase A (2-3 weeks): instrumentation and baseline — **shipped (v1 scope)**

- unify timestamps/events needed for response and stage-gap metrics — **done** (derived from `contact_attempts`, `communication_threads` / `communication_messages`, `reminders`, `candidate_stage_history`; candidate scope matches list visibility).
- build retrospective risk table/job — **done** for aggregates + shadow: `risk_intel_tenant_hourly` + `risk_intel_entity_shadow`, filled by communications scheduler (hourly throttle).
- publish read-only analytics (no user-facing alerts yet) — **done** (live aggregate + persisted trends; ops roles only).

Phase B (2 weeks): shadow scoring + dashboard — **shipped (v1 scope)**

- calculate `risk_score` daily/hourly — **done** (hourly bucket per tenant; same model as live baseline).
- show risk widgets to ops leads only — **done** (API 403 for other roles; Overview block gated by role).
- validate precision/recall on recent outcomes — **done** as **proxy**: `GET /api/v1/analytics/risk-intelligence/validation` — forward stage movement after high/critical shadow cohort (tunable `cohort_days` / `lag_days`).

Phase C (2-4 weeks): assisted operations

- expose risk badge + drivers in list/card;
- enable medium/high nudges and recommended next action;
- no hard blocking yet.

Phase D (after confidence): controlled enforcement — **partially shipped (v1)**

- **Done (v1):** hourly job can fire tenant-defined `candidate.risk_band` automation rules (reminders, deduped); opt-in `Tenant.settings.risk_model_v1.automations`.
- **Done (v1):** opt-in forward **stage gate** — `risk_model_v1.stage_gate` (`enabled`, `min_band`, `block_forward_without_next_action`); mitigation = at least one active reminder on the candidate.
- **Done (v1):** Overview **shadow cohort digest** — latest hourly bucket listing (API + UI).
- **Done (v1):** opt-in **hourly digest email** — `risk_model_v1.digest_email` after persist (explicit `to` + optional `to_roles` → `user_memberships`; dedupe per `bucket_start` via `activity_log`).
- **Done (v1):** **Manager digest queue** on Overview — recent hourly buckets, pick bucket to load shadow cohort; **Mark reviewed** → `risk_intel.manager_digest_ack` (per user, last-seen bucket).
- **Done (v1):** digest queue **read-state filter** — Overview **Show**: all buckets / unread only / reviewed only (client-side; “Latest” chip stays the true newest bucket; viewing a bucket hidden by the filter resets selection to latest).
- **Done (v1):** digest **row handoff** — shadow snapshot items include `recruiter_id`; Overview cohort table **Remind** (24h reminder, `source=risk_intel.shadow_digest`, assignee auto or **picker** from `GET /users/managers`) + **Assign to me** (`recruiter_id` = current user).
- **Done (v1):** digest **bulk handoff** — multi-select + **Remind selected** (one assignee → `POST /reminders/bulk`; auto → parallel per-candidate reminders) + **Assign selected to me**; selection clears on bucket change.
- **Open:** optional stricter policies (e.g. band `high`); richer bulk error UX (per-entity lines, copy-to-clipboard).

**`risk_model_v1.digest_email` (tenant JSON, merged with service defaults)**

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `enabled` | bool | `false` | When true, hourly job attempts send after shadow persist. |
| `to` | string or string[] | `[]` | Explicit recipient addresses. |
| `to_roles` | string or string[] | `[]` | Canonical tenant roles (`administrator`, `supervisor`, `recruiter`, …); active users with matching `user_memberships` for this tenant receive the digest. Aliases: `admin`/`owner`→`administrator`, `manager`→`supervisor`, `hr`→`recruiter`, `client`→`client_manager`, `processor`→`client_processor`. Merged with `to`, emails deduped (case-insensitive). |
| `min_band` | string | `high` | Same semantics as shadow snapshot (`high`+ or `critical` only if configured). |
| `max_rows` | int | `25` | Cap 1–200; top rows by score in the email body. |
| `skip_if_empty` | bool | `true` | If no matching shadow rows for the latest bucket, do not send. |

### Acceptance criteria (must be measurable)

- For high-risk cohorts, median time-to-first-intervention improves by at least 30%.
- `first_response_within_target` improves by at least 20% in pilot teams.
- Conversion for previously high-risk entities improves vs pre-rollout baseline.
- Less than 10% of risk alerts are marked as "noise" by operators after tuning period.

### Immediate next step (this week)

Run a focused discovery sprint and produce a one-page evidence table:

- top 5 delay signals,
- their bucketized success curves,
- proposed half-lives and initial thresholds,
- expected intervention policy per signal.

After this, lock `risk_model_v1` config and start Phase A instrumentation.

### Operational matrix: risk → signals → thresholds → automation (v1 draft)

Use this matrix as the implementation-ready source for analytics, API fields, dashboard widgets, and automation rules.

#### 1) Candidate engagement decay risk

- **Risk definition**: candidate is losing motivation and likely to drop off before target stage.
- **Primary signals**:
  - `first_response_minutes`
  - `last_response_gap_hours`
  - `inbound_unanswered_hours`
  - `interaction_count_7d`
- **Initial thresholds**:
  - medium: first response > 24h
  - high: first response > 48h OR unanswered inbound > 24h
  - critical: first response > 72h OR unanswered inbound > 48h
- **Automation**:
  - medium: notify owner + suggest "contact now with template X"
  - high: auto-reminder due in 2h + manager digest entry
  - critical: escalate to backup owner queue + incident tag `risk_engagement_critical`
- **Success KPI**:
  - `% first response within 24h`
  - conversion from high-risk cohort vs baseline

#### 2) Stage stagnation / bottleneck risk

- **Risk definition**: entity is stuck in stage beyond healthy cycle and unlikely to progress without intervention.
- **Primary signals**:
  - `days_in_stage`
  - `days_since_stage_change`
  - `stage_reopen_count_30d`
- **Initial thresholds**:
  - stage baseline breach (per-stage SLA map) = medium
  - baseline * 1.5 = high
  - baseline * 2.0 = critical
- **Automation**:
  - medium: owner prompt with "next best action by stage"
  - high: require overdue reason code (`waiting_client`, `waiting_docs`, `no_response`, `internal_block`)
  - critical: auto-escalate to team lead board + force review task in 24h
- **Success KPI**:
  - median `days_in_stage` by stage
  - stage transition rate after intervention

#### 3) Next-action discipline risk

- **Risk definition**: work is not operationally controlled; no clear next step exists.
- **Primary signals**:
  - `has_next_action`
  - `next_action_overdue_hours`
  - `overdue_actions_count_7d`
- **Initial thresholds**:
  - no next action for > 24h = medium
  - overdue next action > 24h or 2+ overdue actions in 7d = high
  - overdue next action > 72h = critical
- **Automation**:
  - medium: one-click quick-create next action panel
  - high: auto-create fallback reminder and pin in work panel
  - critical: block non-terminal stage change until mitigation action exists (tenant-configurable)
- **Success KPI**:
  - `% entities with active next action`
  - `% high-risk touched within 24h`

#### 4) Owner capacity / overload risk

- **Risk definition**: assigned owner load is too high; SLA and quality degrade.
- **Primary signals**:
  - `owner_open_entities_count`
  - `owner_overdue_actions_count`
  - `owner_high_risk_entities_count`
- **Initial thresholds** (team-relative, percentile-based):
  - medium: owner above P75 on any 2 load signals
  - high: owner above P90 on any 2 load signals
  - critical: above P95 + rising overdue trend 7d
- **Automation**:
  - medium: recommend rebalance candidates/leads
  - high: notify manager with "reassign shortlist"
  - critical: auto-route new assignments away from overloaded owner until recovered
- **Success KPI**:
  - owner SLA compliance variance
  - overdue ratio before/after rebalancing

#### 5) Handoff failure risk

- **Risk definition**: ownership handoff happened, but new owner did not establish control quickly.
- **Primary signals**:
  - `hours_since_reassignment`
  - `first_action_after_reassignment_hours`
  - `messages_after_reassignment_24h`
- **Initial thresholds**:
  - no action within 8h after reassignment = medium
  - no action within 24h = high
  - no action within 48h = critical
- **Automation**:
  - medium: remind new owner to acknowledge handoff
  - high: notify previous owner + manager
  - critical: re-open handoff checklist and escalate
- **Success KPI**:
  - `% handoffs with first action < 8h`
  - post-handoff conversion vs baseline

#### 6) Readiness / document failure risk

- **Risk definition**: candidate cannot progress due to critical missing/expiring documents.
- **Primary signals**:
  - `missing_critical_docs_count`
  - `expiring_docs_count_14d`
  - `readiness_score`
- **Initial thresholds**:
  - medium: 1 critical missing doc OR >=2 expiring in 14d
  - high: >=2 critical missing docs OR any doc expiring in <=7d at active stage
  - critical: blocking document missing at decision/offer/onboarding stage
- **Automation**:
  - medium: trigger request-docs template flow
  - high: owner + compliance role notification
  - critical: prevent stage progression to dependent stages until resolved
- **Success KPI**:
  - readiness completion rate
  - delay caused by document blockers

#### 7) Communication quality risk

- **Risk definition**: communication exists but is ineffective (no progress signals).
- **Primary signals**:
  - `outbound_without_reply_count_7d`
  - `thread_age_open_days`
  - `resolution_event_absent` (bool)
- **Initial thresholds**:
  - medium: 3 outbound touches without reply in 7d
  - high: 5 touches without reply OR open thread > 10d
  - critical: open thread > 14d without resolution in active funnel stage
- **Automation**:
  - medium: suggest channel switch (email -> call/whatsapp/etc.)
  - high: suggest escalation template / manager outreach
  - critical: mark as "recovery playbook required" and queue specialized intervention
- **Success KPI**:
  - reply rate per channel after suggested switch
  - resolution time per thread

#### 8) Deal health / financial risk (services)

- **Risk definition**: service pipeline advances but commercial outcome degrades.
- **Primary signals**:
  - `invoice_overdue_amount`
  - `invoice_overdue_days_p95`
  - `margin_delta_vs_quote`
  - `delivered_not_invoiced_count`
- **Initial thresholds**:
  - medium: overdue amount > tenant threshold OR margin drop > 10%
  - high: overdue > 30d OR margin drop > 20%
  - critical: overdue > 60d OR negative margin forecast
- **Automation**:
  - medium: finance reminder + owner nudge
  - high: manager review task and payment recovery workflow
  - critical: freeze new discretionary work for account until review
- **Success KPI**:
  - outstanding-to-paid ratio
  - recovery rate for overdue cohort

### Cross-risk prioritization logic

When one entity has multiple risks, show a single priority queue score:

- `priority_score = 0.45*risk_score + 0.25*business_impact + 0.20*urgency + 0.10*recovery_potential`

Where:

- `business_impact` reflects expected value (revenue/hiring impact);
- `urgency` reflects time-to-deadline proximity;
- `recovery_potential` estimates chance to rescue if touched now.

### Implementation notes (v1)

- Keep all thresholds tenant-configurable in one namespace: `Tenant.settings.risk_model_v1`.
- Log every automated intervention with `risk_rule_id`, old/new band, and selected driver.
- Add operator feedback actions: `helpful`, `not_helpful`, `wrong_reason`; use this for monthly tuning.

### Suggested rollout order (lowest complexity to highest value)

1. Candidate engagement decay risk
2. Next-action discipline risk
3. Stage stagnation risk
4. Readiness/document failure risk
5. Owner overload risk
6. Handoff failure risk
7. Communication quality risk
8. Deal health/financial risk
