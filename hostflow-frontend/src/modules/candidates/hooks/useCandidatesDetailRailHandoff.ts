import { useEffect, useState } from 'react'
import { getHandoffStatus, type HandoffStatusResponse } from '../../../api/handoffs'

/** Handoff readiness for Detail Rail — loaded when a row is selected. */
export function useCandidatesDetailRailHandoff(selectedCandidateId: string | null) {
  const [handoffStatus, setHandoffStatus] = useState<HandoffStatusResponse | null>(null)
  const [handoffLoading, setHandoffLoading] = useState(false)

  useEffect(() => {
    if (!selectedCandidateId) {
      setHandoffStatus(null)
      setHandoffLoading(false)
      return
    }
    let cancelled = false
    setHandoffLoading(true)
    void getHandoffStatus(selectedCandidateId)
      .then((status) => {
        if (!cancelled) setHandoffStatus(status)
      })
      .catch(() => {
        if (!cancelled) setHandoffStatus(null)
      })
      .finally(() => {
        if (!cancelled) setHandoffLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [selectedCandidateId])

  return { handoffStatus, handoffLoading }
}
