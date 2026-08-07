/**
 * Pipeline metrics computation for vacancy workspace.
 * Provides stage categorization and KPI calculations.
 */

/** Stage codes that indicate successful hiring (case-insensitive match). */
export const SUCCESS_CODES = [
  'employed',
  'hired',
  'filled',
  'probation',
  'started',
  'onboarded',
  'accepted',
  'completed',
  'employment_pending',
] as const

/** Stage codes that indicate rejection/exit from pipeline (case-insensitive match). */
export const REJECT_CODES = [
  'rejected',
  'declined',
  'refused',
  'withdrawn',
  'cancelled',
  'failed',
  'disqualified',
  'dropped',
  'not_interested',
  'lost',
  'archived',
] as const

export type StageMetric = {
  code: string
  count: number
  category: 'success' | 'rejected' | 'in_process'
}

export type PipelineMetrics = {
  total: number
  hired: number
  rejected: number
  inProcess: number
  plan: number | null
  remaining: number | null
  completionPct: number | null
  hireRatePct: number | null
  stages: StageMetric[]
}

function codeMatchesAny(code: string, patterns: readonly string[]): boolean {
  const lower = code.toLowerCase().replace(/[_-]/g, '')
  return patterns.some((pattern) => {
    const p = pattern.toLowerCase().replace(/[_-]/g, '')
    return lower.includes(p) || p.includes(lower)
  })
}

function categorizeStage(code: string): 'success' | 'rejected' | 'in_process' {
  if (codeMatchesAny(code, SUCCESS_CODES)) return 'success'
  if (codeMatchesAny(code, REJECT_CODES)) return 'rejected'
  return 'in_process'
}

/**
 * Compute pipeline metrics from stage counts.
 * @param pipeCounts Record<stageCode, count>
 * @param headcountTarget Optional target headcount for the vacancy
 */
export function computePipelineMetrics(
  pipeCounts: Record<string, number>,
  headcountTarget?: number | null,
): PipelineMetrics {
  const stages: StageMetric[] = []
  let total = 0
  let hired = 0
  let rejected = 0
  let inProcess = 0

  for (const [code, count] of Object.entries(pipeCounts)) {
    const n = Math.max(0, Number(count) || 0)
    total += n

    const category = categorizeStage(code)
    stages.push({ code, count: n, category })

    if (category === 'success') {
      hired += n
    } else if (category === 'rejected') {
      rejected += n
    } else {
      inProcess += n
    }
  }

  const plan = headcountTarget != null && headcountTarget > 0 ? headcountTarget : null
  const remaining = plan != null ? Math.max(0, plan - hired) : null
  const completionPct = plan != null && plan > 0 ? Math.round((hired / plan) * 100) : null
  const hireRatePct =
    total > 0 ? Math.round((hired / total) * 100) : null

  return {
    total,
    hired,
    rejected,
    inProcess,
    plan,
    remaining,
    completionPct,
    hireRatePct,
    stages,
  }
}

/**
 * Get sorted stages by count descending (for bottleneck identification).
 */
export function getTopStages(
  stages: StageMetric[],
  limit = 5,
  excludeCategories?: ('success' | 'rejected')[],
): StageMetric[] {
  let filtered = stages
  if (excludeCategories?.length) {
    filtered = stages.filter((s) => !excludeCategories.includes(s.category))
  }
  return [...filtered].sort((a, b) => b.count - a.count).slice(0, limit)
}

/**
 * Identify the bottleneck stage (largest in-process stage).
 */
export function getBottleneckStage(stages: StageMetric[]): StageMetric | null {
  const inProcessStages = stages.filter((s) => s.category === 'in_process' && s.count > 0)
  if (inProcessStages.length === 0) return null
  return inProcessStages.reduce((a, b) => (b.count > a.count ? b : a))
}
