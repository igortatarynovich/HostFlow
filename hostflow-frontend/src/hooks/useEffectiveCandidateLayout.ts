import { useEffect, useState } from 'react'

import {
  DEFAULT_CANDIDATE_LAYOUT_CODE,
  getEffectiveCardLayout,
  type EffectiveCardLayout,
} from '../api/fieldRegistry'

export interface UseEffectiveCandidateLayoutOptions {
  enabled?: boolean
  candidateId?: string | null
  candidateProfileId?: string | null
}

export function useEffectiveCandidateLayout(options: UseEffectiveCandidateLayoutOptions = {}) {
  const { enabled = true, candidateId = null, candidateProfileId = null } = options
  const [effectiveLayout, setEffectiveLayout] = useState<EffectiveCardLayout | null>(null)
  const [layoutLoading, setLayoutLoading] = useState(false)
  const [layoutFromApi, setLayoutFromApi] = useState(false)

  useEffect(() => {
    if (!enabled) {
      setEffectiveLayout(null)
      setLayoutFromApi(false)
      return
    }

    let cancelled = false
    setLayoutLoading(true)

    getEffectiveCardLayout({
      entity_type: 'candidate',
      layout_code: DEFAULT_CANDIDATE_LAYOUT_CODE,
      module: 'recruitment',
      candidate_id: candidateId || undefined,
      candidate_profile_id: candidateProfileId || undefined,
    })
      .then((layout) => {
        if (cancelled) return
        setEffectiveLayout(layout)
        setLayoutFromApi(layout.resolution_source !== 'not_found')
      })
      .catch(() => {
        if (cancelled) return
        setEffectiveLayout(null)
        setLayoutFromApi(false)
      })
      .finally(() => {
        if (!cancelled) setLayoutLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [enabled, candidateId, candidateProfileId])

  return {
    effectiveLayout,
    layoutLoading,
    layoutFromApi,
  }
}
