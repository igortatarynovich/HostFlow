import { useCallback, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { submitLeadDuplicateDecision } from '../../api/client'
import type { Lead } from '../../api/types'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'
import { useToast } from '../Toast'
import { usePlanLimitModal } from '../../contexts/PlanLimitModalContext'
import { getFriendlyErrorInfo } from '../../utils/friendlyError'
import { leadDuplicateDecisionActionsOpen, leadInDuplicateReviewContext, readDuplicateMatchV1 } from '../../utils/leadDuplicateReview'

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
  const history = normalized.duplicate_decisions_history_v1
  const resolution = normalized.duplicate_resolution_v1
  const lastDec = lastHistoryEntry(history)

  const visible = leadInDuplicateReviewContext(lead)
  const actionsOpen = leadDuplicateDecisionActionsOpen(lead)

  const level = match?.level != null ? String(match.level) : '—'
  const suggestedId = match?.suggested_candidate_id != null ? String(match.suggested_candidate_id).trim() : ''
  const reasons = strList(match?.reasons)
  const hrBlockers = strList(match?.hr_blockers)
  const errorCode = (lead.error && String(lead.error).trim()) || (match?.error_code != null ? String(match.error_code) : '')

  const sourceBits = useMemo(() => {
    const bits: string[] = []
    const email = normalized.email != null ? String(normalized.email) : ''
    const phone = normalized.phone != null ? String(normalized.phone) : ''
    const name =
      (normalized.full_name != null && String(normalized.full_name).trim()) ||
      `${normalized.first_name || ''} ${normalized.last_name || ''}`.trim()
    if (name) bits.push(name)
    if (email) bits.push(email)
    if (phone) bits.push(phone)
    if (lead.source) bits.push(`${t('app.leads.table.source')}: ${lead.source}`)
    return bits
  }, [lead.source, normalized, t])

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

  return (
    <section
      className={`rounded-lg border-2 border-violet-200 bg-violet-50/40 p-3 text-sm text-slate-800 ${className}`.trim()}
      aria-label={t('app.leads.duplicate_review.title')}
    >
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-violet-950">{t('app.leads.duplicate_review.title')}</h3>
        {lead.status === 'duplicate_review' ? (
          <span className="rounded-md bg-violet-600 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-white">
            {t('app.leads.duplicate_review.badge_active')}
          </span>
        ) : null}
      </div>

      <p className="mb-3 text-xs text-slate-600">{t('app.leads.duplicate_review.subtitle')}</p>

      <dl className="mb-3 grid gap-2 text-xs sm:grid-cols-2">
        <div>
          <dt className="font-medium text-slate-500">{t('app.leads.duplicate_review.level')}</dt>
          <dd className="mt-0.5 font-mono text-slate-900">{level}</dd>
        </div>
        <div>
          <dt className="font-medium text-slate-500">{t('app.leads.duplicate_review.error_code')}</dt>
          <dd className="mt-0.5 break-all font-mono text-slate-900">{errorCode || '—'}</dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="font-medium text-slate-500">{t('app.leads.duplicate_review.suggested')}</dt>
          <dd className="mt-0.5">
            {suggestedId ? (
              <Link
                to={`${CRM_APP_PATHS.candidates}/${suggestedId}`}
                className="font-mono text-brand-700 hover:underline"
              >
                {suggestedId}
              </Link>
            ) : (
              '—'
            )}
          </dd>
        </div>
      </dl>

      {reasons.length > 0 ? (
        <div className="mb-2">
          <div className="text-xs font-medium text-slate-500">{t('app.leads.duplicate_review.reasons')}</div>
          <ul className="mt-1 list-inside list-disc text-xs text-slate-800">
            {reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {hrBlockers.length > 0 ? (
        <div className="mb-3 rounded-md border border-amber-300 bg-amber-50 px-2 py-1.5">
          <div className="text-xs font-semibold text-amber-900">{t('app.leads.duplicate_review.hr_blockers')}</div>
          <ul className="mt-1 list-inside list-disc text-xs text-amber-950">
            {hrBlockers.map((b) => (
              <li key={b}>{b}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="mb-3">
        <div className="text-xs font-medium text-slate-500">{t('app.leads.duplicate_review.source_lead')}</div>
        <div className="mt-1 rounded border border-slate-200 bg-white px-2 py-1.5 font-mono text-[11px] text-slate-700">
          {sourceBits.length ? sourceBits.join(' · ') : '—'}
        </div>
      </div>

      {resolution && typeof resolution === 'object' && !Array.isArray(resolution) ? (
        <div className="mb-2 text-xs text-slate-600">
          <span className="font-medium text-slate-500">{t('app.leads.duplicate_review.last_resolution')}: </span>
          <span className="font-mono">
            {String((resolution as Record<string, unknown>).outcome ?? '—')}
            {(resolution as Record<string, unknown>).resolved_at
              ? ` · ${String((resolution as Record<string, unknown>).resolved_at)}`
              : ''}
          </span>
        </div>
      ) : null}

      {lastDec ? (
        <div className="mb-3 max-h-28 overflow-y-auto rounded border border-slate-200 bg-white px-2 py-1.5 text-[11px] text-slate-700">
          <div className="font-medium text-slate-500">{t('app.leads.duplicate_review.history_last')}</div>
          <div className="mt-1 font-mono">
            {String(lastDec.decision ?? '—')} · {String(lastDec.at ?? '—')}
            {lastDec.outcome != null ? ` → ${String(lastDec.outcome)}` : ''}
          </div>
        </div>
      ) : null}

      {actionsOpen ? (
        <div className="flex flex-col gap-2 border-t border-violet-200 pt-3">
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="btn rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
              disabled={busy !== null || !suggestedId}
              onClick={() => void runDecision('attach_existing')}
            >
              {busy === 'attach_existing' ? t('common.loading') : t('app.leads.duplicate_review.attach')}
            </button>
            <button
              type="button"
              className="btn-secondary rounded-lg px-3 py-1.5 text-xs font-semibold disabled:opacity-50"
              disabled={busy !== null || !suggestedId}
              onClick={() => void runDecision('create_new')}
            >
              {busy === 'create_new' ? t('common.loading') : t('app.leads.duplicate_review.create_new')}
            </button>
            <button
              type="button"
              className="btn-secondary rounded-lg px-3 py-1.5 text-xs font-semibold disabled:opacity-50"
              disabled={busy !== null || !suggestedId}
              onClick={() => void runDecision('ignore')}
            >
              {busy === 'ignore' ? t('common.loading') : t('app.leads.duplicate_review.ignore')}
            </button>
          </div>
          {!suggestedId ? (
            <p className="text-xs text-amber-800">{t('app.leads.duplicate_review.missing_suggestion')}</p>
          ) : null}
        </div>
      ) : (
        <div className="border-t border-violet-200 pt-3 text-xs text-slate-600">{t('app.leads.duplicate_review.readonly_hint')}</div>
      )}
    </section>
  )
}
