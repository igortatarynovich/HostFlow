import { useEffect, useMemo, useRef, useState } from 'react'
import { useCandidatesWorkPanelPreview } from './useCandidatesWorkPanelPreview'

type UseCandidatesWorkPanelArgs = {
  t: (key: string, options?: any) => string
  workPanelAssigneeScope?: 'mine' | 'team'
}

export function useCandidatesWorkPanel({ t, workPanelAssigneeScope = 'mine' }: UseCandidatesWorkPanelArgs) {
  // Selection of the candidate for the persistent right Work panel.
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null)
  const selectedCandidateIdRef = useRef<string | null>(null)
  useEffect(() => {
    selectedCandidateIdRef.current = selectedCandidateId
  }, [selectedCandidateId])

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

    // Topbar: icon "panel opened" = sidebar or active candidate preview (work panel open).
    const panelOpen = sidebarOpen || selectedCandidateId != null
    window.dispatchEvent(new CustomEvent('candidates-sidebar-state', { detail: { open: panelOpen } }))
  }, [sidebarOpen, selectedCandidateId])

  // When preview opens, close fixed/overlay column filter menus to avoid click interception.
  useEffect(() => {
    if (!selectedCandidateId) return
    window.dispatchEvent(new CustomEvent('hf:close-column-filter-menus'))
  }, [selectedCandidateId])

  // Listen to Topbar events: open/close sidebar and report state back.
  const sidebarOpenRef = useRef(sidebarOpen)
  useEffect(() => {
    sidebarOpenRef.current = sidebarOpen
  }, [sidebarOpen])

  useEffect(() => {
    const handleToggle = (e: CustomEvent<{ open: boolean }>) => {
      const next = e.detail.open
      setSidebarOpen(next)
      // When sidebar is closed, clear selection so the preview panel fully disappears.
      if (!next) setSelectedCandidateId(null)
    }

    const handleRequestState = () => {
      const panelOpen = sidebarOpenRef.current || selectedCandidateIdRef.current != null
      window.dispatchEvent(new CustomEvent('candidates-sidebar-state', { detail: { open: panelOpen } }))
    }

    window.addEventListener('candidates-sidebar-toggle', handleToggle as EventListener)
    window.addEventListener('candidates-sidebar-request-state', handleRequestState)

    return () => {
      window.removeEventListener('candidates-sidebar-toggle', handleToggle as EventListener)
      window.removeEventListener('candidates-sidebar-request-state', handleRequestState)
    }
  }, [])

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

