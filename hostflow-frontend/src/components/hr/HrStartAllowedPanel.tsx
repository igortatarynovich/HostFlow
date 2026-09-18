/**
 * ESA slice 3 — HR host binding for employment_start_allowed.v1.
 * UI shows evaluator primary_item only. Evidence = navigate existing Documents.
 * Re-evaluate only after confirmed authority write. unsupported_context = terminal.
 */

import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import {
  applyHandoffEmploymentStartAllowed,
  evaluateHandoffEmploymentStartAllowed,
  type EmploymentStartAllowedOut,
  type StartAllowedPrimaryItem,
} from '../../api/employmentStartAllowed'
import { useI18n } from '../../i18n'
import { useToast } from '../Toast'

type Props = {
  handoffId: string
  employeeId: string
  /** Bump after Documents/authority writes so panel re-evaluates from SoT (no optimistic clear). */
  reloadToken?: string
  onDecision?: (decision: EmploymentStartAllowedOut) => void
}

function scrollToAnchor(anchor: string) {
  const sel = anchor.startsWith('#') ? anchor : `#${anchor}`
  document.querySelector(sel)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

export function primaryWorkItem(result: EmploymentStartAllowedOut | null): StartAllowedPrimaryItem | null {
  if (!result) return null
  return result.ui_primary_item || result.primary_item || null
}

export default function HrStartAllowedPanel({ handoffId, employeeId, reloadToken, onDecision }: Props) {
  const { t } = useI18n()
  const { notify } = useToast()
  const [result, setResult] = useState<EmploymentStartAllowedOut | null>(null)
  const [loading, setLoading] = useState(true)
  const [applying, setApplying] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  // Allowlisted BHP exception form fields (typed exception authority only)
  const [priorRef, setPriorRef] = useState('')
  const [priorEnd, setPriorEnd] = useState('')
  const [currentStart, setCurrentStart] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setErr(null)
    try {
      const next = await evaluateHandoffEmploymentStartAllowed(handoffId)
      setResult(next)
      onDecision?.(next)
    } catch (e: unknown) {
      const ex = e as { response?: { data?: { detail?: string | { message?: string } } }; message?: string }
      const detail = ex?.response?.data?.detail
      const msg =
        typeof detail === 'string'
          ? detail
          : detail && typeof detail === 'object'
            ? detail.message
            : ex?.message
      setErr(msg || t('common.errors.request_failed'))
      setResult(null)
    } finally {
      setLoading(false)
    }
  }, [handoffId, onDecision, t])

  useEffect(() => {
    void load()
  }, [load, reloadToken])

  const primary = primaryWorkItem(result)
  const docsAnchor = result?.evidence_nav?.documents_anchor || '#hr-document-verification'
  const ctx = result?.employment_context || {}

  const submitBhpException = async () => {
    setApplying(true)
    try {
      const next = await applyHandoffEmploymentStartAllowed(handoffId, {
        resolution_patch: {
          exception: {
            exception_code: 'bhp_successive_same_employer_same_post',
            facts: {
              employer_id: ctx.employer_id,
              post_key: ctx.post_key,
              prior_contract_ref: priorRef,
              prior_contract_end_date: priorEnd,
              current_contract_start_date: currentStart || ctx.planned_start_date,
              successive: true,
            },
          },
        },
      })
      // Never optimistic: replace decision only from fresh evaluator response
      setResult(next)
      onDecision?.(next)
      notify({
        variant: 'success',
        title: t('app.hr.start_allowed.reevaluated', { defaultValue: 'Start allowance re-evaluated' }),
      })
    } catch (e: unknown) {
      const ex = e as { response?: { data?: { detail?: string | { message?: string } } }; message?: string }
      const detail = ex?.response?.data?.detail
      const msg =
        typeof detail === 'string'
          ? detail
          : detail && typeof detail === 'object'
            ? detail.message
            : ex?.message
      notify({
        variant: 'error',
        title: msg || t('common.errors.request_failed'),
      })
    } finally {
      setApplying(false)
    }
  }

  return (
    <section
      id="hr-start-allowed"
      className="scroll-mt-24 rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
      data-testid="hr-start-allowed-panel"
    >
      <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">
            {t('app.hr.start_allowed.title', { defaultValue: 'Admit to work (start allowed)' })}
          </h2>
          <p className="mt-1 text-xs text-slate-500">
            {t('app.hr.start_allowed.subtitle', {
              defaultValue: 'Derived from Contract, Medical, and BHP evidence — not an operator switch.',
            })}
          </p>
        </div>
        <button type="button" className="btn-secondary btn-sm" disabled={loading} onClick={() => void load()}>
          {t('common.actions.refresh', { defaultValue: 'Refresh' })}
        </button>
      </div>

      {loading && <p className="text-sm text-slate-500">{t('common.loading')}</p>}
      {err && (
        <div className="rounded border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">{err}</div>
      )}

      {!loading && result && result.decision === 'unsupported_context' && (
        <div
          className="rounded border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-700"
          data-testid="hr-start-allowed-unsupported"
        >
          {t('app.hr.start_allowed.unsupported', {
            defaultValue: 'This start policy does not apply to this employment context.',
          })}
        </div>
      )}

      {!loading && result && result.start_allowed && (
        <div
          className="rounded border border-emerald-200 bg-emerald-50 px-3 py-3 text-sm text-emerald-900"
          data-testid="hr-start-allowed-ok"
        >
          {t('app.hr.start_allowed.allowed', {
            defaultValue: 'Admit-to-work is allowed. Physical start still requires Started confirm.',
          })}
        </div>
      )}

      {!loading && result && !result.start_allowed && result.decision !== 'unsupported_context' && primary && (
        <div className="space-y-3" data-testid="hr-start-allowed-primary">
          <div className="rounded border border-amber-200 bg-amber-50 px-3 py-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-amber-800">
              {t('app.hr.start_allowed.current_work', { defaultValue: 'Current work' })}
            </p>
            <p className="mt-1 text-sm font-medium text-slate-900">{primary.message || primary.code}</p>
            <p className="mt-0.5 font-mono text-xs text-slate-500">{primary.code}</p>
          </div>

          {(primary.kind === 'evidence' ||
            primary.code === 'written_employment_contract_or_confirmation' ||
            primary.code === 'occupational_medical_fit_for_post' ||
            primary.code === 'introductory_bhp_before_admit' ||
            primary.code === 'planned_start_date') &&
            primary.code !== 'introductory_bhp_before_admit' && (
              <div className="flex flex-wrap gap-2">
                <button type="button" className="btn-primary btn-sm" onClick={() => scrollToAnchor(docsAnchor)}>
                  {t('app.hr.start_allowed.open_documents', {
                    defaultValue: 'Open existing documents surface',
                  })}
                </button>
                <Link
                  className="btn-secondary btn-sm inline-flex items-center"
                  to={`${CRM_APP_PATHS.hrEmployees}/${encodeURIComponent(employeeId)}#hr-employee-linked-documents`}
                >
                  {t('app.hr.start_allowed.open_employee_docs', {
                    defaultValue: 'Employee linked documents',
                  })}
                </Link>
              </div>
            )}

          {primary.code === 'introductory_bhp_before_admit' && (
            <div className="space-y-2 rounded border border-slate-200 p-3">
              <p className="text-xs text-slate-600">
                {t('app.hr.start_allowed.bhp_hint', {
                  defaultValue:
                    'Supply BHP via existing documents, or record the allowlisted successive-same-employer exception. No local upload here.',
                })}
              </p>
              <div className="flex flex-wrap gap-2">
                <button type="button" className="btn-secondary btn-sm" onClick={() => scrollToAnchor(docsAnchor)}>
                  {t('app.hr.start_allowed.open_documents', {
                    defaultValue: 'Open existing documents surface',
                  })}
                </button>
              </div>
              <div className="grid gap-2 sm:grid-cols-3">
                <label className="text-xs text-slate-600">
                  {t('app.hr.start_allowed.prior_contract_ref', { defaultValue: 'Prior contract ref' })}
                  <input
                    className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm"
                    value={priorRef}
                    onChange={(e) => setPriorRef(e.target.value)}
                    data-testid="hr-start-allowed-prior-ref"
                  />
                </label>
                <label className="text-xs text-slate-600">
                  {t('app.hr.start_allowed.prior_end', { defaultValue: 'Prior contract end' })}
                  <input
                    type="date"
                    className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm"
                    value={priorEnd}
                    onChange={(e) => setPriorEnd(e.target.value)}
                    data-testid="hr-start-allowed-prior-end"
                  />
                </label>
                <label className="text-xs text-slate-600">
                  {t('app.hr.start_allowed.current_start', { defaultValue: 'Current contract start' })}
                  <input
                    type="date"
                    className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm"
                    value={currentStart}
                    onChange={(e) => setCurrentStart(e.target.value)}
                    data-testid="hr-start-allowed-current-start"
                  />
                </label>
              </div>
              <button
                type="button"
                className="btn-primary btn-sm"
                disabled={applying || !priorRef || !priorEnd}
                onClick={() => void submitBhpException()}
                data-testid="hr-start-allowed-submit-exception"
              >
                {t('app.hr.start_allowed.submit_exception', {
                  defaultValue: 'Record allowlisted BHP exception & re-evaluate',
                })}
              </button>
            </div>
          )}
        </div>
      )}

      {!loading && result && !result.start_allowed && result.decision !== 'unsupported_context' && !primary && (
        <div className="rounded border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-700">
          {t('app.hr.start_allowed.waiting_employee', {
            defaultValue: 'Admit-to-work evaluation needs a linked Employee on this handoff.',
          })}
        </div>
      )}

      {/* Machine may return full active_missing for audit — never render as checklist */}
    </section>
  )
}
