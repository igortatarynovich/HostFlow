# Communications Workspace Research & Target UX (v1)

## 1) Problem statement (current)
- New user cannot understand where to start.
- Too many technical controls are exposed at once (queue diagnostics, scheduler internals, entitlements, role overrides).
- Core operator flow is fragmented: inboxes, planner, calendar, availability, time-off are not tied by one clear entry scenario.
- Inbound channels are not explicit for users: outbound works, inbound path is unclear (poll/webhook, schedule, account readiness).
- In working inboxes, control surface still dominates the viewport: filters, management buttons and auxiliary actions compete with the actual conversation area.
- On mobile, communication screens can degenerate into button stacks where the message timeline is pushed below the fold.
- Email Inbox still needs a hard reliability rule: expected inbound emails must appear in the operator workspace without resorting to technical debugging.

## 2) Product goal
A new tenant admin should be able to:
1. Open one setup entry point.
2. Connect email + at least one messenger.
3. Confirm inbound is active.
4. Configure manager routing basics.
5. Start handling conversations in inboxes.

Target time to first operation: 10-15 minutes.

## 3) Information architecture

### 3.1 User-facing workspaces
- Messages Inbox (`/app/messages`): all non-email channels, live threads, assignment, reply.
- Email Inbox (`/app/email`): mailbox threads, inbound/outbound email operations.
- Planner (`/app/planner`): tasks, calls, meetings, shifts.
- Calendar (`/app/calendar`): unified timeline (messages SLA, reminders, planner, time-off).
- Team Availability (`/app/team-availability`): lead/admin monitoring.
- My Availability (`/app/my-availability`): personal status + time-off request creation.
- Time-off Requests (`/app/time-off`): manager approvals.

### 3.2 Setup and admin zones
- Quick Setup (new): `/app/setup/communications`
  - Guided onboarding/checklist only.
  - No low-level diagnostics.
- Advanced Communications Settings: `/app/settings/communications`
  - Entitlements
  - Role/user access
  - Queue strategy diagnostics
  - Scheduler diagnostics/audit

## 4) First-run setup wizard (must-have)

### Step A. Pick active channels
- Goal: decide what is used now (email + Telegram initially).
- Output: enabled modules/channels in tenant settings.

### Step B. Connect accounts
- Email mailbox (OAuth preferred, IMAP fallback).
- Telegram bot account.
- Output: at least 1 active account for each selected channel.

### Step C. Inbound readiness check
- Email inbound: worker/scheduler active OR manual poll available and tested.
- Telegram inbound: webhook/token configured and test inbound processed.
- Output: “Inbound ready” boolean per channel.

### Step D. Team routing baseline
- Queue enabled.
- Strategy selected (default `round_robin`).
- At least one active manager in queue.
- Respect availability/schedules enabled.

### Step E. Go live
- Open Messages Inbox.
- Open Email Inbox.
- Optional: create first planner task.

## 5) Visibility and permissions model
- Operators/recruiters: only inboxes/planner/calendar/my availability.
- Team leads: + team availability + time-off approvals.
- Tenant admins: + quick setup + advanced settings.
- Superadmin/platform: + subscription/entitlements and global tenant controls.

## 6) What should be hidden from normal users
- Scheduler internals and tick diagnostics.
- Allocator raw audit table.
- Role override matrix.
- Entitlement flags by plan.

These stay in advanced admin settings only.

## 7) Inbound/outbound behavior contract

### Email
- Outbound: send from connected mailbox/OAuth or tenant SMTP fallback.
- Inbound: poll worker must persist messages into threads.
- Threading: by provider refs + subject/sender fallback.

### Messengers (Telegram first)
- Outbound: CRM reply to channel thread.
- Inbound: webhook ingest creates/updates thread and can auto-assign.

## 8) KPI/health indicators (in setup page)
- Connected accounts count by channel.
- Last inbound timestamp by channel.
- Queue readiness (enabled + active managers).
- Messages with failed dispatch in queue.

## 9) Delivery plan

### Phase 1 (now)
- Add Quick Setup page with checklist and status cards.
- Link from communications settings and main nav.
- Keep advanced diagnostics in settings page.

### Phase 2
- Add guided actions directly in setup (toggle modules, create first account, run inbound test).
- Add explicit “Inbound OK / Not OK” checks based on real API data.

### Phase 3
- Enforce first-run flow: if comms not configured, show CTA banner in inbox pages.

## 10) UX principles
- One screen = one decision.
- Default-first: prefill sane defaults.
- Hide advanced controls unless user asks.
- Always show “what to do next” in operational terms, not technical terms.
- Thread-first: conversation list and active timeline are the main surface; secondary controls are subordinate.
- Mobile-first inbox rule: above the fold user sees conversation context, not control chrome.
