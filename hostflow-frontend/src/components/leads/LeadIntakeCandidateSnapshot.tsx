import clsx from 'clsx'
import type { ReactNode } from 'react'

import type { Lead } from '../../api/types'
import { useI18n } from '../../i18n'
import { buildIntakeSnapshotGroups, type IntakeSignalSeverity } from '../../utils/leadIntakeSnapshotGroups'

const SEVERITY_ORDER: Record<IntakeSignalSeverity, number> = {
  critical: 0,
  duplicate: 1,
  risk: 2,
  positive: 3,
  info: 4,
}

function normRecord(normalized: unknown): Record<string, unknown> {
  if (!normalized || typeof normalized !== 'object' || Array.isArray(normalized)) return {}
  return normalized as Record<string, unknown>
}

function SignalPill({ severity, children }: { severity: IntakeSignalSeverity; children: ReactNode }) {
  return (
    <span
      className={clsx(
        'inline-flex max-w-full rounded-lg border-y border-r py-1.5 pl-2.5 pr-2.5 text-sm font-semibold leading-snug shadow-sm [border-left-width:3px]',
        severity === 'critical' &&
          'border-l-red-600 border-y-red-100/90 border-r-red-100/90 bg-red-50 text-red-950',
        severity === 'risk' &&
          'border-l-amber-600 border-y-amber-100/90 border-r-amber-100/90 bg-amber-50 text-amber-950',
        severity === 'positive' &&
          'border-l-emerald-600 border-y-emerald-100/90 border-r-emerald-100/90 bg-emerald-50 text-emerald-950',
        severity === 'duplicate' &&
          'border-l-violet-600 border-y-violet-100/90 border-r-violet-100/90 bg-violet-50 text-violet-950',
        severity === 'info' &&
          'border-l-slate-400 border-y-slate-100/90 border-r-slate-100/90 bg-slate-50 text-slate-800',
      )}
    >
      {children}
    </span>
  )
}

export type LeadIntakeCandidateSnapshotProps = {
  lead: Lead
  /** Name shown as subtle anchor (detail); omit in compact list rail. */
  anchorName?: string | null
  className?: string
  headingClassName?: string
}

/** Operational reading surface — grouped signals, not a CRM form. */
export default function LeadIntakeCandidateSnapshot({
  lead,
  anchorName,
  className = '',
  headingClassName = '',
}: LeadIntakeCandidateSnapshotProps) {
  const { t } = useI18n()
  const n = normRecord(lead.normalized)
  const groups = buildIntakeSnapshotGroups(lead, n, t)

  if (groups.length === 0) return null

  return (
    <section aria-labelledby="intake-snapshot-heading" className={className}>
      <div className={clsx('mb-4 flex items-end justify-between gap-2', headingClassName)}>
        <h2 id="intake-snapshot-heading" className="text-xs font-bold uppercase tracking-[0.14em] text-slate-500">
          {t('app.leads.intake_workspace.snapshot.title')}
        </h2>
        {anchorName ? <span className="truncate text-[10px] font-semibold uppercase tracking-wide text-slate-400">{anchorName}</span> : null}
      </div>
      <div className="space-y-5">
        {groups.map((g) => (
          <div key={g.id}>
            <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-400">{t(g.titleKey)}</h3>
            <div className="flex flex-wrap gap-2">
              {[...g.signals]
                .sort((a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity])
                .map((s) => (
                  <SignalPill key={`${g.id}-${s.key}`} severity={s.severity}>
                    {s.label}
                  </SignalPill>
                ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

export type LeadIntakeRecruitmentContextBlockProps = {
  lead: Lead
  companyLabel: string
  vacancyLabel: string
  duplicateLine: string
  routeLine: string
  campaignLine?: string | null
  /** When set, shown as first row (e.g. formatted created_at). */
  createdLabel?: string | null
  className?: string
}

/** Compact intake context — source, campaign, vacancy, route, duplicate, company. */
export function LeadIntakeRecruitmentContextBlock({
  lead,
  companyLabel,
  vacancyLabel,
  duplicateLine,
  routeLine,
  campaignLine,
  createdLabel,
  className = '',
}: LeadIntakeRecruitmentContextBlockProps) {
  const { t } = useI18n()

  const rows: Array<{ k: string; label: string; value: string }> = []
  if (createdLabel?.trim()) {
    rows.push({ k: 'created', label: t('app.leads.table.created'), value: createdLabel.trim() })
  }
  rows.push(
    { k: 'src', label: t('app.leads.table.source'), value: lead.source || '—' },
    { k: 'camp', label: t('app.leads.detail.qualification_summary.utm'), value: campaignLine?.trim() || '—' },
    { k: 'vac', label: vacancyLabel, value: lead.vacancy_title || lead.vacancy_id || '—' },
    { k: 'route', label: t('app.leads.intake_workspace.snapshot.route_label'), value: routeLine },
    { k: 'dup', label: t('app.leads.intake_workspace.snapshot.duplicate_label'), value: duplicateLine },
    { k: 'co', label: companyLabel, value: lead.company_name || lead.company_id || '—' },
  )

  return (
    <section className={clsx('space-y-3', className)} aria-labelledby="intake-context-heading">
      <h2 id="intake-context-heading" className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
        {t('app.leads.intake_workspace.snapshot.context_title')}
      </h2>
      <ul className="space-y-2.5 text-sm">
        {rows.map((r) => (
          <li key={r.k} className="flex flex-col gap-0.5 sm:flex-row sm:items-baseline sm:gap-3">
            <span className="shrink-0 text-xs text-slate-500">{r.label}</span>
            <span className="min-w-0 font-medium leading-snug text-slate-900">{r.value}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}
