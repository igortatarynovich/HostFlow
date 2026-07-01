import { useEffect, useState } from 'react'

import {
  DEFAULT_VACANCY_LAYOUT_CODE,
  getEffectiveCardLayout,
  type EffectiveCardLayout,
} from '../api/fieldRegistry'

export function useEffectiveVacancyLayout(enabled = true, vacancyId?: string | null) {
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
      entity_type: 'vacancy',
      layout_code: DEFAULT_VACANCY_LAYOUT_CODE,
      module: 'recruitment',
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
  }, [enabled, vacancyId])

  return {
    effectiveLayout,
    layoutLoading,
    layoutFromApi,
  }
}
