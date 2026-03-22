import clsx from 'clsx'
import type { AugmentedCandidate } from '../types'
import type { Dispatch, SetStateAction } from 'react'

/** Компактные chip-кнопки: один ряд по центру, без «лестницы» по высоте строки. */
const rowBtnClass =
  'inline-flex h-7 max-w-full shrink-0 items-center justify-center rounded-md border border-slate-200 bg-white px-2.5 text-[11px] font-medium leading-none text-slate-600 hover:border-slate-300 hover:bg-slate-50 hover:text-slate-800 touch-manipulation whitespace-nowrap'

type CandidatesTableRowQuickActionsProps = {
  c: AugmentedCandidate
  isFocused: boolean
  handleCandidateOpen: (id: string) => void
  navigate: (to: string) => void
  setSelectedCandidateId: Dispatch<SetStateAction<string | null>>
  setSidebarOpen: Dispatch<SetStateAction<boolean>>
  t: (key: string, opts?: any) => string
}

export function CandidatesTableRowQuickActions({
  c,
  isFocused,
  handleCandidateOpen,
  navigate,
  setSelectedCandidateId,
  setSidebarOpen,
  t,
}: CandidatesTableRowQuickActionsProps) {
  return (
    <div
      className={clsx(
        'flex w-full min-w-0 flex-wrap items-center justify-center gap-1.5',
        // На широких экранах — по hover строки; на узких (тач) кнопки всегда видны.
        isFocused
          ? 'flex'
          : 'max-lg:flex lg:hidden lg:group-hover:flex lg:group-focus-within:flex',
      )}
    >
      <button
        type="button"
        className={rowBtnClass}
        onClick={(e) => {
          e.stopPropagation()
          handleCandidateOpen(c.id)
          navigate(`/app/candidates/${c.id}`)
        }}
      >
        {t('common.actions.open', { defaultValue: 'Open' })}
      </button>

      <button
        type="button"
        className={rowBtnClass}
        onPointerDown={(e) => {
          e.stopPropagation()
          if (e.pointerType === 'mouse' && e.button !== 0) return
          try {
            e.currentTarget.setPointerCapture(e.pointerId)
          } catch {
            /* ignore */
          }
        }}
        onPointerUp={(e) => {
          e.stopPropagation()
          if (e.pointerType === 'mouse' && e.button !== 0) return
          try {
            if (e.currentTarget.hasPointerCapture(e.pointerId)) {
              e.currentTarget.releasePointerCapture(e.pointerId)
            }
          } catch {
            /* ignore */
          }
          setSelectedCandidateId(c.id)
          setSidebarOpen(true)
        }}
        onClick={(e) => {
          e.stopPropagation()
          if (e.detail === 0) {
            setSelectedCandidateId(c.id)
            setSidebarOpen(true)
          }
        }}
      >
        {t('app.candidates.actions.preview', { defaultValue: 'Preview' })}
      </button>
    </div>
  )
}
