import { useMemo, useState } from 'react'
import clsx from 'clsx'
import { IconChevronDown } from '@tabler/icons-react'
import type { DetailRailAction } from '../../platform/detail-rail/detailRailTypes'

type CandidateEntityWorkspaceHeaderActionsProps = {
  actions: DetailRailAction[]
}

export function CandidateEntityWorkspaceHeaderActions({ actions }: CandidateEntityWorkspaceHeaderActionsProps) {
  const [open, setOpen] = useState(false)

  const primaryActions = useMemo(() => actions.filter((a) => a.label), [actions])

  if (!primaryActions.length) return null

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
      >
        Действия
        <IconChevronDown size={16} className={clsx('transition', open && 'rotate-180')} />
      </button>
      {open ? (
        <>
          <button
            type="button"
            className="fixed inset-0 z-10 cursor-default"
            aria-label="Закрыть меню"
            onClick={() => setOpen(false)}
          />
          <div className="absolute right-0 z-20 mt-1 min-w-[200px] overflow-hidden rounded-xl border border-slate-200 bg-white py-1 shadow-lg">
            {primaryActions.map((action) =>
              action.href ? (
                <a
                  key={action.id}
                  href={action.href}
                  className="block px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
                  onClick={() => setOpen(false)}
                >
                  {action.label}
                </a>
              ) : (
                <button
                  key={action.id}
                  type="button"
                  className="block w-full px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"
                  onClick={() => {
                    action.onClick?.()
                    setOpen(false)
                  }}
                >
                  {action.label}
                </button>
              ),
            )}
          </div>
        </>
      ) : null}
    </div>
  )
}
