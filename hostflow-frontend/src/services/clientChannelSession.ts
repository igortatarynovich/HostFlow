import type { ClientAcquisitionChannelResult } from './createClientAcquisitionChannel'

const CHANNEL_SESSION_PREFIX = 'hostflow:client-channel:'
const LAST_CHANNEL_ID_KEY = 'hostflow:last-client-channel-id'

export function persistClientChannel(result: ClientAcquisitionChannelResult) {
  try {
    sessionStorage.setItem(`${CHANNEL_SESSION_PREFIX}${result.channelId}`, JSON.stringify(result))
    localStorage.setItem(LAST_CHANNEL_ID_KEY, result.channelId)
  } catch {
    // ignore
  }
}

export function readLastClientChannelId(): string | null {
  try {
    const id = localStorage.getItem(LAST_CHANNEL_ID_KEY)?.trim()
    return id || null
  } catch {
    return null
  }
}

export function persistLastClientChannelId(channelId: string): void {
  try {
    const id = channelId.trim()
    if (id) localStorage.setItem(LAST_CHANNEL_ID_KEY, id)
  } catch {
    /* ignore */
  }
}

export function loadClientChannel(channelId: string): ClientAcquisitionChannelResult | null {
  try {
    const raw = sessionStorage.getItem(`${CHANNEL_SESSION_PREFIX}${channelId}`)
    if (!raw) return null
    return JSON.parse(raw) as ClientAcquisitionChannelResult
  } catch {
    return null
  }
}
