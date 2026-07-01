import { useEffect, useState, useCallback } from 'react'
import { api } from '../api/client'
import type { MetaStages } from '../api/types'

let cache: MetaStages | null = null
let inflight: Promise<MetaStages> | null = null

export function useMetaStages(){
  const [meta, setMeta] = useState<MetaStages | null>(cache)

  const refreshStages = useCallback(() => {
    // Invalidate cache and reload
    cache = null
    if (!inflight) {
      inflight = api.get('/meta/stages').then(({data}) => {
        cache = data
        return data as MetaStages
      }).finally(() => { inflight = null })
    }
    inflight!.then(setMeta).catch(() => {})
  }, [])

  useEffect(() => {
    if (cache) {
      setMeta(cache)
      return
    }
    if (!inflight) {
      inflight = api.get('/meta/stages').then(({data}) => {
        cache = data
        return data as MetaStages
      }).finally(() => { inflight = null })
    }
    inflight!.then(setMeta).catch(() => {})
  }, [])

  // Listen for stage updates to refresh cache
  useEffect(() => {
    const handleStageUpdate = () => {
      refreshStages()
    }
    window.addEventListener('candidate-stage-updated', handleStageUpdate)
    return () => {
      window.removeEventListener('candidate-stage-updated', handleStageUpdate)
    }
  }, [refreshStages])

  return meta
}

// Export refresh function for manual cache invalidation
export function refreshMetaStagesCache() {
  cache = null
  inflight = null
  window.dispatchEvent(new CustomEvent('candidate-stage-updated'))
}