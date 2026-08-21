import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import type { Application } from '../../api/types/application'
import {
  assignRecruitmentApplication,
  confirmRecruitmentApplicationVacancy,
  createRecruitmentApplicationFollowUp,
  processRecruitmentApplication,
  updateRecruitmentApplicationStage,
} from '../../api/applications'
import { listVacancies } from '../../api/client'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useToast } from '../../components/Toast'
import { useI18n, type TranslateFn } from '../../i18n'
import { getFriendlyErrorInfo } from '../../utils/friendlyError'
import { ContextRail } from '../context-rail'
import {
  APPLICATION_STATUS_BADGE,
  applicationInitial,
  applicationStatusLabel,
} from './applicationDisplay'
import { ApplicationCommentsSection } from './ApplicationCommentsSection'
import { ApplicationRodoSection } from './ApplicationRodoSection'
import { ApplicationStageSection } from './ApplicationStageSection'
import { applicationRodoState } from './applicationRail'
import { resolveRecruitmentApplicationDecision } from './resolveRecruitmentApplicationDecision'

const REJECT_REASON_CODES = [
  'insufficient_experience',
  'no_response',
  'duplicate_spam',
  'invalid_contact',
  'other',
] as const

const REJECT_REASON_DEFAULTS: Record<(typeof REJECT_REASON_CODES)[number], string> = {
  insufficient_experience: 'Not a fit',
  no_response: 'No response',
  duplicate_spam: 'Duplicate',
  invalid_contact: 'Spam',
  other: 'Other',
}

const RECRUITMENT_ERROR_CODES = [
  'INTAKE_INFO_REQUESTED',
  'VACANCY_NOT_CONFIRMED',
  'INTAKE_ROUTING_INCOMPLETE',
  'INTAKE_POOL_PATH_REQUIRED',
  'NO_INTAKE_CONTEXT',
  'LEAD_RODO_REQUIRED',
  'LEAD_INTAKE_ALREADY_REJECTED',
  'INTAKE_REJECT_REASON_REQUIRED',
  'LEAD_SOURCE_INTAKE_DECISION_UNSUPPORTED',
] as const

const RECRUITMENT_ERROR_DEFAULTS: Record<(typeof RECRUITMENT_ERROR_CODES)[number], string> = {
  INTAKE_INFO_REQUESTED:
    'Candidate data was requested earlier. Retry “Create candidate” after it is updated.',
  VACANCY_NOT_CONFIRMED: 'Link a vacancy in the Vacancy block first.',
  INTAKE_ROUTING_INCOMPLETE: 'Routing is incomplete: link a vacancy.',
  INTAKE_POOL_PATH_REQUIRED:
    'Link a vacancy in the Vacancy block, then press “Create candidate” again.',
  NO_INTAKE_CONTEXT:
    'Could not create a candidate: this application is missing full intake context. Link a current vacancy and retry.',
  LEAD_RODO_REQUIRED: 'Confirm RODO before this action.',
  LEAD_INTAKE_ALREADY_REJECTED: 'Application is already closed.',
  INTAKE_REJECT_REASON_REQUIRED: 'Provide a rejection reason.',
  LEAD_SOURCE_INTAKE_DECISION_UNSUPPORTED: 'This action is not available for this source.',
}

function recruitmentActionErrorMessage(err: unknown, t: TranslateFn): string {
  const info = getFriendlyErrorInfo(
    err,
    t('app.recruitment_inquiry.action_failed', { defaultValue: 'Action failed' }),
    t,
  )
  const code = String(info.code || '').toUpperCase()
  const mapped =
    code in RECRUITMENT_ERROR_DEFAULTS
      ? t(`app.recruitment_inquiry.errors.${code}`, {
          defaultValue: RECRUITMENT_ERROR_DEFAULTS[code as keyof typeof RECRUITMENT_ERROR_DEFAULTS],
        })
      : undefined
  return [mapped || info.title, info.detail, info.hint].filter(Boolean).join(' ')
}

function processResultError(message: string | null | undefined): { response: { data: { detail: { code: string } } } } {
  return { response: { data: { detail: { code: String(message || 'NO_INTAKE_CONTEXT') } } } }
}

function candidateDetailPath(candidateId: string): string {
  return `${CRM_APP_PATHS.candidates}/${encodeURIComponent(candidateId)}`
}

export type ApplicationRecruitmentDetailPanelProps = {
  application: Application
  patching: boolean
  onClose: () => void
  onRefresh: () => void
  onStage: (stage: 'contacted' | 'qualified' | 'lost') => void | Promise<void>
}

export function ApplicationRecruitmentDetailPanel({
  application,
  patching,
  onClose,
  onRefresh,
  onStage,
}: ApplicationRecruitmentDetailPanelProps) {
  const { t } = useI18n()
  const { notify } = useToast()
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  const [vacancies, setVacancies] = useState<Array<{ id: string; title: string }>>([])
  const [selectedVacancyId, setSelectedVacancyId] = useState(String(application.extensions?.vacancy_id || ''))
  const [showReject, setShowReject] = useState(false)
  const [rejectCode, setRejectCode] = useState('insufficient_experience')
  const [rejectNote, setRejectNote] = useState('')
  const [showFollowUp, setShowFollowUp] = useState(false)
  const [followUpTitle, setFollowUpTitle] = useState(() =>
    t('app.recruitment_inquiry.follow_up_default_title', { defaultValue: 'Call the candidate back' }),
  )
  const [assigneeId, setAssigneeId] = useState(application.assignee_id || '')
  const [appState, setAppState] = useState(application)

  useEffect(() => {
    setAppState(application)
    setSelectedVacancyId(String(application.extensions?.vacancy_id || ''))
    setAssigneeId(application.assignee_id || '')
  }, [application])

  const rejectReasons = useMemo(
    () =>
      REJECT_REASON_CODES.map((code) => ({
        code,
        label: t(`app.recruitment_inquiry.reject_reasons.${code}`, {
          defaultValue: REJECT_REASON_DEFAULTS[code],
        }),
      })),
    [t],
  )

  const contactName =
    appState.contact.name ||
    appState.title ||
    t('app.recruitment_inquiry.candidate_fallback', { defaultValue: 'Candidate' })
  const statusKey = appState.status
  const vacancyTitle = String(appState.extensions?.vacancy_title || appState.subtitle || '')
  const candidateId =
    appState.outcome_entity_type === 'candidate' ? String(appState.outcome_entity_id || '').trim() : ''
  const candidateHref = candidateId ? candidateDetailPath(candidateId) : undefined
  const openCardLabel = t('app.candidates.detail.open_full_profile', { defaultValue: 'Open full card' })
  const contactPhone = appState.contact.phone?.trim() || ''
  const contactEmail = appState.contact.email?.trim() || ''
  const telHref = contactPhone ? `tel:${contactPhone.replace(/\s/g, '')}` : null

  useEffect(() => {
    let cancelled = false
    void listVacancies({ limit: 30 }).then((res) => {
      if (cancelled) return
      const items = Array.isArray(res) ? res : (res as { items?: Array<{ id: string; title?: string }> })?.items ?? []
      setVacancies(items.map((v) => ({ id: String(v.id), title: String(v.title || v.id) })))
    })
    return () => {
      cancelled = true
    }
  }, [])

  const run = useCallback(
    async (fn: () => Promise<void>) => {
      setBusy(true)
      try {
        await fn()
        onRefresh()
      } catch (err: unknown) {
        notify({ title: recruitmentActionErrorMessage(err, t), variant: 'error' })
      } finally {
        setBusy(false)
      }
    },
    [notify, onRefresh, t],
  )

  const createCandidate = useCallback(() => {
    void run(async () => {
      const result = await processRecruitmentApplication(appState.id)
      if (!result.candidate_id) {
        notify({
          title: recruitmentActionErrorMessage(processResultError(result.message), t),
          variant: 'error',
        })
        return
      }
      notify({
        title: t('app.recruitment_inquiry.candidate_created', { defaultValue: 'Candidate created' }),
        variant: 'success',
      })
      navigate(candidateDetailPath(String(result.candidate_id)))
    })
  }, [appState.id, navigate, notify, run, t])

  const applyApp = useCallback(
    (next: Application) => {
      setAppState(next)
      onRefresh()
    },
    [onRefresh],
  )

  const decision = resolveRecruitmentApplicationDecision({
    application: appState,
    patching,
    busy,
    rodoSatisfied: applicationRodoState(appState).satisfied,
    onStage,
    onCreateCandidate: createCandidate,
    onFollowUp: () => setShowFollowUp(true),
    onReject: () => setShowReject(true),
    t,
  })

  const meta = appState.source
    ? `${appState.source}${appState.created_at ? ` · ${new Date(appState.created_at).toLocaleString()}` : ''}`
    : undefined

  const actionDisabled = patching || busy

  return (
    <>
      <ContextRail
        railKind="recruitment"
        header={{
          title: contactName,
          titleHref: candidateHref,
          subtitle:
            vacancyTitle ||
            t('app.recruitment_inquiry.new_application', { defaultValue: 'New application' }),
          meta,
          statusLabel: applicationStatusLabel(statusKey, t),
          statusClassName: `rounded-full px-3 py-0.5 text-xs font-semibold ${APPLICATION_STATUS_BADGE[statusKey]}`,
          entityWorkspaceHref: candidateHref,
          entityWorkspaceLabel: openCardLabel,
        }}
        decision={decision}
        onClose={onClose}
        closeLabel={t('common.close', { defaultValue: 'Close' })}
        contextSlots={{
          workflow: (
            <ApplicationStageSection
              application={appState}
              disabled={actionDisabled}
              onStage={(stage) => void onStage(stage)}
              onReject={() => setShowReject(true)}
            />
          ),
          vacancy: (
            <div>
              <select
                value={selectedVacancyId}
                onChange={(e) => setSelectedVacancyId(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              >
                <option value="">
                  {t('app.recruitment_inquiry.select_vacancy', { defaultValue: 'Select a vacancy' })}
                </option>
                {vacancies.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.title}
                  </option>
                ))}
              </select>
              <button
                type="button"
                disabled={!selectedVacancyId || actionDisabled}
                onClick={() =>
                  void run(async () => {
                    await confirmRecruitmentApplicationVacancy(appState.id, { vacancy_id: selectedVacancyId })
                    notify({
                      title: t('app.recruitment_inquiry.vacancy_linked', { defaultValue: 'Vacancy linked' }),
                      variant: 'success',
                    })
                  })
                }
                className="mt-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium hover:bg-slate-50 disabled:opacity-50"
              >
                {t('app.recruitment_inquiry.link_vacancy', { defaultValue: 'Link to vacancy' })}
              </button>
            </div>
          ),
          assignee: (
            <div className="flex gap-2">
              <input
                value={assigneeId}
                onChange={(e) => setAssigneeId(e.target.value)}
                className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm"
                placeholder={t('app.recruitment_inquiry.assignee_placeholder', {
                  defaultValue: 'User ID',
                })}
              />
              <button
                type="button"
                disabled={!assigneeId.trim() || actionDisabled}
                onClick={() =>
                  void run(async () => {
                    await assignRecruitmentApplication(appState.id, { assignee_id: assigneeId.trim() })
                    notify({
                      title: t('app.recruitment_inquiry.assignee_set', { defaultValue: 'Assignee set' }),
                      variant: 'success',
                    })
                  })
                }
                className="rounded-lg bg-slate-800 px-3 py-2 text-sm font-medium text-white hover:bg-slate-900 disabled:opacity-50"
              >
                {t('app.recruitment_inquiry.assign', { defaultValue: 'Assign' })}
              </button>
            </div>
          ),
          outcome: candidateHref ? (
            <Link to={candidateHref} className="text-sm font-semibold text-brand-700 hover:underline" data-entity-link="primary">
              {openCardLabel}
            </Link>
          ) : null,
          contacts: (
            <div className="flex items-start gap-3">
              <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-100 text-sm font-bold text-brand-800">
                {applicationInitial(appState)}
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-slate-800">{contactName}</p>
                {telHref ? (
                  <a href={telHref} className="mt-1 block break-all text-lg font-semibold text-slate-900 hover:text-brand-700">
                    {contactPhone}
                  </a>
                ) : null}
                {contactEmail ? (
                  <a href={`mailto:${contactEmail}`} className="mt-1 block truncate text-sm text-slate-600 hover:text-brand-700">
                    {contactEmail}
                  </a>
                ) : null}
              </div>
            </div>
          ),
          summary: (
            <div className="space-y-5">
              <ApplicationRodoSection application={appState} disabled={actionDisabled} onUpdated={applyApp} />
              <ApplicationCommentsSection application={appState} disabled={actionDisabled} onUpdated={applyApp} />
            </div>
          ),
        }}
        contextTitles={{
          workflow: t('app.recruitment_inquiry.rail.stages', { defaultValue: 'Stage' }),
          summary: t('app.recruitment_inquiry.rail.work', { defaultValue: 'RODO and comments' }),
          contacts: t('app.context_rail.blocks.contacts', { defaultValue: 'Contact' }),
        }}
      />

      {showReject ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-xl bg-white p-4 shadow-xl">
            <h3 className="font-semibold text-slate-900">
              {t('app.recruitment_inquiry.reject_title', { defaultValue: 'Reject application' })}
            </h3>
            <select
              value={rejectCode}
              onChange={(e) => setRejectCode(e.target.value)}
              className="mt-3 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            >
              {rejectReasons.map((r) => (
                <option key={r.code} value={r.code}>
                  {r.label}
                </option>
              ))}
            </select>
            <textarea
              value={rejectNote}
              onChange={(e) => setRejectNote(e.target.value)}
              placeholder={t('app.recruitment_inquiry.reject_comment', { defaultValue: 'Comment' })}
              className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              rows={3}
            />
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" onClick={() => setShowReject(false)} className="rounded-lg px-3 py-2 text-sm">
                {t('common.actions.cancel', { defaultValue: 'Cancel' })}
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() =>
                  void run(async () => {
                    await updateRecruitmentApplicationStage(appState.id, {
                      stage: 'lost',
                      lost_reason_code: rejectCode,
                      lost_reason_note: rejectNote || undefined,
                    })
                    setShowReject(false)
                    notify({
                      title: t('app.recruitment_inquiry.rejected', { defaultValue: 'Application rejected' }),
                      variant: 'success',
                    })
                  })
                }
                className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-semibold text-white"
              >
                {t('app.recruitment_inquiry.reject', { defaultValue: 'Reject' })}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {showFollowUp ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-xl bg-white p-4 shadow-xl">
            <h3 className="font-semibold text-slate-900">Follow-up</h3>
            <input
              value={followUpTitle}
              onChange={(e) => setFollowUpTitle(e.target.value)}
              className="mt-3 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            />
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" onClick={() => setShowFollowUp(false)} className="rounded-lg px-3 py-2 text-sm">
                {t('common.actions.cancel', { defaultValue: 'Cancel' })}
              </button>
              <button
                type="button"
                disabled={busy || !followUpTitle.trim()}
                onClick={() =>
                  void run(async () => {
                    await createRecruitmentApplicationFollowUp(appState.id, { title: followUpTitle.trim() })
                    setShowFollowUp(false)
                    notify({
                      title: t('app.recruitment_inquiry.follow_up_created', {
                        defaultValue: 'Reminder created',
                      }),
                      variant: 'success',
                    })
                  })
                }
                className="rounded-lg bg-brand-700 px-4 py-2 text-sm font-semibold text-white"
              >
                {t('common.actions.save', { defaultValue: 'Save' })}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  )
}
