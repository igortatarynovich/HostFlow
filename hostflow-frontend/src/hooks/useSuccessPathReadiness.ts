import { useCallback, useEffect, useMemo, useState } from 'react'

import { getOnboardingStatus, type OnboardingStatus } from '../api/client'
import { getSetupReadiness, type SetupReadinessSnapshot } from '../api/onboarding'
import { getTeamOverview } from '../api/tenants'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { ACTIVATION_PATHS, getFirstVacancySetupPath } from '../app/activationRoutes'

const DEFER_META_KEY = 'hf-success-path-defer-meta-v1'

export type SuccessPathItemId =
  | 'company'
  | 'invite'
  | 'client'
  | 'vacancy'
  | 'campaign'
  | 'meta'
  | 'lead'
  | 'contact'

export type SuccessPathItem = {
  id: SuccessPathItemId
  done: boolean
  optional: boolean
  deferred: boolean
  href: string
}

export type SuccessPathNextAction = {
  id: SuccessPathItemId
  href: string
}

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

function buildItems(
  status: OnboardingStatus | null,
  setup: SetupReadinessSnapshot | null,
  metaDeferred: boolean,
  teammatesInvited: boolean,
): SuccessPathItem[] {
  const steps = status?.steps
  const businessType = status?.business_type ?? 'agency'
  const isEmployer = businessType === 'employer'
  const isServices = businessType === 'services'
  return [
    {
      id: 'company',
      done: Boolean(steps?.company_created),
      optional: false,
      deferred: false,
      href: CRM_APP_PATHS.platformSetup,
    },
    {
      id: 'invite',
      done: teammatesInvited,
      optional: true,
      deferred: false,
      href: CRM_APP_PATHS.settingsUsers,
    },
    {
      id: 'client',
      done:
        isEmployer ||
        Boolean(steps?.first_client_created) ||
        Boolean(steps?.first_vacancy_created),
      optional: isEmployer,
      deferred: false,
      href: CRM_APP_PATHS.setupClient,
    },
    {
      id: 'vacancy',
      done: isServices || Boolean(steps?.first_vacancy_created),
      optional: isServices,
      deferred: false,
      href: getFirstVacancySetupPath(status),
    },
    {
      id: 'campaign',
      done: isServices || Boolean(steps?.first_campaign_created),
      optional: isServices,
      deferred: false,
      href: CRM_APP_PATHS.marketingNew,
    },
    {
      id: 'meta',
      done: gatePass(setup, 'G6') || metaDeferred,
      optional: true,
      deferred: metaDeferred && !gatePass(setup, 'G6'),
      href: CRM_APP_PATHS.settingsIntegrationsMeta,
    },
    {
      id: 'lead',
      done: Boolean(steps?.first_lead_created),
      optional: false,
      deferred: false,
      href: ACTIVATION_PATHS.leads,
    },
    {
      id: 'contact',
      done: Boolean(steps?.next_action_created),
      optional: false,
      deferred: false,
      href: ACTIVATION_PATHS.leads,
    },
  ]
}

/** Primary CTA: company → client → vacancy → campaign → meta → lead → contact. */
const NEXT_ORDER: SuccessPathItemId[] = [
  'company',
  'client',
  'vacancy',
  'campaign',
  'meta',
  'lead',
  'contact',
  'invite',
]

function pickNext(items: SuccessPathItem[]): SuccessPathNextAction | null {
  const byId = new Map(items.map((item) => [item.id, item]))
  for (const id of NEXT_ORDER) {
    const item = byId.get(id)
    if (!item || item.done) continue
    if (item.id === 'invite') {
      const blockers = items.filter((i) => !i.optional && !i.done && i.id !== 'invite')
      if (blockers.length > 0) continue
    }
    return { id: item.id, href: item.href }
  }
  return null
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

  const items = useMemo(
    () => buildItems(status, setup, metaDeferred, teammatesInvited),
    [status, setup, metaDeferred, teammatesInvited],
  )
  const nextAction = useMemo(() => pickNext(items), [items])
  const doneCount = items.filter((i) => i.done).length
  const pathComplete = items.filter((i) => !i.optional).every((i) => i.done)

  const deferMeta = useCallback(() => {
    deferSuccessPathMeta()
    setMetaDeferred(true)
  }, [])

  return {
    status,
    setup,
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
