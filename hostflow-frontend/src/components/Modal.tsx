import { useEffect, type PropsWithChildren } from 'react'
import { IconX } from '@tabler/icons-react'
import { useI18n } from '../i18n'

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
  const { t } = useI18n()
  const closeLabel = t('common.actions.close', { defaultValue: 'Close' })

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
            `card modal-surface relative w-full ${SIZE_CLASS[size]} max-h-[calc(100vh-1rem)] overflow-y-auto p-4 pt-12 sm:max-h-[calc(100vh-2rem)] sm:p-5 sm:pt-12` +
            (surfaceClassName ? ` ${surfaceClassName}` : '')
          }
        >
          <button
            type="button"
            className="absolute right-2 top-2 z-10 rounded-lg p-2 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40"
            onClick={onClose}
            aria-label={closeLabel}
          >
            <IconX size={22} stroke={1.5} aria-hidden />
          </button>
          {title ? <h3 className="mb-4 pr-10 text-lg font-semibold leading-snug">{title}</h3> : null}
          {children}
        </div>
      </div>
    </div>
  )
}
