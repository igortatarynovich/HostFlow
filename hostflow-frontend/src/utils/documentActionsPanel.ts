import type { ReminderWorkQueueItem, ReminderWorkQueueSeverity } from '../api/types'

const SEVERITY_ORDER: Record<ReminderWorkQueueSeverity, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
}

export const DOCUMENT_ACTION_LABEL: Record<string, string> = {
  upload_document: 'Upload document',
  request_update: 'Request update',
  renew_document: 'Renew document',
  capture_expiry_date: 'Capture expiry date',
}

export function sortReminderWorkQueue(items: ReminderWorkQueueItem[]): ReminderWorkQueueItem[] {
  return [...items].sort((a, b) => {
    const severityA = SEVERITY_ORDER[a.severity] ?? 9
    const severityB = SEVERITY_ORDER[b.severity] ?? 9
    if (severityA !== severityB) return severityA - severityB
    return String(a.due_date || '').localeCompare(String(b.due_date || ''))
  })
}

export function formatDocumentActionDueDate(value?: string | null): string {
  if (!value) return '—'
  const ms = Date.parse(value)
  if (!Number.isFinite(ms)) return value.slice(0, 10)
  try {
    return new Intl.DateTimeFormat(undefined, { dateStyle: 'short' }).format(ms)
  } catch {
    return value.slice(0, 10)
  }
}

export function humanizePackCode(code: string): string {
  const raw = String(code || '').trim().replace(/_/g, ' ')
  if (!raw) return '—'
  return raw
    .split(' ')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export function humanizeDocumentCode(code: string): string {
  const raw = String(code || '').trim().replace(/_/g, ' ')
  if (!raw) return '—'
  return raw
    .split(' ')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}
