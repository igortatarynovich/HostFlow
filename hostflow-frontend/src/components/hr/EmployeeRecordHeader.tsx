import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { IconBriefcase, IconHistory, IconId } from '@tabler/icons-react'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import type { WorkforceEmployee } from '../../api/workforce'

function formatShortDate(iso: string | null | undefined, locale: string): string | null {
  if (!iso || !String(iso).trim()) return null
  const d = new Date(String(iso))
  if (Number.isNaN(d.getTime())) return null
  try {
    return new Intl.DateTimeFormat(locale, { dateStyle: 'medium' }).format(d)
  } catch {
    return String(iso).slice(0, 10)
  }
}

function statusBadgeClass(status: string): string {
  const s = (status || '').toLowerCase()
  if (s === 'active') return 'border-emerald-300/80 bg-emerald-500/25 text-emerald-50'
  if (s === 'onboarding') return 'border-sky-300/80 bg-sky-500/25 text-sky-50'
  if (s === 'terminated' || s === 'suspended') return 'border-rose-300/80 bg-rose-500/20 text-rose-50'
  if (s === 'on_sick_leave' || s === 'on_vacation' || s === 'on_leave') return 'border-amber-300/80 bg-amber-500/25 text-amber-50'
  if (s === 'contract_ending') return 'border-orange-300/80 bg-orange-500/20 text-orange-50'
  return 'border-white/35 bg-white/15 text-white'
}

export function EmployeeRecordHeader({
  employee,
  heroPipelines,
  onOpenActivity,
  activityDisabled,
  headerActions,
}: {
  employee: WorkforceEmployee
  /** Second row inside hero: workforce + post-handoff candidate journeys (timelines). */
  heroPipelines?: ReactNode
  onOpenActivity?: () => void
  activityDisabled?: boolean
  /** Extra controls in the header actions row (e.g. return to recruitment, terminate). */
  headerActions?: ReactNode
}) {
  const { t, locale } = useI18n()
  const hire = formatShortDate(employee.hire_date, locale)
  const handoff = formatShortDate(employee.handoff_at, locale)
  const statusLabel = t(`app.hr.employee_detail.status_labels.${employee.status}`, {
    defaultValue: employee.status.replace(/_/g, ' '),
  })

  return (
    <div className="rounded-xl bg-gradient-to-br from-brand-600 via-brand-500 to-brand-400 p-4 text-white shadow-lg md:p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 space-y-3">
          <div className="text-[11px] font-medium text-white/85">
            <Link to={CRM_APP_PATHS.hrEmployees} className="hover:underline">
              {t('app.hr.employee_detail.header.back')}
            </Link>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-wide text-white/70">
              {t('app.hr.employee_detail.header.kicker')}
            </p>
            <h1 className="mt-1 truncate text-2xl font-bold tracking-tight text-white md:text-3xl">
              {employee.display_name}
            </h1>
            <p className="mt-1 font-mono text-[11px] text-white/65" title={employee.id}>
              {t('app.hr.employee_detail.header.record_id')}:{' '}
              <span className="select-all">{employee.id}</span>
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`inline-flex items-center rounded-md border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide ${statusBadgeClass(employee.status)}`}
            >
              {statusLabel}
            </span>
            {hire ? (
              <span className="text-[11px] rounded-md border border-white/30 bg-white/10 px-2 py-1 text-white/95">
                {t('app.hr.employee_detail.header.hire', { values: { date: hire } })}
              </span>
            ) : null}
            {handoff ? (
              <span className="text-[11px] rounded-md border border-white/30 bg-white/10 px-2 py-1 text-white/90">
                {t('app.hr.employee_detail.header.handoff', { values: { date: handoff } })}
              </span>
            ) : null}
          </div>
        </div>

        <div className="flex flex-shrink-0 flex-wrap items-center gap-2 lg:justify-end">
          {onOpenActivity ? (
            <button
              type="button"
              disabled={activityDisabled}
              className="btn inline-flex items-center gap-1.5 rounded-lg border border-white/30 bg-white/10 px-3 py-2 text-sm font-medium text-white transition hover:bg-white/20 disabled:cursor-not-allowed disabled:opacity-50"
              onClick={onOpenActivity}
            >
              <IconHistory size={18} className="shrink-0 opacity-90" aria-hidden />
              {t('app.candidate_card.activity_feed.title', { defaultValue: 'Activity' })}
            </button>
          ) : null}
          {headerActions}
          {employee.candidate_id ? (
            <Link
              to={`${CRM_APP_PATHS.candidates}/${encodeURIComponent(employee.candidate_id)}`}
              className="inline-flex items-center gap-1.5 rounded-lg border border-white/30 bg-white/15 px-3 py-2 text-sm font-medium text-white transition hover:bg-white/25"
            >
              <IconId size={18} className="opacity-90" aria-hidden />
              {t('app.hr.employee_detail.open_candidate')}
            </Link>
          ) : null}
          {employee.vacancy_id ? (
            <Link
              to={`${CRM_APP_PATHS.vacancies}/${encodeURIComponent(employee.vacancy_id)}`}
              className="inline-flex items-center gap-1.5 rounded-lg border border-white/30 bg-white/15 px-3 py-2 text-sm font-medium text-white transition hover:bg-white/25"
            >
              <IconBriefcase size={18} className="opacity-90" aria-hidden />
              {t('app.hr.employee_detail.header.open_vacancy')}
            </Link>
          ) : null}
        </div>
      </div>
      {heroPipelines ? <div className="mt-3 space-y-3">{heroPipelines}</div> : null}
      <p className="mt-4 border-t border-white/20 pt-3 text-[11px] leading-relaxed text-white/80">
        {t('app.hr.employee_detail.header.footer_hint')}
      </p>
    </div>
  )
}
