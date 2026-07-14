import { useCallback, useEffect, useState } from 'react'
import { getCandidateTransferReadiness, type TransferReadinessReport } from '../../api/candidates'

export function useTransferReadiness(candidateId: string | null | undefined, refreshTrigger = 0) {
  const [report, setReport] = useState<TransferReadinessReport | null>(null)
  const [loading, setLoading] = useState(false)

  const reload = useCallback(async () => {
    const id = String(candidateId || '').trim()
    if (!id) {
      setReport(null)
      return
    }
    setLoading(true)
    try {
      const data = await getCandidateTransferReadiness(id)
      setReport(data)
    } catch {
      setReport(null)
    } finally {
      setLoading(false)
    }
  }, [candidateId])

  useEffect(() => {
    void reload()
  }, [reload, refreshTrigger])

  return { report, loading, reload }
}
