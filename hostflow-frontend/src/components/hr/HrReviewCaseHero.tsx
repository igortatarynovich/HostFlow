import clsx from 'clsx'
import { useI18n } from '../../i18n'
import type { HrReviewHero, HrReviewPanel } from '../../api/workforce'
import { formatShortDateIso } from './hrEmployeeUiFormat'

const STAGE_ORDER = [
  'transferred_from_recruitment',
  'hr_pickup',
  'document_verification',
  'legal_eligibility',
  'hr_decision',
  'employee_onboarding',
]

function fallbackHero(panel: HrReviewPanel, displayName?: string | null): HrReviewHero {
  return {
    candidate_display_name: displayName || null,
    handoff_id: panel.handoff_id,
    review_status: panel.status,
    state_message: panel.next_required_action || '',
    process_stages: STAGE_ORDER.map((code, i) => ({
      code,
      label: code.replace(/_/g, ' '),
      state: i === 0 ? 'current' : 'pending',
    })),
  }
}

function stageDot(state: string) {
  if (state === 'done') return 'bg-emerald-500 text-white'
  if (state === 'current') return 'bg-brand-600 text-white ring-4 ring-brand-100'
  if (state === 'blocked') return 'bg-rose-500 text-white'
  if (state === 'skipped') return 'bg-slate-200 text-slate-400'
  return 'bg-slate-200 text-slate-500'
}

type Props = {
  panel: HrReviewPanel
  displayName?: string | null
  pageTitle?: string
}

export default function HrReviewCaseHero({ panel, displayName, pageTitle }: Props) {
  const { t } = useI18n()
  const hero = panel.hero ?? fallbackHero(panel, displayName)
  const stages = hero.process_stages ?? []
  const isReviewCase = panel.mode !== 'employee_profile' && panel.status !== 'approved_for_employment'

  return (
    <section className="rounded-2xl border border-slate-200 bg-gradient-to-br from-white via-brand-50/40 to-slate-50 p-4 shadow-sm sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-wide text-slate-500">
            {isReviewCase
              ? t('app.hr.review_case.badge', { defaultValue: 'HR review case' })
              : t('app.hr.review_case.profile_badge', { defaultValue: 'Employee profile' })}
          </p>
          <h1 className="mt-1 text-xl font-semibold tracking-tight text-slate-900">
            {pageTitle || hero.candidate_display_name || displayName || t('app.hr.review_case.untitled', { defaultValue: 'HR case' })}
          </h1>
          <p className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-600">
            {hero.handoff_id ? (
              <span>
                {t('app.hr.review_case.handoff', { defaultValue: 'Handoff' })}:{' '}
                <span className="font-mono">{hero.handoff_id.slice(0, 8)}…</span>
              </span>
            ) : null}
            {hero.transferred_at ? (
              <span>
                {t('app.hr.review_case.transferred', { defaultValue: 'Transferred' })}:{' '}
                {formatShortDateIso(hero.transferred_at)}
              </span>
            ) : null}
            {hero.vacancy_label ? <span>{hero.vacancy_label}</span> : null}
          </p>
        </div>
        <span className="rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-semibold uppercase text-indigo-950">
          {(hero.current_stage_label || hero.review_status || panel.status).replace(/_/g, ' ')}
        </span>
      </div>

      {stages.length > 0 ? (
        <ol className="mt-5 flex flex-wrap items-start gap-1 sm:gap-0">
          {stages.map((st, idx) => (
            <li key={st.code} className="flex min-w-[4.5rem] flex-1 flex-col items-center text-center sm:min-w-0">
              <div className="flex w-full items-center">
                {idx > 0 ? <span className="hidden h-0.5 flex-1 bg-slate-200 sm:block" aria-hidden /> : null}
                <span
                  className={clsx(
                    'flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[11px] font-bold',
                    stageDot(st.state),
                  )}
                  title={st.label}
                >
                  {st.state === 'done' ? '✓' : idx + 1}
                </span>
                {idx < stages.length - 1 ? (
                  <span className="hidden h-0.5 flex-1 bg-slate-200 sm:block" aria-hidden />
                ) : null}
              </div>
              <span className="mt-1.5 hidden px-0.5 text-[9px] font-medium leading-tight text-slate-600 sm:block">
                {st.label}
              </span>
            </li>
          ))}
        </ol>
      ) : null}

      {hero.state_message ? (
        <p className="mt-4 rounded-lg border border-sky-200 bg-sky-50/90 px-3 py-2 text-sm text-sky-950">
          {hero.state_message}
        </p>
      ) : null}
    </section>
  )
}
