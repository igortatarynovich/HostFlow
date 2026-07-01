import { useCallback, useEffect, useMemo, useState } from 'react'
import { getSummary } from '../api/documents'
import type { FriendlyErrorInfo } from '../utils/friendlyError'
import { getFriendlyErrorInfo } from '../utils/friendlyError'
import {
  buildRuntimeWorkspaceFromSummary,
  type RuntimeWorkspaceSnapshot,
} from '../utils/runtimeWorkspacePresentation'

export function useCandidateRuntimeWorkspace({
  candidateId,
  ownerContext,
  enabled = true,
  embeddedSummary,
}: {
  candidateId: string
  ownerContext?: Record<string, unknown> | null
  enabled?: boolean
  embeddedSummary?: Record<string, unknown> | null
}) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [summary, setSummary] = useState<Record<string, unknown> | null>(embeddedSummary ?? null)

  const load = useCallback(async () => {
    if (!candidateId || !enabled) return
    setLoading(true)
    setError(null)
    try {
      const res = await getSummary(candidateId, { context: ownerContext || null, fillMissing: true })
      const next = ((res as { summary?: Record<string, unknown> })?.summary ?? null) as Record<string, unknown> | null
      setSummary(next)
    } catch (err: unknown) {
      setSummary(null)
      setError(getFriendlyErrorInfo(err, 'Request failed'))
    } finally {
      setLoading(false)
    }
  }, [candidateId, enabled, ownerContext])

  useEffect(() => {
    if (embeddedSummary !== undefined) {
      setSummary(embeddedSummary)
      return
    }
    if (!enabled || !candidateId) return
    void load()
  }, [candidateId, embeddedSummary, enabled, load])

  const workspace = useMemo(
    () => buildRuntimeWorkspaceFromSummary(summary),
    [summary],
  )

  return {
    loading,
    error,
    summary,
    workspace,
    reload: load,
  }
}

export type { RuntimeWorkspaceSnapshot }
