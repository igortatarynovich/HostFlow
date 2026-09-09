import { useCallback, useEffect, useState } from 'react'
import {
  applyEmploymentAcceptPolicy,
  applyEmploymentFormalize,
  confirmEmploymentStarted,
  type EmploymentFormalizeOut,
  type EmploymentStartedOut,
} from '../../../api/handoffs'
import { useToast } from '../../../components/Toast'
import { useI18n } from '../../../i18n'
import { ContextRailDecisionZone } from '../../../platform/context-rail'
import { applicationReadyForEmploymentPrep } from '../../../platform/application-workspace/resolveRecruitmentApplicationDecision'
import type { WorkspaceCapabilityRenderContext } from '../../../platform/workspace-capability/renderContext'
import { getFriendlyErrorInfo } from '../../../utils/friendlyError'
import {
  FORMALIZE_CONTRACT_ACTION,
  resolveEmploymentSpineDecision,
} from '../employmentSpineDecision'

function todayIsoDate(): string {
  return new Date().toISOString().slice(0, 10)
}

function employmentActionError(err: unknown, fallback: string, t: (key: string, options?: Record<string, unknown>) => string): string {
  const info = getFriendlyErrorInfo(err, fallback, t)
  return [info.title, info.detail, info.hint].filter(Boolean).join(' ')
}

/**
 * Employment owns next_action after Transfer. Same application workspace.
 * Not an HR-card screen. Does not mint a new host.
 */
export function HrEmploymentContribution({
  application,
  patching,
  onRefresh,
}: WorkspaceCapabilityRenderContext) {
  const { t } = useI18n()
  const { notify } = useToast()
  const [busy, setBusy] = useState(false)
  const [formalize, setFormalize] = useState<EmploymentFormalizeOut | null>(null)
  const [started, setStarted] = useState<EmploymentStartedOut | null>(null)

  const prep = application ? applicationReadyForEmploymentPrep(application) : null
  const handoffId = String(prep?.handoff_id || '').trim()
  const handedOff = Boolean(handoffId) || String(prep?.next_action || '').trim() === 'handed_off'

  const refreshSpine = useCallback(async () => {
    if (!handoffId) return
    setBusy(true)
    try {
      await applyEmploymentAcceptPolicy(handoffId)
      const formalizeOut = await applyEmploymentFormalize(handoffId)
      setFormalize(formalizeOut)
      const startedOut = await confirmEmploymentStarted(handoffId, {
        require_confirm_when_not_started: false,
        ensure_employee: false,
      })
      setStarted(startedOut)
    } catch (err: unknown) {
      notify({
        title: employmentActionError(err, t('app.recruitment_inquiry.eso.refresh_failed', { defaultValue: 'Не удалось продолжить трудоустройство' }), t),
        variant: 'error',
      })
    } finally {
      setBusy(false)
    }
  }, [handoffId, notify, t])

  useEffect(() => {
    if (!handedOff || !handoffId) return
    void refreshSpine()
  }, [handedOff, handoffId, refreshSpine])

  const run = useCallback(
    async (fn: () => Promise<void>) => {
      setBusy(true)
      try {
        await fn()
        onRefresh()
      } catch (err: unknown) {
        notify({
          title: employmentActionError(err, t('app.recruitment_inquiry.eso.action_failed', { defaultValue: 'Не удалось выполнить действие Employment' }), t),
          variant: 'error',
        })
      } finally {
        setBusy(false)
      }
    },
    [notify, onRefresh, t],
  )

  const onFormalize = useCallback(() => {
    if (!handoffId) return
    void run(async () => {
      const out = await applyEmploymentFormalize(handoffId, {
        confirmed_actions: [FORMALIZE_CONTRACT_ACTION],
      })
      setFormalize(out)
      notify({
        title: t('app.recruitment_inquiry.eso.formalize_done', {
          defaultValue: 'Оформление подтверждено',
        }),
        variant: 'success',
      })
    })
  }, [handoffId, notify, run, t])

  const onConfirmStart = useCallback(() => {
    if (!handoffId) return
    void run(async () => {
      const out = await confirmEmploymentStarted(handoffId, {
        start_confirmation: { confirmed: true, start_date: todayIsoDate() },
        known_start_date: todayIsoDate(),
        ensure_employee: true,
      })
      setStarted(out)
      notify({
        title: t('app.recruitment_inquiry.eso.started_title', { defaultValue: 'Вышел' }),
        variant: 'success',
      })
    })
  }, [handoffId, notify, run, t])

  if (!application || !handedOff || !handoffId) return null

  const decision = resolveEmploymentSpineDecision({
    busy: busy || patching,
    onFormalize,
    onConfirmStart,
    formalize,
    started,
    t,
  })

  return (
    <div data-capability-id="hr.employment" data-widget-class="decision_zone">
      <ContextRailDecisionZone decision={decision} />
    </div>
  )
}
