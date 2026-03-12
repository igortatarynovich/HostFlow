# Communications Module Test Matrix (Phase 1-2)

## Goal
Validate communications foundation before enabling real messenger/email webhooks in production.

## Scope
- Tenant communications settings
- Manager queue / schedules / availability
- Allocator dry-run preview
- Threads / messages API
- Communications Hub UI (Inbox / Channels / Calendar / Planner)
- SMTP settings handoff (existing module)

## Test Data Preparation
1. Create at least 4 managers in tenant:
   - `M1` available, normal load
   - `M2` busy
   - `M3` available but outside schedule
   - `M4` at capacity
2. Enable queue and configure at least 2 strategies:
   - `round_robin`
   - `least_busy`
3. Enable channels in settings:
   - `email`, `whatsapp`, `telegram`
4. Create 5+ communication threads across channels.
5. Create inbound and outbound messages in at least 2 threads.

## A. Tenant Settings Persistence
1. Change channel enable/inbound/outbound/SLA and save.
2. Reload page -> values persist.
3. Reload tenant (switch tenant if available) -> settings isolated per tenant.
4. Change manager schedule and availability -> save -> reload -> values persist.

## B. Manager Queue Logic (Manual Checks)
1. Queue disabled:
   - Preview returns `queue_disabled`
   - Auto-assign endpoint does not assign
2. Strategy `manual`:
   - Preview returns `manual_strategy`
   - Auto-assign endpoint leaves `assignee_id` unchanged
3. Strategy `round_robin`:
   - Repeated assigns rotate managers by `queueOrder`
   - Winner moves to end after assignment
4. Strategy `least_busy`:
   - Manager with lower load ratio wins
   - Capacity limits block overloaded managers
5. Strategy `weighted_round_robin`:
   - Higher `priorityWeight` influences winner when loads comparable

## C. Schedule / Availability Filters
1. Outside schedule:
   - In `Queue Test Lab`, set time outside manager shift
   - Candidate shows `outside_schedule`
2. Availability states:
   - `busy`, `meeting`, `break`, `offline` should exclude manager (if `respectAvailability=true`)
3. Capacity:
   - `currentLoad + open_threads >= maxConcurrentChats` => `at_capacity`
4. Toggle `respectSchedules=false`:
   - previously excluded by schedule becomes eligible
5. Toggle `respectAvailability=false`:
   - previously excluded by status/capacity becomes eligible

## D. Allocator Dry-Run Preview (Queue Test Lab)
1. Test each channel (`email`, `whatsapp`, `telegram`, `sms`)
2. Test current time and future time
3. Confirm output shows:
   - strategy
   - winner
   - candidate rows
   - exclusion reasons (`disabled`, `channel_not_allowed`, `outside_schedule`, `availability:*`, `at_capacity`)

## E. Threads API
1. Create thread (`POST /communications/threads`)
2. Create thread with `auto_assign=true`
3. List threads with filters:
   - `channel`
   - `assignee_id`
   - `entity_type/entity_id`
   - `status_filter`
4. Patch thread:
   - assign manually
   - archive/unarchive
   - change priority/status
5. Thread detail returns messages sorted ascending by `created_at`

## F. Messages API
1. Create inbound message:
   - thread `unread_count` increments
   - `last_inbound_at`, `last_message_at`, preview updated
2. Create outbound message:
   - `last_outbound_at`, `last_message_at` updated
3. Mark thread read:
   - inbound `read_at` set
   - thread `unread_count=0`
4. Internal note:
   - `is_internal_note=true`
   - does not break timeline sorting

## G. Communications Hub UI
1. Inbox shows threads + reminders + notifications together
2. Thread rows display:
   - channel
   - assignee
   - unread badge
3. `Auto assign` button updates assignee in row
4. `Mark read` clears unread badge/count
5. Metrics update:
   - `Open threads`
   - `Unread threads`
   - reminders/events counts

## H. Calendar / Planner
1. Reminder due/remind dates appear in calendar
2. Notification events appear in calendar
3. Planner buckets react to reminder statuses
4. Planner settings persist (backend settings)

## I. SMTP / Email Operational Prep (Current Foundation)
1. Configure SMTP in `/app/settings/email`
2. Send test email successfully
3. In communications settings, enable incoming email sync flag and save
4. Validate tenant config persisted (prepares for future IMAP/Graph/Gmail sync)

## J. Negative / Edge Cases
1. No managers in queue items
2. All managers disabled
3. All managers filtered out by schedule
4. Invalid timezone in settings
5. Queue order duplicates / non-sequential values (should still normalize after assignments)
6. Historical manager IDs in queue not present in current manager catalog

## Exit Criteria (Before Live Channel Integrations)
- Settings persist reliably per tenant
- Allocator preview results deterministic and explainable
- Auto-assign works and matches preview expectations
- Threads/messages API stable under CRUD and read flows
- UI reflects backend state after actions without stale data

## Next Phase (to reach full production)
- Real inbound adapters: Telegram / WhatsApp / Viber / Messenger
- Email inbound sync (IMAP / Microsoft Graph / Gmail API)
- Thread detail UI with composer + attachments
- Delivery webhooks/status updates
- SLA alerts/escalations and manager performance dashboards
