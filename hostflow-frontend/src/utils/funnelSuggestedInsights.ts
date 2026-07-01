import type { LeadConversionFunnelResponse } from '../api/leadConversionFunnel'

/** Mirror backend `nba_conversion_funnel_insight_groups` thresholds (`service.py`). */
export const FUNNEL_NBA_MIN_TOTAL_WIN = 5
export const FUNNEL_NBA_MIN_AT_OR_BEYOND = 6
export const FUNNEL_NBA_WEAK_SHARE_MAX = 0.49
export const FUNNEL_NBA_SLOW_DWELL_DAYS = 5.0
export const FUNNEL_NBA_MIN_DWELL_SAMPLE = 3

export type FunnelSuggestedWeak = { conversionRoot: string; progressedPct: number; drop: number }
export type FunnelSuggestedSlow = { conversionRoot: string; dwellDays: number; bucketCount: number }

export function computeFunnelSuggestedInsights(
  data: LeadConversionFunnelResponse | null,
): { weak?: FunnelSuggestedWeak; slow?: FunnelSuggestedSlow } {
  if (!data?.stages?.length) return {}
  const totalWin = data.stages.reduce((acc, s) => acc + s.count, 0)
  if (totalWin < FUNNEL_NBA_MIN_TOTAL_WIN) return {}

  let worstIdx: number | null = null
  let worstShare: number | null = null
  for (let i = 0; i < data.edges.length; i++) {
    const edge = data.edges[i]
    if (edge.progressed_share == null) continue
    const atHere = data.stages[i]?.at_or_beyond ?? 0
    if (atHere < FUNNEL_NBA_MIN_AT_OR_BEYOND) continue
    const sh = edge.progressed_share
    if (worstShare == null || sh < worstShare) {
      worstShare = sh
      worstIdx = i
    }
  }

  let weak: FunnelSuggestedWeak | undefined
  if (
    worstIdx != null &&
    worstShare != null &&
    worstShare <= FUNNEL_NBA_WEAK_SHARE_MAX &&
    worstIdx + 1 < data.stages.length
  ) {
    const fromRoot = data.stages[worstIdx].stage
    const atTop = data.stages[worstIdx].at_or_beyond
    const atNext = data.stages[worstIdx + 1].at_or_beyond
    const drop = Math.max(0, atTop - atNext)
    if (drop > 0) {
      weak = {
        conversionRoot: fromRoot,
        progressedPct: Math.max(0, Math.min(100, Math.round(worstShare * 100))),
        drop,
      }
    }
  }

  let slow: FunnelSuggestedSlow | undefined
  let slowDays = 0
  let slowStage: string | null = null
  let slowBucketCount = 0
  for (const s of data.stages) {
    const n = s.dwell_sample_size ?? 0
    if (n < FUNNEL_NBA_MIN_DWELL_SAMPLE) continue
    if (s.dwell_avg_days == null) continue
    const d = s.dwell_avg_days
    if (d >= FUNNEL_NBA_SLOW_DWELL_DAYS && d > slowDays) {
      slowDays = d
      slowStage = s.stage
      slowBucketCount = s.count
    }
  }
  if (slowStage && slowBucketCount > 0) {
    slow = { conversionRoot: slowStage, dwellDays: slowDays, bucketCount: slowBucketCount }
  }

  return { weak, slow }
}
