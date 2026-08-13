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
    messengerConnected: false,
    emailInboundSeen: false,
    messengerInboundSeen: false,
  }
}

export function useCommunicationsSetupStatus() {
  const { me } = useAuth()
  const { role, rawRole, accessContext, presetId } = usePermissions()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [settings, setSettings] = useState<any | null>(null)
  const [accounts, setAccounts] = useState<CommunicationChannelAccount[]>([])
  const [threads, setThreads] = useState<CommunicationThread[]>([])

  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const canLoadSettings =
        Boolean(me?.tenant_id) &&
        roleMayLoadFullCommunicationsSettings(rawRole || role, { accessContext, presetId })
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
  }, [accessContext, me?.tenant_id, presetId, rawRole, role])

  useEffect(() => {
    void reload()
  }, [reload])

  const state = useMemo<SetupState>(() => {
    if (!settings) return emptyState()
    const enabledChannels = Array.isArray(settings?.channels?.channels)
      ? settings.channels.channels.filter((x: any) => x?.enabled)
      : []
    const channelsEnabled = enabledChannels.length > 0

    const activeAccounts = accounts.filter((x) => Boolean(x?.is_active))
    const emailConnected = activeAccounts.some((x) => String(x.channel || '').toLowerCase() === 'email')
    const messengerConnected = activeAccounts.some((x) => String(x.channel || '').toLowerCase() !== 'email')

    const emailThreads = threads.filter((x) => String(x.channel || '').toLowerCase() === 'email')
    const messengerThreads = threads.filter((x) => String(x.channel || '').toLowerCase() !== 'email')

    const emailInboundSeen = emailThreads.some((x) => Boolean(x.last_inbound_at))
    const messengerInboundSeen = messengerThreads.some((x) => Boolean(x.last_inbound_at))

    return {
      channelsEnabled,
      emailConnected,
      messengerConnected,
      emailInboundSeen,
      messengerInboundSeen,
    }
  }, [accounts, settings, threads])

  const emailPathReady = state.emailConnected && state.emailInboundSeen
  const messengerPathReady = state.messengerConnected && state.messengerInboundSeen
  // One working channel path is enough — do not block email-only tenants on messenger.
  const isComplete = state.channelsEnabled && (emailPathReady || messengerPathReady)

  const doneCount = useMemo(
    () =>
      [
        state.channelsEnabled,
        state.emailConnected,
        state.messengerConnected,
        state.emailInboundSeen,
        state.messengerInboundSeen,
      ].filter(Boolean).length,
    [state],
  )

  const missingStepKeys = useMemo<CommunicationsSetupStepKey[]>(() => {
    if (isComplete) return []
    const out: CommunicationsSetupStepKey[] = []
    if (!state.channelsEnabled) out.push('channels')
    // Prefer finishing the email path when email is already connected or nothing is ready yet.
    if (!emailPathReady) {
      if (!state.emailConnected) out.push('email_connected')
      else if (!state.emailInboundSeen) out.push('email_inbound')
    }
    if (!messengerPathReady && !state.emailConnected) {
      if (!state.messengerConnected) out.push('messenger_connected')
      else if (!state.messengerInboundSeen) out.push('messenger_inbound')
    }
    return out
  }, [emailPathReady, isComplete, messengerPathReady, state])

  const nextStepKey = missingStepKeys[0] ?? null

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
