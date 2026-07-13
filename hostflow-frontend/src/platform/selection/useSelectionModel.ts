import { useCallback, useEffect, useMemo, useState } from 'react'
import type { SelectionBulkState, SelectionModel, SelectionModelConfig } from './types'

/**
 * Universal Selection Model — table/kanban/calendar only emit entity ids; rail is independent.
 */
export function useSelectionModel({
  orderedIds,
  closeRailWhenEntityMissing = true,
}: SelectionModelConfig): SelectionModel {
  const [activeId, setActiveId] = useState<string | null>(null)
  const [railOpen, setRailOpen] = useState(false)
  const [pinned, setPinnedState] = useState(false)
  const [pinnedEntityId, setPinnedEntityId] = useState<string | null>(null)
  const [bulkIds, setBulkIds] = useState<SelectionBulkState>({})

  const railEntityId = useMemo(() => {
    if (!railOpen) return null
    if (pinned && pinnedEntityId) return pinnedEntityId
    return activeId
  }, [railOpen, pinned, pinnedEntityId, activeId])

  useEffect(() => {
    if (!closeRailWhenEntityMissing || !railOpen || !railEntityId) return
    if (orderedIds.includes(railEntityId)) return
    setRailOpen(false)
    setActiveId(null)
    setPinnedState(false)
    setPinnedEntityId(null)
  }, [orderedIds, railEntityId, railOpen, closeRailWhenEntityMissing])

  const openDetailRail = useCallback((id: string) => {
    setActiveId(id)
    setRailOpen(true)
  }, [])

  const selectRow = useCallback(
    (id: string) => {
      // Decision Flow: repeat click on active row toggles rail closed (when not pinned).
      if (railOpen && !pinned && activeId === id) {
        setRailOpen(false)
        return
      }
      setActiveId(id)
      setRailOpen(true)
    },
    [railOpen, pinned, activeId],
  )

  const closeDetailRail = useCallback(() => {
    setRailOpen(false)
    // Keep activeId — row stays highlighted; Esc closes rail only (Interaction Rules / FB-2).
  }, [])

  const setPinned = useCallback(
    (next: boolean) => {
      if (next) {
        const pinTarget = railEntityId ?? activeId
        setPinnedState(true)
        setPinnedEntityId(pinTarget)
      } else {
        setPinnedState(false)
        setPinnedEntityId(null)
        if (activeId) {
          /* rail follows active again */
        }
      }
    },
    [activeId, railEntityId],
  )

  const togglePin = useCallback(() => {
    setPinned(!pinned)
  }, [pinned, setPinned])

  const navIndex = useMemo(() => {
    const id = railEntityId ?? activeId
    if (!id) return -1
    return orderedIds.indexOf(id)
  }, [orderedIds, railEntityId, activeId])

  const hasPrevious = !pinned && navIndex > 0
  const hasNext = !pinned && navIndex >= 0 && navIndex < orderedIds.length - 1

  const selectPrevious = useCallback(() => {
    if (pinned || navIndex <= 0) return
    const id = orderedIds[navIndex - 1]
    if (!id) return
    setActiveId(id)
  }, [navIndex, orderedIds, pinned])

  const selectNext = useCallback(() => {
    if (pinned || navIndex < 0 || navIndex >= orderedIds.length - 1) return
    const id = orderedIds[navIndex + 1]
    if (!id) return
    setActiveId(id)
  }, [navIndex, orderedIds, pinned])

  const highlightedId = useMemo(() => {
    if (pinned && pinnedEntityId) return activeId
    return activeId ?? railEntityId
  }, [activeId, pinned, pinnedEntityId, railEntityId])

  const isRowActive = useCallback(
    (id: string) => {
      if (pinned && pinnedEntityId) return id === pinnedEntityId
      const focusId = activeId ?? railEntityId
      return focusId != null && id === focusId
    },
    [pinned, pinnedEntityId, activeId, railEntityId],
  )

  const toggleBulk = useCallback((id: string) => {
    setBulkIds((prev) => ({ ...prev, [id]: !prev[id] }))
  }, [])

  const clearBulk = useCallback(() => {
    setBulkIds({})
  }, [])

  return {
    activeId,
    railOpen,
    railEntityId,
    pinned,
    pinnedEntityId,
    bulkIds,
    selectRow,
    openDetailRail,
    closeDetailRail,
    togglePin,
    setPinned,
    selectPrevious,
    selectNext,
    hasPrevious,
    hasNext,
    highlightedId,
    isRowActive,
    setBulkIds,
    toggleBulk,
    clearBulk,
  }
}
