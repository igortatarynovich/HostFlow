import { useEffect, useMemo, useState } from 'react'
import { useCandidatesWorkPanelPreview } from './useCandidatesWorkPanelPreview'

type UseCandidatesWorkPanelArgs = {
  t: (key: string, options?: any) => string
  workPanelAssigneeScope?: 'mine' | 'team'
}

export function useCandidatesWorkPanel({ t, workPanelAssigneeScope = 'mine' }: UseCandidatesWorkPanelArgs) {
  // Selection of the candidate for the persistent right Work panel.
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null)

  // Persisted open/close state for the side panel shell (§2.13: default collapsed; new key resets old “always open” prefs).
  const SIDEBAR_STORAGE_KEY = 'hf:candidates:workRailShell:v1'
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    try {
      return window.localStorage.getItem(SIDEBAR_STORAGE_KEY) === '1'
    } catch {
      return false
    }
  })

  useEffect(() => {
    try {
      window.localStorage.setItem(SIDEBAR_STORAGE_KEY, sidebarOpen ? '1' : '0')
    } catch {
      /* ignore */
    }
  }, [sidebarOpen])

  // When preview opens, close fixed/overlay column filter menus to avoid click interception.
  useEffect(() => {
    if (!selectedCandidateId) return
    window.dispatchEvent(new CustomEvent('hf:close-column-filter-menus'))
  }, [selectedCandidateId])

  const workPanelOpen = useMemo(() => sidebarOpen || selectedCandidateId != null, [sidebarOpen, selectedCandidateId])

  const preview = useCandidatesWorkPanelPreview({ t, selectedCandidateId, workPanelAssigneeScope })

  return {
    selectedCandidateId,
    setSelectedCandidateId,
    sidebarOpen,
    setSidebarOpen,
    workPanelOpen,
    ...preview,
  }
}

