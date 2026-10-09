import type { ReactNode } from 'react'
import type { TranslateFn } from '../../../i18n'
import type { RecruitmentOverviewResponse } from '../../../api/analytics'

export interface RecruitmentOverviewPanelProps {
  t: TranslateFn
  formatNumber: (value?: number) => string
  overview: RecruitmentOverviewResponse | null
  loading: boolean
}

function StatCard({ label, value, testId }: { label: string; value: string; testId: string }) {
  return (
    <div className="relative overflow-hidden rounded-lg border border-slate-200 bg-slate-50/90 px-3 py-2.5" data-testid={testId}>
      <div className="absolute inset-y-0 left-0 w-1 bg-slate-400" />
      <div className="pl-1.5">
        <div className="text-[11px] text-slate-500">{label}</div>
        <div className="text-xl font-semibold tabular-nums text-slate-900">{value}</div>
      </div>
    </div>
  )
}

function Section({
  testId,
  title,
  hint,
  children,
}: {
  testId: string
  title: string
  hint: string
  children: ReactNode
}) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm" data-testid={testId}>
      <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
      <p className="mt-0.5 text-xs text-slate-500">{hint}</p>
      {children}
    </section>
  )
}

function CountRow({ label, value }: { label: string; value: string }) {
  return (
    <li className="flex items-center justify-between gap-3 border-b border-slate-100 py-1.5 text-sm last:border-0">
      <span className="min-w-0 truncate text-slate-700">{label}</span>
      <span className="shrink-0 tabular-nums font-semibold text-slate-900">{value}</span>
    </li>
  )
}

export function RecruitmentOverviewPanel({
  t,
  formatNumber,
  overview,
  loading,
}: RecruitmentOverviewPanelProps) {
  if (!overview) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-500">
        {loading ? t('common.loading') : t('app.dashboard.efficiency.empty')}
      </div>
    )
  }

  const acquisition = overview.acquisition
  const people = overview.people
  const recruitment = overview.recruitment
  const gap = overview.historical_gap.linked_recruitment_leads_without_application
  const noVacancy = t('app.dashboard.efficiency.overview.recruitment.no_vacancy')
  const noRecruiter = t('app.dashboard.efficiency.overview.recruitment.no_recruiter')

  return (
    <div className={`space-y-4 ${loading ? 'opacity-70 transition-opacity' : ''}`}>
      <Section
        testId="overview-acquisition"
        title={t('app.dashboard.efficiency.overview.acquisition.title')}
        hint={t('app.dashboard.efficiency.overview.acquisition.hint')}
      >
        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            testId="kpi-leads-received"
            label={t('app.dashboard.efficiency.overview.acquisition.leads')}
            value={formatNumber(acquisition.leads_received)}
          />
          <StatCard
            testId="kpi-unique-candidates"
            label={t('app.dashboard.efficiency.overview.acquisition.unique')}
            value={formatNumber(acquisition.unique_candidates_linked)}
          />
          <StatCard
            testId="kpi-acquisition-new"
            label={t('app.dashboard.efficiency.overview.acquisition.new')}
            value={formatNumber(acquisition.new_candidates)}
          />
          <StatCard
            testId="kpi-acquisition-returning"
            label={t('app.dashboard.efficiency.overview.acquisition.returning')}
            value={formatNumber(acquisition.returning_candidates)}
          />
          <StatCard
            testId="kpi-leads-with-application"
            label={t('app.dashboard.efficiency.overview.acquisition.with_application')}
            value={formatNumber(acquisition.leads_with_application)}
          />
          <StatCard
            testId="kpi-duplicate-review"
            label={t('app.dashboard.efficiency.overview.acquisition.duplicate_review')}
            value={formatNumber(acquisition.leads_in_duplicate_review)}
          />
          <StatCard
            testId="kpi-duplicated"
            label={t('app.dashboard.efficiency.overview.acquisition.duplicated')}
            value={formatNumber(acquisition.leads_duplicated)}
          />
        </div>
        {gap > 0 ? (
          <p
            className="mt-3 text-xs text-slate-600"
            data-testid="historical-gap"
            title={t('app.dashboard.efficiency.overview.gap_hint')}
          >
            {t('app.dashboard.efficiency.overview.gap', { values: { count: formatNumber(gap) } })}
          </p>
        ) : null}
        {acquisition.leads_received === 0 ? (
          <p className="mt-3 text-sm text-slate-500">{t('app.dashboard.efficiency.overview.acquisition.empty')}</p>
        ) : (
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('app.dashboard.efficiency.overview.acquisition.sources')}
              </h3>
              <ul className="mt-1" data-testid="acquisition-sources">
                {acquisition.by_source.map((row) => (
                  <CountRow
                    key={row.source || '—'}
                    label={row.source || '—'}
                    value={formatNumber(row.leads)}
                  />
                ))}
              </ul>
            </div>
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('app.dashboard.efficiency.overview.acquisition.vacancies')}
              </h3>
              <ul className="mt-1" data-testid="acquisition-vacancies">
                {acquisition.by_vacancy.map((row) => (
                  <CountRow
                    key={row.vacancy_id ?? 'none'}
                    label={row.vacancy_name || noVacancy}
                    value={formatNumber(row.leads)}
                  />
                ))}
              </ul>
            </div>
          </div>
        )}
      </Section>

      <Section
        testId="overview-people"
        title={t('app.dashboard.efficiency.overview.people.title')}
        hint={t('app.dashboard.efficiency.overview.people.hint')}
      >
        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            testId="kpi-people-new"
            label={t('app.dashboard.efficiency.overview.people.new')}
            value={formatNumber(people.new_candidates)}
          />
        </div>
        {people.new_candidates === 0 ? (
          <p className="mt-3 text-sm text-slate-500">{t('app.dashboard.efficiency.overview.people.empty')}</p>
        ) : null}
      </Section>

      <Section
        testId="overview-recruitment"
        title={t('app.dashboard.efficiency.overview.recruitment.title')}
        hint={t('app.dashboard.efficiency.overview.recruitment.hint')}
      >
        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            testId="kpi-applications-started"
            label={t('app.dashboard.efficiency.overview.recruitment.started')}
            value={formatNumber(recruitment.applications_started)}
          />
        </div>
        {recruitment.applications_started === 0 ? (
          <p className="mt-3 text-sm text-slate-500">{t('app.dashboard.efficiency.overview.recruitment.empty')}</p>
        ) : (
          <>
            <div className="mt-4" data-testid="current-status">
              <h3 className="text-sm font-semibold text-slate-900">
                {t('app.dashboard.efficiency.overview.recruitment.status_title')}
              </h3>
              <p className="mt-0.5 text-xs text-slate-500">
                {t('app.dashboard.efficiency.overview.recruitment.status_hint')}
              </p>
              <ul className="mt-1">
                {recruitment.by_current_status.map((row) => (
                  <CountRow
                    key={row.status}
                    label={t(`app.dashboard.efficiency.overview.recruitment.statuses.${row.status}`, {
                      defaultValue: row.status,
                    })}
                    value={formatNumber(row.count)}
                  />
                ))}
              </ul>
            </div>
            <div className="mt-4 grid gap-4 lg:grid-cols-2">
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {t('app.dashboard.efficiency.overview.recruitment.by_vacancy')}
                </h3>
                <ul className="mt-1" data-testid="recruitment-vacancies">
                  {recruitment.by_vacancy.map((row) => (
                    <CountRow
                      key={row.vacancy_id ?? 'none'}
                      label={row.vacancy_name || noVacancy}
                      value={formatNumber(row.applications)}
                    />
                  ))}
                </ul>
              </div>
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {t('app.dashboard.efficiency.overview.recruitment.by_recruiter')}
                </h3>
                <ul className="mt-1" data-testid="recruitment-recruiters">
                  {recruitment.by_recruiter.map((row) => (
                    <CountRow
                      key={row.recruiter_id ?? 'none'}
                      label={row.recruiter_name || noRecruiter}
                      value={formatNumber(row.applications)}
                    />
                  ))}
                </ul>
              </div>
            </div>
          </>
        )}
      </Section>
    </div>
  )
}
