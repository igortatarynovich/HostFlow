/** Client-side pipeline / headcount KPIs for vacancy Workspace. */

const SUCCESS_TOKENS = [
  'employed',
  'hired',
  'filled',
  'probation',
  'трудоустроен',
  'zatrudniony',
] as const

const REJECT_TOKENS = [
  'rejected',
  'declined',
  'refused',
  'withdrawn',
  'отклон',
  'отказ',
  'odrzucon',
] as const

function codeMatches(code: string, tokens: readonly string[]): boolean {
  const c = code.trim().toLowerCase()
  if (!c) return false
  return tokens.some((t) => c === t || c.includes(t))
}

export type StageCount = { code: string; count: number }
/** Alias used by StageMetricCards. */
export type StageMetric = StageCount

export type PipelineMetrics = {
  total: number
  hired: number
  rejected: number
  inProcess: number
  plan: number | null
  remaining: number | null
  completionPct: number | null
  hireRatePct: number | null
  stages: StageCount[]
}

export function computePipelineMetrics(
  pipeCounts: Record<string, number>,
  headcountTarget?: number | null,
): PipelineMetrics {
  const stages: StageCount[] = Object.entries(pipeCounts || {})
    .map(([code, count]) => ({ code, count: Number(count) || 0 }))
    .sort((a, b) => b.count - a.count)

  let hired = 0
  let rejected = 0
  let total = 0
  for (const s of stages) {
    total += s.count
    if (codeMatches(s.code, SUCCESS_TOKENS)) hired += s.count
    else if (codeMatches(s.code, REJECT_TOKENS)) rejected += s.count
  }

  const inProcess = Math.max(0, total - hired - rejected)
  const plan =
    headcountTarget != null && Number(headcountTarget) > 0
      ? Math.floor(Number(headcountTarget))
      : null
  const remaining = plan != null ? Math.max(0, plan - hired) : null
  const completionPct =
    plan != null && plan > 0 ? Math.round((hired / plan) * 1000) / 10 : null
  const hireRatePct = total > 0 ? Math.round((hired / total) * 1000) / 10 : null

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

export function isDocsWaitStage(code: string): boolean {
  const c = code.toLowerCase()
  return (
    c.includes('docs') ||
    c.includes('document') ||
    c.includes('dokument') ||
    c.includes('ожидаем')
  )
}

export function isPermitStage(code: string): boolean {
  const c = code.toLowerCase()
  return c.includes('permit') || c.includes('разрешен') || c.includes('zezwolen')
}
