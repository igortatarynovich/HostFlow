# Email Client UX Research (Outlook-like) for HostFlow

## Goal
Сделать `Email Inbox` рабочим инструментом оператора, а не страницей технических настроек.

## Core principle
- `/app/email` = только работа с письмами.
- Настройки каналов/ящиков/интеграций = только в setup/settings.

## Target information architecture

### A. Main email workspace (Outlook-like)
1. Left rail (folders + counters):
- Inbox
- Unread
- Sent
- Assigned
- All

2. Center pane (conversation list):
- Subject
- Preview
- Last activity date
- Unread badge
- Assignee marker
- Quick status chip

3. Right pane (preview/details):
- Subject
- Status/unread/assignee
- Last message preview
- Created/updated timestamps
- Primary CTA: Open thread

### B. Toolbar
- Search input
- Refresh button
- Minimal single CTA to setup only when setup is incomplete

## What should NOT be in /app/email
- Mailbox account list
- OAuth raw controls
- Worker/manual poll controls
- Ingest test forms
- Cursor internals

Все это должно быть в:
- `/app/setup/communications` (guided setup)
- `/app/settings/communications` (advanced)
- `/app/settings/email` (SMTP transport)

## Interaction model
- Default folder: Inbox
- If folder/search changes, first visible thread auto-selected
- Mobile: panes stack vertically (folders -> list -> preview)
- Desktop: 3-column layout

## Role model
- Operator/Recruiter: full email workspace
- Team lead: same + assignment context
- Admin: same workspace, но настройки отдельно

## KPI for usability
- Time to first open conversation < 5s
- No technical terms in daily workflow pane
- One-click from list to thread detail

## Rollout plan
1. Step 1: Outlook-like layout in `/app/email` (folders/list/preview)
2. Step 2: Compose/reply actions directly in workspace
3. Step 3: Multi-mailbox selector (if needed) as simple business filter, not technical account management
4. Step 4: Keyboard navigation and bulk actions

## Acceptance criteria
- Пользователь не видит технические блоки в `/app/email`
- Папки и счетчики понятны без обучения
- Любой входящий поток открывается максимум в 2 клика
