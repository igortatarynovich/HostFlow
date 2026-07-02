import { useCallback, useEffect, useState } from 'react'
import {
  approveRequirementEvidence,
  getCandidateRequirementsChecklist,
  linkRequirementEvidenceDocument,
  rejectRequirementEvidence,
  replaceRequirementEvidence,
  selectRequirementEvidence,
  type RequirementsChecklistResponse,
} from '../api/candidateRequirements'

export function useCandidateRequirementsChecklist(
  candidateId: string | null | undefined,
  refreshTrigger = 0,
  onChanged?: () => void,
) {
  const [checklist, setChecklist] = useState<RequirementsChecklistResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [actionBusy, setActionBusy] = useState(false)

  const reload = useCallback(async () => {
    const id = String(candidateId || '').trim()
    if (!id) {
      setChecklist(null)
      return null
    }
    setLoading(true)
    setError(null)
    try {
      const data = await getCandidateRequirementsChecklist(id)
      setChecklist(data)
      return data
    } catch (err: any) {
      setChecklist(null)
      setError(err?.response?.data?.detail || err?.message || 'Failed to load requirements checklist')
      return null
    } finally {
      setLoading(false)
    }
  }, [candidateId])

  useEffect(() => {
    void reload()
  }, [reload, refreshTrigger])

  const runAction = useCallback(
    async <T,>(fn: () => Promise<T>): Promise<T | null> => {
      setActionBusy(true)
      setError(null)
      try {
        const result = await fn()
        await reload()
        onChanged?.()
        return result
      } catch (err: any) {
        const detail = err?.response?.data?.detail
        setError(typeof detail === 'string' ? detail : err?.message || 'Action failed')
        return null
      } finally {
        setActionBusy(false)
      }
    },
    [reload, onChanged],
  )

  const selectEvidence = useCallback(
    (requirementCode: string, evidenceVariantCode: string) => {
      const id = String(candidateId || '').trim()
      if (!id) return Promise.resolve(null)
      return runAction(() =>
        selectRequirementEvidence(id, requirementCode, { evidence_variant_code: evidenceVariantCode }),
      )
    },
    [candidateId, runAction],
  )

  const linkDocument = useCallback(
    (evidenceId: string, documentId: string, role?: string | null) => {
      const id = String(candidateId || '').trim()
      if (!id) return Promise.resolve(null)
      return runAction(() =>
        linkRequirementEvidenceDocument(id, evidenceId, { document_id: documentId, role }),
      )
    },
    [candidateId, runAction],
  )

  const approveEvidence = useCallback(
    (evidenceId: string) => {
      const id = String(candidateId || '').trim()
      if (!id) return Promise.resolve(null)
      return runAction(() => approveRequirementEvidence(id, evidenceId))
    },
    [candidateId, runAction],
  )

  const rejectEvidence = useCallback(
    (evidenceId: string, reason?: string | null) => {
      const id = String(candidateId || '').trim()
      if (!id) return Promise.resolve(null)
      return runAction(() => rejectRequirementEvidence(id, evidenceId, { reason }))
    },
    [candidateId, runAction],
  )

  const replaceEvidence = useCallback(
    (requirementCode: string, evidenceVariantCode: string) => {
      const id = String(candidateId || '').trim()
      if (!id) return Promise.resolve(null)
      return runAction(() =>
        replaceRequirementEvidence(id, requirementCode, { evidence_variant_code: evidenceVariantCode }),
      )
    },
    [candidateId, runAction],
  )

  return {
    checklist,
    loading,
    error,
    actionBusy,
    reload,
    selectEvidence,
    linkDocument,
    approveEvidence,
    rejectEvidence,
    replaceEvidence,
  }
}
