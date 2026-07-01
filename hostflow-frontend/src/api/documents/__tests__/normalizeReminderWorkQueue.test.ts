// @vitest-environment node
import { describe, expect, it } from 'vitest'
import { normalizeReminderWorkQueueItem } from '../normalize'

describe('normalizeReminderWorkQueueItem', () => {
  it('normalizes backend reminder_work_queue row', () => {
    const row = normalizeReminderWorkQueueItem({
      task_key: 'document:passport:expired:employee:123',
      title: 'Passport expired',
      severity: 'critical',
      owner_type: 'employee',
      owner_id: '123',
      recipient_role: 'hr',
      due_date: '2026-05-29',
      source_pack: 'legal_stay_pack',
      action: 'request_update',
      document_code: 'passport',
      reason: 'expired',
    })

    expect(row).toMatchObject({
      task_key: 'document:passport:expired:employee:123',
      title: 'Passport expired',
      severity: 'critical',
      action: 'request_update',
      document_code: 'passport',
      due_date: '2026-05-29',
    })
  })
})
