import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { MetaStages } from '../api/types'

let cache: MetaStages | null = null
let inflight: Promise<MetaStages> | null = null

export function useMetaStages(){
  const [meta, setMeta] = useState<MetaStages | null>(cache)

  useEffect(() => {
    if (cache) return
    if (!inflight) {
      inflight = api.get('/meta/stages').then(({data}) => {
        cache = data
        return data as MetaStages
      }).finally(() => { inflight = null })
    }
    inflight!.then(setMeta).catch(() => {})
  }, [])

  return meta
}

export function labelForStage(code?: string | null, meta?: MetaStages | null){
  if (!code) return ''
  const c = String(code).toLowerCase()
  return meta?.labels?.[c] || c
}