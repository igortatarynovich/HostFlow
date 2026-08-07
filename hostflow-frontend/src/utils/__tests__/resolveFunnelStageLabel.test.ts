import { describe, expect, it } from 'vitest'

import { isJourneyStageCompletedByPosition } from '../journeyStageProgress'
import { resolveFunnelStageLabel } from '../resolveFunnelStageLabel'

describe('isJourneyStageCompletedByPosition', () => {
  it('marks only stages before current as completed', () => {
    expect(isJourneyStageCompletedByPosition(0, 2)).toBe(true)
    expect(isJourneyStageCompletedByPosition(1, 2)).toBe(true)
    expect(isJourneyStageCompletedByPosition(2, 2)).toBe(false)
    expect(isJourneyStageCompletedByPosition(3, 2)).toBe(false)
  })

  it('marks nothing completed when current is unknown', () => {
    expect(isJourneyStageCompletedByPosition(0, -1)).toBe(false)
    expect(isJourneyStageCompletedByPosition(5, -1)).toBe(false)
  })
})

describe('resolveFunnelStageLabel', () => {
  const t = (key: string, opts?: { defaultValue?: string }) => opts?.defaultValue || key

  it('prefers labels_i18n for UI locale', () => {
    expect(
      resolveFunnelStageLabel(
        { code: 'new', label: 'Nowy', labels_i18n: { pl: 'Nowy', ru: 'Новый', en: 'New' } },
        'ru',
        t,
      ),
    ).toBe('Новый')
  })

  it('falls back to primary label when locale missing', () => {
    expect(
      resolveFunnelStageLabel(
        { code: 'new', label: 'Nowy', labels_i18n: { pl: 'Nowy' } },
        'en',
        t,
      ),
    ).toBe('Nowy')
  })

  it('falls back to system i18n when no funnel labels', () => {
    const out = resolveFunnelStageLabel({ code: 'contacted', label: '' }, 'en', t)
    expect(out.length).toBeGreaterThan(0)
  })
})
