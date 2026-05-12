import { useCallback, useEffect, useMemo, useState } from 'react'
import { getSummary } from '../api/documents'
import { useCurrentTenantId } from '../contexts/CurrentTenant'

export type CandidateDocBlockers = {
  missing: string[]
  problematic: string[]
  inProgress: string[]
}

/**
 * Lightweight document blocker snapshot for embedded views (e.g. HR employee card).
 * Mirrors CandidateDocsRailPanel → getSummary + required.* fields.
 */
export function useCandidateDocBlockers(
  candidateId: string | null | undefined,
  citizenship: string,
  refreshTrigger: number,
): { blockers: CandidateDocBlockers; loading: boolean; refresh: () => Promise<void> } {
  const workspaceTenantId = useCurrentTenantId()
  const ownerContext = useMemo(() => ({ citizenship: String(citizenship || '') }), [citizenship])
  const [loading, setLoading] = useState(false)
  const [blockers, setBlockers] = useState<CandidateDocBlockers>({
    missing: [],
    problematic: [],
    inProgress: [],
  })

  const load = useCallback(async () => {
    if (!candidateId) {
      setBlockers({ missing: [], problematic: [], inProgress: [] })
      return
    }
    setLoading(true)
    try {
      const res = await getSummary(candidateId, {
        context: ownerContext,
        fillMissing: true,
        ...(workspaceTenantId != null && String(workspaceTenantId).trim()
          ? { scopeTenantId: String(workspaceTenantId).trim() }
          : {}),
      })
      const s = (res as { summary?: { required?: Record<string, unknown> } })?.summary
      const req = s?.required as
        | {
            missing?: string[]
            problematic?: string[]
            in_progress_types?: string[]
          }
        | undefined
      setBlockers({
        missing: Array.isArray(req?.missing) ? req.missing.map((x) => String(x)) : [],
        problematic: Array.isArray(req?.problematic) ? req.problematic.map((x) => String(x)) : [],
        inProgress: Array.isArray(req?.in_progress_types) ? req.in_progress_types.map((x) => String(x)) : [],
      })
    } catch {
      setBlockers({ missing: [], problematic: [], inProgress: [] })
    } finally {
      setLoading(false)
    }
  }, [candidateId, ownerContext, workspaceTenantId])

  useEffect(() => {
    void load()
  }, [load, refreshTrigger])

  return { blockers, loading, refresh: load }
}
