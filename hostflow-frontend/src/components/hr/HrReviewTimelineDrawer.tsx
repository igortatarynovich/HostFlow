import type { HrReviewPanel, WorkforceProfileAlert, WorkforceTimelineEvent } from '../../api/workforce'
import { useI18n } from '../../i18n'

type Props = {
  open: boolean
  onClose: () => void
  panel: HrReviewPanel
  profileTimeline?: WorkforceTimelineEvent[]
  profileAlerts?: WorkforceProfileAlert[]
}

export default function HrReviewTimelineDrawer({ open, onClose, panel, profileTimeline, profileAlerts }: Props) {
  const { t } = useI18n()
  if (!open) return null

  const events = [
    ...(panel.recent_timeline ?? []).map((e) => ({ at: e.at, label: e.label })),
    ...(profileTimeline ?? []).map((e) => ({
      at: e.occurred_at,
      label: e.title || e.kind,
    })),
  ]

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/30" role="dialog" aria-modal onClick={onClose}>
      <div
        className="h-full w-full max-w-md overflow-y-auto bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <h2 className="text-sm font-semibold text-slate-900">
            {t('app.hr.review_case.full_history', { defaultValue: 'Full history' })}
          </h2>
          <button type="button" className="text-sm text-slate-600 hover:text-slate-900" onClick={onClose}>
            {t('common.actions.close', { defaultValue: 'Close' })}
          </button>
        </div>
        <ul className="divide-y divide-slate-100 p-4 text-sm">
          {events.length === 0 ? (
            <li className="text-slate-500">{t('app.hr.review_case.no_events', { defaultValue: 'No events yet.' })}</li>
          ) : (
            events.map((ev, i) => (
              <li key={i} className="py-2">
                <div className="font-medium text-slate-900">{ev.label}</div>
                {ev.at ? <div className="text-xs text-slate-500">{ev.at}</div> : null}
              </li>
            ))
          )}
        </ul>
        {profileAlerts && profileAlerts.length > 0 ? (
          <div className="border-t border-slate-200 p-4">
            <h3 className="text-xs font-bold uppercase text-slate-500">
              {t('app.hr.employee_rail.alerts', { defaultValue: 'Alerts' })}
            </h3>
            <ul className="mt-2 space-y-1 text-xs">
              {profileAlerts.map((a, i) => (
                <li key={i}>{String(a.message || a.code || '—')}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </div>
  )
}
