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

/**
 * Count by **candidate stage code**, not kanban column key.
 *
 * `/vacancies/:id/pipeline` buckets cards into aggregated columns
 * (`client_process`, `internal_hr`, …). Vacancy Progress must use each
 * item's `stage` (e.g. `employed` / `hired`) — otherwise success rows
 * collapse into column keys that never match SUCCESS_TOKENS → 0%.
 */
export function stageCountsFromPipelineColumns(
  columns: Record<string, unknown> | null | undefined,
): Record<string, number> {
  const res: Record<string, number> = {}
  for (const [columnKey, val] of Object.entries(columns || {})) {
    const arr = Array.isArray(val)
      ? val
      : Array.isArray((val as { items?: unknown })?.items)
        ? ((val as { items: unknown[] }).items)
        : []
    for (const item of arr) {
      const stage =
        item && typeof item === 'object'
          ? String((item as { stage?: unknown }).stage ?? '').trim()
          : ''
      const code = stage || columnKey
      res[code] = (res[code] || 0) + 1
    }
  }
  return res
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
