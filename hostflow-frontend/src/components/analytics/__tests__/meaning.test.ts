// @vitest-environment node
import { describe, expect, it } from 'vitest'

import {
  MEANING_CHART,
  chartKindForMeaning,
  fillForStatusKey,
  resolveSeriesFill,
  toneForStatusKey,
  UI_SEMANTIC_FILL,
  DATA_CATEGORICAL_FILL,
} from '../index'

describe('chartKindForMeaning', () => {
  it('binds conversion to funnel and mix to bar — never pie', () => {
    expect(chartKindForMeaning('funnel')).toBe('funnel')
    expect(chartKindForMeaning('composition')).toBe('bar')
    expect(chartKindForMeaning('distribution')).toBe('bar')
    expect(chartKindForMeaning('trend')).toBe('line-area')
    expect(MEANING_CHART.kpi).toBe('kpi-card')
  })
})

describe('resolveSeriesFill', () => {
  it('keeps semantic, categorical, and sequential spaces independent', () => {
    expect(resolveSeriesFill({ space: 'semantic', tone: 'danger' })).toBe(UI_SEMANTIC_FILL.danger)
    expect(resolveSeriesFill({ space: 'categorical', index: 0 })).toBe(DATA_CATEGORICAL_FILL['data.01'])
    expect(resolveSeriesFill({ space: 'categorical', index: 99 })).toBe(DATA_CATEGORICAL_FILL['data.12'])
    expect(resolveSeriesFill({ space: 'sequential', t: 0 })).toBeDefined()
    expect(resolveSeriesFill({ space: 'diverging', t: 1 })).toBe(UI_SEMANTIC_FILL.success)
  })
})

describe('fillForStatusKey', () => {
  it('keeps rejected as danger across modules', () => {
    expect(toneForStatusKey('rejected')).toBe('danger')
    expect(fillForStatusKey('rejected')).toBe(UI_SEMANTIC_FILL.danger)
    expect(fillForStatusKey('lost')).toBe(UI_SEMANTIC_FILL.danger)
    expect(fillForStatusKey('handoff_rejected')).toBe(UI_SEMANTIC_FILL.danger)
  })

  it('does not assign a random categorical hue to a status meaning', () => {
    expect(fillForStatusKey('rejected', 4)).toBe(UI_SEMANTIC_FILL.danger)
    expect(toneForStatusKey('declined')).toBe('warning')
    expect(toneForStatusKey('reached')).toBe('success')
  })
})
