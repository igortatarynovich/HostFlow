import { formatDistanceToNow } from 'date-fns'
import { enUS, pl as plFns, ru as ruFns } from 'date-fns/locale'
import { IconAlertTriangle, IconCircleCheck } from '@tabler/icons-react'
import type { AcquisitionActivity } from '../../api/searchAcquisition'
import { useI18n, type LocaleCode } from '../../i18n'
import { acquisitionActivityStatusLabel } from '../../utils/searchWorkspaceI18n'

function dateFnsLocale(code: LocaleCode) {
  if (code === 'pl') return plFns
  if (code === 'ru') return ruFns
  return enUS
}

function statusTone(status: string, lifecycle?: string): string {
  if (lifecycle === 'paused') return 'border-slate-200 bg-slate-50/80'
  if (status === 'active') return 'border-emerald-200 bg-emerald-50/40'
  if (status === 'needs_attention') return 'border-amber-200 bg-amber-50/40'
  if (status === 'draft') return 'border-slate-200 bg-slate-50/60'
  return 'border-slate-200 bg-white'
}

type AcquisitionActivityCardProps = {
  activity: AcquisitionActivity
  highlighted?: boolean
  onPause: () => void
  onResume: () => void
  onDuplicate?: () => void
  onArchive: () => void
  onEditBindings?: () => void
  busy?: boolean
}

export function AcquisitionActivityCard({
  activity,
  highlighted,
  onPause,
  onResume,
  onDuplicate,
  onArchive,
  onEditBindings,
  busy,
}: AcquisitionActivityCardProps) {
  const { t, locale } = useI18n()
  const dfLocale = dateFnsLocale(locale)
  const week = activity.metrics?.period_7d ?? {}
  const lifecycle = activity.lifecycle || 'active'
  const actions = activity.actions ?? {}
  const lastSync = activity.last_sync_at
    ? formatDistanceToNow(new Date(activity.last_sync_at), { addSuffix: true, locale: dfLocale })
    : null

  const statusLabel = acquisitionActivityStatusLabel(activity, t)

  return (
    <article
      id={`activity-${activity.id}`}
      className={`rounded-xl border p-4 shadow-sm transition ${statusTone(activity.status, lifecycle)} ${
        highlighted ? 'ring-2 ring-brand-500' : ''
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-slate-900">{activity.name}</h3>
          <p className="mt-1 inline-flex items-center gap-1 text-sm text-slate-600">
            {activity.status === 'active' || activity.status === 'needs_attention' ? (
              <IconCircleCheck
                size={16}
                className={activity.status === 'needs_attention' ? 'text-amber-600' : 'text-emerald-600'}
              />
            ) : (
              <IconAlertTriangle size={16} className="text-slate-400" />
            )}
            {statusLabel}
          </p>
          {activity.search_titles && activity.search_titles.length > 0 ? (
            <div className="mt-2 text-sm text-slate-600">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                {t('app.acquisition.works_on')}
              </p>
              <ul className="mt-1 list-inside list-disc">
                {activity.search_titles.map((title) => (
                  <li key={title}>{title}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {lastSync ? (
            <p className="mt-2 text-xs text-slate-500">
              {t('app.acquisition.activity_last_sync', {
                
                values: { ago: lastSync } })}
            </p>
          ) : null}
        </div>
        {(activity.channel_type === 'meta' || activity.type === 'meta') && week.spend != null ? (
          <div className="text-right text-sm text-slate-600">
            <p>{t('app.acquisition.spend_7d', { values: { amount: Number(week.spend ?? 0).toFixed(0) } })}</p>
            {week.cpl != null ? <p className="text-xs">CPL €{week.cpl.toFixed(2)}</p> : null}
          </div>
        ) : null}
      </div>

      <div className="mt-4 flex flex-wrap gap-2 border-t border-slate-200/80 pt-4">
        {actions.open_meta && activity.meta_external_url ? (
          <a
            href={activity.meta_external_url}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            {t('app.acquisition.action_open_meta')}
          </a>
        ) : null}
        {actions.update_bindings && onEditBindings ? (
          <button
            type="button"
            disabled={busy}
            onClick={onEditBindings}
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            {t('app.acquisition.action_bindings')}
          </button>
        ) : null}
        {actions.pause ? (
          <button
            type="button"
            disabled={busy}
            onClick={onPause}
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            {t('app.acquisition.action_pause')}
          </button>
        ) : null}
        {actions.resume ? (
          <button
            type="button"
            disabled={busy}
            onClick={onResume}
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            {t('app.acquisition.action_resume')}
          </button>
        ) : null}
        {actions.duplicate && onDuplicate ? (
          <button
            type="button"
            disabled={busy}
            onClick={onDuplicate}
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            {t('app.acquisition.action_duplicate')}
          </button>
        ) : null}
        {actions.archive ? (
          <button
            type="button"
            disabled={busy}
            onClick={onArchive}
            className="rounded-lg border border-rose-200 bg-white px-3 py-2 text-sm font-medium text-rose-700 hover:bg-rose-50 disabled:opacity-50"
          >
            {t('app.acquisition.action_archive')}
          </button>
        ) : null}
        {activity.public_url ? (
          <a
            href={activity.public_url}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            {t('app.acquisition.action_open_link')}
          </a>
        ) : null}
      </div>
    </article>
  )
}
