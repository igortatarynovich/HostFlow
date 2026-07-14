import { useCallback, useEffect, useState } from 'react'
import {
  getClientChannelWorkspacePulse,
  type ClientChannelWorkspacePulse,
} from '../api/clientChannelWorkspace'

export function useClientChannelWorkspacePulse(channelId: string) {
  const [pulse, setPulse] = useState<ClientChannelWorkspacePulse | null>(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    if (!channelId) return
    setLoading(true)
    try {
      const data = await getClientChannelWorkspacePulse(channelId)
      setPulse(data)
    } catch {
      setPulse(null)
    } finally {
      setLoading(false)
    }
  }, [channelId])

  useEffect(() => {
    void refresh()
    const timer = window.setInterval(() => void refresh(), 5 * 60 * 1000)
    return () => window.clearInterval(timer)
  }, [refresh])

  return { pulse, loading, refresh }
}
