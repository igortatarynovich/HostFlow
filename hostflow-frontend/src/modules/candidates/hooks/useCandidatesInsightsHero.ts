import { useCallback, useEffect, useMemo, useState } from 'react'
import { isLikelyNewStage, normalizeStageKey } from '../candidateUtils'
import { QUICK_DOC_STATUS_SETS } from '../constants'

export type InsightCardKey = 'total' | 'new' | 'docs_ready' | 'docs_attention'

type InsightSource = {
  total: number
  newCount: number
  docsReady: number
  docsAttention: number
}

type UseCandidatesInsightsHeroArgs = {
  t: (key: string, options?: any) => string
  insightSource: InsightSource
  enrichedItems: Array<{ stage?: string | null }>
  handleResetFilters: () => void
  setStageFilter: (v: string[]) => void
  setDocsStatusFilter: (v: string[]) => void
}

export function useCandidatesInsightsHero({
  t,
  insightSource,
  enrichedItems,
  handleResetFilters,
  setStageFilter,
  setDocsStatusFilter,
}: UseCandidatesInsightsHeroArgs) {
  const HERO_STORAGE_KEY = 'hf:candidates:heroExpanded'

  const [heroExpanded, setHeroExpanded] = useState(() => {
    try {
      return window.localStorage.getItem(HERO_STORAGE_KEY) === '1'
    } catch {
      return false
    }
  })

  useEffect(() => {
    try {
      window.localStorage.setItem(HERO_STORAGE_KEY, heroExpanded ? '1' : '0')
    } catch {
      /* ignore */
    }
  }, [heroExpanded])

  const handleInsightDrillDown = useCallback(
    (key: InsightCardKey) => {
      switch (key) {
        case 'total':
          handleResetFilters()
          break
        case 'new': {
          const newStages = Array.from(
            new Set(
              enrichedItems
                .map((item) => String(item.stage || '').trim())
                .filter((stage) => stage && isLikelyNewStage(normalizeStageKey(stage))),
            ),
          )
          handleResetFilters()
          setStageFilter(newStages.length > 0 ? newStages : ['new'])
          break
        }
        case 'docs_ready':
          handleResetFilters()
          setDocsStatusFilter(['ready'])
          break
        case 'docs_attention':
          handleResetFilters()
          setDocsStatusFilter([...QUICK_DOC_STATUS_SETS.attention])
          break
        default:
          break
      }
    },
    [enrichedItems, handleResetFilters, setDocsStatusFilter, setStageFilter],
  )

  const insightCards = useMemo(
    () => [
      {
        key: 'total' as const,
        label: t('app.candidates.insights.total'),
        value: insightSource.total,
        hint: t('app.candidates.insights.total_hint', { values: { count: insightSource.total } }),
      },
      {
        key: 'new' as const,
        label: t('app.candidates.insights.new'),
        value: insightSource.newCount,
        hint: t('app.candidates.insights.new_hint', { values: { count: insightSource.newCount } }),
      },
      {
        key: 'docs_ready' as const,
        label: t('app.candidates.insights.docs_ready'),
        value: insightSource.docsReady,
        hint: t('app.candidates.insights.docs_ready_hint', { values: { count: insightSource.docsReady } }),
      },
      {
        key: 'docs_attention' as const,
        label: t('app.candidates.insights.docs_attention'),
        value: insightSource.docsAttention,
        hint: t('app.candidates.insights.docs_attention_hint', { values: { count: insightSource.docsAttention } }),
      },
    ],
    [insightSource.docsAttention, insightSource.docsReady, insightSource.newCount, insightSource.total, t],
  )

  return {
    heroExpanded,
    setHeroExpanded,
    insightCards,
    handleInsightDrillDown,
  }
}

