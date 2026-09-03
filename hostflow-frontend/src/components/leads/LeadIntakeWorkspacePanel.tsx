import { type ReactNode, useCallback, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconExternalLink } from '@tabler/icons-react'

import { submitLeadIntakeDecision } from '../../api/client'
import type { Lead } from '../../api/types'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'
import { usePlanLimitModal } from '../../contexts/PlanLimitModalContext'
import { useToast } from '../Toast'
import { leadIntakeWorkspaceSuppressesCrmChrome } from '../../utils/leadIntakeWorkspace'
import LeadIntakeCandidateSnapshot, { LeadIntakeRecruitmentContextBlock } from './LeadIntakeCandidateSnapshot'
import LeadIntakeDecisionRail from './LeadIntakeDecisionRail'
import LeadIntakeFormAnswers from './LeadIntakeFormAnswers'
import LeadIntakeCallStep from './LeadIntakeCallStep'
import LeadIntakeIdentityBar from './LeadIntakeIdentityBar'
import LeadDuplicateReviewPanel from './LeadDuplicateReviewPanel'

function normRecord(normalized: unknown): Record<string, unknown> {
  if (!normalized || typeof normalized !== 'object' || Array.isArray(normalized)) return {}
  return normalized as Record<string, unknown>
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

export type LeadIntakeWorkspacePanelProps = {
  lead: Lead
  isServicesTenant: boolean
  formatDate: (iso: string | null | undefined) => string
  processing: boolean
  routingBusy: boolean
  onClose: () => void
  onLeadUpdated: (l: Lead) => void
  onProcess: () => void | Promise<void>
  onPickVacancy: () => void
  onConfirmRouting: (vacancyId: string, thenProcess: boolean) => void
  /** Stage, reminders, timeline, playbook, call/write… */
  moreSection?: ReactNode
}

export default function LeadIntakeWorkspacePanel({
  lead,
  isServicesTenant,
  formatDate,
  processing,
  routingBusy,
  onClose,
  onLeadUpdated,
  onProcess,
  onConfirmRouting,
  moreSection,
}: LeadIntakeWorkspacePanelProps) {
  const { t } = useI18n()
  const { notify } = useToast()
  const planLimitModal = usePlanLimitModal()
  const [poolBusy, setPoolBusy] = useState(false)
  const [rejectNonce, setRejectNonce] = useState(0)

  const n = normRecord(lead.normalized)
  const displayName = useMemo(() => {
    const fn = str(n.full_name)
    if (fn) return fn
    const c = `${str(n.first_name) || ''} ${str(n.last_name) || ''}`.trim()
    if (c) return c
    return lead.company_name || t('app.leads.inbox.lead')
  }, [lead.company_name, n, t])

  const suppressCrm = leadIntakeWorkspaceSuppressesCrmChrome(lead, isServicesTenant)

  const vacancyLabel = t('app.leads.table.vacancy')
  const companyLabel = t('app.leads.table.company')

  const dupLine =
    String(lead.status || '').toLowerCase() === 'duplicate_review'
      ? t('app.leads.intake_workspace.snapshot.duplicate_review_active')
      : t('app.leads.intake_workspace.snapshot.duplicate_clear')

  const routeLine = lead.vacancy_routing_confirmed
    ? t('app.leads.intake_workspace.snapshot.route_confirmed')
    : lead.vacancy_id || lead.vacancy_title
      ? t('app.leads.intake_workspace.snapshot.route_unconfirmed')
      : t('app.leads.intake_workspace.snapshot.route_missing')

  const runPool = useCallback(async () => {
    setPoolBusy(true)
    try {
      const updated = await submitLeadIntakeDecision(lead.id, { decision: 'pool' })
      onLeadUpdated(updated)
      notify({ title: t('app.leads.detail.intake_resolution.intake_actions.success'), variant: 'success' })
    } catch (err: unknown) {
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.leads.detail.intake_resolution.intake_actions.failed'))) {
        return
      }
      const detail =
        (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail ??
        (err as Error)?.message ??
        t('app.leads.detail.intake_resolution.intake_actions.failed')
      notify({ title: typeof detail === 'string' ? detail : JSON.stringify(detail), variant: 'error' })
    } finally {
      setPoolBusy(false)
    }
  }, [lead.id, notify, onLeadUpdated, planLimitModal, t])

  if (isServicesTenant) {
    return (
      <div className="flex h-full min-h-0 flex-col">
        <div className="border-b border-slate-100 px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.leads.intake_workspace.title')}</p>
          <p className="mt-1 text-sm text-slate-600">{t('app.leads.intake_workspace.services_hint')}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Link
              to={`${CRM_APP_PATHS.leads}/${lead.id}`}
              className="btn-secondary inline-flex h-8 items-center gap-1 rounded-lg px-2 text-xs"
            >
              <IconExternalLink size={14} stroke={1.75} aria-hidden />
              {t('app.leads.table.full_page')}
            </Link>
            <button type="button" className="btn-secondary h-8 rounded-lg px-2 text-xs" onClick={onClose}>
              {t('common.actions.close')}
            </button>
          </div>
        </div>
        {moreSection ? <div className="min-h-0 flex-1 overflow-y-auto p-3">{moreSection}</div> : null}
      </div>
    )
  }

  if (lead.candidate_id) {
    const appKindRaw = n.intake_application_kind
    const appKind = typeof appKindRaw === 'string' && (appKindRaw === 'candidate' || appKindRaw === 'client') ? appKindRaw : null

    return (
      <div className="flex h-full min-h-0 flex-col">
        <div className="shrink-0 border-b border-slate-100 px-4 py-3">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.leads.intake_workspace.audit.badge')}</p>
              <h2 className="mt-1 truncate text-lg font-semibold text-slate-900">{displayName}</h2>
              <p className="mt-1 text-sm text-slate-600">{t('app.leads.intake_workspace.audit.subtitle')}</p>
            </div>
            <div className="flex shrink-0 flex-col gap-1">
              <Link
                to={`${CRM_APP_PATHS.leads}/${lead.id}`}
                className="btn-secondary inline-flex h-8 items-center justify-center gap-1 rounded-lg px-2 text-xs"
                title={t('app.leads.table.full_page')}
              >
                <IconExternalLink size={14} stroke={1.75} aria-hidden />
              </Link>
              <button type="button" className="btn-secondary h-8 rounded-lg px-2 text-xs" onClick={onClose}>
                {t('common.actions.close')}
              </button>
            </div>
          </div>
        </div>
        <div className="min-h-0 flex-1 space-y-6 overflow-y-auto p-4">
          <Link
            to={`${CRM_APP_PATHS.candidates}/${lead.candidate_id}`}
            className="btn-primary inline-flex w-full items-center justify-center rounded-xl py-3 text-sm font-semibold shadow-sm"
          >
            {t('app.leads.intake_workspace.audit.open_candidate')}
          </Link>
          <ul className="space-y-2 text-sm text-slate-800">
            <li className="flex justify-between gap-3 border-b border-slate-100 pb-2">
              <span className="text-slate-500">{t('app.leads.table.source')}</span>
              <span className="font-medium">{lead.source || '—'}</span>
            </li>
            <li className="flex justify-between gap-3 border-b border-slate-100 pb-2">
              <span className="text-slate-500">{vacancyLabel}</span>
              <span className="min-w-0 text-right font-medium">{lead.vacancy_title || lead.vacancy_id || '—'}</span>
            </li>
            <li className="flex justify-between gap-3 border-b border-slate-100 pb-2">
              <span className="text-slate-500">{t('app.leads.table.created')}</span>
              <span className="font-medium">{formatDate(lead.created_at)}</span>
            </li>
            {appKind ? (
              <li className="flex justify-between gap-3 border-b border-slate-100 pb-2">
                <span className="text-slate-500">{t('app.leads.intake_workspace.detail.application')}</span>
                <span className="font-medium">{appKind}</span>
              </li>
            ) : null}
            {lead.recruiter_id ? (
              <li className="flex justify-between gap-3 pb-2">
                <span className="text-slate-500">{t('app.leads.table.manager')}</span>
                <span className="font-mono text-xs font-medium text-slate-800">{lead.recruiter_id}</span>
              </li>
            ) : null}
          </ul>
          {moreSection ? (
            <details className="overflow-hidden rounded-xl bg-slate-500/[0.04]">
              <summary className="cursor-pointer px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('app.leads.intake_workspace.audit.history')}
              </summary>
              <div className="border-t border-slate-200/60 p-3">{moreSection}</div>
            </details>
          ) : null}
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-full min-h-[320px] flex-col lg:max-h-[calc(100dvh-8rem)]">
      <div className="shrink-0 border-b border-slate-100 px-4 py-2">
        <div className="flex items-center justify-between gap-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">{t('app.leads.intake_workspace.title')}</p>
          <div className="flex shrink-0 gap-1">
            <Link
              to={`${CRM_APP_PATHS.leads}/${lead.id}`}
              className="btn-secondary inline-flex h-8 items-center gap-1 rounded-lg px-2 text-xs"
              title={t('app.leads.table.full_page')}
            >
              <IconExternalLink size={14} stroke={1.75} aria-hidden />
            </Link>
            <button type="button" className="btn-secondary h-8 rounded-lg px-2 text-xs" onClick={onClose}>
              {t('common.actions.close')}
            </button>
          </div>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-5">
        <div className="space-y-4">
          <LeadIntakeIdentityBar
            lead={lead}
            displayName={displayName}
            formatDate={formatDate}
            createLabel={t('app.leads.intake_workspace.unified.create_candidate')}
            rejectLabel={t('app.leads.intake_workspace.decision_rail.reject_open')}
            poolLabel={t('app.leads.detail.intake_resolution.intake_actions.pool')}
            createBusy={processing || routingBusy}
            poolDisabled={poolBusy}
            onCreate={() => void onProcess()}
            onReject={() => setRejectNonce((n) => n + 1)}
            onPool={() => void runPool()}
          />

          <LeadIntakeFormAnswers lead={lead} />

          <LeadIntakeCallStep lead={lead} onLeadUpdated={onLeadUpdated} showTelButton={false} />
        </div>

        <div className="mt-8 space-y-8">
        <LeadDuplicateReviewPanel lead={lead} onLeadUpdated={onLeadUpdated} />

        <LeadIntakeDecisionRail
          layout="embedded"
          lead={lead}
          processing={processing}
          routingBusy={routingBusy}
          poolBusy={poolBusy}
          onLeadUpdated={onLeadUpdated}
          onRequestProcess={() => void onProcess()}
          onConfirmRouting={onConfirmRouting}
          onPool={() => void runPool()}
          forceRejectOpen={rejectNonce}
        />

        <details className="overflow-hidden rounded-xl bg-slate-500/[0.04]">
          <summary className="cursor-pointer px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('app.leads.intake_workspace.snapshot.qual_toggle')}
          </summary>
          <div className="space-y-8 border-t border-slate-200/60 p-4">
            <LeadIntakeCandidateSnapshot lead={lead} />

            <LeadIntakeRecruitmentContextBlock
              lead={lead}
              companyLabel={companyLabel}
              vacancyLabel={vacancyLabel}
              duplicateLine={dupLine}
              routeLine={routeLine}
              campaignLine={formatUtm(n.utm)}
              createdLabel={formatDate(lead.created_at)}
            />
          </div>
        </details>

        {moreSection ? (
          <details className="overflow-hidden rounded-xl bg-slate-500/[0.04]">
            <summary className="cursor-pointer px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
              {suppressCrm ? t('app.leads.intake_workspace.section.more') : t('app.leads.routing.expand_crm_tools')}
            </summary>
            <div className="border-t border-slate-200/60 bg-slate-50/30 p-3">{moreSection}</div>
          </details>
        ) : null}
        </div>
      </div>
    </div>
  )
}
