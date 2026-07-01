import { Link } from 'react-router-dom'

import type { Lead } from '../../api/types'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'
import { formatLeadPipelineError } from '../../utils/leadPipelineErrors'
import { manualProcessBlockHint, manualProcessBlockedUserMessage } from '../../utils/intakeResolution'
import { leadSupportsManualProcess } from '../../utils/leadCrm'
import { formatQualificationReasonLabel, readLeadQualificationPreview } from '../../utils/leadQualificationPreview'

export type { LeadQualificationPreviewV1 } from '../../utils/leadQualificationPreview'

type Props = {
  lead: Lead
  /** Hide for services / client-lead flows */
  isServicesTenant?: boolean
  onProcess?: () => void
  processing?: boolean
  className?: string
  /** When the parent already shows Primary Process (e.g. lead detail header). */
  hideProcessButton?: boolean
}

/**
 * §2.10 Assisted: show suggested vacancy + fit from normalized.lead_qualification_preview_v1;
 * Automatic blocks: LEAD_FIT_* on lead.error.
 */
export default function LeadQualificationSuggestionPanel({
  lead,
  isServicesTenant = false,
  onProcess,
  processing = false,
  className = '',
  hideProcessButton = false,
}: Props) {
  const { t } = useI18n()

  if (isServicesTenant || lead.candidate_id) return null

  const preview = readLeadQualificationPreview(lead.normalized)
  const err = lead.error?.trim() || ''
  const isFitBlock = err === 'LEAD_FIT_NO_MATCH' || err === 'LEAD_FIT_NEEDS_INFO'
  const manualPipeline = leadSupportsManualProcess(lead)
  const manualProcessStatuses =
    lead.status === 'needs_routing' ||
    lead.status === 'new' ||
    lead.status === 'failed' ||
    lead.status === 'duplicate_review'
  if (!preview && !isFitBlock && !(manualPipeline && manualProcessStatuses)) return null

  const intakeProcessBlock = manualProcessBlockHint(lead)

  const blocked = Boolean(preview?.blocked_auto_convert) || isFitBlock
  const processCtaKey =
    blocked ? 'app.leads.qualification.accept_process_cta' : 'app.leads.qualification.process_cta'
  const titleKey = blocked ? 'app.leads.qualification.title_blocked' : 'app.leads.qualification.title_suggested'
  const fitStatus = preview?.fit_status || null
  const showProcess =
    !hideProcessButton &&
    typeof onProcess === 'function' &&
    manualPipeline &&
    !lead.candidate_id &&
    (lead.status === 'needs_routing' ||
      lead.status === 'new' ||
      lead.status === 'failed' ||
      lead.status === 'duplicate_review')

  return (
    <div
      className={`rounded-lg border p-3 text-sm ${
        blocked ? 'border-amber-200 bg-amber-50/90 text-amber-950' : 'border-brand-200/80 bg-brand-50/40 text-slate-800'
      } ${className}`.trim()}
    >
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-600">{t(titleKey)}</div>
      {isFitBlock ? (
        <p className="mt-1 text-sm text-slate-800">{formatLeadPipelineError(err, t)}</p>
      ) : null}
      {preview ? (
        <>
          <div className="mt-2 space-y-1 text-slate-800">
            <div>
              <span className="font-medium text-slate-600">{t('app.leads.qualification.vacancy_line')}: </span>
              {lead.vacancy_title || lead.vacancy_id || preview.suggested_vacancy_id || '—'}
            </div>
            {fitStatus ? (
              <div>
                <span className="font-medium text-slate-600">{t('app.leads.qualification.fit_status_label')}: </span>
                {(() => {
                  const k = `app.leads.qualification.fit_status.${fitStatus}`
                  const tr = t(k)
                  return tr === k ? fitStatus : tr
                })()}
              </div>
            ) : null}
          </div>
          {preview.fit_reasons && preview.fit_reasons.length > 0 ? (
            <div className="mt-2">
              <div className="text-xs font-medium text-slate-600">{t('app.leads.qualification.reasons_title')}</div>
              <ul className="mt-1 list-inside list-disc text-xs text-slate-700">
                {preview.fit_reasons.map((r) => (
                  <li key={r}>{formatQualificationReasonLabel(r, t)}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </>
      ) : null}
      <div className="mt-3 flex flex-wrap gap-2">
        {showProcess ? (
          <button
            type="button"
            className="btn-primary h-8 rounded-lg px-3 text-xs"
            disabled={processing || Boolean(intakeProcessBlock)}
            title={
              intakeProcessBlock ? manualProcessBlockedUserMessage(t, intakeProcessBlock) : undefined
            }
            onClick={() => onProcess?.()}
          >
            {processing ? t('common.loading') : t(processCtaKey)}
          </button>
        ) : null}
        <Link
          to={`${CRM_APP_PATHS.settingsIntegrationsMeta}?tab=settings`}
          className="btn-secondary inline-flex h-8 items-center rounded-lg px-3 text-xs"
        >
          {t('app.leads.qualification.open_meta_settings')}
        </Link>
        <Link to={CRM_APP_PATHS.vacancies} className="btn-secondary inline-flex h-8 items-center rounded-lg px-3 text-xs">
          {t('app.leads.qualification.open_vacancies')}
        </Link>
      </div>
      <p className="mt-2 text-[11px] text-slate-600">{t('app.leads.qualification.footer_hint')}</p>
    </div>
  )
}
