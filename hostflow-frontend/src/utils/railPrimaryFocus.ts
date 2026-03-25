/**
 * Single “do this next” focus for the candidate work rail — same order as forward stage gates
 * (documents → contact attempt → vacancy), with overdue reminders first.
 */
import type { ReminderRecord } from '../api/types'

export type RailPrimaryFocus = 'next_action' | 'docs' | 'contact_stack' | 'vacancy' | null

function parseTs(value?: string | null): number {
  if (!value) return 0
  const ts = Date.parse(String(value))
  return Number.isNaN(ts) ? 0 : ts
}

function pickEarliestActiveReminder(reminders: ReminderRecord[]): ReminderRecord | null {
  const active = reminders.filter((r) => r && r.status !== 'done' && r.status !== 'cancelled')
  if (!active.length) return null
  const nowTs = Date.now()
  active.sort((a, b) => {
    const aDue = parseTs(a.due_at)
    const bDue = parseTs(b.due_at)
    const aOver = a.status === 'overdue' || (aDue > 0 && aDue < nowTs)
    const bOver = b.status === 'overdue' || (bDue > 0 && bDue < nowTs)
    if (aOver !== bOver) return aOver ? -1 : 1
    if (aDue !== bDue) return (aDue || Number.MAX_SAFE_INTEGER) - (bDue || Number.MAX_SAFE_INTEGER)
    return String(a.id).localeCompare(String(b.id))
  })
  return active[0] ?? null
}

/** True when the top-priority reminder is overdue (due in the past or status overdue). */
export function railHasUrgentReminder(reminders: ReminderRecord[], nowTs: number): boolean {
  const next = pickEarliestActiveReminder(reminders)
  if (!next) return false
  if (next.status === 'overdue') return true
  const ts = parseTs(next.due_at)
  return ts > 0 && ts < nowTs
}

export function resolveRailPrimaryFocus(input: {
  hasUrgentReminder: boolean
  docsHardBlocking: boolean
  docsSoftOnly: boolean
  contactAttemptBlocking: boolean
  contactPriorityRailVisible: boolean
  vacancyBlocking: boolean
}): RailPrimaryFocus {
  if (input.hasUrgentReminder) return 'next_action'
  if (input.docsHardBlocking) return 'docs'
  if (input.contactAttemptBlocking && input.contactPriorityRailVisible) return 'contact_stack'
  if (input.vacancyBlocking) return 'vacancy'
  if (input.docsSoftOnly) return 'docs'
  return null
}
