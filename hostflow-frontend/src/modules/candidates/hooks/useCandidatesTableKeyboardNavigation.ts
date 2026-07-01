import type { RefObject, Dispatch, SetStateAction } from 'react'
import { useEffect, useRef, useState } from 'react'
import { CRM_APP_PATHS } from '../../../app/crmAppPaths'
import type { AugmentedCandidate } from '../types'

type UseCandidatesTableKeyboardNavigationArgs = {
  searchRef: RefObject<HTMLInputElement | null>
  canManage: boolean
  displayedItems: AugmentedCandidate[]
  checked: Record<string, boolean>
  setChecked: Dispatch<SetStateAction<Record<string, boolean>>>
  toggle: (id: string) => void
  handleCandidateOpen: (id: string) => void
  navigate: (to: string) => void
}

export function useCandidatesTableKeyboardNavigation({
  searchRef,
  canManage,
  displayedItems,
  checked,
  setChecked,
  toggle,
  handleCandidateOpen,
  navigate,
}: UseCandidatesTableKeyboardNavigationArgs) {
  const [focusedRowIndex, setFocusedRowIndex] = useState<number | null>(null)
  const focusedRowRef = useRef<HTMLTableRowElement | null>(null)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement
      const isInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT'
      const isContentEditable = target.isContentEditable || target.closest('[contenteditable]')

      // Ctrl/Cmd + K - focus search
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k' && !e.shiftKey) {
        e.preventDefault()
        searchRef.current?.focus()
        return
      }

      // Ignore most shortcuts when in editable fields.
      if (isInput || isContentEditable) {
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'a' && target.tagName === 'INPUT' && (target as HTMLInputElement).type !== 'checkbox') {
          return
        }
        if (e.key === 'Escape') return
      }

      // Escape - reset selection and focus
      if (e.key === 'Escape' && !isInput && !isContentEditable) {
        e.preventDefault()
        setChecked({})
        setFocusedRowIndex(null)
        focusedRowRef.current = null
        return
      }

      // Ctrl/Cmd + A - select all visible
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'a' && !isInput && !isContentEditable) {
        e.preventDefault()
        if (!canManage) return
        const newChecked: Record<string, boolean> = {}
        displayedItems.forEach((candidate) => {
          newChecked[candidate.id] = true
        })
        setChecked(newChecked)
        return
      }

      // Arrow navigation only when not typing in inputs
      if (isInput || isContentEditable) return

      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault()
        const currentIndex = focusedRowIndex !== null ? focusedRowIndex : -1
        const nextIndex =
          e.key === 'ArrowDown'
            ? currentIndex < displayedItems.length - 1
              ? currentIndex + 1
              : displayedItems.length - 1
            : currentIndex > 0
              ? currentIndex - 1
              : 0

        setFocusedRowIndex(nextIndex)

        if (nextIndex >= 0 && nextIndex < displayedItems.length) {
          queueMicrotask(() => {
            const row = document.querySelector(
              `[data-candidates-table-container] tr[data-index="${nextIndex}"]`,
            ) as HTMLElement | null
            row?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
          })
        }
        return
      }

      // Space/Enter - toggle current candidate selection
      if ((e.key === ' ' || e.key === 'Enter') && focusedRowIndex !== null && focusedRowIndex >= 0 && focusedRowIndex < displayedItems.length) {
        e.preventDefault()
        const candidate = displayedItems[focusedRowIndex]
        if (candidate && canManage) toggle(candidate.id)
        return
      }

      // Enter - open candidate card
      if (e.key === 'Enter' && focusedRowIndex !== null && focusedRowIndex >= 0 && focusedRowIndex < displayedItems.length) {
        e.preventDefault()
        const candidate = displayedItems[focusedRowIndex]
        if (candidate) {
          handleCandidateOpen(candidate.id)
          navigate(`${CRM_APP_PATHS.candidates}/${candidate.id}`)
        }
        return
      }

      // '/' - focus search
      if (e.key === '/' && !isInput && !isContentEditable) {
        e.preventDefault()
        searchRef.current?.focus()
        return
      }
    }

    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canManage, displayedItems.length, Object.keys(checked).length, focusedRowIndex, searchRef, setChecked, toggle, handleCandidateOpen, navigate])

  return { focusedRowIndex, focusedRowRef }
}

