import { useEffect, useMemo, useState } from 'react'
import {
  DEFAULT_COMMUNICATIONS_SETTINGS,
  getCommunicationsSettings,
  type CommunicationsWorkspaceSettings,
} from '../api/communications'
import { useAuth } from '../store/useAuth'
import { usePermissions } from './usePermissions'

export type CommunicationsFeatureKey =
  | 'messages'
  | 'email'
  | 'calendar'
  | 'planner'
  | 'teamAvailability'
  | 'myAvailability'
  | 'timeOffRequests'
  | 'communicationsAdmin'

type AccessState = {
  loading: boolean
  settings: CommunicationsWorkspaceSettings
  error: string | null
}

const defaultState: AccessState = {
  loading: true,
  settings: DEFAULT_COMMUNICATIONS_SETTINGS,
  error: null,
}

const featureToModule: Record<CommunicationsFeatureKey, string> = {
  messages: 'messages',
  email: 'email',
  calendar: 'calendar',
  planner: 'planner',
  teamAvailability: 'availability',
  myAvailability: 'availability',
  timeOffRequests: 'timeOff',
  communicationsAdmin: 'communicationsAdmin',
}

const featureToAccessKey: Record<CommunicationsFeatureKey, keyof CommunicationsWorkspaceSettings['access']['roles']> = {
  messages: 'messages',
  email: 'email',
  calendar: 'calendar',
  planner: 'planner',
  teamAvailability: 'teamAvailability',
  myAvailability: 'myAvailability',
  timeOffRequests: 'timeOffRequests',
  communicationsAdmin: 'communicationsAdmin',
}

function normalizeError(err: any): string {
  const d = err?.response?.data?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) {
    const msg = d.map((x) => (typeof x?.msg === 'string' ? x.msg : null)).filter(Boolean).join('; ')
    if (msg) return msg
  }
  if (d && typeof d === 'object' && typeof d.msg === 'string') return d.msg
  return err?.message || 'Failed to load communications access settings'
}

export function useCommunicationsAccess() {
  const { me } = useAuth()
  const { role } = usePermissions()
  const [state, setState] = useState<AccessState>(defaultState)

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        const settings = await getCommunicationsSettings()
        if (!mounted) return
        setState({ loading: false, settings, error: null })
      } catch (err: any) {
        if (!mounted) return
        // Fallback to defaults to avoid breaking the UI on temporary settings endpoint issues.
        setState({ loading: false, settings: DEFAULT_COMMUNICATIONS_SETTINGS, error: normalizeError(err) })
      }
    })()
    return () => {
      mounted = false
    }
  }, [])

  const userIdSet = useMemo(() => {
    const ids = new Set<string>()
    const rawIds = [
      (me as any)?.user_id,
      (me as any)?.id,
      me?.sub,
      me?.email,
    ]
    rawIds.forEach((v) => {
      if (v != null && String(v).trim()) ids.add(String(v))
    })
    return ids
  }, [me])

  const canUseCommunicationsFeature = useMemo(() => {
    return (feature: CommunicationsFeatureKey): boolean => {
      const settings = state.settings || DEFAULT_COMMUNICATIONS_SETTINGS
      const moduleKey = featureToModule[feature]
      const accessKey = featureToAccessKey[feature]
      const moduleCfg = settings.entitlements?.modules?.[moduleKey]
      if (moduleCfg && !moduleCfg.enabled) return false

      const overrides = settings.access?.usersOverrides || {}
      for (const uid of userIdSet) {
        const override = overrides[uid]
        if (override && Object.prototype.hasOwnProperty.call(override, feature)) {
          return Boolean((override as Record<string, boolean>)[feature])
        }
      }

      const allowedRoles = settings.access?.roles?.[accessKey] || []
      if (!allowedRoles.length) return true
      return allowedRoles.map((r) => String(r).toLowerCase()).includes(String(role || '').toLowerCase())
    }
  }, [role, state.settings, userIdSet])

  return {
    loading: state.loading,
    error: state.error,
    settings: state.settings,
    canUseCommunicationsFeature,
  }
}

