import { Link } from 'react-router-dom'

import type { Dispatch, SetStateAction } from 'react'

import { leadsNextActionHref } from '../../api/nextActions'
import type { LeadConversionFunnelResponse } from '../../api/leadConversionFunnel'
import type { LeadStage } from '../../api/types'
import { useI18n } from '../../i18n'

export type LeadFunnelSliceDraft = {
  source: string
  vacancyId: string
  funnelId: string
  assigneeUserId: string
}

type Props = {
  data: LeadConversionFunnelResponse | null
  /** Team NBA tier unlocks slice filters on the API. */
  teamTierSlices: boolean
  funnelSliceDraft: LeadFunnelSliceDraft
  setFunnelSliceDraft: Dispatch<SetStateAction<LeadFunnelSliceDraft>>
  onApplySlices: () => void
  onClearSlices: () => void
  stageLabels: Record<string, string>
  /** `compact` matches Leads inbox strip; `vertical` is the full analytics layout (§2.12). */
  layout?: 'compact' | 'vertical'
}

export default function LeadConversionFunnelPanel({
  data: leadConversionFunnel,
  teamTierSlices,
  funnelSliceDraft,
  setFunnelSliceDraft,
  onApplySlices,
  onClearSlices,
  stageLabels,
  layout = 'compact',
}: Props) {
  const { t } = useI18n()

  if (!leadConversionFunnel || leadConversionFunnel.stages.length === 0) {
    return null
  }

  const slicesSection = (
    <div className="mb-2 max-w-3xl rounded-lg border border-dashed border-slate-200 bg-slate-50/80 px-2 py-1.5">
      <div className="mb-1 text-[10px] font-medium text-slate-600">
        {t('app.leads.conversion_funnel.slices_title')}
      </div>
      {!teamTierSlices ? (
        <p className="text-[10px] text-slate-500">{t('app.leads.conversion_funnel.slices_team_hint')}</p>
      ) : (
        <>
          <div className="flex flex-wrap gap-2">
            <label className="flex min-w-[100px] flex-1 flex-col text-[9px] font-medium text-slate-600">
              {t('app.leads.conversion_funnel.slice_source')}
              <input
                className="input mt-0.5 h-7 rounded border-slate-300 px-1.5 text-[10px]"
                value={funnelSliceDraft.source}
                onChange={(e) => setFunnelSliceDraft((d) => ({ ...d, source: e.target.value }))}
                placeholder="meta"
                autoComplete="off"
              />
            </label>
            <label className="flex min-w-[120px] flex-1 flex-col text-[9px] font-medium text-slate-600">
              {t('app.leads.conversion_funnel.slice_vacancy_id')}
              <input
                className="input mt-0.5 h-7 rounded border-slate-300 px-1.5 font-mono text-[10px]"
                value={funnelSliceDraft.vacancyId}
                onChange={(e) => setFunnelSliceDraft((d) => ({ ...d, vacancyId: e.target.value }))}
                placeholder="UUID"
                autoComplete="off"
              />
            </label>
            <label className="flex min-w-[120px] flex-1 flex-col text-[9px] font-medium text-slate-600">
              {t('app.leads.conversion_funnel.slice_funnel_id')}
              <input
                className="input mt-0.5 h-7 rounded border-slate-300 px-1.5 font-mono text-[10px]"
                value={funnelSliceDraft.funnelId}
                onChange={(e) => setFunnelSliceDraft((d) => ({ ...d, funnelId: e.target.value }))}
                placeholder="UUID"
                autoComplete="off"
              />
            </label>
            <label className="flex min-w-[120px] flex-1 flex-col text-[9px] font-medium text-slate-600">
              {t('app.leads.conversion_funnel.slice_assignee')}
              <input
                className="input mt-0.5 h-7 rounded border-slate-300 px-1.5 font-mono text-[10px]"
                value={funnelSliceDraft.assigneeUserId}
                onChange={(e) => setFunnelSliceDraft((d) => ({ ...d, assigneeUserId: e.target.value }))}
                placeholder="User UUID"
                autoComplete="off"
              />
            </label>
          </div>
          <div className="mt-1.5 flex flex-wrap gap-2">
            <button type="button" className="btn-secondary h-7 rounded px-2 text-[10px]" onClick={() => onApplySlices()}>
              {t('app.leads.conversion_funnel.slices_apply')}
            </button>
            <button type="button" className="btn-secondary h-7 rounded px-2 text-[10px]" onClick={() => onClearSlices()}>
              {t('app.leads.conversion_funnel.slices_clear')}
            </button>
          </div>
        </>
      )}
      {leadConversionFunnel &&
      (leadConversionFunnel.filter_source ||
        leadConversionFunnel.filter_vacancy_id ||
        leadConversionFunnel.filter_funnel_id ||
        leadConversionFunnel.filter_assignee_user_id) ? (
        <div className="mt-1.5 text-[9px] text-slate-600">
          <span className="font-medium">{t('app.leads.conversion_funnel.slices_active')}:</span>{' '}
          {[
            leadConversionFunnel.filter_source
              ? `${t('app.leads.conversion_funnel.slice_source')}=${leadConversionFunnel.filter_source}`
              : null,
            leadConversionFunnel.filter_vacancy_id
              ? `${t('app.leads.conversion_funnel.slice_vacancy_id')}=${leadConversionFunnel.filter_vacancy_id}`
              : null,
            leadConversionFunnel.filter_funnel_id
              ? `${t('app.leads.conversion_funnel.slice_funnel_id')}=${leadConversionFunnel.filter_funnel_id}`
              : null,
            leadConversionFunnel.filter_assignee_user_id
              ? `${t('app.leads.conversion_funnel.slice_assignee')}=${leadConversionFunnel.filter_assignee_user_id}`
              : null,
          ]
            .filter(Boolean)
            .join(' · ')}
        </div>
      ) : null}
    </div>
  )

  const summaryRow = (
    <div className="flex flex-wrap items-end gap-1 text-[11px] text-slate-700">
      {leadConversionFunnel.status_new_count > 0 ? (
        <div className="mb-1 rounded-md border border-amber-200/80 bg-amber-50/90 px-2 py-1 tabular-nums">
          <Link to={leadsNextActionHref({ status: 'new' })} className="font-medium text-amber-900 hover:underline">
            {t('app.leads.conversion_funnel.new_status')}: {leadConversionFunnel.status_new_count}
          </Link>
        </div>
      ) : null}
      {leadConversionFunnel.lost_processed_count > 0 ? (
        <div className="mb-1 rounded-md border border-slate-200 bg-slate-50 px-2 py-1 tabular-nums">
          <Link
            to={leadsNextActionHref({ status: 'processed', stage: 'lost' })}
            className="font-medium text-slate-800 hover:underline"
          >
            {t('app.leads.conversion_funnel.lost')}: {leadConversionFunnel.lost_processed_count}
          </Link>
          {(leadConversionFunnel.lost_dwell_sample_size ?? 0) > 0 && leadConversionFunnel.lost_dwell_avg_days != null ? (
            <div className="mt-0.5 text-[9px] font-normal text-slate-500">
              {t('app.leads.conversion_funnel.dwell_line', {
                values: {
                  avg: leadConversionFunnel.lost_dwell_avg_days,
                  p50: leadConversionFunnel.lost_dwell_p50_days ?? '—',
                },
              })}
            </div>
          ) : null}
        </div>
      ) : null}
      {leadConversionFunnel.lost_from_stage && leadConversionFunnel.lost_from_stage.length > 0 ? (
        <div className="mb-1 mt-1 w-full max-w-xl rounded-md border border-slate-200 bg-white px-2 py-1.5">
          <div className="text-[9px] font-medium uppercase tracking-wide text-slate-500">
            {t('app.leads.conversion_funnel.lost_from_title')}
          </div>
          <p className="mb-1 text-[9px] text-slate-500">{t('app.leads.conversion_funnel.lost_from_hint')}</p>
          <ul className="space-y-0.5 text-[10px] text-slate-700">
            {leadConversionFunnel.lost_from_stage.map((row) => (
              <li key={row.from_stage} className="flex justify-between gap-2 tabular-nums">
                <span>
                  <span className="font-medium text-slate-800">
                    {stageLabels[row.from_stage as LeadStage] ?? row.from_stage}
                  </span>
                  <span className="text-slate-500"> → {t('app.leads.stages.lost')}</span>
                </span>
                <Link
                  to={leadsNextActionHref({
                    status: 'processed',
                    stage: 'lost',
                    lost_from_crm_stage: row.from_stage.trim().toLowerCase(),
                  })}
                  className="shrink-0 text-brand-700 hover:underline"
                >
                  {row.lead_count}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {leadConversionFunnel.lost_reason_breakdown && leadConversionFunnel.lost_reason_breakdown.length > 0 ? (
        <div className="mb-1 mt-1 w-full max-w-xl rounded-md border border-slate-200 bg-white px-2 py-1.5">
          <div className="text-[9px] font-medium uppercase tracking-wide text-slate-500">
            {t('app.leads.conversion_funnel.lost_reason_title')}
          </div>
          <p className="mb-1 text-[9px] text-slate-500">{t('app.leads.conversion_funnel.lost_reason_hint')}</p>
          <ul className="space-y-0.5 text-[10px] text-slate-700">
            {leadConversionFunnel.lost_reason_breakdown.map((row) => (
              <li key={row.reason_code} className="flex justify-between gap-2 tabular-nums">
                <span className="font-medium text-slate-800">{t(`app.leads.lost_reason.codes.${row.reason_code}`)}</span>
                <Link
                  to={leadsNextActionHref(
                    row.reason_code === 'unknown'
                      ? { status: 'processed', stage: 'lost' }
                      : { status: 'processed', stage: 'lost', lost_reason_code: row.reason_code },
                  )}
                  className="shrink-0 text-brand-700 hover:underline"
                >
                  {row.lead_count}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  )

  const maxCount = Math.max(1, ...leadConversionFunnel.stages.map((s) => s.count))

  const stagesCompact = (
    <div className="mt-1 flex flex-wrap items-end gap-x-1 gap-y-2">
      {leadConversionFunnel.stages.map((s, idx) => {
        const barW = Math.max(52, Math.round(52 + (s.count / maxCount) * 76))
        const edge = leadConversionFunnel.edges[idx]
        return (
          <div key={s.stage} className="flex items-end gap-x-0.5">
            <div className="flex flex-col items-center gap-0.5">
              <div
                className="flex min-h-[52px] items-end justify-center rounded-md border border-slate-200 bg-gradient-to-t from-brand-600/90 to-brand-500/80 px-1.5 pb-1 pt-2 shadow-sm"
                style={{ width: barW }}
              >
                <Link
                  to={leadsNextActionHref({
                    status: 'processed',
                    conversion_root: s.stage,
                  })}
                  className="w-full text-center text-[10px] font-semibold leading-tight text-white hover:underline"
                >
                  {s.count}
                </Link>
              </div>
              <div className="max-w-[96px] text-center text-[10px] font-medium text-slate-700">
                {stageLabels[s.stage] ?? s.stage}
              </div>
              {(s.dwell_sample_size ?? 0) > 0 && s.dwell_avg_days != null ? (
                <div className="max-w-[104px] text-center text-[9px] leading-tight text-slate-500">
                  {t('app.leads.conversion_funnel.dwell_line', {
                    values: { avg: s.dwell_avg_days, p50: s.dwell_p50_days ?? '—' },
                  })}
                </div>
              ) : null}
            </div>
            {edge ? (
              <div className="mb-6 px-0.5 text-[9px] font-medium tabular-nums text-slate-500">
                → {edge.progressed_share != null ? `${Math.round(edge.progressed_share * 100)}%` : '—'}
              </div>
            ) : null}
          </div>
        )
      })}
    </div>
  )

  const stagesVertical = (
    <div className="mt-4 space-y-1">
      {leadConversionFunnel.stages.map((s, idx) => {
        const edge = leadConversionFunnel.edges[idx]
        const hPct = Math.max(8, Math.round((s.count / maxCount) * 100))
        const atBeyond = s.at_or_beyond
        const dropOff =
          idx < leadConversionFunnel.stages.length - 1
            ? Math.max(0, atBeyond - (leadConversionFunnel.stages[idx + 1]?.at_or_beyond ?? 0))
            : null
        return (
          <div key={s.stage}>
            <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:items-stretch">
              <div className="min-w-0 flex-1 space-y-1">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {stageLabels[s.stage] ?? s.stage}
                </div>
                <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                  <span className="text-3xl font-bold tabular-nums text-slate-900">{s.count}</span>
                  <span className="text-xs text-slate-500">
                    {t('app.analytics.lead_conversion.at_or_beyond', { values: { n: atBeyond } })}
                  </span>
                  {dropOff != null && dropOff > 0 ? (
                    <span className="text-xs text-rose-700">
                      {t('app.analytics.lead_conversion.drop_off', { values: { n: dropOff } })}
                    </span>
                  ) : null}
                </div>
                {(s.dwell_sample_size ?? 0) > 0 && s.dwell_avg_days != null ? (
                  <p className="text-xs text-slate-600">
                    {t('app.leads.conversion_funnel.dwell_line', {
                      values: { avg: s.dwell_avg_days, p50: s.dwell_p50_days ?? '—' },
                    })}
                  </p>
                ) : (
                  <p className="text-xs text-slate-400">{t('app.analytics.lead_conversion.dwell_empty')}</p>
                )}
                <Link
                  to={leadsNextActionHref({ status: 'processed', conversion_root: s.stage })}
                  className="inline-flex text-sm font-medium text-brand-700 hover:underline"
                >
                  {t('app.analytics.lead_conversion.open_leads')}
                </Link>
              </div>
              <div className="flex w-full shrink-0 flex-col items-center justify-end sm:w-28">
                <div
                  className="w-full max-w-[120px] rounded-t-md bg-gradient-to-t from-brand-600 to-brand-500 shadow-inner transition-all"
                  style={{ height: `${Math.min(160, 40 + hPct * 1.2)}px` }}
                  title={`${s.count}`}
                />
              </div>
            </div>
            {edge ? (
              <div className="flex justify-center py-2">
                <div className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-600">
                  {t('app.analytics.lead_conversion.step_conversion', {
                    values: {
                      pct: edge.progressed_share != null ? Math.round(edge.progressed_share * 100) : '—',
                    },
                  })}
                </div>
              </div>
            ) : null}
          </div>
        )
      })}
    </div>
  )

  return (
    <div className={layout === 'vertical' ? 'space-y-4' : 'mt-2'}>
      {layout === 'compact' ? (
        <div className="mb-1 text-[10px] font-medium uppercase tracking-wide text-slate-400">
          {t('app.leads.conversion_funnel.title')}
        </div>
      ) : null}
      {layout === 'compact' ? (
        <p className="mb-1.5 max-w-3xl text-[10px] leading-snug text-slate-500">{t('app.leads.conversion_funnel.hint')}</p>
      ) : null}
      {slicesSection}
      {summaryRow}
      {layout === 'vertical' ? stagesVertical : stagesCompact}
    </div>
  )
}
