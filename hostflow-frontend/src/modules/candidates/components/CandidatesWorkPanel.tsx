import type { ReactNode } from 'react'
import clsx from 'clsx'
import { CANDIDATES_WORK_PANEL_RAIL_WIDTH_PX } from '../constants'

type CandidatesWorkPanelProps = {
  /** KPI / insights strip (list scope). */
  summaryHero: ReactNode
  /** Выбранный кандидат: next action, docs, timeline. */
  previewSlot: ReactNode
  /** Поиск не дублируем здесь — он над таблицей. Управление списком: виды, фильтры, таблица/pipeline. */
  controlsSlot: ReactNode
  /** Без выбранной строки средняя колонка не растягивается — иначе пустой зазор под обзором. */
  previewVisible?: boolean
}

/**
 * Правый рейл списка кандидатов: три зоны — сводка | превью кандидата | управление списком.
 */
export function CandidatesWorkPanel({
  summaryHero,
  previewSlot,
  controlsSlot,
  previewVisible = true,
}: CandidatesWorkPanelProps) {
  return (
    <aside
      style={{ maxWidth: CANDIDATES_WORK_PANEL_RAIL_WIDTH_PX }}
      className={clsx(
        'flex w-full min-w-0 flex-col overflow-hidden rounded-l-lg border-l border-y border-slate-200/90 bg-white/95 shadow-[inset_1px_0_0_rgb(241_245_249),0_8px_24px_rgba(15,23,42,0.06)] backdrop-blur-[1px]',
        previewVisible ? 'h-full min-h-0' : 'h-auto max-h-full',
      )}
    >
      <div className="shrink-0 border-b border-slate-200/90 bg-slate-50/50 px-2.5 py-2">{summaryHero}</div>
      {previewVisible && previewSlot ? (
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
          <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-2.5 py-2">{previewSlot}</div>
        </div>
      ) : null}
      <div
        className={clsx(
          'shrink-0 border-t border-slate-200/90 bg-slate-50/70 px-2.5 py-2',
          previewVisible &&
            'max-h-[min(36vh,320px)] min-h-0 overflow-y-auto overflow-x-hidden overscroll-contain',
        )}
      >
        {controlsSlot}
      </div>
    </aside>
  )
}
