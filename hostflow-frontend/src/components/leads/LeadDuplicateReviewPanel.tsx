import { useCallback, useMemo, useState } from 'react'

import { submitLeadDuplicateDecision } from '../../api/client'
import type { Lead } from '../../api/types'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'
import { useToast } from '../Toast'
import { usePlanLimitModal } from '../../contexts/PlanLimitModalContext'
import { getFriendlyErrorInfo } from '../../utils/friendlyError'
import {
  leadDuplicateDecisionActionsOpen,
  leadInDuplicateReviewContext,
  readDuplicateMatchV1,
  readDuplicatePrior,
} from '../../utils/leadDuplicateReview'
import { Button } from '../ui/Button'
import { FieldGrid } from '../ui/FieldGrid'
import { StatusBadge } from '../ui/StatusBadge'
import StageTag from '../StageTag'

type Props = {
  lead: Lead
  className?: string
  onLeadUpdated: (lead: Lead) => void
}

function strList(v: unknown): string[] {
  if (!Array.isArray(v)) return []
  return v.map((x) => String(x).trim()).filter(Boolean)
}

function lastHistoryEntry(history: unknown): Record<string, unknown> | null {
  if (!Array.isArray(history) || history.length === 0) return null
  for (let i = history.length - 1; i >= 0; i -= 1) {
    const row = history[i]
    if (row && typeof row === 'object' && !Array.isArray(row)) return row as Record<string, unknown>
  }
  return null
}

export default function LeadDuplicateReviewPanel({ lead, className = '', onLeadUpdated }: Props) {
  const { t } = useI18n()
  const { notify } = useToast()
  const planLimitModal = usePlanLimitModal()
  const [busy, setBusy] = useState<'attach_existing' | 'create_new' | 'ignore' | null>(null)

  const normalized = useMemo(() => {
    const n = lead.normalized
    return n && typeof n === 'object' && !Array.isArray(n) ? (n as Record<string, unknown>) : {}
  }, [lead.normalized])

  const match = useMemo(() => readDuplicateMatchV1(normalized), [normalized])
  const prior = useMemo(() => readDuplicatePrior(normalized), [normalized])
  const history = normalized.duplicate_decisions_history_v1
  const resolution = normalized.duplicate_resolution_v1
  const lastDec = lastHistoryEntry(history)

  const visible = leadInDuplicateReviewContext(lead)
  const actionsOpen = leadDuplicateDecisionActionsOpen(lead)

  const level = match?.level != null ? String(match.level) : ''
  const suggestedId =
    (prior?.candidate_id || (match?.suggested_candidate_id != null ? String(match.suggested_candidate_id).trim() : ''))
  const reasons = strList(match?.reasons)
  const hrBlockers = strList(match?.hr_blockers)

  const runDecision = useCallback(
    async (decision: 'attach_existing' | 'create_new' | 'ignore') => {
      setBusy(decision)
      try {
        const updated = await submitLeadDuplicateDecision(lead.id, { decision })
        onLeadUpdated(updated)
        notify({
          title: t(`app.leads.duplicate_review.toast.${decision}`),
          variant: 'success',
        })
      } catch (err: unknown) {
        if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.leads.duplicate_review.error_title'))) {
          return
        }
        const info = getFriendlyErrorInfo(err, t('app.leads.duplicate_review.error_title'), t)
        notify({
          title: info.title,
          description: [info.detail, info.hint].filter(Boolean).join(' '),
          variant: 'error',
        })
      } finally {
        setBusy(null)
      }
    },
    [lead.id, notify, onLeadUpdated, planLimitModal, t],
  )

  if (!visible) return null

  const outcomeLabel = prior?.outcome || prior?.intake_status || prior?.stage
  const reasonLabel = prior?.reason || prior?.intake_reason

  return (
    <section className={className} aria-labelledby="intake-duplicate-heading">
      <div className="flex flex-wrap items-center gap-2">
        <h2 id="intake-duplicate-heading" className="text-xs font-bold uppercase tracking-[0.14em] text-slate-500">
          {t('app.leads.duplicate_review.title')}
        </h2>
        <StatusBadge
          label={
            lead.status === 'duplicated'
              ? t('app.leads.duplicate_review.badge_attached', { defaultValue: 'Attached' })
              : t('app.leads.duplicate_review.badge_active')
          }
          semantic="warning"
          size="sm"
        />
      </div>
      <p className="mt-1 text-[11px] leading-snug text-slate-500">{t('app.leads.duplicate_review.subtitle')}</p>

      <div className="mt-3 space-y-3">
        <FieldGrid cols={2}>
          <div>
            <div className="text-[11px] font-medium text-slate-500">
              {t('app.leads.duplicate_review.prior_candidate', { defaultValue: 'Previous candidate' })}
            </div>
            <div className="mt-1 text-sm font-medium text-slate-900">
              {prior?.candidate_created === false
                ? t('app.leads.duplicate_review.prior_no_candidate', { defaultValue: 'No candidate was created' })
                : prior?.display_name || t('app.leads.duplicate_review.prior_candidate_created', { defaultValue: 'Candidate already exists' })}
            </div>
            {suggestedId ? (
              <Button variant="link" href={`${CRM_APP_PATHS.candidates}/${suggestedId}`} size="sm">
                {t('app.leads.duplicate_review.open_candidate', { defaultValue: 'Open candidate' })}
              </Button>
            ) : null}
          </div>
          <div>
            <div className="text-[11px] font-medium text-slate-500">
              {t('app.leads.duplicate_review.prior_outcome', { defaultValue: 'Outcome' })}
            </div>
            <div className="mt-1 flex flex-wrap items-center gap-1.5">
              {prior?.stage ? <StageTag code={prior.stage} size="sm" /> : null}
              {outcomeLabel && outcomeLabel !== prior?.stage ? (
                <StatusBadge label={outcomeLabel} semantic="neutral" size="sm" />
              ) : null}
              {!prior?.stage && !outcomeLabel ? <span className="text-sm text-slate-500">—</span> : null}
            </div>
            {reasonLabel ? (
              <p className="mt-1 text-sm text-slate-800">
                <span className="text-[11px] font-medium text-slate-500">
                  {t('app.leads.duplicate_review.prior_reason', { defaultValue: 'Reason' })}:{' '}
                </span>
                {reasonLabel}
              </p>
            ) : null}
          </div>
        </FieldGrid>

        {level ? (
          <p className="text-xs text-slate-600">
            {t('app.leads.duplicate_review.level')}: {level}
          </p>
        ) : null}

        {reasons.length > 0 ? (
          <div>
            <div className="text-[11px] font-medium text-slate-500">{t('app.leads.duplicate_review.reasons')}</div>
            <ul className="mt-1 list-inside list-disc text-sm text-slate-800">
              {reasons.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          </div>
        ) : null}

        {hrBlockers.length > 0 ? (
          <div>
            <StatusBadge label={t('app.leads.duplicate_review.hr_blockers')} semantic="danger" size="sm" />
            <ul className="mt-1 list-inside list-disc text-sm text-slate-800">
              {hrBlockers.map((b) => (
                <li key={b}>{b}</li>
              ))}
            </ul>
          </div>
        ) : null}

        {prior?.previous_duplicate_intakes ? (
          <p className="text-xs text-slate-600">
            {t('app.leads.duplicate_review.prior_repeat', {
              defaultValue: 'Already seen as a duplicate {n} time(s).',
              values: { n: prior.previous_duplicate_intakes },
            })}
          </p>
        ) : null}

        {resolution && typeof resolution === 'object' && !Array.isArray(resolution) ? (
          <p className="text-xs text-slate-600">
            {t('app.leads.duplicate_review.last_resolution')}: {String((resolution as Record<string, unknown>).outcome ?? '—')}
          </p>
        ) : null}

        {lastDec ? (
          <p className="text-xs text-slate-600">
            {t('app.leads.duplicate_review.history_last')}: {String(lastDec.decision ?? '—')}
            {lastDec.outcome != null ? ` → ${String(lastDec.outcome)}` : ''}
          </p>
        ) : null}

        {actionsOpen ? (
          <div className="flex flex-wrap gap-2">
            <Button
              variant="primary"
              size="sm"
              disabled={busy !== null || !suggestedId}
              onClick={() => void runDecision('attach_existing')}
            >
              {busy === 'attach_existing' ? t('common.loading') : t('app.leads.duplicate_review.attach')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={busy !== null || !suggestedId}
              onClick={() => void runDecision('create_new')}
            >
              {busy === 'create_new' ? t('common.loading') : t('app.leads.duplicate_review.create_new')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={busy !== null || !suggestedId}
              onClick={() => void runDecision('ignore')}
            >
              {busy === 'ignore' ? t('common.loading') : t('app.leads.duplicate_review.ignore')}
            </Button>
            {!suggestedId ? (
              <p className="w-full text-xs text-slate-600">{t('app.leads.duplicate_review.missing_suggestion')}</p>
            ) : null}
          </div>
        ) : (
          <p className="text-xs text-slate-500">{t('app.leads.duplicate_review.readonly_hint')}</p>
        )}
      </div>
    </section>
  )
}
