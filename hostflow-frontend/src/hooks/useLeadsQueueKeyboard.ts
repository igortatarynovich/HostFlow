import { useEffect, useRef } from 'react'

/** True when focus is in a field that should consume typing (not queue shortcuts). */
export function leadsQueueKeyboardConsumesTyping(target: EventTarget | null): boolean {
  const el = target instanceof HTMLElement ? target : null
  if (!el) return false
  if (el.isContentEditable) return true
  const tag = el.tagName
  if (tag === 'TEXTAREA' || tag === 'SELECT') return true
  if (tag === 'INPUT') {
    const type = (el as HTMLInputElement).type?.toLowerCase() || 'text'
    if (type === 'checkbox' || type === 'radio' || type === 'button' || type === 'submit' || type === 'reset' || type === 'file') {
      return false
    }
    return true
  }
  if (el.closest('[role="dialog"]') || el.closest('[data-leads-queue-modal]')) return true
  return false
}

export type LeadsQueueKeyboardHandlers = {
  onMoveSelection: (delta: 1 | -1) => void
  onEnterPrimary: () => void
  onEscape: () => void
  onVacancy: () => void
  onPool: () => void
  onRequestInfo: () => void
  onReject: () => void
}

export type UseLeadsQueueKeyboardOptions = {
  enabled: boolean
  /** When true, do not handle (modals, bulk flows, etc.). */
  suspend: boolean
  handlers: LeadsQueueKeyboardHandlers
}

/**
 * Recruitment leads table: j/k or arrows move selection; Enter primary; Esc clear;
 * v vacancy picker; p pool; i request info; r reject (parent opens modal).
 */
export function useLeadsQueueKeyboard({ enabled, suspend, handlers }: UseLeadsQueueKeyboardOptions): void {
  const handlersRef = useRef(handlers)
  handlersRef.current = handlers

  useEffect(() => {
    if (!enabled) return

    const onKeyDown = (e: KeyboardEvent) => {
      if (suspend) return
      if (e.defaultPrevented) return
      if (e.metaKey || e.ctrlKey || e.altKey) return
      if (leadsQueueKeyboardConsumesTyping(e.target)) return

      const h = handlersRef.current

      switch (e.key) {
        case 'j':
        case 'J':
          e.preventDefault()
          h.onMoveSelection(1)
          return
        case 'k':
        case 'K':
          e.preventDefault()
          h.onMoveSelection(-1)
          return
        case 'ArrowDown':
          e.preventDefault()
          h.onMoveSelection(1)
          return
        case 'ArrowUp':
          e.preventDefault()
          h.onMoveSelection(-1)
          return
        case 'Enter':
          e.preventDefault()
          h.onEnterPrimary()
          return
        case 'Escape':
          e.preventDefault()
          h.onEscape()
          return
        case 'v':
        case 'V':
          e.preventDefault()
          h.onVacancy()
          return
        case 'p':
        case 'P':
          e.preventDefault()
          h.onPool()
          return
        case 'i':
        case 'I':
          e.preventDefault()
          h.onRequestInfo()
          return
        case 'r':
        case 'R':
          e.preventDefault()
          h.onReject()
          return
        default:
          break
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [enabled, suspend])
}
