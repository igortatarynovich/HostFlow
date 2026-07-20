import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  getCommunicationsSettings,
  listCommunicationAccounts,
  listCommunicationThreads,
  type CommunicationChannelAccount,
  type CommunicationThread,
} from '../api/communications'
import { roleMayLoadFullCommunicationsSettings } from '../constants/communicationsSettingsAccess'
import { useAuth } from '../store/useAuth'
import { usePermissions } from './usePermissions'

type SetupState = {
  channelsEnabled: boolean
  emailConnected: boolean
  emailOAuthConnected: boolean
  messengerConnected: boolean
  emailInboundSeen: boolean
  messengerInboundSeen: boolean
}

export type CommunicationsSetupStepKey =
  | 'channels'
  | 'email_connected'
  | 'messenger_connected'
  | 'email_inbound'
  | 'messenger_inbound'

function emptyState(): SetupState {
  return {
    channelsEnabled: false,
    emailConnected: false,
    emailOAuthConnected: false,
    messengerConnected: false,
    emailInboundSeen: false,
    messengerInboundSeen: false,
  }
}

function accountOAuthConnected(account: CommunicationChannelAccount): boolean {
  const oauth =
    account?.settings_json?.oauth && typeof account.settings_json.oauth === 'object'
      ? account.settings_json.oauth
      : {}
  if (String(oauth.oauth_status || '').toLowerCase() === 'connected') return true
  if (oauth.has_refresh_token === true || oauth.has_access_token === true) return true
  return false
}

export function useCommunicationsSetupStatus() {
  const { me } = useAuth()
  const { role } = usePermissions()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [settings, setSettings] = useState<any | null>(null)
  const [accounts, setAccounts] = useState<CommunicationChannelAccount[]>([])
  const [threads, setThreads] = useState<CommunicationThread[]>([])

  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const canLoadSettings = Boolean(me?.tenant_id) && roleMayLoadFullCommunicationsSettings(role)
      const [cfg, acc, th] = await Promise.all([
        canLoadSettings
          ? getCommunicationsSettings()
          : Promise.resolve(null as Awaited<ReturnType<typeof getCommunicationsSettings>> | null),
        listCommunicationAccounts(),
        listCommunicationThreads({ limit: 300 }).catch(() => ({ items: [] as CommunicationThread[] })),
      ])
      setSettings(cfg)
      setAccounts(Array.isArray(acc?.items) ? acc.items : [])
      setThreads(Array.isArray(th?.items) ? th.items : [])
    } catch (err: any) {
      setError(err?.message || 'Failed to load communications setup status')
    } finally {
      setLoading(false)
    }
  }, [me?.tenant_id, role])

  useEffect(() => {
    void reload()
  }, [reload])

  const state = useMemo<SetupState>(() => {
    if (!accounts.length && !settings && !threads.length) {
      // Keep empty until first load finishes; reload() always settles loading.
    }
    const activeAccounts = accounts.filter((x) => Boolean(x?.is_active))
    const emailAccounts = activeAccounts.filter((x) => String(x.channel || '').toLowerCase() === 'email')
    const messengerAccounts = activeAccounts.filter((x) => String(x.channel || '').toLowerCase() !== 'email')
    const emailConnected = emailAccounts.length > 0
    const emailOAuthConnected = emailAccounts.some(accountOAuthConnected)
    const messengerConnected = messengerAccounts.length > 0

    const emailThreads = threads.filter((x) => String(x.channel || '').toLowerCase() === 'email')
    const messengerThreads = threads.filter((x) => String(x.channel || '').toLowerCase() !== 'email')
    const emailInboundSeen = emailThreads.some((x) => Boolean(x.last_inbound_at))
    const messengerInboundSeen = messengerThreads.some((x) => Boolean(x.last_inbound_at))

    // Settings may be null for non-admin roles; fall back to "has a connected channel".
    let channelsEnabled = emailOAuthConnected || messengerConnected
    if (settings) {
      const enabledChannels = Array.isArray(settings?.channels?.channels)
        ? settings.channels.channels.filter((x: any) => x?.enabled)
        : []
      channelsEnabled = enabledChannels.length > 0 || channelsEnabled
    } else if (!emailConnected && !messengerConnected) {
      return emptyState()
    }

    return {
      channelsEnabled,
      emailConnected,
      emailOAuthConnected,
      messengerConnected,
      emailInboundSeen,
      messengerInboundSeen,
    }
  }, [accounts, settings, threads])

  /**
   * Inbox is ready when at least one real channel works.
   * Messenger is optional — email OAuth alone is enough.
   * Inbound messages are a later health signal, not a setup gate.
   */
  const isComplete = useMemo(
    () => state.channelsEnabled && (state.emailOAuthConnected || state.messengerConnected),
    [state.channelsEnabled, state.emailOAuthConnected, state.messengerConnected],
  )

  const missingStepKeys = useMemo<CommunicationsSetupStepKey[]>(() => {
    const out: CommunicationsSetupStepKey[] = []
    if (!state.channelsEnabled) out.push('channels')
    if (!state.emailOAuthConnected && !state.messengerConnected) out.push('email_connected')
    return out
  }, [state])

  const nextStepKey = missingStepKeys[0] ?? null

  const doneCount = useMemo(() => {
    let n = 0
    if (state.channelsEnabled) n += 1
    if (state.emailOAuthConnected) n += 1
    if (state.messengerConnected) n += 1
    if (state.emailInboundSeen) n += 1
    if (state.messengerInboundSeen) n += 1
    return n
  }, [state])

  return {
    loading,
    error,
    state,
    doneCount,
    isComplete,
    missingStepKeys,
    nextStepKey,
    reload,
  }
}
