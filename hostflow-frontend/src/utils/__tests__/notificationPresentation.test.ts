import { describe, expect, it } from 'vitest'
import type { NotificationItem } from '../../api/types'
import type { TranslateFn } from '../../i18n'
import {
  notificationDisplayDescription,
  notificationDisplayTitle,
  notificationEventTypeLabel,
} from '../notificationPresentation'

const STRINGS: Record<string, string> = {
  'app.notifications.communications_sla_overdue_title': 'SLA przekroczone',
  'app.notifications.event_types.candidate_docs_pending_upload': 'Oczekiwane dokumenty kandydata',
  'app.notifications.event_types.candidate_docs_pending_upload_desc':
    '{name}: postęp {ready}/{total}, brakuje jeszcze {missing} plików.',
  'app.notifications.event_types.reminder_due': 'Zadanie na termin',
}

const t: TranslateFn = (key, options) => {
  const raw = STRINGS[key] ?? (options?.defaultValue || '')
  if (!raw) return key === options?.defaultValue ? key : options?.defaultValue || ''
  const values = { ...(options || {}), ...(options?.values || {}) } as Record<string, unknown>
  return Object.entries(values).reduce((acc, [k, v]) => {
    if (k === 'defaultValue' || k === 'values') return acc
    if (typeof v !== 'string' && typeof v !== 'number') return acc
    return acc.split(`{${k}}`).join(String(v))
  }, raw)
}

function item(partial: Partial<NotificationItem> & { event_type: string }): NotificationItem {
  return {
    id: 'n1',
    channel: 'in_app',
    is_read: false,
    created_at: '2026-01-01T00:00:00Z',
    payload: {},
    ...partial,
  }
}

describe('notificationPresentation', () => {
  it('prefers localized event type over English/Russian payload titles', () => {
    expect(
      notificationDisplayTitle(
        item({
          event_type: 'candidate_docs_pending_upload',
          payload: { title: 'Ожидаются документы кандидата' },
        }),
        t,
      ),
    ).toBe('Oczekiwane dokumenty kandydata')
    expect(
      notificationDisplayTitle(
        item({
          event_type: 'communications_sla_overdue',
          payload: { title: 'SLA overdue: WHATSAPP' },
        }),
        t,
      ),
    ).toBe('SLA przekroczone')
  })

  it('keeps reminder task titles from payload', () => {
    expect(
      notificationDisplayTitle(
        item({
          event_type: 'reminder_due',
          payload: { title: 'Call Jan Kowalski' },
        }),
        t,
      ),
    ).toBe('Call Jan Kowalski')
  })

  it('formats candidate docs description from payload fields', () => {
    expect(
      notificationDisplayDescription(
        item({
          event_type: 'candidate_docs_pending_upload',
          payload: { candidate_name: 'Jan', ready: 1, total: 4, missing: 3 },
        }),
        t,
      ),
    ).toBe('Jan: postęp 1/4, brakuje jeszcze 3 plików.')
  })

  it('labels event types instead of raw keys', () => {
    expect(notificationEventTypeLabel('candidate_docs_pending_upload', t)).toBe(
      'Oczekiwane dokumenty kandydata',
    )
  })
})
