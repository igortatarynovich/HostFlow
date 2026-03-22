// замените строку импорта на type-only
import { useEffect, type PropsWithChildren } from 'react'

const SIZE_CLASS: Record<'md' | 'lg' | 'xl' | '2xl', string> = {
  md: 'max-w-lg',
  lg: 'max-w-2xl',
  xl: 'max-w-4xl',
  '2xl': 'max-w-6xl',
}

export function Modal({
  open,
  onClose,
  title,
  children,
  size = 'md',
  surfaceClassName,
}: {
  open: boolean
  onClose: () => void
  title?: string
  /** Wider modals for lists (e.g. Activities from Candidates hero). */
  size?: keyof typeof SIZE_CLASS
  surfaceClassName?: string
} & PropsWithChildren) {
  useEffect(() => {
    function onKey(e: KeyboardEvent){ if (e.key === 'Escape') onClose() }
    if (open) window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null
  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/40" onClick={onClose}/>
      <div className="absolute inset-0 grid place-items-center p-2 sm:p-4">
        <div
          className={
            `card modal-surface w-full ${SIZE_CLASS[size]} max-h-[calc(100vh-1rem)] overflow-y-auto p-4 sm:max-h-[calc(100vh-2rem)] sm:p-5` +
            (surfaceClassName ? ` ${surfaceClassName}` : '')
          }
        >
          {title && <h3 className="text-lg font-semibold mb-4">{title}</h3>}
          {children}
        </div>
      </div>
    </div>
  )
}
