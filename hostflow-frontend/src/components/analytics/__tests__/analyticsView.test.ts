// @vitest-environment node
import { describe, expect, it } from 'vitest'

import { readAnalyticsView, writeAnalyticsView } from '../analyticsView'

describe('Analytics View URL', () => {
  it('round-trips period, dimensions, and presentation without dropping unrelated keys', () => {
    const params = new URLSearchParams('module=recruitment&from=2026-01-01&to=2026-01-31&company_id=c1&present=1')
    const view = readAnalyticsView(params)
    expect(view.from).toBe('2026-01-01')
    expect(view.companyId).toBe('c1')
    expect(view.present).toBe(true)

    const next = writeAnalyticsView(params, { vacancyId: 'v9', present: false, range: '30d' })
    expect(next.get('module')).toBe('recruitment')
    expect(next.get('vacancy_id')).toBe('v9')
    expect(next.get('present')).toBeNull()
    expect(next.get('range')).toBe('30d')

    const presented = writeAnalyticsView(params, { present: true })
    expect(presented.get('present')).toBe('1')
    expect(presented.get('module')).toBe('recruitment')
  })
})
