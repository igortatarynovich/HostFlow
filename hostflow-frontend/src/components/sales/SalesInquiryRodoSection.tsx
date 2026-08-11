import { useCallback, useEffect, useState } from 'react'
import { IconAlertTriangle } from '@tabler/icons-react'
import clsx from 'clsx'

import {
  getLead,
  markLeadRodoSourceProvided,
  sendLeadRodoCompliance,
} from '../../api/client'
import type { Lead } from '../../api/types'
import { useToast } from '../Toast'
import { useI18n } from '../../i18n'
import {
  leadEmailPolicyBlocked,
  leadRodoNoticeStatus,
  leadRodoSatisfied,
} from '../../utils/intakeResolution'

type Props = {
  leadId: string
  /** When provided, skip initial fetch until refresh. */
  lead?: Lead | null
  disabled?: boolean
  onUpdated?: (lead: Lead) => void
}

/**
 * Sales / B2B rail — same RODO unlock as Intake Decision rail (ADR-033 slice C).
 * Call-result and stage→contacted stay gated until notice is sent or marked at source.
 */
export default function SalesInquiryRodoSection({ leadId, lead: leadProp, disabled, onUpdated }: Props) {
  const { t } = useI18n()
  const { notify } = useToast()
  const [lead, setLead] = useState<Lead | null>(leadProp ?? null)
  const [loading, setLoading] = useState(!leadProp)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    if (!leadId) return
    setLoading(true)
    try {
      const next = await getLead(leadId)
      setLead(next)
      onUpdated?.(next)
    } catch {
      setLead(null)
    } finally {
      setLoading(false)
    }
  }, [leadId, onUpdated])

  useEffect(() => {
    if (leadProp) {
      setLead(leadProp)
      setLoading(false)
      return
    }
    void load()
  }, [leadProp, load])

  const rodoOk = leadRodoSatisfied(lead)
  const rodoStatus = leadRodoNoticeStatus(lead)
  const policyBlocked = leadEmailPolicyBlocked(lead)

  const sendRodoNotice = async () => {
    if (!leadId || busy || disabled) return
    setBusy(true)
    try {
      await sendLeadRodoCompliance(leadId)
      const updated = await getLead(leadId)
      setLead(updated)
      onUpdated?.(updated)
      notify({
        title: t('app.leads.intake_workspace.decision_rail.rodo_send_success', {
          defaultValue: 'RODO notice sent.',
        }),
        variant: 'success',
      })
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail ??
        (err as Error)?.message ??
        t('app.leads.intake_workspace.decision_rail.rodo_send_failed', {
          defaultValue: 'Could not send RODO notice.',
        })
      notify({ title: typeof detail === 'string' ? detail : JSON.stringify(detail), variant: 'error' })
    } finally {
      setBusy(false)
    }
  }

  const markSourceProvided = async () => {
    if (!leadId || busy || disabled) return
    setBusy(true)
    try {
      await markLeadRodoSourceProvided(leadId)
      const updated = await getLead(leadId)
      setLead(updated)
      onUpdated?.(updated)
      notify({
        title: t('app.leads.intake_workspace.decision_rail.rodo_source_marked', {
          defaultValue: 'Marked as covered at source.',
        }),
        variant: 'success',
      })
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail ??
        (err as Error)?.message ??
        t('app.leads.intake_workspace.decision_rail.rodo_source_failed', {
          defaultValue: 'Could not update RODO status.',
        })
      notify({ title: typeof detail === 'string' ? detail : JSON.stringify(detail), variant: 'error' })
    } finally {
      setBusy(false)
    }
  }

  if (loading) {
    return (
      <p className="text-sm text-slate-500" data-testid="sales-rodo-loading">
        {t('common.loading', { defaultValue: 'Loading…' })}
      </p>
    )
  }

  if (!lead || lead.candidate_id) return null

  return (
    <div
      className={clsx(
        'space-y-3 rounded-xl px-3 py-3 text-sm ring-1',
        rodoOk
          ? 'bg-emerald-500/[0.08] text-emerald-950 ring-emerald-900/10'
          : 'bg-amber-500/[0.1] text-amber-950 ring-amber-800/15',
      )}
      role="status"
      data-testid="sales-rodo-gate"
      data-rodo-ok={rodoOk ? '1' : '0'}
    >
      <p className="text-[11px] font-bold uppercase tracking-wide text-slate-800">
        {t('app.leads.intake_workspace.decision_rail.rodo_required_title', {
          defaultValue: 'RODO required',
        })}
      </p>
      {!rodoOk ? (
        <>
          <p className="text-xs leading-relaxed text-amber-900/95">
            {rodoStatus === 'pending_channel'
              ? t('app.leads.intake_workspace.decision_rail.rodo_pending_channel', {
                  defaultValue: 'No email on this lead — send is blocked until a channel exists, or mark covered at source.',
                })
              : rodoStatus === 'pending_policy'
                ? t('app.leads.intake_workspace.decision_rail.rodo_pending_policy', {
                    defaultValue:
                      'Email policy blocked RODO send (missing or invalid template). Configure Lead lifecycle email in Communications settings.',
                  })
                : rodoStatus === 'failed'
                  ? t('app.leads.intake_workspace.decision_rail.rodo_failed', {
                      defaultValue: 'Previous RODO send failed — retry or mark covered at source.',
                    })
                  : t('app.leads.intake_workspace.decision_rail.rodo_required_hint', {
                      defaultValue:
                        'Send the art.14 GDPR/RODO notice, or confirm it was covered at source, before logging a call or moving to contacted.',
                    })}
          </p>
          {policyBlocked ? (
            <p className="inline-flex items-center gap-1 rounded-md bg-rose-100 px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-rose-900 ring-1 ring-rose-900/10">
              <IconAlertTriangle size={14} aria-hidden />
              {t('app.leads.intake_workspace.decision_rail.email_policy_blocked_badge', {
                defaultValue: 'Email policy blocked',
              })}
            </p>
          ) : null}
          <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
            <button
              type="button"
              className="btn-primary inline-flex justify-center rounded-lg px-3 py-2 text-sm font-semibold disabled:opacity-50"
              disabled={busy || disabled || rodoStatus === 'pending_channel'}
              onClick={() => void sendRodoNotice()}
              data-testid="sales-rodo-send"
            >
              {busy
                ? t('app.leads.intake_workspace.decision_rail.rodo_sending', { defaultValue: 'Sending…' })
                : t('app.leads.intake_workspace.decision_rail.send_rodo_notice', {
                    defaultValue: 'Send RODO notice',
                  })}
            </button>
            <button
              type="button"
              className="btn-secondary inline-flex justify-center rounded-lg px-3 py-2 text-sm font-semibold disabled:opacity-50"
              disabled={busy || disabled}
              onClick={() => void markSourceProvided()}
              data-testid="sales-rodo-source-provided"
            >
              {t('app.leads.intake_workspace.decision_rail.mark_source_provided', {
                defaultValue: 'Covered at source',
              })}
            </button>
          </div>
        </>
      ) : (
        <p className="text-xs font-medium text-emerald-900">
          {t('app.leads.intake_workspace.decision_rail.rodo_ok_hint', {
            defaultValue: 'RODO notice is satisfied for this lead.',
          })}
        </p>
      )}
    </div>
  )
}

export function salesLeadRodoAllowsCallResult(lead: Lead | null | undefined): boolean {
  return leadRodoSatisfied(lead ?? null)
}
