import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  getCommunicationsSettings,
  listCommunicationAccounts,
  listCommunicationThreads,
  type CommunicationChannelAccount,
  type CommunicationThread,
} from '../api/communications'

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
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [settings, setSettings] = useState<any | null>(null)
  const [accounts, setAccounts] = useState<CommunicationChannelAccount[]>([])
  const [threads, setThreads] = useState<CommunicationThread[]>([])

  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [cfg, acc, th] = await Promise.all([
        getCommunicationsSettings(),
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
  }, [])

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
    const out: CommunicationsSetupStepKey[] = []
    if (!state.channelsEnabled) out.push('channels')
    if (!state.emailConnected) out.push('email_connected')
    if (!state.messengerConnected) out.push('messenger_connected')
    if (!state.emailInboundSeen) out.push('email_inbound')
    if (!state.messengerInboundSeen) out.push('messenger_inbound')
    return out
  }, [state])

  const nextStepKey = missingStepKeys[0] ?? null

  return {
    loading,
    error,
    state,
    doneCount,
    isComplete: doneCount === 5,
    missingStepKeys,
    nextStepKey,
    reload,
  }
}
