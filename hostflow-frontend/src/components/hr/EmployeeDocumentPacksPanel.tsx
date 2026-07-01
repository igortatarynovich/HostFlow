import { useEffect, useState } from 'react'
import { getSummary } from '../../api/documents/summary'
import type { DocumentPackProjection } from '../../api/types'
import { DocumentPackCards } from './DocumentPackCards'

type Props = {
  candidateId: string
  ownerContext?: Record<string, unknown> | null
  compact?: boolean
}

export function EmployeeDocumentPacksPanel({ candidateId, ownerContext, compact = false }: Props) {
  const [packs, setPacks] = useState<DocumentPackProjection[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      setError(null)
      try {
        const response = await getSummary(candidateId, {
          context: ownerContext || undefined,
          fillMissing: false,
        })
        if (!cancelled) {
          setPacks(response.summary.packs || [])
        }
      } catch {
        if (!cancelled) {
          setPacks(null)
          setError('Could not load document packs')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [candidateId, ownerContext])

  return <DocumentPackCards packs={packs} loading={loading} error={error} compact={compact} />
}
