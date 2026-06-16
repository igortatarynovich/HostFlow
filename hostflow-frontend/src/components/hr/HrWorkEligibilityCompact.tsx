import { useEffect, useState } from 'react'
import type { HrReviewEligibilitySummary, HrReviewPanel } from '../../api/workforce'
import WorkEligibilityJourneyWorkspace from './WorkEligibilityJourneyWorkspace'
import { useI18n } from '../../i18n'

type Props = {
  panel: HrReviewPanel
  employeeId: string
  manage: boolean
  onRefresh?: () => void
  journeyExpanded?: boolean
  onJourneyExpandedChange?: (open: boolean) => void
}

export default function HrWorkEligibilityCompact({
  panel,
  employeeId,
  manage,
  onRefresh,
  journeyExpanded,
  onJourneyExpandedChange,
}: Props) {
  const { t } = useI18n()
  const [showFullInternal, setShowFullInternal] = useState(false)
  const controlled = journeyExpanded !== undefined
  const showFull = controlled ? journeyExpanded : showFullInternal

  useEffect(() => {
    if (journeyExpanded) setShowFullInternal(true)
  }, [journeyExpanded])

  const setShowFull = (next: boolean | ((prev: boolean) => boolean)) => {
    const value = typeof next === 'function' ? next(showFull) : next
    if (controlled) onJourneyExpandedChange?.(value)
    else setShowFullInternal(value)
  }
  const summary: HrReviewEligibilitySummary | null | undefined = panel.work_eligibility_summary

  return (
    <section id="hr-review-eligibility" className="scroll-mt-24 rounded-xl border border-slate-200 bg-white p-4">
      <h2 className="text-sm font-semibold text-slate-900">
        {t('app.hr.work_eligibility.section_title', { defaultValue: 'Work eligibility' })}
      </h2>
      {summary ? (
        <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-xs text-slate-500">{t('app.hr.review_case.current_step', { defaultValue: 'Current step' })}</dt>
            <dd className="font-medium text-slate-900">{summary.current_step_title || summary.current_step_code || '—'}</dd>
          </div>
          <div>
            <dt className="text-xs text-slate-500">{t('app.hr.review_case.step_status', { defaultValue: 'Status' })}</dt>
            <dd className="font-medium text-slate-900">{summary.current_step_status || '—'}</dd>
          </div>
          {summary.recommended_next_action ? (
            <div className="sm:col-span-2">
              <dt className="text-xs text-slate-500">{t('app.hr.review.next_action', { defaultValue: 'Next' })}</dt>
              <dd className="text-slate-800">{summary.recommended_next_action}</dd>
            </div>
          ) : null}
          {summary.blockers && summary.blockers.length > 0 ? (
            <div className="sm:col-span-2">
              <dt className="text-xs text-slate-500">{t('app.hr.review_case.blockers', { defaultValue: 'Blockers' })}</dt>
              <dd>
                <ul className="list-inside list-disc text-xs text-rose-800">
                  {summary.blockers.map((b) => (
                    <li key={b}>{b}</li>
                  ))}
                </ul>
              </dd>
            </div>
          ) : null}
        </dl>
      ) : (
        <p className="mt-2 text-sm text-slate-500">
          {t('app.hr.review_case.eligibility_after_employee', {
            defaultValue: 'Full eligibility journey is available after workforce employee is linked.',
          })}
        </p>
      )}
      {employeeId ? (
        <button
          type="button"
          className="mt-3 text-sm font-medium text-brand-700 hover:underline"
          onClick={() => setShowFull((x) => !x)}
        >
          {showFull
            ? t('app.hr.review_case.hide_journey', { defaultValue: 'Hide full eligibility journey' })
            : t('app.hr.review_case.show_journey', { defaultValue: 'Show full eligibility journey' })}
        </button>
      ) : null}
      {showFull && employeeId ? (
        <div className="mt-4 border-t border-slate-100 pt-4">
          <WorkEligibilityJourneyWorkspace employeeId={employeeId} manage={manage} onChanged={onRefresh} />
        </div>
      ) : null}
    </section>
  )
}
