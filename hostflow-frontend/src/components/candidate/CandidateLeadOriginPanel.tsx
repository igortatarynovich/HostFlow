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
  const call = record(continuity.call_result_v1)
  const callResult = text(call.result)
  const callNote = text(call.note)
  const callHistoryRaw = continuity.call_results_v1
  const callHistory = Array.isArray(callHistoryRaw)
    ? callHistoryRaw.filter((item): item is IntakeRecord => Boolean(item && typeof item === 'object'))
    : []
  const answersRaw = extra.intake_answers_v1 || continuity.intake_answers_v1
  const answers = Array.isArray(answersRaw)
    ? answersRaw.filter((item): item is IntakeRecord => Boolean(item && typeof item === 'object'))
    : []
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
            {callHistory.length === 0 && callResult ? (
              <div>
                <dt className="text-xs text-slate-500">
                  {t('app.candidate_card.from_lead_call', { defaultValue: 'Lead call result' })}
                </dt>
                <dd className="font-medium text-slate-900">
                  {t(`app.leads.detail.call_result.results.${callResult}`, { defaultValue: callResult })}
                  {callNote ? ` — ${callNote}` : ''}
                </dd>
              </div>
            ) : null}
            {callHistory.length > 0 ? (
              <div className="sm:col-span-2">
                <dt className="text-xs text-slate-500">
                  {t('app.candidate_card.from_lead_calls', { defaultValue: 'Call history' })}
                </dt>
                <dd className="font-medium text-slate-900">
                  <ul className="mt-1 space-y-1 text-sm">
                    {callHistory.map((item, idx) => {
                      const result = text(item.result)
                      const at = text(item.at)
                      const nextAt = text(item.next_contact_at)
                      return (
                        <li key={`${at}-${idx}`}>
                          {t(`app.leads.detail.call_result.results.${result}`, { defaultValue: result })}
                          {text(item.note) ? ` — ${text(item.note)}` : ''}
                          {at ? <span className="text-slate-500"> · {new Date(at).toLocaleString()}</span> : null}
                          {nextAt ? (
                            <span className="text-slate-500">
                              {' '}
                              · {t('app.leads.intake_workspace.call.next_contact', { defaultValue: 'Next contact' })}{' '}
                              {new Date(nextAt).toLocaleString()}
                            </span>
                          ) : null}
                        </li>
                      )
                    })}
                  </ul>
                </dd>
              </div>
            ) : null}
            {answers.length > 0 ? (
              <div className="sm:col-span-2">
                <dt className="text-xs text-slate-500">
                  {t('app.candidate_card.from_lead_answers', { defaultValue: 'Original questionnaire' })}
                </dt>
                <dd className="font-medium text-slate-900">
                  <ul className="mt-1 space-y-1 text-sm">
                    {answers.slice(0, 12).map((item, idx) => {
                      const label = text(item.label) || text(item.name) || `#${idx}`
                      const values = item.values
                      const value = Array.isArray(values) ? values.map((v) => String(v)).join(', ') : text(values)
                      return (
                        <li key={`${label}-${idx}`}>
                          <span className="text-slate-500">{label}:</span> {value}
                        </li>
                      )
                    })}
                  </ul>
                </dd>
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
