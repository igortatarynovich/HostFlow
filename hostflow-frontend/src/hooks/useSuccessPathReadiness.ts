import { useCallback, useEffect, useMemo, useState } from 'react'

import { getOnboardingStatus, type OnboardingStatus } from '../api/client'
import { getSetupReadiness, type SetupReadinessSnapshot } from '../api/onboarding'
import { getTeamOverview } from '../api/tenants'
import {
  buildSuccessPathItems,
  isSuccessPathComplete,
  normalizeSuccessPathBusinessType,
  pickSuccessPathNext,
  type SuccessPathItemId,
} from '../utils/successPathReadiness'

export type {
  SuccessPathItem,
  SuccessPathItemId,
  SuccessPathNextAction,
} from '../utils/successPathReadiness'

const DEFER_META_KEY = 'hf-success-path-defer-meta-v1'

function readMetaDeferred(): boolean {
  try {
    return window.sessionStorage.getItem(DEFER_META_KEY) === '1'
  } catch {
    return false
  }
}

export function deferSuccessPathMeta(): void {
  try {
    window.sessionStorage.setItem(DEFER_META_KEY, '1')
  } catch {
    // ignore
  }
}

function gatePass(snapshot: SetupReadinessSnapshot | null, gateId: string): boolean {
  const gate = snapshot?.gates.find((g) => g.id === gateId)
  if (!gate) return false
  return !gate.applicable || gate.status === 'pass'
}

export type UseSuccessPathReadinessOptions = {
  enabled?: boolean
}

export function useSuccessPathReadiness(options: UseSuccessPathReadinessOptions = {}) {
  const { enabled = true } = options
  const [status, setStatus] = useState<OnboardingStatus | null>(null)
  const [setup, setSetup] = useState<SetupReadinessSnapshot | null>(null)
  const [teammatesInvited, setTeammatesInvited] = useState(false)
  const [metaDeferred, setMetaDeferred] = useState(false)
  const [loading, setLoading] = useState(enabled)
  const [error, setError] = useState<unknown>(null)

  const refresh = useCallback(async () => {
    if (!enabled) {
      setStatus(null)
      setSetup(null)
      setTeammatesInvited(false)
      setLoading(false)
      setError(null)
      return
    }
    setLoading(true)
    setError(null)
    setMetaDeferred(readMetaDeferred())
    try {
      const [onboarding, readiness] = await Promise.all([getOnboardingStatus(), getSetupReadiness()])
      setStatus(onboarding)
      setSetup(readiness)
      try {
        const team = await getTeamOverview()
        setTeammatesInvited((team.members?.length ?? 0) > 1)
      } catch {
        setTeammatesInvited(false)
      }
    } catch (err) {
      setError(err)
      setStatus(null)
      setSetup(null)
    } finally {
      setLoading(false)
    }
  }, [enabled])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const businessType = normalizeSuccessPathBusinessType(status?.business_type)
  const metaConnected = gatePass(setup, 'G6')
  const metaConnectedOrDeferred = metaConnected || metaDeferred

  const items = useMemo(
    () =>
      buildSuccessPathItems({
        businessType,
        steps: status?.steps,
        metaConnectedOrDeferred,
        metaDeferredOnly: metaDeferred && !metaConnected,
        teammatesInvited,
      }),
    [businessType, status?.steps, metaConnectedOrDeferred, metaDeferred, metaConnected, teammatesInvited],
  )
  const nextAction = useMemo(() => pickSuccessPathNext(items, businessType), [items, businessType])
  const doneCount = items.filter((i) => i.done).length
  const pathComplete = isSuccessPathComplete(items)

  const deferMeta = useCallback(() => {
    deferSuccessPathMeta()
    setMetaDeferred(true)
  }, [])

  return {
    status,
    setup,
    businessType,
    items,
    nextAction,
    doneCount,
    totalCount: items.length,
    pathComplete,
    loading,
    error,
    refresh,
    deferMeta,
    itemDone: (id: SuccessPathItemId) => Boolean(items.find((i) => i.id === id)?.done),
  }
}
