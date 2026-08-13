/** ADR-046 analytics color spaces. Semantic UI status ≠ categorical series ≠ intensity. */

export type UiSemanticTone = 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'brand'

export type DataCategoricalToken =
  | 'data.01'
  | 'data.02'
  | 'data.03'
  | 'data.04'
  | 'data.05'
  | 'data.06'
  | 'data.07'
  | 'data.08'
  | 'data.09'
  | 'data.10'
  | 'data.11'
  | 'data.12'

export const UI_SEMANTIC_FILL: Record<UiSemanticTone, string> = {
  success: '#059669',
  warning: '#D97706',
  danger: '#E11D48',
  info: '#2563EB',
  neutral: '#64748B',
  brand: '#0F766E',
}

/** Independent categories with no status meaning. Max 12; remainder → Other. */
export const DATA_CATEGORICAL_FILL: Record<DataCategoricalToken, string> = {
  'data.01': '#2563EB',
  'data.02': '#7C3AED',
  'data.03': '#0D9488',
  'data.04': '#C026D3',
  'data.05': '#A16207',
  'data.06': '#EA580C',
  'data.07': '#4F46E5',
  'data.08': '#0891B2',
  'data.09': '#4D7C0F',
  'data.10': '#DB2777',
  'data.11': '#57534E',
  'data.12': '#1E3A8A',
}

export const DATA_CATEGORICAL_ORDER: DataCategoricalToken[] = [
  'data.01',
  'data.02',
  'data.03',
  'data.04',
  'data.05',
  'data.06',
  'data.07',
  'data.08',
  'data.09',
  'data.10',
  'data.11',
  'data.12',
]

/** Weak → strong intensity (volume / density). */
export const DATA_SEQUENTIAL_FILL = ['#E2E8F0', '#94A3B8', '#64748B', '#334155', '#0F172A'] as const

/** Negative ← neutral → positive. */
export const DATA_DIVERGING_FILL = {
  negative: '#E11D48',
  negativeMuted: '#FECDD3',
  neutral: '#CBD5E1',
  positiveMuted: '#A7F3D0',
  positive: '#059669',
} as const

export const CHART_CHROME = {
  grid: '#E2E8F0',
  tick: '#64748B',
  axis: '#475569',
  track: '#F1F5F9',
} as const

export const OTHER_CATEGORY_INDEX = 11

export type SeriesFillRequest =
  | { space: 'semantic'; tone: UiSemanticTone }
  | { space: 'categorical'; index: number }
  | { space: 'sequential'; t: number }
  | { space: 'diverging'; t: number }

function clamp01(value: number): number {
  if (!Number.isFinite(value)) return 0
  return Math.min(1, Math.max(0, value))
}

function pickRamp(ramp: readonly string[], t: number): string {
  const x = clamp01(t)
  if (ramp.length === 1) return ramp[0]
  const scaled = x * (ramp.length - 1)
  const i = Math.min(ramp.length - 1, Math.round(scaled))
  return ramp[i]
}

export function categoricalToken(index: number): DataCategoricalToken {
  const n = DATA_CATEGORICAL_ORDER.length
  if (!Number.isFinite(index) || index < 0) return DATA_CATEGORICAL_ORDER[OTHER_CATEGORY_INDEX]
  if (index >= n) return DATA_CATEGORICAL_ORDER[OTHER_CATEGORY_INDEX]
  return DATA_CATEGORICAL_ORDER[index]
}

export function resolveSeriesFill(request: SeriesFillRequest): string {
  if (request.space === 'semantic') return UI_SEMANTIC_FILL[request.tone]
  if (request.space === 'categorical') return DATA_CATEGORICAL_FILL[categoricalToken(request.index)]
  if (request.space === 'sequential') return pickRamp(DATA_SEQUENTIAL_FILL, request.t)
  const t = clamp01(request.t)
  if (t < 0.45) return t < 0.2 ? DATA_DIVERGING_FILL.negative : DATA_DIVERGING_FILL.negativeMuted
  if (t > 0.55) return t > 0.8 ? DATA_DIVERGING_FILL.positive : DATA_DIVERGING_FILL.positiveMuted
  return DATA_DIVERGING_FILL.neutral
}

export const KPI_TONE_CLASSES: Record<
  UiSemanticTone,
  { wrap: string; value: string; bar: string }
> = {
  success: {
    wrap: 'border-emerald-200 bg-emerald-50/80',
    value: 'text-emerald-900',
    bar: 'bg-emerald-600',
  },
  warning: {
    wrap: 'border-amber-200 bg-amber-50/80',
    value: 'text-amber-900',
    bar: 'bg-amber-500',
  },
  danger: {
    wrap: 'border-rose-200 bg-rose-50/80',
    value: 'text-rose-800',
    bar: 'bg-rose-500',
  },
  info: {
    wrap: 'border-blue-200 bg-blue-50/80',
    value: 'text-blue-900',
    bar: 'bg-blue-600',
  },
  neutral: {
    wrap: 'border-slate-200 bg-slate-50/90',
    value: 'text-slate-900',
    bar: 'bg-slate-400',
  },
  brand: {
    wrap: 'border-brand-200 bg-brand-50/80',
    value: 'text-brand-900',
    bar: 'bg-brand-600',
  },
}
