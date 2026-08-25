import { useCallback, useState } from 'react'
import { api } from '../api/client'
import type { Candidate } from '../api/types'
import { buildRequirementFieldPatch } from '../utils/requirementFieldPatch'

export function usePatchRequirementField(candidateId: string | null | undefined) {
  const [savingCode, setSavingCode] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const saveField = useCallback(
    async (
      qualifiedCode: string,
      value: string,
      candidate: Candidate,
    ): Promise<Candidate | null> => {
      const id = String(candidateId || candidate.id || '').trim()
      if (!id) return null

      setSavingCode(qualifiedCode)
      setError(null)
      try {
        const patch = buildRequirementFieldPatch(qualifiedCode, value, candidate)
        const { data } = await api.patch<Candidate>(`/candidates/${id}`, patch)
        return data
      } catch (err: unknown) {
        const ex = err as { response?: { data?: { detail?: string } }; message?: string }
        setError(ex?.response?.data?.detail || ex?.message || 'Failed to save field')
        return null
      } finally {
        setSavingCode(null)
      }
    },
    [candidateId],
  )

  return { saveField, savingCode, error, clearError: () => setError(null) }
}
