/** @vitest-environment node */
import { describe, expect, it } from 'vitest'
import type { AcquisitionActivityEvent } from '../../../api/acquisitionActivity'
import { countFlightFunnel, destinationSummary, statusLabel } from '../marketingPresentation'
import type { Campaign } from '../../../api/platformCampaigns'

function event(partial: Partial<AcquisitionActivityEvent>): AcquisitionActivityEvent {
  return {
    id: partial.id || 'e1',
    tenant_id: 't1',
    campaign_id: 'c1',
    flight_id: partial.flight_id ?? 'f1',
    event_type: partial.event_type || 'SubmissionReceived',
    event_version: '1',
    occurred_at: '2026-07-21T10:00:00Z',
    recorded_at: '2026-07-21T10:00:00Z',
    actor_type: 'system',
    payload: {},
    ...partial,
  }
}

describe('marketingPresentation', () => {
  it('counts funnel events for a flight', () => {
    const events = [
      event({ id: '1', event_type: 'SubmissionReceived' }),
      event({ id: '2', event_type: 'RoutingCompleted' }),
      event({ id: '3', event_type: 'RoutingFailed' }),
      event({ id: '4', event_type: 'DuplicateDetected' }),
      event({ id: '5', flight_id: 'other', event_type: 'SubmissionReceived' }),
    ]
    expect(countFlightFunnel(events, 'f1')).toEqual({
      received: 1,
      routed: 1,
      routingFailed: 1,
      duplicates: 1,
    })
  })

  it('summarizes destination without raw UUID', () => {
    const campaign = {
      targets: [{ target_type: 'vacancy', target_id: 'uuid-here', route_intent: 'candidate_application' }],
    } as Campaign
    const summary = destinationSummary(campaign)
    expect(summary).toContain('Вакансия')
    expect(summary).not.toContain('uuid-here')
  })

  it('labels statuses in Russian', () => {
    expect(statusLabel('active')).toBe('Активна')
    expect(statusLabel('paused')).toBe('На паузе')
  })
})
