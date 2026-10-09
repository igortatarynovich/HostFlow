import type { ReactNode } from 'react'
import type { TranslateFn } from '../../../i18n'
import type {
  RecruitmentOverviewReasonCategory,
  RecruitmentOverviewResponse,
} from '../../../api/analytics'
import { translateReasonLabel, translateStageLabel } from '../../../utils/stageLabels'

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

function stageName(t: TranslateFn, code: string) {
  if (!code) return t('app.dashboard.efficiency.overview.operations.no_stage')
  return translateStageLabel(t, code)
}

function ReasonList({
  t,
  formatNumber,
  title,
  category,
  testId,
}: {
  t: TranslateFn
  formatNumber: (value?: number) => string
  title: string
  category: RecruitmentOverviewReasonCategory
  testId: string
}) {
  const rows = category.by_reason
  return (
    <div data-testid={testId}>
      <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
      <p className="mt-0.5 text-xs text-slate-500">
        {t('app.dashboard.efficiency.overview.operations.reason_candidates')}: {formatNumber(category.candidates)}
      </p>
      {category.candidates === 0 ? (
        <p className="mt-2 text-sm text-slate-500">{t('app.dashboard.efficiency.overview.operations.reasons_empty')}</p>
      ) : (
        <ul className="mt-1">
          {rows.map((row) => (
            <CountRow
              key={row.reason}
              label={translateReasonLabel(t, row.reason) || row.reason}
              value={
                row.occurrences === row.candidates
                  ? formatNumber(row.candidates)
                  : `${formatNumber(row.candidates)} · ${formatNumber(row.occurrences)}`
              }
            />
          ))}
          {category.candidates_without_reason > 0 ? (
            <CountRow
              label={t('app.dashboard.efficiency.overview.operations.without_reason')}
              value={formatNumber(category.candidates_without_reason)}
            />
          ) : null}
        </ul>
      )}
    </div>
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

      <Section
        testId="overview-stages"
        title={t('app.dashboard.efficiency.overview.operations.stages_title')}
        hint={t('app.dashboard.efficiency.overview.operations.stages_hint')}
      >
        <div className="mt-4" data-testid="current-stages">
          <h3 className="text-sm font-semibold text-slate-900">
            {t('app.dashboard.efficiency.overview.operations.current_stages')}
          </h3>
          <p className="mt-0.5 text-xs text-slate-500">
            {t('app.dashboard.efficiency.overview.operations.current_stages_hint')}
          </p>
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              testId="kpi-current-candidates"
              label={t('app.dashboard.efficiency.overview.operations.current_total')}
              value={formatNumber(overview.stages.current.total_candidates)}
            />
          </div>
          {overview.stages.current.total_candidates === 0 ? null : (
            <ul className="mt-1">
              {overview.stages.current.by_stage.map((row) => (
                <CountRow
                  key={row.stage || 'none'}
                  label={stageName(t, row.stage)}
                  value={formatNumber(row.candidates)}
                />
              ))}
            </ul>
          )}
        </div>
        <div className="mt-4" data-testid="stage-transitions">
          <h3 className="text-sm font-semibold text-slate-900">
            {t('app.dashboard.efficiency.overview.operations.transitions')}
          </h3>
          <p className="mt-0.5 text-xs text-slate-500">
            {t('app.dashboard.efficiency.overview.operations.transitions_hint')}
          </p>
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              testId="kpi-transitions-total"
              label={t('app.dashboard.efficiency.overview.operations.transitions_total')}
              value={formatNumber(overview.stages.transitions.total)}
            />
          </div>
          {overview.stages.transitions.total === 0 ? (
            <p className="mt-3 text-sm text-slate-500">
              {t('app.dashboard.efficiency.overview.operations.transition_empty')}
            </p>
          ) : (
            <>
            <ul className="mt-1" data-testid="entered-by-stage">
              {overview.stages.transitions.entered_by_stage.map((row) => (
                <CountRow key={row.stage} label={stageName(t, row.stage)} value={formatNumber(row.count)} />
              ))}
            </ul>
            <ul className="mt-2" data-testid="transition-pairs">
              {overview.stages.transitions.by_transition.map((row) => (
                <CountRow
                  key={`${row.from_stage ?? ''}-${row.to_stage}`}
                  label={t('app.dashboard.efficiency.overview.operations.from_to', {
                    values: {
                      from: row.from_stage ? stageName(t, row.from_stage) : '—',
                      to: stageName(t, row.to_stage),
                    },
                  })}
                  value={formatNumber(row.count)}
                />
              ))}
            </ul>
            </>
          )}
        </div>
      </Section>

      <Section
        testId="overview-contacts"
        title={t('app.dashboard.efficiency.overview.operations.contacts_title')}
        hint={t('app.dashboard.efficiency.overview.operations.contacts_hint')}
      >
        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            testId="kpi-contact-attempts"
            label={t('app.dashboard.efficiency.overview.operations.attempts')}
            value={formatNumber(overview.contacts.attempts_total)}
          />
          <StatCard
            testId="kpi-candidates-contacted"
            label={t('app.dashboard.efficiency.overview.operations.candidates_contacted')}
            value={formatNumber(overview.contacts.candidates_contacted)}
          />
          <StatCard
            testId="kpi-successful-contacts"
            label={t('app.dashboard.efficiency.overview.operations.successful')}
            value={formatNumber(overview.contacts.successful_attempts)}
          />
        </div>
        <p className="mt-2 text-xs text-slate-500">{t('app.dashboard.efficiency.overview.operations.successful_hint')}</p>
        {overview.contacts.attempts_total === 0 ? (
          <p className="mt-3 text-sm text-slate-500">{t('app.dashboard.efficiency.overview.operations.contacts_empty')}</p>
        ) : (
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('app.dashboard.efficiency.overview.operations.results')}
              </h3>
              <ul className="mt-1" data-testid="contact-results">
                {overview.contacts.by_result.map((row) => (
                  <CountRow
                    key={row.result || 'none'}
                    label={t(`app.dashboard.efficiency.overview.operations.result_labels.${row.result}`, {
                      defaultValue: row.result,
                    })}
                    value={formatNumber(row.attempts)}
                  />
                ))}
              </ul>
            </div>
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('app.dashboard.efficiency.overview.operations.channels')}
              </h3>
              <ul className="mt-1" data-testid="contact-channels">
                {overview.contacts.by_channel.map((row) => (
                  <CountRow
                    key={row.channel || 'none'}
                    label={t(`app.dashboard.efficiency.overview.operations.channel_labels.${row.channel}`, {
                      defaultValue: row.channel,
                    })}
                    value={formatNumber(row.attempts)}
                  />
                ))}
              </ul>
            </div>
          </div>
        )}
        {overview.contacts.by_recruiter.length > 0 ? (
          <div className="mt-4">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t('app.dashboard.efficiency.overview.operations.by_actor')}
            </h3>
            <ul className="mt-1" data-testid="contact-actors">
              {overview.contacts.by_recruiter.map((row) => (
                <CountRow
                  key={row.recruiter_id ?? 'none'}
                  label={row.recruiter_name || noRecruiter}
                  value={formatNumber(row.attempts)}
                />
              ))}
            </ul>
          </div>
        ) : null}
      </Section>

      <Section
        testId="overview-reasons"
        title={t('app.dashboard.efficiency.overview.operations.reasons_title')}
        hint={t('app.dashboard.efficiency.overview.operations.reasons_hint')}
      >
        <p className="mt-2 text-xs text-slate-500">
          {t('app.dashboard.efficiency.overview.operations.multiple_reasons')}
        </p>
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <ReasonList
            t={t}
            formatNumber={formatNumber}
            testId="company-reasons"
            title={t('app.dashboard.efficiency.overview.operations.company_reasons')}
            category={overview.reasons.rejected}
          />
          <ReasonList
            t={t}
            formatNumber={formatNumber}
            testId="candidate-reasons"
            title={t('app.dashboard.efficiency.overview.operations.candidate_reasons')}
            category={overview.reasons.declined}
          />
        </div>
      </Section>
    </div>
  )
}
