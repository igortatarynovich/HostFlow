import { Link } from 'react-router-dom'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'

type IntakeRecord = Record<string, unknown>

function record(value: unknown): IntakeRecord {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as IntakeRecord) : {}
}

function text(value: unknown): string {
  if (value == null) return ''
  return String(value).trim()
}

export type CandidateLeadOriginPanelProps = {
  candidateExtra: IntakeRecord | null | undefined
}

export function CandidateLeadOriginPanel({ candidateExtra }: CandidateLeadOriginPanelProps) {
  const { t } = useI18n()
  const extra = record(candidateExtra)
  const continuity = record(extra.lead_continuity_v1)
  const sourceLeadId = text(extra.source_lead_id) || text(continuity.source_lead_id)
  if (!sourceLeadId) return null

  return (
    <div className="flex justify-end">
      <Link to={`${CRM_APP_PATHS.leads}/${sourceLeadId}`} className="btn-secondary btn-sm shrink-0">
        {t('app.clients.open_source_lead', { defaultValue: 'Open lead' })}
      </Link>
    </div>
  )
}
