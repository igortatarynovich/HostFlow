import { useState } from 'react'
import { IconAlertTriangle } from '@tabler/icons-react'
import clsx from 'clsx'

import {
  markRecruitmentApplicationRodoSourceProvided,
  sendRecruitmentApplicationRodo,
} from '../../api/applications'
import type { Application } from '../../api/types/application'
import { useToast } from '../../components/Toast'
import { useI18n } from '../../i18n'
import { applicationRodoState } from './applicationRail'

type Props = {
  application: Application
  disabled?: boolean
  onUpdated: (application: Application) => void
}

export function ApplicationRodoSection({ application, disabled, onUpdated }: Props) {
  const { t } = useI18n()
  const { notify } = useToast()
  const [busy, setBusy] = useState(false)
  const rodo = applicationRodoState(application)

  if (application.outcome_entity_type === 'candidate' && application.outcome_entity_id) {
    return null
  }

  const sendRodoNotice = async () => {
    if (busy || disabled) return
    setBusy(true)
    try {
      const result = await sendRecruitmentApplicationRodo(application.id)
      onUpdated(result.application)
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
    if (busy || disabled) return
    setBusy(true)
    try {
      const result = await markRecruitmentApplicationRodoSourceProvided(application.id)
      onUpdated(result.application)
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

  return (
    <div
      className={clsx(
        'space-y-3 rounded-xl px-3 py-3 text-sm ring-1',
        rodo.satisfied
          ? 'bg-emerald-500/[0.08] text-emerald-950 ring-emerald-900/10'
          : 'bg-amber-500/[0.1] text-amber-950 ring-amber-800/15',
      )}
      role="status"
      data-testid="recruitment-rodo-gate"
      data-rodo-ok={rodo.satisfied ? '1' : '0'}
    >
      <p className="text-[11px] font-bold uppercase tracking-wide text-slate-800">
        {t('app.leads.intake_workspace.decision_rail.rodo_required_title', {
          defaultValue: 'RODO required',
        })}
      </p>
      {!rodo.satisfied ? (
        <>
          <p className="text-xs leading-relaxed text-amber-900/95">
            {rodo.status === 'pending_channel'
              ? t('app.leads.intake_workspace.decision_rail.rodo_pending_channel', {
                  defaultValue:
                    'No email on this application — send is blocked until a channel exists, or mark covered at source.',
                })
              : rodo.status === 'pending_policy'
                ? t('app.leads.intake_workspace.decision_rail.rodo_pending_policy', {
                    defaultValue:
                      'Email policy blocked RODO send (missing or invalid template). Configure Lead lifecycle email in Communications settings.',
                  })
                : rodo.status === 'failed'
                  ? t('app.leads.intake_workspace.decision_rail.rodo_failed', {
                      defaultValue: 'Previous RODO send failed — retry or mark covered at source.',
                    })
                  : t('app.leads.intake_workspace.decision_rail.rodo_required_hint', {
                      defaultValue:
                        'Send the art.14 GDPR/RODO notice, or confirm it was covered at source, before contacting or creating a candidate.',
                    })}
          </p>
          {rodo.policyBlocked ? (
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
              disabled={busy || disabled || rodo.status === 'pending_channel'}
              onClick={() => void sendRodoNotice()}
              data-testid="recruitment-rodo-send"
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
              data-testid="recruitment-rodo-source-provided"
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
            defaultValue: 'RODO notice is satisfied for this application.',
          })}
        </p>
      )}
    </div>
  )
}
