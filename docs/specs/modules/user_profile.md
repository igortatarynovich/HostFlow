# User Profile & Preferences — Specification

_Updated: 2025-10-19_

This document describes the consolidated “Personal Cabinet” experience for HostFlow users. It covers profile data, UI preferences, notification settings, active sessions, security tools, and default shortcuts that integrate with Companies/Vacancies/Candidates modules.

---

## Goals
- Give every authenticated user a single `/profile` cockpit for managing personal data, contact info, preferences, and security.
- Provide backend APIs that expose profile, preferences, notifications, and session management in a single surface.
- Persist defaults (company, saved views) that immediately influence list pages.
- Ensure the solution works in the multi-tenant environment with RLS.

---

## Data Model

| Resource | Storage | Notes |
|----------|---------|-------|
| **Profile** | `users.extra -> profile` JSON | Keys: `first_name`, `last_name`, `position`, `phone`, `email`, `country`, `city`, `birth_date`, `avatar_url`. |
| **Preferences** | `user_preferences` JSONB (new column/table) | Root object with namespaces: `ui`, `notifications`, `defaults`, `saved_views`. |
| **UI Preferences** | `preferences.ui` | `locale`, `timezone`, `date_format`, `phone_format`, `theme` (`light` \| `dark` \| `system`). |
| **Notifications** | `preferences.notifications` | Map of event codes → `{ enabled: bool, channel: "email", mode: "immediate" \| "daily_digest" }`. MVP supports email channel only. |
| **Defaults** | `preferences.defaults` | `company_id` (UUID) used as default filter; future fields can be added. |
| **Saved Views** | `preferences.saved_views` | Map indexed by module (`candidates`, `vacancies`). Each entry: `{ id, name, filters, is_default? }`. |
| **Sessions** | `user_sessions` table | Columns: `id`, `user_id`, `tenant_id`, `created_at`, `last_seen_at`, `ip_address`, `user_agent`, `device_label`, `expires_at`, `revoked_at`. |

### Migrations
1. Add `user_preferences` JSONB column to `users` table (Postgres) + JSON fallback for SQLite dev. Default `{}`.
2. Create `user_sessions` table with foreign key to `users` and partial index on `(user_id, revoked_at)`.
3. (Optional) Add GIN index on `user_preferences` for jsonb queries.

### Validation
- `email` unique per tenant (existing constraint).
- `birth_date` ISO `YYYY-MM-DD`.
- Password complexity: min 12 chars; at least one uppercase, lowercase, digit, and special character.
- Saved views capped to 20 per module for MVP.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/users/me` | Returns profile, preferences, security summary (role, supervisor, companies, last_login, sessions_count). |
| `PATCH` | `/api/v1/users/me` | Partial update of profile fields and preferences, including defaults & saved views. |
| `POST` | `/api/v1/users/me/avatar` | Upload avatar image, returns `avatar_url`. Supports multipart or presigned workflow. |
| `POST` | `/api/v1/users/me/password` | Change password with complexity enforcement. |
| `GET` | `/api/v1/users/me/sessions` | List active sessions (current + others). |
| `DELETE` | `/api/v1/users/me/sessions` | Revoke all sessions except current. |
| `GET` | `/api/v1/users/me/notifications` | Fetch notification matrix. |
| `PATCH` | `/api/v1/users/me/notifications` | Update notification preferences (enabled/mode per event). |

### Response Shapes

```json
GET /api/v1/users/me
{
  "profile": {
    "user_id": "uuid",
    "email": "admin@hostflow.dev",
    "first_name": "Игорь",
    "last_name": "Татарнович",
    "position": "Менеджер",
    "phone": "+48 504 004 622",
    "country": "Польша",
    "city": "Познань",
    "birth_date": "1990-02-13",
    "avatar_url": "https://cdn/avatars/...png"
  },
  "preferences": {
    "ui": {
      "locale": "ru-RU",
      "timezone": "Europe/Warsaw",
      "date_format": "DD.MM.YYYY",
      "phone_format": "+CC (AAA) BBB-CC-DD",
      "theme": "dark"
    },
    "notifications": {
      "candidate.new_assignment": { "enabled": true, "mode": "immediate" },
      "candidate.stage_changed": { "enabled": true, "mode": "daily_digest" },
      "documents.deadline": { "enabled": true, "mode": "immediate" },
      "mentions.direct": { "enabled": true, "mode": "immediate" }
    },
    "defaults": {
      "company_id": "uuid-company"
    },
    "saved_views": {
      "candidates": [
        { "id": "team-ready", "name": "Готовы к выезду", "filters": {...}, "is_default": true }
      ],
      "vacancies": [
        { "id": "priority", "name": "Приоритетные", "filters": {...} }
      ]
    }
  },
  "security": {
    "role": "administrator",
    "companies": [
      { "id": "uuid-company", "name": "LogiTrans", "can_edit": true }
    ],
    "supervisor": {
      "id": "uuid-supervisor",
      "name": "Ольга Иванова",
      "email": "o.ivanova@hostflow.dev"
    },
    "last_login_at": "2025-10-18T09:42:10Z",
    "sessions_count": 3
  }
}
```

PATCH requests accept partial objects; omitted sections remain unchanged. Backend merges JSON paths, respecting `null` for resets (e.g., clearing `defaults.company_id`).

---

## Frontend UX

- Route `/profile`, accessible by clicking username in sidebar.
- Layout: cards for Profile, Contacts, Preferences, Notifications, Security, Sessions.
- Forms support inline validation, dirty-state tracking, “Сохранить” / “Отменить”.
- Toast feedback for success/error; error messages from API `detail`.
- Avatar upload: drag-and-drop, square cropper, preview before save.
- Preferences apply immediately: theme toggles global CSS, locale/timezone propagate to date/time formatting.
- Saved views manager: list, rename, delete, set default. The selected default pushes to list pages via shared store.

---

## Integrations

- **Companies/Vacancies/Candidates**: default company & saved views feed list filters.
- **Notifications**: scheduling hooks will live in existing services (pipeline, documents). MVP stores preferences and triggers email events via existing mailer; digest scheduler TBD.
- **Sessions**: reuse refresh-token issuance to register session entries; session revocation clears refresh tokens.

---

## Open Questions & Future Work
- Decide storage location for avatars (S3 vs local). MVP will use existing uploads bucket.
- Digest email scheduling: integrate with reminders cron or add new worker.
- Saved views import/export for power users (future).
- “Next” and “Pro” scopes (2FA, integrations, API tokens, etc.) tracked separately per roadmap.

---

## Acceptance Criteria
1. User can change profile data, preferences, notifications, defaults, and saved views; data persists across reload.
2. Avatar uploads result in accessible URL and updated preview.
3. Session list populates with active devices; “logout everywhere” revokes all other sessions.
4. Default company/saved views immediately affect list pages (candidates & vacancies) without manual reconfiguration.
5. Specs (`auth.md`, this document) and API references are updated; seeds populate sane defaults for new fields.

