import { Link } from 'react-router-dom'
import { IconAlertTriangle, IconCircleCheck } from '@tabler/icons-react'
import type { AcquisitionActivity } from '../../api/searchAcquisition'
import { useI18n } from '../../i18n'

type AcquisitionChannelCardProps = {
  channel: AcquisitionActivity
  metaHref?: string
}

function statusTone(status: string): string {
  if (status === 'active') return 'border-emerald-200 bg-emerald-50/40'
  if (status === 'needs_attention') return 'border-amber-200 bg-amber-50/40'
  if (status === 'draft') return 'border-slate-200 bg-slate-50/60'
  return 'border-slate-200 bg-white'
}

export function AcquisitionChannelCard({ channel, metaHref }: AcquisitionChannelCardProps) {
  const { t } = useI18n()
  const today = channel.metrics?.today ?? {}
  const week = channel.metrics?.period_7d ?? {}
  const funnel = channel.funnel ?? {}
  const responses = Number(today.responses ?? today.leads ?? week.responses ?? week.leads ?? 0)
  const spend = Number(week.spend ?? 0)
  const cpl = week.cpl ?? null

  const body = (
    <article className={`rounded-2xl border p-5 shadow-sm ${statusTone(channel.status)}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-slate-900">{channel.name}</h3>
          {channel.search_titles && channel.search_titles.length > 0 ? (
            <p className="mt-1 text-xs text-slate-500">
              {t('app.acquisition.works_on', { defaultValue: 'Работает на:' })}{' '}
              {channel.search_titles.join(' • ')}
            </p>
          ) : null}
          <p className="mt-1 inline-flex items-center gap-1 text-sm text-slate-600">
            {channel.status === 'active' || channel.status === 'needs_attention' ? (
              <IconCircleCheck size={16} className={channel.status === 'needs_attention' ? 'text-amber-600' : 'text-emerald-600'} />
            ) : (
              <IconAlertTriangle size={16} className="text-slate-400" />
            )}
            {channel.status_label ||
              t(`app.acquisition.status.${channel.status}`, { defaultValue: channel.status })}
          </p>
        </div>
      </div>

      {(channel.type === 'meta' || channel.type === 'public_link') && (
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <div className="rounded-xl bg-white/80 px-3 py-2 ring-1 ring-slate-100">
            <p className="text-xs text-slate-500">{t('app.acquisition.metric_responses', { defaultValue: 'Отклики (7д)' })}</p>
            <p className="text-lg font-semibold text-slate-900">{responses}</p>
          </div>
          {channel.type === 'meta' ? (
            <>
              <div className="rounded-xl bg-white/80 px-3 py-2 ring-1 ring-slate-100">
                <p className="text-xs text-slate-500">{t('app.acquisition.metric_spend', { defaultValue: 'Потрачено (7д)' })}</p>
                <p className="text-lg font-semibold text-slate-900">€{spend.toFixed(0)}</p>
              </div>
              <div className="rounded-xl bg-white/80 px-3 py-2 ring-1 ring-slate-100">
                <p className="text-xs text-slate-500">CPL</p>
                <p className="text-lg font-semibold text-slate-900">{cpl != null ? `€${cpl.toFixed(2)}` : '—'}</p>
              </div>
            </>
          ) : null}
        </div>
      )}

      {funnel.leads != null && channel.type === 'meta' ? (
        <div className="mt-4 rounded-xl bg-white/70 px-4 py-3 text-sm text-slate-700 ring-1 ring-slate-100">
          <p className="font-medium text-slate-900">{t('app.acquisition.funnel_title', { defaultValue: 'Путь до результата' })}</p>
          <p className="mt-2 leading-relaxed">
            {funnel.leads ?? 0} {t('app.acquisition.funnel_leads', { defaultValue: 'лидов' })} →{' '}
            {funnel.candidates ?? 0} {t('app.acquisition.funnel_candidates', { defaultValue: 'кандидатов' })} →{' '}
            {funnel.interviews ?? 0} {t('app.acquisition.funnel_interviews', { defaultValue: 'интервью' })} →{' '}
            {funnel.offers ?? 0} {t('app.acquisition.funnel_offers', { defaultValue: 'офферов' })} →{' '}
            {funnel.hired ?? 0} {t('app.acquisition.funnel_hired', { defaultValue: 'трудоустроены' })}
            {funnel.cost_per_hire != null ? (
              <span className="mt-1 block text-slate-600">
                {t('app.acquisition.cost_per_hire', {
                  defaultValue: 'Стоимость одного сотрудника €{amount}',
                  values: { amount: funnel.cost_per_hire },
                })}
              </span>
            ) : null}
          </p>
        </div>
      ) : null}

      {channel.next_action?.title ? (
        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
          <span className="font-medium">{t('app.acquisition.next_action', { defaultValue: 'Следующее действие' })}:</span>{' '}
          {channel.next_action.title}
        </div>
      ) : null}

      {channel.type === 'meta' && metaHref ? (
        <div className="mt-4 flex flex-wrap gap-2">
          <span className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700">
            {t('app.acquisition.action_view', { defaultValue: 'Посмотреть рекламу' })}
          </span>
          <span className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-500">
            {t('app.acquisition.action_edit_soon', { defaultValue: 'Изменить — скоро' })}
          </span>
        </div>
      ) : null}
    </article>
  )

  if (metaHref) {
    return (
      <Link to={metaHref} className="block transition hover:opacity-95">
        {body}
      </Link>
    )
  }

  return body
}
