import clsx from 'clsx'
import { IconLayoutSidebarRight } from '@tabler/icons-react'
import type { AugmentedCandidate } from '../types'
import type { Dispatch, SetStateAction } from 'react'

type CandidatesTableRowNamePreviewProps = {
  c: AugmentedCandidate
  isFocused: boolean
  selectedCandidateId: string | null
  workPanelOpen: boolean
  setSelectedCandidateId: Dispatch<SetStateAction<string | null>>
  setSidebarOpen: Dispatch<SetStateAction<boolean>>
  t: (key: string, opts?: Record<string, unknown>) => string
}

/**
 * Переключатель боковой панели: повторный клик по той же строке закрывает рейл (как ожидают с кнопки превью).
 */
export function CandidatesTableRowNamePreview({
  c,
  isFocused,
  selectedCandidateId,
  workPanelOpen,
  setSelectedCandidateId,
  setSidebarOpen,
  t,
}: CandidatesTableRowNamePreviewProps) {
  const id = c.id
  const isActive = Boolean(id && workPanelOpen && selectedCandidateId === id)

  const toggle = () => {
    if (!id) return
    if (isActive) {
      setSelectedCandidateId(null)
      setSidebarOpen(false)
      return
    }
    setSelectedCandidateId(id)
    setSidebarOpen(true)
  }

  const label = isActive
    ? t('app.candidates.actions.preview_close', { defaultValue: 'Close preview' })
    : t('app.candidates.actions.preview', { defaultValue: 'Preview' })
  const title = isActive
    ? t('app.candidates.actions.preview_close_hint', { defaultValue: 'Close the preview window' })
    : t('app.candidates.actions.preview_panel_hint', { defaultValue: 'Open preview in a window' })

  return (
    <button
      type="button"
      className={clsx(
        'inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border text-slate-500 shadow-sm transition-all duration-150',
        isActive
          ? 'border-brand-400 bg-brand-50 text-brand-700 ring-1 ring-brand-200'
          : 'border-slate-200/90 bg-white hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700 hover:shadow',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/35 focus-visible:ring-offset-1',
        'touch-manipulation',
        isFocused
          ? 'opacity-100'
          : 'opacity-[0.38] max-lg:opacity-100 lg:group-hover/name:opacity-100',
      )}
      title={title}
      aria-label={label}
      aria-pressed={isActive}
      onPointerDown={(e) => e.stopPropagation()}
      onClick={(e) => {
        e.stopPropagation()
        toggle()
      }}
    >
      <IconLayoutSidebarRight size={18} stroke={isActive ? 2.25 : 1.75} aria-hidden />
    </button>
  )
}
