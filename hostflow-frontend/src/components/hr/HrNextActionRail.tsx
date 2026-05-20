import { useState } from 'react'
import { Link } from 'react-router-dom'
import clsx from 'clsx'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import type { HrReviewPanel, WorkforceProfileAlert, WorkforceTimelineEvent } from '../../api/workforce'
import { useI18n } from '../../i18n'
import HrReviewTimelineDrawer from './HrReviewTimelineDrawer'

type Props = {
  panel: HrReviewPanel
  employeeId?: string
  profileAlerts?: WorkforceProfileAlert[]
  profileTimeline?: WorkforceTimelineEvent[]
  onScrollTo?: (anchor: string) => void
}

function AnchorButton({
  label,
  anchor,
  onScrollTo,
}: {
  label: string
  anchor?: string | null
  onScrollTo?: (anchor: string) => void
}) {
  if (!anchor) return null
  const href = anchor.startsWith('#') ? anchor : `#${anchor}`
  return (
    <button
      type="button"
      className="btn-primary btn-sm w-full"
      onClick={() => {
        if (onScrollTo) onScrollTo(href)
        else document.querySelector(href)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }}
    >
      {label}
    </button>
  )
}

export default function HrNextActionRail({ panel, employeeId, profileAlerts, profileTimeline, onScrollTo }: Props) {
  const { t } = useI18n()
  const [historyOpen, setHistoryOpen] = useState(false)
  const na = panel.next_action
  const readiness = panel.decision_readiness
  const blockers = na?.blockers?.length ? na.blockers : panel.blockers
  const timeline = panel.recent_timeline ?? []

  return (
    <aside className="space-y-4 xl:sticky xl:top-4">
      <div className="card border-2 border-brand-200 bg-gradient-to-b from-brand-50/80 to-white p-4">
        <h2 className="text-xs font-bold uppercase tracking-wide text-brand-900">
          {t('app.hr.review_case.next_action', { defaultValue: 'Next HR action' })}
        </h2>
        <p className="mt-2 text-sm font-semibold text-slate-900">
          {na?.title || panel.next_required_action || t('app.hr.review_case.continue_review', { defaultValue: 'Continue HR review' })}
        </p>
        {na?.reason ? <p className="mt-1 text-xs text-slate-600">{na.reason}</p> : null}
        <div className="mt-3 space-y-2">
          <AnchorButton
            label={na?.primary_label || t('app.hr.doc_flow.continue_verify', { defaultValue: 'Continue verification' })}
            anchor={na?.primary_anchor || '#hr-document-verification'}
            onScrollTo={onScrollTo}
          />
          {na?.secondary_label && na.secondary_anchor ? (
            <button
              type="button"
              className="btn-secondary btn-sm w-full"
              onClick={() => onScrollTo?.(na.secondary_anchor!)}
            >
              {na.secondary_label}
            </button>
          ) : null}
        </div>
      </div>

      {blockers.length > 0 ? (
        <div className="card p-4">
          <h3 className="text-xs font-bold uppercase tracking-wide text-rose-800">
            {t('app.hr.review_case.critical_blockers', { defaultValue: 'Critical blockers' })}
          </h3>
          <p className="mt-2 text-xs text-slate-800">{blockers[0]?.replace(/_/g, ' ')}</p>
          {blockers.length > 1 ? (
            <p className="mt-1 text-[11px] text-slate-500">+{blockers.length - 1} more in checklist</p>
          ) : null}
        </div>
      ) : null}

      {readiness ? (
        <div className="card p-4">
          <h3 className="text-xs font-bold uppercase tracking-wide text-slate-600">
            {t('app.hr.review_case.decision_readiness', { defaultValue: 'Decision readiness' })}
          </h3>
          {readiness.data_verification_total != null && readiness.data_verification_total > 0 ? (
            <p className="mt-2 text-sm font-medium text-slate-900">
              {t('app.hr.review_case.documents_progress', {
                defaultValue: 'Documents: confirm each in the verification workspace',
              })}
            </p>
          ) : (
            <p className="mt-2 text-sm font-medium text-slate-900">
              {t('app.hr.review_case.checklist_progress', {
                defaultValue: 'Checklist: {done}/{total}',
                values: { done: readiness.checklist_done, total: readiness.checklist_total },
              })}
            </p>
          )}
          {readiness.identity_status ? (
            <p className="mt-1 text-xs text-slate-600">Identity: {readiness.identity_status}</p>
          ) : null}
          <p
            className={clsx(
              'mt-1 text-xs font-semibold',
              readiness.can_approve ? 'text-emerald-800' : 'text-amber-900',
            )}
          >
            {readiness.can_approve
              ? t('app.hr.review_case.approve_yes', { defaultValue: 'Approve allowed' })
              : t('app.hr.review_case.approve_no', { defaultValue: 'Approve blocked' })}
          </p>
          {!readiness.can_approve && readiness.approve_blocked_reason ? (
            <p className="mt-1 text-xs text-slate-600">{readiness.approve_blocked_reason}</p>
          ) : null}
          {readiness.post_approve_effects && readiness.post_approve_effects.length > 0 ? (
            <ul className="mt-2 list-inside list-disc text-[11px] text-slate-600">
              {readiness.post_approve_effects.map((e) => (
                <li key={e}>{e}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      <div className="card p-4">
        <h3 className="text-xs font-bold uppercase tracking-wide text-slate-600">
          {t('app.hr.review_case.quick_actions', { defaultValue: 'Quick actions' })}
        </h3>
        <ul className="mt-2 space-y-1 text-sm">
          <li>
            <button type="button" className="text-brand-700 hover:underline" onClick={() => onScrollTo?.('#hr-document-verification')}>
              {t('app.hr.review.open_docs', { defaultValue: 'Open documents' })}
            </button>
          </li>
          <li>
            <button type="button" className="text-brand-700 hover:underline" onClick={() => onScrollTo?.('#hr-review-eligibility')}>
              {t('app.hr.review_case.open_eligibility', { defaultValue: 'Open work eligibility' })}
            </button>
          </li>
          {employeeId ? (
            <li>
              <Link className="text-brand-700 hover:underline" to={CRM_APP_PATHS.hrDocuments}>
                {t('app.nav.hr.inbox.quick_hub', { defaultValue: 'Documents hub' })}
              </Link>
            </li>
          ) : null}
        </ul>
      </div>

      <div className="card p-4">
        <h3 className="text-xs font-bold uppercase tracking-wide text-slate-600">
          {t('app.hr.review_case.recent_history', { defaultValue: 'Recent history' })}
        </h3>
        {timeline.length === 0 && (!profileTimeline || profileTimeline.length === 0) ? (
          <p className="mt-2 text-xs text-slate-500">{t('app.hr.review_case.no_events', { defaultValue: 'No events yet.' })}</p>
        ) : (
          <ul className="mt-2 space-y-1 text-xs text-slate-700">
            {(timeline.length ? timeline : (profileTimeline ?? []).slice(0, 3).map((e) => ({
              at: e.occurred_at,
              kind: e.kind,
              label: e.title || e.kind,
            }))).map((ev, i) => (
              <li key={`${ev.kind}-${i}`}>{ev.label}</li>
            ))}
          </ul>
        )}
        <button type="button" className="mt-2 text-xs font-medium text-brand-700 hover:underline" onClick={() => setHistoryOpen(true)}>
          {t('app.hr.review_case.full_history', { defaultValue: 'Open full history' })}
        </button>
      </div>

      <HrReviewTimelineDrawer
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        panel={panel}
        profileTimeline={profileTimeline}
        profileAlerts={profileAlerts}
      />
    </aside>
  )
}
