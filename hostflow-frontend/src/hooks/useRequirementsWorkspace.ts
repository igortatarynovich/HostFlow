import { useCallback, useEffect, useState } from 'react'
import {
  getCandidateRequirementsWorkspace,
  type RequirementsWorkspaceResponse,
} from '../api/candidateRequirements'

export function useRequirementsWorkspace(candidateId: string | null | undefined, refreshTrigger = 0) {
  const [workspace, setWorkspace] = useState<RequirementsWorkspaceResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    const id = String(candidateId || '').trim()
    if (!id) {
      setWorkspace(null)
      return null
    }
    setLoading(true)
    setError(null)
    try {
      const data = await getCandidateRequirementsWorkspace(id)
      setWorkspace(data)
      return data
    } catch (err: unknown) {
      setWorkspace(null)
      const ex = err as { response?: { data?: { detail?: string } }; message?: string }
      setError(ex?.response?.data?.detail || ex?.message || 'Failed to load requirements workspace')
      return null
    } finally {
      setLoading(false)
    }
  }, [candidateId])

  useEffect(() => {
    void reload()
  }, [reload, refreshTrigger])

  return {
    workspace,
    loading,
    error,
    reload,
  }
}
