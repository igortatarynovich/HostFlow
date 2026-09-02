import { Link } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../../app/crmAppPaths'
import { useI18n } from '../../../i18n'
import type { WorkspaceCapabilityRenderContext } from '../../workspace-capability/renderContext'

function candidateDetailPath(candidateId: string): string {
  return `${CRM_APP_PATHS.candidates}/${encodeURIComponent(candidateId)}`
}

export function IdentityCapability({ application }: WorkspaceCapabilityRenderContext) {
  const { t } = useI18n()
  if (!application) return null
  const contactName = application.contact.name || application.title || 'Кандидат'
  const vacancyTitle = String(application.extensions?.vacancy_title || application.subtitle || '')
  const outcomeType = String(application.outcome_entity_type || '').trim()
  const outcomeId = String(application.outcome_entity_id || '').trim()
  const candidateId = outcomeType === 'candidate' || (!outcomeType && outcomeId) ? outcomeId : ''
  const candidateHref = candidateId ? candidateDetailPath(candidateId) : undefined
  const meta = application.source
    ? `${application.source}${application.created_at ? ` · ${new Date(application.created_at).toLocaleString()}` : ''}`
    : undefined
  const openCardLabel = t('app.candidates.detail.open_full_profile', { defaultValue: 'Открыть полную карточку' })

  return (
    <div className="min-w-0 flex-1" data-capability-id="identity">
      {candidateHref ? (
        <Link
          to={candidateHref}
          className="text-sm font-semibold text-brand-700 hover:text-brand-800 hover:underline"
          data-entity-link="primary"
        >
          {contactName}
        </Link>
      ) : (
        <h2 className="text-sm font-semibold text-slate-900">{contactName}</h2>
      )}
      <p className="mt-0.5 truncate text-xs text-slate-500">{vacancyTitle || t('app.recruitment_inquiry.workspace.new_application')}</p>
      {application.contact.phone ? (
        <p className="mt-0.5 text-xs font-medium text-slate-800">{application.contact.phone}</p>
      ) : null}
      {meta ? <p className="mt-0.5 truncate text-[11px] text-slate-400">{meta}</p> : null}
      {candidateHref ? (
        <Link to={candidateHref} className="mt-1 inline-flex text-xs font-medium text-brand-700 hover:underline" data-entity-link="primary">
          {openCardLabel}
        </Link>
      ) : null}
    </div>
  )
}
