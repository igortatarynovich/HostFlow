// @vitest-environment node
import { describe, expect, it } from 'vitest'
import type { ReminderWorkQueueItem } from '../../api/types'
import { sortReminderWorkQueue } from '../documentActionsPanel'

function item(
  overrides: Partial<ReminderWorkQueueItem> & Pick<ReminderWorkQueueItem, 'task_key' | 'severity'>,
): ReminderWorkQueueItem {
  return {
    title: 'Test',
    owner_type: 'employee',
    owner_id: '1',
    recipient_role: 'hr',
    source_pack: 'legal_stay_pack',
    action: 'request_update',
    document_code: 'passport',
    reason: 'expired',
    ...overrides,
  }
}

describe('sortReminderWorkQueue', () => {
  it('orders by severity then due_date ascending', () => {
    const sorted = sortReminderWorkQueue([
      item({ task_key: 'a', severity: 'low', due_date: '2026-06-01' }),
      item({ task_key: 'b', severity: 'critical', due_date: '2026-06-10' }),
      item({ task_key: 'c', severity: 'high', due_date: '2026-05-20' }),
      item({ task_key: 'd', severity: 'critical', due_date: '2026-05-15' }),
      item({ task_key: 'e', severity: 'medium', due_date: null }),
    ])

    expect(sorted.map((row) => row.task_key)).toEqual(['d', 'b', 'c', 'e', 'a'])
  })
})
