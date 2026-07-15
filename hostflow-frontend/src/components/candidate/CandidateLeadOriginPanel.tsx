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
  candidateNote?: string | null
}

export function CandidateLeadOriginPanel({
  candidateExtra,
  candidateNote,
}: CandidateLeadOriginPanelProps) {
  const { t } = useI18n()
  const extra = record(candidateExtra)
  const continuity = record(extra.lead_continuity_v1)
  const sourceLeadId = text(extra.source_lead_id) || text(continuity.source_lead_id)
  if (!sourceLeadId) return null

  const leadNote = text(continuity.lead_note)
  const intake = record(continuity.intake_resolution_v1)
  const intakeStatus = text(intake.status)
  const intakeSummary = text(intake.summary) || text(intake.note)
  const leadStage = text(continuity.lead_stage)
  const notePreview = leadNote || (candidateNote?.includes('[From lead]') ? candidateNote : '')

  return (
    <section className="rounded-xl border border-brand-100 bg-brand-50/40 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">
            {t('app.candidate_card.from_lead_badge', { defaultValue: 'Converted from lead' })}
          </p>
          <p className="mt-1 text-sm text-slate-700">
            {t('app.candidate_card.from_lead_hint', {
              defaultValue: 'Context from the lead intake is carried here so you do not start from scratch.',
            })}
          </p>
          {notePreview ? (
            <p className="mt-2 whitespace-pre-wrap text-sm font-medium text-slate-900">{notePreview}</p>
          ) : null}
          <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
            {leadStage ? (
              <div>
                <dt className="text-xs text-slate-500">
                  {t('app.candidate_card.from_lead_stage', { defaultValue: 'Lead stage' })}
                </dt>
                <dd className="font-medium text-slate-900">{leadStage}</dd>
              </div>
            ) : null}
            {intakeStatus ? (
              <div>
                <dt className="text-xs text-slate-500">
                  {t('app.candidate_card.from_lead_intake', { defaultValue: 'Intake decision' })}
                </dt>
                <dd className="font-medium text-slate-900">{intakeStatus}</dd>
              </div>
            ) : null}
            {intakeSummary ? (
              <div className="sm:col-span-2">
                <dt className="text-xs text-slate-500">
                  {t('app.candidate_card.from_lead_intake_summary', { defaultValue: 'Intake summary' })}
                </dt>
                <dd className="font-medium text-slate-900">{intakeSummary}</dd>
              </div>
            ) : null}
          </dl>
        </div>
        <Link
          to={`${CRM_APP_PATHS.leads}/${sourceLeadId}`}
          className="btn-secondary btn-sm shrink-0"
        >
          {t('app.clients.open_source_lead', { defaultValue: 'Open lead' })}
        </Link>
      </div>
    </section>
  )
}
