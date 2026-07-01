import { useEffect, useRef } from 'react'

type SeoPageType = 'landing' | 'feature' | 'use_case' | 'comparison'

type SeoTrackingOptions = {
  pageType: SeoPageType
  pageKey: string
}

type SeoEventPayload = Record<string, string | number | boolean | null | undefined>

function pushDataLayer(event: string, payload: SeoEventPayload) {
  if (typeof window === 'undefined') return
  const target = window as typeof window & { dataLayer?: Array<Record<string, unknown>> }
  const item: Record<string, unknown> = {
    event,
    ...payload,
    source: 'seo_content',
    ts: Date.now(),
  }
  if (Array.isArray(target.dataLayer)) {
    target.dataLayer.push(item)
  } else {
    target.dataLayer = [item]
  }
}

export function useSeoTracking({ pageType, pageKey }: SeoTrackingOptions) {
  const milestonesRef = useRef<Set<number>>(new Set())

  useEffect(() => {
    milestonesRef.current.clear()
    const milestones = [25, 50, 75, 100]

    const onScroll = () => {
      const root = document.documentElement
      const scrollTop = root.scrollTop || document.body.scrollTop
      const max = Math.max(1, root.scrollHeight - root.clientHeight)
      const progress = Math.min(100, Math.round((scrollTop / max) * 100))
      for (const milestone of milestones) {
        if (progress >= milestone && !milestonesRef.current.has(milestone)) {
          milestonesRef.current.add(milestone)
          pushDataLayer('seo_scroll_depth', {
            page_type: pageType,
            page_key: pageKey,
            depth: milestone,
          })
        }
      }
    }

    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [pageKey, pageType])

  const trackCta = (ctaId: string, targetHref: string) => {
    pushDataLayer('seo_cta_click', {
      page_type: pageType,
      page_key: pageKey,
      cta_id: ctaId,
      target_href: targetHref,
    })
  }

  return { trackCta }
}
