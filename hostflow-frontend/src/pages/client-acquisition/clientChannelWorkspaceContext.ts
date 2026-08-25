import { createContext, useContext } from 'react'
import type { ClientChannelWorkspacePulse } from '../../api/clientChannelWorkspace'

export type ClientChannelWorkspaceContextValue = {
  channelId: string
  channelName: string
  publicUrl?: string
  pulse: ClientChannelWorkspacePulse | null
  pulseLoading: boolean
  reload: () => void
  refreshPulse: () => void
}

export const ClientChannelWorkspaceContext = createContext<ClientChannelWorkspaceContextValue | null>(null)

export function useClientChannelWorkspace(): ClientChannelWorkspaceContextValue {
  const ctx = useContext(ClientChannelWorkspaceContext)
  if (!ctx) {
    throw new Error('useClientChannelWorkspace must be used within ClientChannelWorkspaceLayout')
  }
  return ctx
}
