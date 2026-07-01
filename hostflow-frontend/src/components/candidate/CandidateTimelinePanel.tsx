import { useEffect, useMemo, useState, useCallback } from 'react'
import clsx from 'clsx'
import type { ReminderRecord } from '../../api/types'
import type { CandidateNote, StageHistoryEntry } from '../../modules/candidate-card/types'
import { useI18n } from '../../i18n'
import { formatDateSafe } from '../../modules/candidates/candidateUtils'
import type { FriendlyErrorInfo } from '../../utils/friendlyError'

type TimelineFilter = { stage: boolean; notes: boolean; reminders: boolean }

type Props = {
  locale: string
  stageHistory: StageHistoryEntry[]
  notes: CandidateNote[]
  reminders: ReminderRecord[]
  loading: boolean
  timelineError: FriendlyErrorInfo | null
  resolveStageLabel: (code: string) => string
  onRequestLoad?: () => void
  onOpenStageHistory?: () => void
  onToggleRemindersPanel?: () => void
  defaultOpen?: boolean
  /** When set together with `onExpandedChange`, expanded/collapsed state is controlled by the parent. */
  expanded?: boolean
  onExpandedChange?: (next: boolean) => void
  hideToggle?: boolean
  hideFilters?: boolean
  includeStageChanges?: boolean
  collapsedCount?: number
  variant?: 'info' | 'full'
  itemsMaxHeightClass?: string
  /** Карточка кандидата: кнопка «только смены стадий» в шапке Activity (без отдельной модалки). */
  stageHistoryShortcut?: boolean
}

type TimelineItem =
  | { kind: 'stage'; at: string; title: string; meta?: string }
  | { kind: 'note'; at: string; title: string; meta?: string }
  | { kind: 'reminder'; at: string; title: string; meta?: string }

export default function CandidateTimelinePanel({
  locale,
  stageHistory,
  notes,
  reminders,
  loading,
  timelineError,
  resolveStageLabel,
  onRequestLoad,
  onOpenStageHistory,
  onToggleRemindersPanel,
  defaultOpen = false,
  expanded: expandedProp,
  onExpandedChange,
  hideToggle = false,
  hideFilters = false,
  includeStageChanges = true,
  collapsedCount = 3,
  variant = 'info',
  itemsMaxHeightClass,
  stageHistoryShortcut = false,
}: Props) {
  const { t } = useI18n()
  const controlled = expandedProp !== undefined
  const [uncontrolledOpen, setUncontrolledOpen] = useState(defaultOpen || hideToggle)
  const open = controlled ? Boolean(expandedProp) : uncontrolledOpen
  const setOpen = useCallback(
    (next: boolean) => {
      if (!controlled) setUncontrolledOpen(next)
      onExpandedChange?.(next)
    },
    [controlled, onExpandedChange],
  )
  const [filter, setFilter] = useState<TimelineFilter>({
    stage: true,
    notes: true,
    reminders: true,
  })

  // When toggle is hidden, load + render immediately (no extra UI).
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (hideToggle) onRequestLoad?.()
  }, [hideToggle, onRequestLoad])

  const items = useMemo(() => {
    const out: TimelineItem[] = []

    if (includeStageChanges && filter.stage) {
      stageHistory.forEach((h) => {
        if (!h.at) return
        const from = h.from_code
          ? resolveStageLabel(String(h.from_code))
          : t('app.candidate_card.history.modal.previous', { defaultValue: 'Previous' })
        const to = h.to_code ? resolveStageLabel(String(h.to_code)) : '—'
        out.push({
          kind: 'stage',
          at: String(h.at),
          title: t('app.candidate_card.timeline.items.stage_change', { defaultValue: 'Stage change' }),
          meta: `${from} → ${to}${h.actor ? ` · ${h.actor}` : ''}${h.reason ? ` · ${h.reason}` : ''}`,
        })
      })
    }

    if (filter.notes) {
      notes.forEach((n) => {
        if (!n.created_at) return
        const txt = String(n.text || '').trim()
        out.push({
          kind: 'note',
          at: String(n.created_at),
          title: t('app.candidate_card.timeline.items.note', { defaultValue: 'Note' }),
          meta: txt.length > 180 ? `${txt.slice(0, 180)}…` : txt,
        })
      })
    }

    if (filter.reminders) {
      reminders.forEach((r) => {
        const at = (r.completed_at || r.due_at || r.created_at || '').toString()
        if (!at) return
        out.push({
          kind: 'reminder',
          at,
          title: r.title || t('app.reminders.item.untitled', { defaultValue: 'Untitled' }),
          meta: `${t('app.reminders.fields.due_at', { defaultValue: 'Due' })}: ${
            formatDateSafe(r.due_at, locale) || r.due_at
          } · ${String(r.status)}`,
        })
      })
    }

    out.sort((a, b) => {
      const ta = Date.parse(a.at)
      const tb = Date.parse(b.at)
      return (Number.isFinite(tb) ? tb : 0) - (Number.isFinite(ta) ? ta : 0)
    })

    return out
  }, [filter.notes, filter.reminders, filter.stage, includeStageChanges, locale, notes, reminders, resolveStageLabel, stageHistory, t])

  const collapsedItems = useMemo(() => {
    const n = Math.max(0, Math.min(50, Number(collapsedCount) || 0))
    return n > 0 ? items.slice(0, n) : []
  }, [collapsedCount, items])
  return (
    <section className={clsx('rounded-2xl border border-slate-200 bg-white p-3', variant === 'info' && 'flex flex-col')}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <div className="text-xs font-semibold text-slate-700">
              {t('app.candidate_card.activity_feed.title', { defaultValue: 'Activity' })}
            </div>
            {stageHistoryShortcut && includeStageChanges ? (
              <button
                type="button"
                className="text-[11px] font-medium text-brand-700 hover:text-brand-800 hover:underline"
                onClick={() => {
                  setFilter({ stage: true, notes: false, reminders: false })
                  setOpen(true)
                }}
              >
                {t('app.candidate_card.timeline.stage_changes_only', { defaultValue: 'Stage changes only' })}
              </button>
            ) : null}
            {!hideToggle ? (
              <button
                type="button"
                className="text-[11px] text-slate-500 hover:text-slate-700"
                onClick={() => {
                  const next = !open
                  setOpen(next)
                  if (next) onRequestLoad?.()
                }}
              >
                {open ? t('common.actions.collapse') : t('common.actions.expand')}
              </button>
            ) : null}
          </div>
          {timelineError ? (
            <div className="mt-1 text-xs text-red-600">
              <div>{timelineError.title}</div>
              {timelineError.detail ? (
                <div className="mt-0.5 text-[11px] text-red-700/90">{timelineError.detail}</div>
              ) : null}
            </div>
          ) : null}
          {!timelineError && loading ? <div className="mt-1 text-xs text-slate-500">{t('common.loading')}</div> : null}
        </div>

        {/* Intentionally no extra action buttons in Info block header. */}
      </div>

      <div className={clsx(variant === 'info' && 'flex-1')}>
      {open ? (
        <>
          {!hideFilters ? (
            <div className="mt-2 flex flex-wrap items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 p-2">
              {(
                [
                  ...(includeStageChanges
                    ? ([['stage', t('app.candidate_card.timeline.filters.stage', { defaultValue: 'Stage' })]] as const)
                    : ([] as const)),
                  ['notes', t('app.candidate_card.timeline.filters.notes', { defaultValue: 'Notes' })],
                  ['reminders', t('app.candidate_card.timeline.filters.reminders', { defaultValue: 'Reminders' })],
                ] as const
              ).map(([key, label]) => (
                <label
                  key={key}
                  className="inline-flex cursor-pointer items-center gap-2 rounded-lg bg-white px-2 py-1 text-xs text-slate-700"
                >
                  <input
                    type="checkbox"
                    checked={filter[key]}
                    onChange={() =>
                      setFilter((prev) => ({
                        ...prev,
                        [key]: !prev[key],
                      }))
                    }
                  />
                  <span>{label}</span>
                </label>
              ))}
            </div>
          ) : null}

          {items.length ? (
            <div className={clsx('mt-2 space-y-2', itemsMaxHeightClass ? `${itemsMaxHeightClass} overflow-y-auto pr-1` : '')}>
              {items.map((it, idx) => (
                <div
                  key={`${it.kind}-${it.at}-${idx}`}
                  className={clsx(
                    'rounded-xl border border-slate-200 bg-white p-3',
                    it.kind === 'reminder' && 'border-brand-100'
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="text-sm font-medium text-slate-900">{it.title}</div>
                      {it.meta ? <div className="mt-0.5 text-xs text-slate-600">{it.meta}</div> : null}
                    </div>
                    <div className="shrink-0 text-[11px] text-slate-500" title={it.at}>
                      {formatDateSafe(it.at, locale) || it.at}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="mt-2 rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-500">
              {t('app.candidate_card.timeline.empty', { defaultValue: 'No events yet.' })}
            </div>
          )}
        </>
      ) : (
        <div className="mt-2">
          {collapsedItems.length ? (
            <div className="space-y-2">
              {collapsedItems.map((it, idx) => (
                <div key={`${it.kind}-${it.at}-${idx}`} className="rounded-xl border border-slate-200 bg-white p-2">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="text-xs font-semibold text-slate-900 truncate">{it.title}</div>
                      {it.meta ? <div className="mt-0.5 text-[11px] text-slate-600 truncate">{it.meta}</div> : null}
                    </div>
                    <div className="shrink-0 text-[11px] text-slate-500" title={it.at}>
                      {formatDateSafe(it.at, locale) || it.at}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : timelineError || loading ? null : (
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-500">
              {t('app.candidate_card.timeline.collapsed_hint', { defaultValue: 'No recent activity.' })}
            </div>
          )}
        </div>
      )}
      </div>
    </section>
  )
}

