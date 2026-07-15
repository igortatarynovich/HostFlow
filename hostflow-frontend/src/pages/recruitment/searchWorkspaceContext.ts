import { createContext, useContext } from 'react'
import type { SearchWorkspacePulse } from '../../api/searchWorkspace'

export type SearchWorkspaceContextValue = {
  searchId: string
  searchName: string
  companyName?: string
  publicUrl?: string
  pulse: SearchWorkspacePulse | null
  pulseLoading: boolean
  reload: () => Promise<void>
  refreshPulse: () => Promise<void>
}

export const SearchWorkspaceContext = createContext<SearchWorkspaceContextValue | null>(null)

export function useSearchWorkspace(): SearchWorkspaceContextValue {
  const ctx = useContext(SearchWorkspaceContext)
  if (!ctx) {
    throw new Error('useSearchWorkspace must be used within SearchWorkspaceLayout')
  }
  return ctx
}
