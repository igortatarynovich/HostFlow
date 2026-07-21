/** @vitest-environment node */
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { mockGet } = vi.hoisted(() => ({
  mockGet: vi.fn(),
}))

vi.mock('../client', () => ({
  api: { get: mockGet, post: vi.fn(), patch: vi.fn(), put: vi.fn(), delete: vi.fn() },
}))

import { listAcquisitionActivity } from '../acquisitionActivity'
import * as acquisitionActivityModule from '../acquisitionActivity'

describe('listAcquisitionActivity', () => {
  beforeEach(() => {
    mockGet.mockReset()
  })

  it('calls GET /platform/acquisition-activity with params', async () => {
    mockGet.mockResolvedValue({
      data: {
        items: [{ id: 'e1', event_type: 'FlightCreated', payload: {} }],
        next_cursor: { occurred_at: '2026-07-21T12:00:00Z', id: 'e1' },
        order: ['occurred_at', 'id'],
      },
    })

    const res = await listAcquisitionActivity({
      campaign_id: 'camp-1',
      flight_id: 'flight-1',
      limit: 50,
      after_occurred_at: '2026-07-21T11:00:00Z',
      after_id: 'prev',
    })

    expect(mockGet).toHaveBeenCalledWith('/platform/acquisition-activity', {
      params: {
        campaign_id: 'camp-1',
        flight_id: 'flight-1',
        limit: 50,
        after_occurred_at: '2026-07-21T11:00:00Z',
        after_id: 'prev',
      },
    })
    expect(res.items).toHaveLength(1)
    expect(res.next_cursor?.id).toBe('e1')
  })

  it('normalizes missing payload fields', async () => {
    mockGet.mockResolvedValue({ data: {} })
    const res = await listAcquisitionActivity()
    expect(res.items).toEqual([])
    expect(res.next_cursor).toBeNull()
    expect(res.order).toEqual(['occurred_at', 'id'])
  })

  it('exports read-only client surface (no write helpers)', () => {
    const exported = Object.keys(acquisitionActivityModule).sort()
    expect(exported).toEqual(['listAcquisitionActivity'])
    expect(exported.some((k) => /post|patch|put|delete|create|update|emit/i.test(k))).toBe(false)
  })
})
