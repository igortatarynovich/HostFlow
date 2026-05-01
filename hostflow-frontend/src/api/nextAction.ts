/**
 * Shared types for the per-entity primary "what to do next" CTA.
 *
 * Mirrors `backend/app/services/next_action.py` (`NextActionDTO`,
 * `NextActionKind`, `NextActionPriority`). Stage 1a shipped only the
 * candidate variant; stage 2 generalises the shape so leads, vacancies,
 * documents, and threads can render through the same `<NextActionBadge>`.
 *
 * Keep the unions in sync with the backend enums — a drifted union here
 * silently renders the wrong colour or icon (the badge falls back to the
 * idle palette and `<IconClock>`, which is misleading on a critical row).
 */

export type NextActionEntityType = 'candidate' | 'lead' | 'vacancy' | 'document' | 'thread'

export type NextActionKind =
  | 'reminder'
  | 'contact'
  | 'handoff_await'
  | 'handoff_decision'
  | 'done'
  | 'idle'

export type NextActionPriority = 'critical' | 'high' | 'normal' | 'idle'

/**
 * Canonical DTO for the primary next-action surface. The `entity_type`
 * field is a discriminator the popover / badge use to vary the rendered
 * copy ("Closed: lost" makes sense on a lead, not on a candidate).
 */
export interface NextActionDTO {
  entity_type: NextActionEntityType
  entity_id: string
  kind: NextActionKind
  priority: NextActionPriority
  reason_code: string
  title: string
  title_key?: string | null
  hint?: string | null
  hint_key?: string | null
  due_at?: string | null
  href?: string | null
}
