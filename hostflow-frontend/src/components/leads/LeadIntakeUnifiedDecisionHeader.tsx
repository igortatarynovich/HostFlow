import type { Lead } from '../../api/types'
import { useI18n } from '../../i18n'
import { intakeWorkspaceHeader, type IntakeWorkspaceHeader } from '../../utils/leadIntakeWorkspace'
import {
  leadRoutingTableAction,
  leadStatusAllowsIntakeDecision,
  manualProcessBlockHint,
} from '../../utils/intakeResolution'
import { leadSupportsManualProcess } from '../../utils/leadCrm'

function headerKeys(tone: IntakeWorkspaceHeader['tone']): { titleKey: string; hintKey: string } {
  return {
    titleKey: `app.leads.intake_workspace.header.${tone}_title`,
    hintKey: `app.leads.intake_workspace.header.${tone}_hint`,
  }
}

export type LeadIntakeUnifiedDecisionHeaderProps = {
  lead: Lead
  isServicesTenant: boolean
  processing: boolean
  routingBusy: boolean
  poolBusy?: boolean
  onProcess: () => void | Promise<void>
  onPickVacancy: () => void
  onConfirmRouting: (vacancyId: string, thenProcess: boolean) => void
  onPool?: () => void | Promise<void>
  /** Omit the secondary “what to do” line (detail page shows it in the page title). */
  hideQuestionLine?: boolean
  className?: string
}

/**
 * Single primary decision strip: confirm route + create candidate, pick vacancy, pool, or create candidate when unblocked.
 * Used on the list workspace and lead detail — avoids duplicate “Process” / “Quick decision” blocks.
 */
export default function LeadIntakeUnifiedDecisionHeader({
  lead,
  isServicesTenant,
  processing,
  routingBusy,
  poolBusy = false,
  onProcess,
  onPickVacancy,
  onConfirmRouting,
  onPool,
  hideQuestionLine = false,
  className = '',
}: LeadIntakeUnifiedDecisionHeaderProps) {
  const { t } = useI18n()

  if (isServicesTenant || lead.candidate_id) return null

  const canManual = leadSupportsManualProcess(lead)
  if (!canManual) return null

  const tone = intakeWorkspaceHeader(lead, isServicesTenant)
  const { titleKey, hintKey } = headerKeys(tone.tone)
  const title = t(titleKey)
  const hintRaw = t(hintKey)
  const hint = hintRaw !== hintKey ? hintRaw : ''

  const routing = leadRoutingTableAction(lead, isServicesTenant)
  const block = manualProcessBlockHint(lead)
  const st = String(lead.status || '')
    .trim()
    .toLowerCase()

  const norm = lead.normalized && typeof lead.normalized === 'object' && !Array.isArray(lead.normalized) ? lead.normalized : {}
  const ir = (norm as Record<string, unknown>).intake_resolution_v1
  const intakeRejected =
    ir &&
    typeof ir === 'object' &&
    !Array.isArray(ir) &&
    String((ir as { status?: string }).status || '')
      .trim()
      .toLowerCase() === 'rejected'

  const showProcessPrimary =
    routing.kind === 'none' &&
    !block &&
    st !== 'duplicate_review' &&
    !intakeRejected &&
    canManual

  const busy = processing || routingBusy
  const intakeDecisionsAllowed = leadStatusAllowsIntakeDecision(lead)

  return (
    <section className={`space-y-3 ${className}`.trim()}>
      <div>
        <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</h3>
        {hint ? <p className="mt-1 text-sm leading-relaxed text-slate-600">{hint}</p> : null}
        {!hideQuestionLine ? (
          <p className="mt-2 text-xs text-slate-500">{t('app.leads.intake_workspace.question')}</p>
        ) : null}
      </div>

      <div className="flex flex-wrap gap-2">
        {routing.kind === 'confirm_suggested' || routing.kind === 'confirm_current' ? (
          <>
            <button
              type="button"
              className="btn-primary rounded-xl px-3 py-2 text-sm font-semibold disabled:opacity-50"
              disabled={busy || poolBusy}
              onClick={() => onConfirmRouting(routing.vacancyId, true)}
            >
              {busy ? t('common.loading') : t('app.leads.intake_workspace.unified.confirm_and_create')}
            </button>
            <button
              type="button"
              className="btn-secondary rounded-xl px-3 py-2 text-sm font-semibold disabled:opacity-50"
              disabled={busy || poolBusy}
              onClick={onPickVacancy}
            >
              {t('app.leads.intake_workspace.unified.change_vacancy')}
            </button>
          </>
        ) : routing.kind === 'pick_vacancy' ? (
          <>
            <button
              type="button"
              className="btn-primary rounded-xl px-3 py-2 text-sm font-semibold disabled:opacity-50"
              disabled={busy || poolBusy}
              onClick={onPickVacancy}
            >
              {t('app.leads.intake_workspace.unified.pick_vacancy_cta')}
            </button>
            {onPool && intakeDecisionsAllowed ? (
              <button
                type="button"
                className="btn-secondary rounded-xl px-3 py-2 text-sm font-semibold disabled:opacity-50"
                disabled={poolBusy || processing}
                onClick={() => void onPool()}
              >
                {poolBusy ? t('common.loading') : t('app.leads.intake_workspace.actions.to_pool')}
              </button>
            ) : null}
          </>
        ) : null}

        {showProcessPrimary ? (
          <button
            type="button"
            className="btn-primary rounded-xl px-3 py-2 text-sm font-semibold disabled:opacity-50"
            disabled={processing || routingBusy}
            onClick={() => void onProcess()}
          >
            {processing ? t('common.loading') : t('app.leads.intake_workspace.unified.create_candidate')}
          </button>
        ) : null}
      </div>
    </section>
  )
}
