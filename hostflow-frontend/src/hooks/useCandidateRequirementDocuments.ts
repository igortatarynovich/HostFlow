import { useCallback, useEffect, useState } from 'react'
import { listCandidateDocuments } from '../api/documents'
import type { Document } from '../../api/types'

export function useCandidateRequirementDocuments(
  candidateId: string | null | undefined,
  refreshTrigger = 0,
) {
  const [candidateDocuments, setCandidateDocuments] = useState<Document[]>([])
  const [docsLoading, setDocsLoading] = useState(false)

  const reload = useCallback(async () => {
    const id = String(candidateId || '').trim()
    if (!id) {
      setCandidateDocuments([])
      return
    }
    setDocsLoading(true)
    try {
      const docs = await listCandidateDocuments(id, { includeLastCheck: true })
      setCandidateDocuments(docs)
    } catch {
      setCandidateDocuments([])
    } finally {
      setDocsLoading(false)
    }
  }, [candidateId])

  useEffect(() => {
    void reload()
  }, [reload, refreshTrigger])

  return { candidateDocuments, docsLoading, reload }
}
