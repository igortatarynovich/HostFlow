import { useEffect, useRef } from 'react'

export type ComboboxOption = { value: string; label: string }

export type MenuBox = { top: number; left: number; width: number; maxHeight: number }

export function menuBox(anchor: HTMLElement): MenuBox {
  const rect = anchor.getBoundingClientRect()
  const roomBelow = window.innerHeight - rect.bottom - 8
  const roomAbove = rect.top - 8
  const openUp = roomBelow < 160 && roomAbove > roomBelow
  const maxHeight = Math.max(120, Math.min(288, openUp ? roomAbove : roomBelow))
  const top = openUp ? Math.max(8, rect.top - maxHeight - 8) : rect.bottom + 8
  return { top, left: rect.left, width: rect.width, maxHeight }
}

export function useClickOutside<T extends HTMLElement>(onOutside: () => void) {
  const ref = useRef<T | null>(null)
  useEffect(() => {
    function handler(e: MouseEvent) {
      const el = ref.current
      if (!el) return
      if (!el.contains(e.target as Node)) onOutside()
    }
    function onEsc(e: KeyboardEvent) {
      if (e.key === 'Escape') onOutside()
    }
    document.addEventListener('mousedown', handler)
    document.addEventListener('keydown', onEsc)
    return () => {
      document.removeEventListener('mousedown', handler)
      document.removeEventListener('keydown', onEsc)
    }
  }, [onOutside])
  return ref
}
