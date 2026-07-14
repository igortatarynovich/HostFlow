import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

import type { Lead } from '../api/types'
import LeadIntakeCandidateSnapshot, { LeadIntakeRecruitmentContextBlock } from '../components/leads/LeadIntakeCandidateSnapshot'
import LeadIntakeDecisionRail from '../components/leads/LeadIntakeDecisionRail'
import LeadQualificationSummaryCard from '../components/leads/LeadQualificationSummaryCard'
import { CRM_APP_PATHS } from '../app/crmAppPaths'

export type LeadDetailTimelineItem = {
  at: string
  kind: string
  source: string
  title?: string | null
  description?: string | null
}

function str(v: unknown): string | null {
  if (v == null) return null
  const s = String(v).trim()
  return s || null
}

function formatUtm(utm: unknown): string | null {
  if (!utm || typeof utm !== 'object' || Array.isArray(utm)) return null
  const parts: string[] = []
  for (const [k, val] of Object.entries(utm as Record<string, unknown>)) {
    if (val == null) continue
    const s = String(val).trim()
    if (s) parts.push(`${k}: ${s}`)
  }
  return parts.length ? parts.join(' · ') : null
}

type TFn = (key: string, opts?: { defaultValue?: string; values?: Record<string, string | number> }) => string

export type RecruitmentAgencyIntakeDetailViewProps = {
  lead: Lead
  leadDisplayName: string
  normalized: Record<string, unknown>
  companyLabel: string
  vacancyLabel: string
  intakeNote: string | null
  formatDateValue: (iso: string | null | undefined) => string
  locale: string
  t: TFn
  processing: boolean
  routingConfirming: boolean
  poolBusy: boolean
  onLeadUpdated: (l: Lead) => void
  onRequestProcess: () => void
  onConfirmRouting: (vacancyId: string, thenProcess: boolean) => void
  onPool: () => void
  timelineItems: LeadDetailTimelineItem[]
  timelineLoading: boolean
  timelineError: string | null
}

export function RecruitmentAgencyIntakeDetailView({
  lead,
  leadDisplayName,
  normalized: n,
  companyLabel,
  vacancyLabel,
  intakeNote,
  formatDateValue,
  locale,
  t,
  processing,
  routingConfirming,
  poolBusy,
  onLeadUpdated,
  onRequestProcess,
  onConfirmRouting,
  onPool,
  timelineItems,
  timelineLoading,
  timelineError,
}: RecruitmentAgencyIntakeDetailViewProps) {
  const name = str(n.full_name) || `${str(n.first_name) || ''} ${str(n.last_name) || ''}`.trim() || leadDisplayName
  const dupLine =
    String(lead.status || '').toLowerCase() === 'duplicate_review'
      ? t('app.leads.intake_workspace.snapshot.duplicate_review_active')
      : t('app.leads.intake_workspace.snapshot.duplicate_clear')

  const campaign = formatUtm(n.utm)
  const routeLine = lead.vacancy_routing_confirmed
    ? t('app.leads.intake_workspace.snapshot.route_confirmed')
    : lead.vacancy_id || lead.vacancy_title
      ? t('app.leads.intake_workspace.snapshot.route_unconfirmed')
      : t('app.leads.intake_workspace.snapshot.route_missing')

  return (
    <div className="grid grid-cols-1 items-start gap-8 lg:grid-cols-[minmax(0,65fr)_minmax(280px,35fr)] lg:gap-10">
      <div className="space-y-8">
        <LeadIntakeCandidateSnapshot lead={lead} anchorName={name} />

        <LeadIntakeRecruitmentContextBlock
          lead={lead}
          companyLabel={companyLabel}
          vacancyLabel={vacancyLabel}
          duplicateLine={dupLine}
          routeLine={routeLine}
          campaignLine={campaign}
          createdLabel={formatDateValue(lead.created_at)}
        />

        {intakeNote ? (
          <section className="rounded-xl bg-slate-500/[0.06] px-4 py-3">
            <h2 className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500">{t('app.leads.intake_workspace.detail.notes_heading')}</h2>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-slate-800">{intakeNote}</p>
          </section>
        ) : null}

        <details className="group rounded-xl bg-slate-500/[0.04]">
          <summary className="cursor-pointer list-none px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500 marker:content-none [&::-webkit-details-marker]:hidden">
            {t('app.leads.intake_workspace.snapshot.qual_toggle')}
          </summary>
          <div className="border-t border-slate-200/60 px-4 py-3">
            <LeadQualificationSummaryCard lead={lead} isServicesTenant={false} formatAt={(iso) => formatDateValue(iso, locale)} />
          </div>
        </details>
      </div>

      <div className="flex flex-col gap-6 lg:sticky lg:top-4 lg:self-start">
        <LeadIntakeDecisionRail
          lead={lead}
          processing={processing}
          routingBusy={routingConfirming}
          poolBusy={poolBusy}
          onLeadUpdated={onLeadUpdated}
          onRequestProcess={onRequestProcess}
          onConfirmRouting={onConfirmRouting}
          onPool={onPool}
        />

        {lead.recruiter_id ? (
          <p className="text-[11px] text-slate-500">
            {t('app.leads.intake_workspace.owner')}: <span className="font-mono text-slate-700">{lead.recruiter_id}</span>
          </p>
        ) : null}

        <details className="overflow-hidden rounded-xl bg-slate-500/[0.04]">
          <summary className="cursor-pointer list-none px-4 py-3 text-[10px] font-bold uppercase tracking-wide text-slate-500 marker:content-none [&::-webkit-details-marker]:hidden">
            {t('app.leads.intake_workspace.audit.history')}
          </summary>
          <div className="border-t border-slate-200/60 px-4 py-3">
            {timelineLoading && <p className="text-sm text-slate-500">{t('common.loading')}</p>}
            {timelineError && <p className="text-sm text-rose-600">{timelineError}</p>}
            {!timelineLoading && !timelineError && timelineItems.length === 0 && (
              <p className="text-sm text-slate-500">{t('app.leads.detail.timeline_empty')}</p>
            )}
            {!timelineLoading && timelineItems.length > 0 && (
              <ul className="space-y-3 border-l-2 border-slate-200 pl-4">
                {timelineItems.map((item, idx) => (
                  <li key={`${item.at}-${item.kind}-${idx}`} className="relative">
                    <span className="absolute -left-[calc(0.5rem+2px)] top-2 h-2 w-2 rounded-full bg-brand-500" aria-hidden />
                    <div className="text-xs text-slate-500">{formatDateValue(item.at, locale)}</div>
                    <div className="text-sm font-medium text-slate-900">{item.title || item.kind || '—'}</div>
                    {item.description ? <div className="text-sm text-slate-600">{item.description}</div> : null}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </details>
      </div>
    </div>
  )
}

export type RecruitmentAgencyAuditDetailViewProps = {
  lead: Lead
  leadDisplayName: string
  normalized: Record<string, unknown>
  companyLabel: string
  vacancyLabel: string
  formatDateValue: (iso: string | null | undefined) => string
  locale: string
  t: TFn
  timelineItems: LeadDetailTimelineItem[]
  timelineLoading: boolean
  timelineError: string | null
  /** Ingest, meta, stage controls, delete — folded away from the tiny receipt. */
  auditDiagnostics?: ReactNode
}

export function RecruitmentAgencyAuditDetailView({
  lead,
  normalized: _n,
  companyLabel: _companyLabel,
  vacancyLabel,
  formatDateValue,
  locale,
  t,
  timelineItems,
  timelineLoading,
  timelineError,
  auditDiagnostics,
}: RecruitmentAgencyAuditDetailViewProps) {
  const routeLine = lead.vacancy_routing_confirmed
    ? t('app.leads.intake_workspace.snapshot.route_confirmed')
    : t('app.leads.intake_workspace.snapshot.route_unconfirmed')

  const receiptRows: Array<{ k: string; label: string; value: ReactNode }> = [
    { k: 'vac', label: vacancyLabel, value: lead.vacancy_title || lead.vacancy_id || '—' },
    { k: 'src', label: t('app.leads.intake_workspace.audit.created_from'), value: lead.source || '—' },
    {
      k: 'rec',
      label: t('app.leads.table.manager'),
      value: lead.recruiter_id ? <span className="font-mono text-xs">{lead.recruiter_id}</span> : '—',
    },
    { k: 'at', label: t('app.leads.table.created'), value: formatDateValue(lead.created_at) },
  ]

  const timelineBlock = (
    <div className="space-y-2">
      <h3 className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-500">{t('app.leads.intake_workspace.audit.history')}</h3>
      {timelineLoading && <p className="text-sm text-slate-500">{t('common.loading')}</p>}
      {timelineError && <p className="text-sm text-rose-600">{timelineError}</p>}
      {!timelineLoading && !timelineError && timelineItems.length === 0 && (
        <p className="text-sm text-slate-500">{t('app.leads.detail.timeline_empty')}</p>
      )}
      {!timelineLoading && timelineItems.length > 0 && (
        <ul className="space-y-2 border-l-2 border-slate-200 pl-3">
          {timelineItems.map((item, idx) => (
            <li key={`${item.at}-${item.kind}-${idx}`} className="relative">
              <span className="absolute -left-[calc(0.75rem+2px)] top-2 h-1.5 w-1.5 rounded-full bg-slate-400" aria-hidden />
              <div className="text-[11px] text-slate-500">{formatDateValue(item.at, locale)}</div>
              <div className="text-sm font-medium text-slate-900">{item.title || item.kind || '—'}</div>
              {item.description ? <div className="text-xs text-slate-600">{item.description}</div> : null}
            </li>
          ))}
        </ul>
      )}
    </div>
  )

  return (
    <div className="mx-auto w-full max-w-md space-y-5">
      <Link
        to={`${CRM_APP_PATHS.candidates}/${lead.candidate_id}`}
        className="btn-primary inline-flex w-full items-center justify-center rounded-xl py-3 text-sm font-semibold shadow-sm"
      >
        {t('app.leads.intake_workspace.detail.open_candidate_primary')}
      </Link>

      <ul className="space-y-2 border-t border-slate-200/80 pt-4 text-sm">
        {receiptRows.map((row) => (
          <li key={row.k} className="flex items-baseline justify-between gap-3">
            <span className="shrink-0 text-xs text-slate-500">{row.label}</span>
            <span className="min-w-0 text-right text-sm font-medium text-slate-900">{row.value}</span>
          </li>
        ))}
      </ul>

      <details className="rounded-xl bg-slate-500/[0.05] ring-1 ring-slate-900/[0.05]">
        <summary className="cursor-pointer list-none px-3 py-3 text-xs font-semibold text-slate-600 marker:content-none [&::-webkit-details-marker]:hidden">
          {t('app.leads.intake_workspace.audit.trace_expand')}
        </summary>
        <div className="space-y-5 border-t border-slate-200/70 px-3 py-4">
          {timelineBlock}
          <p className="text-xs text-slate-600">
            <span className="font-semibold text-slate-700">{t('app.leads.intake_workspace.snapshot.route_label')}: </span>
            {routeLine}
          </p>
          <LeadQualificationSummaryCard lead={lead} isServicesTenant={false} formatAt={(iso) => formatDateValue(iso, locale)} />
          {auditDiagnostics ? <div className="space-y-4 border-t border-slate-200/70 pt-4">{auditDiagnostics}</div> : null}
        </div>
      </details>
    </div>
  )
}
