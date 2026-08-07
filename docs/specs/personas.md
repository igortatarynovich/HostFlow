# Personas — Канонические пользовательские пути HostFlow

**Назначение:** кто пользуется HostFlow, trust role, preset/org/scope, и путь UAT. Журналы: `docs/specs/journeys/`.

**Canon:** [`ADR-036`](architecture/ADR-036-four-trust-roles-rbac.md) · [`rbac_matrix.md`](architecture/rbac_matrix.md)

**Связи:** `usePermissions.ts`, `backend/app/auth/trust_roles.py`, `plans-matrix.md`, tenant modules.

**Правило UAT:** (1) trust role + permissions; (2) тариф; (3) production-checklist (skeleton/error/empty, i18n, a11y).

**Инвариант:** новая «должность» = preset / scope / org / capability, **не** пятая trust role.

---

## Trust personas

### P-1. `administrator` (Tenant admin / Owner)

**Trust role:** `administrator` · **access_context:** `tenant`  
**Кто:** основатель / админ тенанта.  
**Цель:** воронка работает; команда и доступы под контролем; биллинг понятен.

**Top-3 JTBD:**

1. Подключить источник лидов и увидеть приход.
2. Пригласить Employee, выдать preset, задать scope / supervisor.
3. Править **Settings → Team → Roles & access** в пределах trust ceilings.

**Видит:** tenant admin (users, roles/access, billing, settings).  
**Не видит:** чужие tenants (кроме если также superadmin).  
**Журнал:** `journeys/administrator.md`

---

### P-SA. `superadmin` (Platform)

**Trust role:** `superadmin`  
**Кто:** HostFlow platform operator.  
**Видит:** Platform / tenants, impersonation.  
Не смешивать с tenant administrator.

---

### P-2. `employee` — preset `team_lead` (бывш. supervisor)

**Trust role:** `employee` · **preset:** `team_lead` · **org:** имеет подчинённых через `supervisor_id`  
**Кто:** тимлид / recruitment manager.  
**Цель:** SLA команды, переназначения, эскалации — **без** users/roles/billing.

**Не видит:** Admin-locked (users/roles matrix write, billing, platform).  
**Журнал:** `journeys/supervisor.md` (legacy name; persona = employee + team_lead)

---

### P-3. `employee` — preset `recruiter`

**Trust role:** `employee` · **preset:** `recruiter`  
**Кто:** ежедневный операционный пользователь.  
**Цель:** Tasks/Inbox → кандидаты → pipeline в 2 клика.

**Не видит:** Settings admin, Users, Billing, Tenants.  
**Журнал:** `journeys/recruiter.md`

---

### P-3b. `employee` — presets `hr` / `compliance`

**Trust role:** `employee` · **preset:** `hr` или `compliance`  
**Кто:** HR / process documents.  
Доступы из пресета + module matrix; не отдельные trust roles.  
Legacy strings `hr_officer` / `compliance_officer` → aliases → employee + preset.

---

### P-6. `viewer` — tenant stakeholder

**Trust role:** `viewer` · **access_context:** `tenant`  
**Кто:** инвестор, аудитор, обучение.  
**Цель:** смотреть, не ломать. Read-oriented; без Create/bulk/settings admin.

**Журнал:** `journeys/viewer.md`

---

### P-4 / P-5. Portal guest (deprecated client_* roles)

**Trust role:** `viewer` · **access_context:** `portal` · **preset:** `portal_guest`  
**Кто:** сотрудник компании-клиента **без** лицензии HostFlow.  
**Не** `client_manager` / `client_processor` (deprecated).  
**Seat:** не billable CRM Employee/Admin.

**Top-3 JTBD:** видеть scoped кандидатов; подписать документ (portal capability); комментарий.

Paying client with own HF tenant → их Admin/Employee (`access_context=tenant`), не portal guest.

**Журналы (legacy names):** `journeys/client-manager.md`, `journeys/client-processor.md` — трактовать как portal viewer.

---

### P-7. `candidate_portal_user` (External — magic link)

Не CRM trust role. Token intake. Журнал: `journeys/candidate-portal.md`

---

### P-8. Branded client portal (token UI)

Может совпадать с P-4/P-5 (viewer + portal) или оставаться token-only surface. Журнал: `journeys/client-portal.md`

---

## Org example (обе Employee)

| | Anna | Valentina |
|--|------|-----------|
| Role | employee | employee |
| Preset | recruiter | team_lead |
| Team | Recruitment Poland | Recruitment Poland |
| Supervisor | Valentina | Igor |
| Scope | Company A+B | all recruitment companies |
| access_context | tenant | tenant |

Повышение Anna → смена preset + org, не trust role.

---

## Cheat-sheet (trust × surface)

| Surface | Admin | Employee (ops presets) | Viewer tenant | Viewer portal | Candidate ext | Superadmin |
|---------|:-----:|:----------------------:|:-------------:|:-------------:|:-------------:|:----------:|
| Dashboard | ✓ | ✓ scoped | ✓ read | ✓ scoped | — | ✓ |
| Leads | ✓ | ✓ (recruiter/team_lead) | ✓ read | — | — | ✓ |
| Candidates | ✓ | ✓ | ✓ read | ✓ scope | — | ✓ |
| Settings users/roles/billing | ✓ | — | — | — | — | ✓ |
| Roles & access matrix | ✓ | — | — | — | — | ✓ (tenants) |
| Portal sign/comment | — | — | — | capability | — | — |
| Platform tenants | — | — | — | — | — | ✓ |

---

## Acceptance — UAT template

См. прежний checklist в `docs/specs/journeys/{persona}.md` (skeleton, CTA, plan, empty/error, i18n, a11y, mobile).
