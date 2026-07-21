/** @vitest-environment node */
import { describe, expect, it } from 'vitest'
import type { AcquisitionActivityEvent } from '../../../api/acquisitionActivity'
import {
  formatActivityDetailsJson,
  humanizeEventType,
  mergeActivityPages,
} from '../acquisitionActivityPresentation'

const base = (id: string, eventType = 'FlightCreated'): AcquisitionActivityEvent => ({
  id,
  tenant_id: 't1',
  campaign_id: 'c1',
  event_type: eventType,
  event_version: 'v1',
  occurred_at: '2026-07-21T12:00:00Z',
  recorded_at: '2026-07-21T12:00:01Z',
  actor_type: 'system',
  payload: { note: '<script>alert(1)</script>' },
})

describe('acquisitionActivityPresentation', () => {
  it('humanizes CamelCase event types', () => {
    expect(humanizeEventType('FlightCreated')).toBe('Flight Created')
    expect(humanizeEventType('')).toBe('—')
  })

  it('merges pages without duplicating ids', () => {
    const page1 = [base('a'), base('b')]
    const page2 = [base('b'), base('c')]
    expect(mergeActivityPages(page1, page2).map((e) => e.id)).toEqual(['a', 'b', 'c'])
  })

  it('formats payload as escaped JSON text (no HTML rendering)', () => {
    const json = formatActivityDetailsJson(base('a'))
    expect(json).toContain('<script>alert(1)</script>')
    expect(json).not.toMatch(/dangerouslySetInnerHTML/)
    // Round-trip proves it is data text, not markup nodes.
    expect(JSON.parse(json).payload.note).toBe('<script>alert(1)</script>')
  })
})
