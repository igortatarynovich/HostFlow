import { useCallback, useEffect, useState } from 'react'
import { Button } from '../../../components/ui/Button'
import { Checkbox } from '../../../components/ui/Checkbox'
import { useToast } from '../../../components/Toast'
import { useI18n } from '../../../i18n'
import type { WorkspaceCapabilityRenderContext } from '../../workspace-capability/renderContext'
import {
  consentSubjectKey,
  loadConsent,
  markConsentCoveredAtSource,
  sendConsentNotice,
  type ConsentView,
} from './consentOwner'

/**
 * Shared Consent widget. Owner = Compliance. Host only places.
 * Policy action remains `lead_rodo_v1` — capability_id is `consent`, never `rodo`.
 * Boolean acknowledgement must use CHECKBOX_V1 — not a local input.
 * Lead transport is the Compliance owner facade — not imported here.
 */
export function ConsentCapability(ctx: WorkspaceCapabilityRenderContext) {
  const { t } = useI18n()
  const { notify } = useToast()
  const { onRefresh } = ctx
  const subjectKey = consentSubjectKey(ctx)
  const [view, setView] = useState<ConsentView | null>(null)
  const [loading, setLoading] = useState(Boolean(subjectKey))
  const [busy, setBusy] = useState(false)
  const [sourceAcknowledged, setSourceAcknowledged] = useState(false)

  const load = useCallback(async () => {
    if (!subjectKey) {
      setView({ available: false, satisfied: false, status: null, policyBlocked: false })
      setLoading(false)
      return
    }
    setLoading(true)
    try {
      setView(await loadConsent(ctx))
    } catch {
      setView({ available: false, satisfied: false, status: null, policyBlocked: false })
    } finally {
      setLoading(false)
    }
    // subjectKey is the owner-resolved transport id; avoid depending on ctx identity.
  }, [subjectKey]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    void load()
  }, [load])

  const sendNotice = async () => {
    if (!subjectKey || busy) return
    setBusy(true)
    try {
      await sendConsentNotice(ctx)
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
    if (!subjectKey || busy || !sourceAcknowledged) return
    setBusy(true)
    try {
      await markConsentCoveredAtSource(ctx)
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

  const available = Boolean(view?.available)
  const satisfied = Boolean(view?.satisfied)
  const status = view?.status
  const policyBlocked = Boolean(view?.policyBlocked)

  return (
    <section className="space-y-3" data-capability-id="consent" data-widget-class="consent">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {t('app.leads.intake_workspace.decision_rail.rodo_required_title', { defaultValue: 'Согласие / уведомление' })}
      </p>
      {loading ? <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Загрузка…' })}</p> : null}
      {!subjectKey ? (
        <p className="text-sm text-slate-500">{t('app.platform.consent.no_intake')}</p>
      ) : null}
      {!loading && available && satisfied ? (
        <p className="text-sm font-medium text-emerald-800">
          {t('app.leads.intake_workspace.decision_rail.rodo_ok_hint', {
            defaultValue: 'Notice is satisfied for this intake.',
          })}
        </p>
      ) : null}
      {!loading && available && !satisfied ? (
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
            description={t('app.platform.consent.source_ack_hint')}
          />
          <Button variant="secondary" size="sm" disabled={busy || !sourceAcknowledged} onClick={() => void markCovered()}>
            {t('common.confirm', { defaultValue: 'Подтвердить' })}
          </Button>
        </>
      ) : null}
    </section>
  )
}
