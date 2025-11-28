# Documents Readiness Contract

## Payload (GET /api/v1/documents)

Each document entry includes readiness helpers:
- `ordered_at` (date|null)
- `valid_from` (date|null)
- `has_files` (bool)
- `readiness_state` (`pending`, `requested`, `ordered`, `in_progress`, `awaiting_review`, `ready`, `problem`)
- `status_rank` (number for sorting by lifecycle)

Filters:
- `ordered=true|false`
- Existing `status`, `type`, `candidate_id`.

UI should allow column toggles for:
- Ordered at
- Valid from
- Readiness badge (uses `readiness_state`)
- Files attached indicator (from `has_files`)

Sorting recommendation:
- Default: by `status_rank` desc, then `ordered_at` desc.

## SLA Offsets

Reminder payloads contain:
- `offset_hours`
- `schedule_key` (e.g. `document_expiry:-24`)
- `channel_templates` map for in_app/email/webhook.

Frontend should render friendly labels:
- T−24 → 24 hours before expiry
- T−4 → 4 hours before expiry
- T+0 → On expiry day
- T+N → repeats every `repeat_interval_hours` (24h).
