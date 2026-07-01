import { useState } from 'react'
import clsx from 'clsx'
import type { HrReviewCurrentTask, HrReviewPanel, HrReviewTaskPriorityStep } from '../../api/workforce'
import { useI18n } from '../../i18n'

type Props = {
  task: HrReviewCurrentTask
  priorityLadder?: HrReviewTaskPriorityStep[]
  onScrollTo?: (anchor: string) => void
}

function scrollToAnchor(anchor: string, onScrollTo?: (anchor: string) => void) {
  const href = anchor.startsWith('#') ? anchor : `#${anchor}`
  if (onScrollTo) onScrollTo(href)
  else document.querySelector(href)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function priorityClass(priority: string): string {
  switch (priority) {
    case 'critical':
      return 'border-rose-300 bg-gradient-to-br from-rose-50/90 to-white'
    case 'high':
      return 'border-amber-300 bg-gradient-to-br from-amber-50/80 to-white'
    default:
      return 'border-brand-300 bg-gradient-to-br from-brand-50/80 to-white'
  }
}

function TaskPriorityLadder({ ladder }: { ladder: HrReviewTaskPriorityStep[] }) {
  const { t } = useI18n()
  const [open, setOpen] = useState(false)
  if (!ladder.length) return null

  return (
    <details className="mt-4 rounded-lg border border-slate-200/90 bg-white/60" open={open} onToggle={(e) => setOpen(e.currentTarget.open)}>
      <summary className="cursor-pointer select-none px-3 py-2 text-xs font-semibold text-slate-600">
        {t('app.hr.review_case.priority_ladder_toggle', {
          defaultValue: 'System priority order (v1)',
        })}
      </summary>
      <ol className="border-t border-slate-200/80 px-3 py-2 space-y-1.5">
        {ladder.map((row) => (
          <li
            key={row.task_type}
            className={clsx(
              'flex gap-2 text-xs rounded-md px-2 py-1',
              row.state === 'current' ? 'bg-brand-100/80 font-semibold text-brand-950' : 'text-slate-600',
            )}
          >
            <span className="tabular-nums text-slate-500 w-5 shrink-0">{row.step}.</span>
            <span>
              <span className="text-slate-900">{row.label}</span>
              {row.summary ? <span className="block font-normal text-slate-500 mt-0.5">{row.summary}</span> : null}
            </span>
          </li>
        ))}
      </ol>
    </details>
  )
}

export default function HrCurrentTaskPanel({ task, priorityLadder, onScrollTo }: Props) {
  const { t } = useI18n()
  const blockers = task.related_checklist_items?.length
    ? task.related_checklist_items.map((c) => c.replace(/_/g, ' '))
    : []
  const step = task.priority_step ?? 0
  const total = task.priority_total ?? 8

  return (
    <section
      id="hr-current-task"
      className={clsx('scroll-mt-24 rounded-xl border-2 p-4 shadow-sm', priorityClass(task.priority))}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-slate-600">
            {t('app.hr.review_case.current_task_kicker', { defaultValue: 'What to do now' })}
            {step > 0 ? (
              <span className="ml-2 font-normal normal-case text-slate-500">
                {t('app.hr.review_case.priority_step', {
                  defaultValue: 'Step {{step}} of {{total}}',
                  step,
                  total,
                })}
              </span>
            ) : null}
          </p>
          <h2 className="mt-1 text-lg font-semibold text-slate-900">{task.title}</h2>
          {task.priority_catalog_label && task.priority_catalog_label !== task.title ? (
            <p className="mt-0.5 text-xs text-slate-500">{task.priority_catalog_label}</p>
          ) : null}
        </div>
        {task.blocks_approval ? (
          <span className="inline-flex rounded-full border border-rose-200 bg-rose-100 px-2 py-0.5 text-[11px] font-semibold text-rose-900">
            {t('app.hr.review_case.blocks_approval', { defaultValue: 'Blocks approval' })}
          </span>
        ) : (
          <span className="inline-flex rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-900">
            {t('app.hr.review_case.ready_step', { defaultValue: 'Ready' })}
          </span>
        )}
      </div>

      <p className="mt-3 text-sm text-slate-800">{task.description}</p>

      <div className="mt-3 rounded-lg border border-slate-200/80 bg-white/70 px-3 py-2 text-sm">
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t('app.hr.review_case.why_this_task', { defaultValue: 'Why this task' })}
        </span>
        <p className="mt-1 text-slate-700">{task.why}</p>
      </div>

      {blockers.length > 0 ? (
        <div className="mt-3">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('app.hr.review_case.task_closes', { defaultValue: 'This step closes' })}
          </span>
          <ul className="mt-1 list-inside list-disc text-xs text-slate-800">
            {blockers.map((b) => (
              <li key={b}>{b}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {task.related_documents && task.related_documents.length > 0 ? (
        <ul className="mt-3 flex flex-wrap gap-2 text-xs text-slate-700">
          {task.related_documents.map((d) => (
            <li
              key={`${d.document_key}-${d.document_id}`}
              className="rounded-md border border-slate-200 bg-white px-2 py-1"
            >
              {d.label || d.document_key}
            </li>
          ))}
        </ul>
      ) : null}

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          className="btn-primary"
          onClick={() => scrollToAnchor(task.primary_action.anchor || task.target_anchor || '#hr-employee-review', onScrollTo)}
        >
          {task.primary_action.label}
        </button>
        {task.secondary_actions?.map((a) =>
          a.anchor ? (
            <button
              key={`${a.label}-${a.anchor}`}
              type="button"
              className="btn-secondary"
              onClick={() => scrollToAnchor(a.anchor!, onScrollTo)}
            >
              {a.label}
            </button>
          ) : null,
        )}
      </div>

      <p className="mt-4 border-t border-slate-200/80 pt-3 text-xs text-slate-600">
        <span className="font-semibold text-slate-700">
          {t('app.hr.review_case.after_completion', { defaultValue: 'After this' })}:{' '}
        </span>
        {task.completion_condition}
      </p>

      {priorityLadder && priorityLadder.length > 0 ? <TaskPriorityLadder ladder={priorityLadder} /> : null}
    </section>
  )
}

export function HrCurrentTaskPanelFromReview({
  panel,
  onScrollTo,
}: {
  panel: HrReviewPanel
  onScrollTo?: (anchor: string) => void
}) {
  if (!panel.current_task) return null
  return (
    <HrCurrentTaskPanel
      task={panel.current_task}
      priorityLadder={panel.task_priority_v1}
      onScrollTo={onScrollTo}
    />
  )
}
