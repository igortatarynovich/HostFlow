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

  it('labels service_order destinations', () => {
    const campaign = {
      targets: [{ target_type: 'service_order', target_id: 'ord-1', route_intent: 'service_request' }],
    } as Campaign
    expect(destinationSummary(campaign)).toContain('Заказ')
  })

  it('maps legacy flow query to subject kinds', async () => {
    const { subjectKindFromFlowParam, SUBJECT_PRESETS } = await import('../marketingPresentation')
    expect(subjectKindFromFlowParam('candidates')).toBe('vacancy')
    expect(subjectKindFromFlowParam('clients')).toBe('service')
    expect(subjectKindFromFlowParam('service_order')).toBe('service_order')
    expect(SUBJECT_PRESETS.map((p) => p.kind)).toEqual(['vacancy', 'service_order', 'service'])
    expect(SUBJECT_PRESETS.find((p) => p.kind === 'vacancy')?.scopedToClient).toBe(true)
    expect(SUBJECT_PRESETS.find((p) => p.kind === 'service')?.scopedToClient).toBe(false)
  })

  it('labels statuses in Russian', () => {
    expect(statusLabel('active')).toBe('Активна')
    expect(statusLabel('paused')).toBe('На паузе')
  })
})
