import { useEffect, useRef } from 'react'

export type ComboboxOption = { value: string; label: string }

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
