import { useCallback, useEffect, useState } from 'react'
import {
  getLead,
  markLeadRodoSourceProvided,
  sendLeadRodoCompliance,
} from '../../../api/client'
import type { Lead } from '../../../api/types'
import { Button } from '../../../components/ui/Button'
import { Checkbox } from '../../../components/ui/Checkbox'
import { useToast } from '../../../components/Toast'
import { useI18n } from '../../../i18n'
import { leadEmailPolicyBlocked, leadRodoNoticeStatus, leadRodoSatisfied } from '../../../utils/intakeResolution'
import type { WorkspaceCapabilityRenderContext } from '../../workspace-capability/renderContext'

/**
 * Shared Consent widget. Owner = Compliance. Host only places.
 * Policy action remains `lead_rodo_v1` — capability_id is `consent`, never `rodo`.
 * Boolean acknowledgement must use CHECKBOX_V1 — not a local input.
 */
export function ConsentCapability({ application, onRefresh }: WorkspaceCapabilityRenderContext) {
  const { t } = useI18n()
  const { notify } = useToast()
  const leadId = String(application.transport_lead_id || '').trim()
  const [lead, setLead] = useState<Lead | null>(null)
  const [loading, setLoading] = useState(Boolean(leadId))
  const [busy, setBusy] = useState(false)
  const [sourceAcknowledged, setSourceAcknowledged] = useState(false)

  const load = useCallback(async () => {
    if (!leadId) {
      setLead(null)
      setLoading(false)
      return
    }
    setLoading(true)
    try {
      setLead(await getLead(leadId))
    } catch {
      setLead(null)
    } finally {
      setLoading(false)
    }
  }, [leadId])

  useEffect(() => {
    void load()
  }, [load])

  const satisfied = leadRodoSatisfied(lead)
  const status = leadRodoNoticeStatus(lead)
  const policyBlocked = leadEmailPolicyBlocked(lead)

  const sendNotice = async () => {
    if (!leadId || busy) return
    setBusy(true)
    try {
      await sendLeadRodoCompliance(leadId)
      await load()
      onRefresh()
      notify({
        title: t('app.leads.intake_workspace.decision_rail.rodo_send_success', { defaultValue: 'RODO notice sent.' }),
        variant: 'success',
      })
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      notify({ title: typeof detail === 'string' ? detail : 'Could not send notice', variant: 'error' })
    } finally {
      setBusy(false)
    }
  }

  const markCovered = async () => {
    if (!leadId || busy || !sourceAcknowledged) return
    setBusy(true)
    try {
      await markLeadRodoSourceProvided(leadId)
      setSourceAcknowledged(false)
      await load()
      onRefresh()
      notify({
        title: t('app.leads.intake_workspace.decision_rail.rodo_source_marked', {
          defaultValue: 'Marked as covered at source.',
        }),
        variant: 'success',
      })
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      notify({ title: typeof detail === 'string' ? detail : 'Could not update consent', variant: 'error' })
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="space-y-3" data-capability-id="consent" data-widget-class="consent">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {t('app.leads.intake_workspace.decision_rail.rodo_required_title', { defaultValue: 'Согласие / уведомление' })}
      </p>
      {loading ? <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Загрузка…' })}</p> : null}
      {!leadId ? (
        <p className="text-sm text-slate-500">Нет intake-контекста для согласия на этом отклике.</p>
      ) : null}
      {!loading && lead && satisfied ? (
        <p className="text-sm font-medium text-emerald-800">
          {t('app.leads.intake_workspace.decision_rail.rodo_ok_hint', {
            defaultValue: 'Notice is satisfied for this intake.',
          })}
        </p>
      ) : null}
      {!loading && lead && !satisfied ? (
        <>
          <p className="text-sm text-slate-600">
            {status === 'pending_channel'
              ? t('app.leads.intake_workspace.decision_rail.rodo_pending_channel', {
                  defaultValue: 'No email on this lead — send is blocked until a channel exists, or mark covered at source.',
                })
              : t('app.leads.intake_workspace.decision_rail.rodo_required_hint', {
                  defaultValue: 'Send the art.14 notice, or confirm it was covered at source.',
                })}
          </p>
          {policyBlocked ? (
            <p className="text-xs font-semibold text-rose-800">
              {t('app.leads.intake_workspace.decision_rail.email_policy_blocked_badge', {
                defaultValue: 'Email policy blocked',
              })}
            </p>
          ) : null}
          <Button variant="primary" size="sm" disabled={busy || status === 'pending_channel'} onClick={() => void sendNotice()}>
            {t('app.leads.intake_workspace.decision_rail.send_rodo_notice', { defaultValue: 'Send notice' })}
          </Button>
          <Checkbox
            checked={sourceAcknowledged}
            onChange={setSourceAcknowledged}
            disabled={busy}
            label={t('app.leads.intake_workspace.decision_rail.mark_source_provided', {
              defaultValue: 'Covered at source',
            })}
            description="Подтвердите, что уведомление уже закрыто на источнике, затем нажмите подтверждение."
          />
          <Button variant="secondary" size="sm" disabled={busy || !sourceAcknowledged} onClick={() => void markCovered()}>
            {t('common.confirm', { defaultValue: 'Подтвердить' })}
          </Button>
        </>
      ) : null}
    </section>
  )
}
