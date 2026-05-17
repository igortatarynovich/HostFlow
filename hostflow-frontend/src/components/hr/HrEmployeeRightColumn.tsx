/**
 * HR employee desktop context column: operational KPIs, alerts, timeline peek,
 * employment summary, and quick navigation. Sticky wrapper applied by parent.
 * Uses the same CRM primitives (card, links) as the rest of the app — layout/density only.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'
import {
  getWorkEligibilityJourney,
  type HrReviewPanel,
  type NextHrAction,
  type WorkforceEmployeeOperationalProfile,
  type WorkforceHrBundle,
  type WorkforceOperationalSummary,
  type WorkforceProfileAlert,
  type WorkforceTimelineEvent,
} from '../../api/workforce'
import { formatShortDateIso } from './hrEmployeeUiFormat'

function KpiTile({
  label,
  value,
  tone = 'slate',
}: {
  label: string
  value: string | number
  tone?: 'slate' | 'amber' | 'rose' | 'brand'
}) {
  const toneRing =
    tone === 'amber'
      ? 'border-amber-100 bg-amber-50/80'
      : tone === 'rose'
        ? 'border-rose-100 bg-rose-50/80'
        : tone === 'brand'
          ? 'border-brand-100 bg-brand-50/60'
          : 'border-slate-100 bg-slate-50/80'
  return (
    <div className={`rounded-lg border px-2.5 py-2 ${toneRing}`}>
      <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-0.5 text-sm font-semibold tabular-nums text-slate-900">{value}</div>
    </div>
  )
}

export function HrEmployeeOperationalRail({
  summary,
  zusRegistrationStatus,
  storedComplianceStatus,
  onboardingOverdue,
}: {
  summary: WorkforceOperationalSummary
  zusRegistrationStatus: string | null | undefined
  storedComplianceStatus: string | null | undefined
  onboardingOverdue: number
}) {
  const { t } = useI18n()
  const risk = summary.risk_level || '—'
  const riskTone = /high|critical/i.test(risk) ? 'rose' : /medium|attention/i.test(risk) ? 'amber' : 'slate'

  return (
    <div className="card p-4">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {t('app.hr.employee_rail.control_title', { defaultValue: 'Operational control' })}
      </div>
      <dl className="mt-3 grid grid-cols-2 gap-2">
        <KpiTile
          label={t('app.hr.employee_rail.compliance', { defaultValue: 'Compliance' })}
          value={summary.compliance_status || '—'}
          tone="brand"
        />
        <KpiTile label={t('app.hr.employee_rail.risk', { defaultValue: 'Risk' })} value={risk} tone={riskTone as 'slate' | 'amber' | 'rose'} />
        <KpiTile
          label={t('app.hr.employee_rail.missing_docs', { defaultValue: 'Missing docs' })}
          value={summary.missing_documents_count}
          tone={summary.missing_documents_count > 0 ? 'amber' : 'slate'}
        />
        <KpiTile
          label={t('app.hr.employee_rail.expiring_docs', { defaultValue: 'Expiring' })}
          value={summary.expiring_documents_count}
          tone={summary.expiring_documents_count > 0 ? 'amber' : 'slate'}
        />
      </dl>
      <ul className="mt-3 space-y-1.5 border-t border-slate-100 pt-3 text-xs text-slate-700">
        <li className="flex justify-between gap-2">
          <span className="text-slate-500">{t('app.hr.employee_rail.assigned_hr', { defaultValue: 'Assigned HR' })}</span>
          <span className="min-w-0 truncate text-right font-medium text-slate-900">{summary.assigned_hr || '—'}</span>
        </li>
        <li className="flex justify-between gap-2">
          <span className="text-slate-500">{t('app.nav.hr.directory.col_employer', { defaultValue: 'Employer' })}</span>
          <span className="min-w-0 truncate text-right font-medium">{summary.employer || '—'}</span>
        </li>
        <li className="flex justify-between gap-2">
          <span className="text-slate-500">{t('app.nav.hr.directory.col_client', { defaultValue: 'Client' })}</span>
          <span className="min-w-0 truncate text-right font-medium">{summary.client || '—'}</span>
        </li>
        <li className="flex justify-between gap-2">
          <span className="text-slate-500">{t('app.hr.employee_rail.zus_registration', { defaultValue: 'ZUS registration' })}</span>
          <span className="font-mono text-[11px] font-medium text-slate-900">{zusRegistrationStatus || '—'}</span>
        </li>
        {storedComplianceStatus ? (
          <li className="flex justify-between gap-2">
            <span className="text-slate-500">{t('app.hr.employee_rail.stored_compliance', { defaultValue: 'Stored compliance' })}</span>
            <span className="font-medium text-slate-900">{storedComplianceStatus}</span>
          </li>
        ) : null}
        {onboardingOverdue > 0 ? (
          <li className="flex justify-between gap-2 text-rose-800">
            <span>{t('app.hr.employee_rail.onboarding_overdue', { defaultValue: 'Onboarding overdue' })}</span>
            <span className="font-semibold tabular-nums">{onboardingOverdue}</span>
          </li>
        ) : null}
      </ul>
    </div>
  )
}

function AlertsPanel({ alerts }: { alerts: WorkforceProfileAlert[] }) {
  const { t } = useI18n()
  if (!alerts.length) return null
  return (
    <div className="card p-4">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {t('app.hr.employee_rail.alerts', { defaultValue: 'Alerts' })}
      </div>
      <ul className="mt-2 space-y-2">
        {alerts.map((a) => (
          <li key={`${a.code}-${a.message}`} className="rounded border border-amber-100 bg-amber-50/90 px-3 py-2 text-xs text-amber-950">
            {a.message}
          </li>
        ))}
      </ul>
    </div>
  )
}

const HR_REVIEW_TERMINAL = new Set(['approved_for_employment', 'returned_to_recruitment', 'rejected_by_hr'])

function TimelineEventList({ events }: { events: WorkforceTimelineEvent[] }) {
  return (
    <ul className="space-y-2 text-xs">
      {events.map((ev) => (
        <li key={ev.id} className="border-b border-slate-100 pb-2 last:border-0">
          <div className="text-[10px] text-slate-500">
            {formatShortDateIso(ev.occurred_at)} · {ev.kind}
          </div>
          <div className="font-medium text-slate-900">{ev.title}</div>
          {ev.detail ? <div className="mt-0.5 break-all text-slate-600">{ev.detail}</div> : null}
        </li>
      ))}
    </ul>
  )
}

function TimelinePanel({ events }: { events: WorkforceTimelineEvent[] }) {
  const { t } = useI18n()
  const dialogRef = useRef<HTMLDialogElement>(null)
  const peek = events.slice(0, 3)

  return (
    <>
      <div className="card p-4">
        <div className="flex items-center justify-between gap-2">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('app.hr.employee_operational.section_timeline', { defaultValue: 'Timeline' })}
          </div>
          {events.length > 3 ? (
            <button
              type="button"
              className="text-[11px] font-medium text-brand-700 hover:underline"
              onClick={() => dialogRef.current?.showModal()}
            >
              {t('app.hr.employee_rail.timeline_full', { defaultValue: 'Open full history' })}
            </button>
          ) : null}
        </div>
        {peek.length === 0 ? (
          <p className="mt-2 text-xs text-slate-500">{t('app.hr.employee_operational.timeline_empty', { defaultValue: 'No timeline events.' })}</p>
        ) : (
          <div className="mt-2">
            <TimelineEventList events={peek} />
          </div>
        )}
        {events.length > 3 ? (
          <button type="button" className="btn-secondary btn-sm mt-3 w-full" onClick={() => dialogRef.current?.showModal()}>
            {t('app.hr.employee_rail.timeline_full', { defaultValue: 'Open full history' })}
          </button>
        ) : null}
      </div>
      <dialog
        ref={dialogRef}
        className="max-h-[85vh] w-[min(32rem,92vw)] rounded-xl border border-slate-200 bg-white p-0 shadow-xl backdrop:bg-slate-900/40"
        onCancel={(e) => {
          e.preventDefault()
          dialogRef.current?.close()
        }}
        onClick={(e) => {
          if (e.target === dialogRef.current) dialogRef.current.close()
        }}
      >
        <div className="flex max-h-[85vh] flex-col">
          <div className="flex items-center justify-between gap-2 border-b border-slate-100 px-4 py-3">
            <h3 className="text-sm font-semibold text-slate-900">
              {t('app.hr.employee_rail.timeline_modal_title', { defaultValue: 'Full timeline' })}
            </h3>
            <button type="button" className="btn-ghost btn-sm" onClick={() => dialogRef.current?.close()}>
              {t('common.close', { defaultValue: 'Close' })}
            </button>
          </div>
          <div className="overflow-y-auto px-4 py-3">
            <TimelineEventList events={events} />
          </div>
        </div>
      </dialog>
    </>
  )
}

function EmploymentPeek({
  rows,
}: {
  rows: WorkforceEmployeeOperationalProfile['employment_operational']
}) {
  const { t } = useI18n()
  if (!rows.length) return null
  const slice = rows.slice(0, 4)
  return (
    <div className="card p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t('app.hr.employee_rail.employment_peek', { defaultValue: 'Employment (summary)' })}
        </div>
        <a href="#hr-employee-employments" className="shrink-0 text-xs font-medium text-brand-700 hover:underline">
          {t('app.hr.employee_rail.open_full', { defaultValue: 'Open contracts' })}
        </a>
      </div>
      <ul className="mt-2 space-y-1.5 text-xs text-slate-800">
        {slice.map((r) => (
          <li key={r.id} className="flex flex-wrap justify-between gap-1 border-b border-slate-50 pb-1.5 last:border-0">
            <span className="font-mono text-[11px] text-slate-600">{r.contract_type}</span>
            <span className="text-slate-500">{formatShortDateIso(r.start_date)}</span>
            <span className="w-full text-[11px] text-slate-600">{r.position || '—'}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function NextHrActionFromReview({ panel }: { panel: HrReviewPanel }) {
  const { t } = useI18n()
  const title =
    panel.next_required_action?.trim() ||
    (panel.blockers.length
      ? t('app.hr.review.rail_blockers', { defaultValue: 'Resolve HR review blockers' })
      : t('app.hr.review.rail_continue', { defaultValue: 'Continue HR review' }))

  return (
    <div className="card border-indigo-100 bg-gradient-to-b from-indigo-50/90 to-white p-4 shadow-sm">
      <div className="text-[10px] font-semibold uppercase tracking-wide text-indigo-800">
        {t('app.hr.employee_rail.next_hr_action', { defaultValue: 'Next HR action' })}
      </div>
      <h3 className="mt-2 text-sm font-semibold leading-snug text-slate-900">{title}</h3>
      {panel.blockers.length ? (
        <ul className="mt-2 list-inside list-disc text-[11px] text-rose-800">
          {panel.blockers.map((b) => (
            <li key={b}>{b.replace(/_/g, ' ')}</li>
          ))}
        </ul>
      ) : null}
      {!panel.can_approve && panel.failed_required_items.length ? (
        <p className="mt-2 text-[11px] text-slate-600">
          {t('app.hr.review.rail_items', {
            defaultValue: 'Required: {items}',
            values: { items: panel.failed_required_items.join(', ') },
          })}
        </p>
      ) : null}
      <div className="mt-3">
        <a
          href="#hr-employee-review"
          className="btn-primary btn-sm inline-flex"
          onClick={(e) => {
            e.preventDefault()
            const el = document.getElementById('hr-employee-review')
            el?.scrollIntoView({ behavior: 'smooth', block: 'start' })
            el?.focus({ preventScroll: true })
          }}
        >
          {t('app.hr.review.rail_open', { defaultValue: 'Open HR review' })}
        </a>
      </div>
    </div>
  )
}

function NextHrActionPanel({ employeeId, hrReview }: { employeeId: string; hrReview?: HrReviewPanel | null }) {
  const { t } = useI18n()
  const [data, setData] = useState<NextHrAction | null | undefined>(undefined)
  const [recommendedFallback, setRecommendedFallback] = useState('')
  const [loading, setLoading] = useState(true)

  const showReviewFirst =
    hrReview &&
    !HR_REVIEW_TERMINAL.has(hrReview.status) &&
    Boolean(hrReview.next_required_action?.trim() || hrReview.blockers.length || !hrReview.can_approve)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const j = await getWorkEligibilityJourney(employeeId)
      setData(j.next_hr_action ?? null)
      setRecommendedFallback((j.recommended_next_action || '').trim())
    } catch {
      setData(null)
      setRecommendedFallback('')
    } finally {
      setLoading(false)
    }
  }, [employeeId])

  useEffect(() => {
    void load()
  }, [load])

  if (showReviewFirst && hrReview) {
    return <NextHrActionFromReview panel={hrReview} />
  }

  if (loading) {
    return (
      <div className="card border-indigo-100 bg-indigo-50/50 p-4">
        <div className="text-[10px] font-semibold uppercase tracking-wide text-indigo-800">
          {t('app.hr.employee_rail.next_hr_action', { defaultValue: 'Next HR action' })}
        </div>
        <p className="mt-2 text-xs text-slate-600">{t('common.loading', { defaultValue: 'Loading…' })}</p>
      </div>
    )
  }

  if (!data && !recommendedFallback) {
    return null
  }

  if (!data && recommendedFallback) {
    return (
      <div className="card border-indigo-100 bg-gradient-to-b from-indigo-50/90 to-white p-4 shadow-sm">
        <div className="text-[10px] font-semibold uppercase tracking-wide text-indigo-800">
          {t('app.hr.employee_rail.next_hr_action', { defaultValue: 'Next HR action' })}
        </div>
        <p className="mt-2 text-xs leading-relaxed text-slate-800">{recommendedFallback}</p>
        <div className="mt-3">
          <a href="#hr-employee-work-eligibility" className="btn-secondary btn-sm inline-flex">
            {t('app.hr.employee_rail.open_journey', { defaultValue: 'Open work eligibility' })}
          </a>
        </div>
      </div>
    )
  }

  if (!data) {
    return null
  }

  const cta = data.primary_cta
  const ctaHref = cta?.href || '#hr-employee-work-eligibility'

  return (
    <div className="card border-indigo-100 bg-gradient-to-b from-indigo-50/90 to-white p-4 shadow-sm">
      <div className="text-[10px] font-semibold uppercase tracking-wide text-indigo-800">
        {t('app.hr.employee_rail.next_hr_action', { defaultValue: 'Next HR action' })}
      </div>
      <h3 className="mt-2 text-sm font-semibold leading-snug text-slate-900">{data.title}</h3>
      {data.reason ? <p className="mt-2 text-xs leading-relaxed text-slate-700">{data.reason}</p> : null}
      {data.cannot_determine_reason ? (
        <p className="mt-1 text-[11px] font-medium text-amber-900">
          {t('app.hr.employee_rail.cannot_determine', {
            defaultValue: 'Needs data: {code}',
            values: { code: data.cannot_determine_reason.replace(/_/g, ' ') },
          })}
        </p>
      ) : null}
      {data.blockers?.length ? (
        <ul className="mt-2 list-inside list-disc text-[11px] text-rose-800">
          {data.blockers.map((b) => (
            <li key={b}>{b.replace(/_/g, ' ')}</li>
          ))}
        </ul>
      ) : null}
      {cta ? (
        <div className="mt-3">
          <a href={ctaHref} className="btn-primary btn-sm inline-flex">
            {cta.label}
          </a>
        </div>
      ) : (
        <div className="mt-3">
          <a href="#hr-employee-work-eligibility" className="btn-secondary btn-sm inline-flex">
            {t('app.hr.employee_rail.open_journey', { defaultValue: 'Open work eligibility' })}
          </a>
        </div>
      )}
      {data.secondary_ctas?.length ? (
        <ul className="mt-2 space-y-1 text-[11px] text-brand-800">
          {data.secondary_ctas.map((a) => (
            <li key={a.code}>
              <a className="font-medium hover:underline" href={a.href || '#hr-employee-work-eligibility'}>
                {a.label}
              </a>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}

function QuickActionsPanel() {
  const { t } = useI18n()
  const p = CRM_APP_PATHS
  return (
    <div className="card p-4">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {t('app.hr.employee_rail.quick_actions', { defaultValue: 'Quick actions' })}
      </div>
      <ul className="mt-2 space-y-2 text-sm">
        <li>
          <Link className="font-medium text-brand-700 hover:underline" to={p.hrTasks}>
            {t('app.hr.employee_rail.goto_tasks', { defaultValue: 'HR tasks' })}
          </Link>
        </li>
        <li>
          <Link className="font-medium text-brand-700 hover:underline" to={p.hrDocuments}>
            {t('app.hr.employee_rail.goto_hub', { defaultValue: 'Documents hub' })}
          </Link>
        </li>
        <li>
          <a className="font-medium text-brand-700 hover:underline" href={`#hr-employee-linked-documents`}>
            {t('app.hr.employee_rail.goto_docs', { defaultValue: 'Linked documents' })}
          </a>
        </li>
        <li>
          <Link className="font-medium text-brand-700 hover:underline" to={p.hrEmployees}>
            {t('app.hr.employee_rail.goto_directory', { defaultValue: 'Employee directory' })}
          </Link>
        </li>
      </ul>
    </div>
  )
}

export function HrEmployeeRightColumn({
  employeeId,
  profile,
  bundle,
  hrReview,
}: {
  employeeId: string
  profile: WorkforceEmployeeOperationalProfile
  bundle: WorkforceHrBundle
  hrReview?: HrReviewPanel | null
}) {
  return (
    <div className="flex flex-col gap-4">
      <NextHrActionPanel employeeId={employeeId} hrReview={hrReview} />
      <HrEmployeeOperationalRail
        summary={profile.operational_summary}
        zusRegistrationStatus={bundle.zus_profile?.registration_status}
        storedComplianceStatus={bundle.compliance_state?.status}
        onboardingOverdue={profile.onboarding_overdue_count}
      />
      <AlertsPanel alerts={profile.alerts} />
      <EmploymentPeek rows={profile.employment_operational} />
      <TimelinePanel events={profile.timeline} />
      <QuickActionsPanel />
    </div>
  )
}
