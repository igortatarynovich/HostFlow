import { describe, expect, it } from 'vitest'

import {
  isSalesInquiryTimelineItemVisible,
  salesInquiryTimelineDescription,
  salesInquiryTimelineKindTitle,
} from '../salesInquiryTimeline'

const t = (key: string, opts?: { defaultValue?: string }) => {
  const map: Record<string, string> = {
    'app.leads.detail.timeline_kinds.lead_received': 'Inquiry received',
    'app.leads.detail.timeline_kinds.call_result': 'Call result',
    'app.leads.detail.timeline_kinds.gdpr_notice': 'GDPR notice sent',
    'app.leads.detail.timeline_kinds.system_event': 'System event',
    'app.leads.detail.call_result.results.no_answer': 'No answer',
  }
  return map[key] ?? opts?.defaultValue ?? key
}

describe('salesInquiryTimeline', () => {
  it('hides recruitment application_received and NBA reminders', () => {
    expect(
      isSalesInquiryTimelineItemVisible({
        at: '2026-07-28T10:49:00Z',
        kind: 'activity',
        source: 'activity_log',
        title: 'lead.communication.application_received_sent',
      }),
    ).toBe(false)
    expect(
      isSalesInquiryTimelineItemVisible({
        at: '2026-07-29T10:49:00Z',
        kind: 'reminder_created',
        source: 'reminder',
        title: 'Lead: create next action',
      }),
    ).toBe(false)
  })

  it('keeps sales-owned events and localizes titles', () => {
    expect(
      isSalesInquiryTimelineItemVisible({
        at: '2026-07-28T10:49:00Z',
        kind: 'lead_received',
        source: 'lead',
        title: 'lead.received',
      }),
    ).toBe(true)
    expect(salesInquiryTimelineKindTitle(t, 'lead_received', 'lead.received')).toBe('Inquiry received')
    expect(salesInquiryTimelineKindTitle(t, 'gdpr_notice', 'rodo_sent')).toBe('GDPR notice sent')
    expect(salesInquiryTimelineKindTitle(t, 'activity', 'lead.communication.application_received_sent')).toBe(
      'System event',
    )
  })

  it('localizes call result codes in the description', () => {
    expect(
      salesInquiryTimelineDescription(t, {
        at: '2026-08-12T13:03:00Z',
        kind: 'call_result',
        source: 'activity_log',
        title: 'lead.call_result',
        description: 'no_answer',
      }),
    ).toBe('No answer')
  })
})
