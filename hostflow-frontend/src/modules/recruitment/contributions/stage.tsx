import { useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  createRecruitmentApplicationFollowUp,
  processRecruitmentApplication,
  updateRecruitmentApplicationStage,
} from '../../../api/applications'
import { CRM_APP_PATHS } from '../../../app/crmAppPaths'
import { Button } from '../../../components/ui/Button'
import { useToast } from '../../../components/Toast'
import { useI18n } from '../../../i18n'
import { getFriendlyErrorInfo } from '../../../utils/friendlyError'
import { ContextRailDecisionZone } from '../../../platform/context-rail'
import { resolveRecruitmentApplicationDecision } from '../../../platform/application-workspace/resolveRecruitmentApplicationDecision'
import type { WorkspaceCapabilityRenderContext } from '../../../platform/workspace-capability/renderContext'

const REJECT_REASON_CODES = [
  'insufficient_experience',
  'no_response',
  'duplicate_spam',
  'invalid_contact',
  'other',
] as const

function recruitmentActionErrorMessage(err: unknown, t: (key: string, options?: Record<string, unknown>) => string): string {
  const info = getFriendlyErrorInfo(err, t('app.recruitment.contributions.action_failed'), t)
  const code = String(info.code || '').toUpperCase()
  const mapped = t(`app.recruitment.contributions.err.${code}`, { defaultValue: '' })
  return [mapped || info.title, info.detail, info.hint].filter(Boolean).join(' ')
}

function processResultError(message: string | null | undefined): { response: { data: { detail: { code: string } } } } {
  return { response: { data: { detail: { code: String(message || 'NO_INTAKE_CONTEXT') } } } }
}

function candidateDetailPath(candidateId: string): string {
  return `${CRM_APP_PATHS.candidates}/${encodeURIComponent(candidateId)}`
}

/** Recruitment owns stage/decision semantics. Host only places this contribution. */
export function RecruitmentStageContribution({
  application,
  patching,
  onRefresh,
  onStage,
}: WorkspaceCapabilityRenderContext) {
  const { t } = useI18n()
  const { notify } = useToast()
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  const [showReject, setShowReject] = useState(false)
  const [rejectCode, setRejectCode] = useState('insufficient_experience')
  const [rejectNote, setRejectNote] = useState('')
  const [showFollowUp, setShowFollowUp] = useState(false)
  const [followUpTitle, setFollowUpTitle] = useState('')

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
    if (!application) return
    void run(async () => {
      const result = await processRecruitmentApplication(application.id)
      if (!result.candidate_id) {
        notify({
          title: recruitmentActionErrorMessage(processResultError(result.message), t),
          variant: 'error',
        })
        return
      }
      notify({ title: t('app.recruitment.contributions.candidate_created'), variant: 'success' })
      navigate(candidateDetailPath(String(result.candidate_id)))
    })
  }, [application, navigate, notify, run, t])

  if (!application || !onStage) return null

  const decision = resolveRecruitmentApplicationDecision({
    application,
    patching,
    busy,
    onStage,
    onCreateCandidate: createCandidate,
    onFollowUp: () => {
      setFollowUpTitle((prev) => prev || t('app.recruitment.contributions.followup_default'))
      setShowFollowUp(true)
    },
    onReject: () => setShowReject(true),
    t,
  })

  return (
    <div data-capability-id="recruitment.stage" data-widget-class="decision_zone">
      <ContextRailDecisionZone decision={decision} />
      {showReject ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md border border-slate-200 bg-white p-4 shadow-xl">
            <h3 className="font-semibold text-slate-900">{t('app.recruitment.contributions.reject_title')}</h3>
            <select
              value={rejectCode}
              onChange={(event) => setRejectCode(event.target.value)}
              className="input mt-3"
            >
              {REJECT_REASON_CODES.map((code) => (
                <option key={code} value={code}>
                  {t(`app.recruitment.contributions.reason.${code}`)}
                </option>
              ))}
            </select>
            <textarea
              value={rejectNote}
              onChange={(event) => setRejectNote(event.target.value)}
              placeholder={t('app.recruitment.contributions.comment_placeholder')}
              className="textarea mt-2"
              rows={3}
            />
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="ghost" size="sm" onClick={() => setShowReject(false)}>
                {t('common.cancel')}
              </Button>
              <Button
                variant="danger"
                size="sm"
                disabled={busy}
                onClick={() =>
                  void run(async () => {
                    await updateRecruitmentApplicationStage(application.id, {
                      stage: 'lost',
                      lost_reason_code: rejectCode,
                      lost_reason_note: rejectNote || undefined,
                    })
                    setShowReject(false)
                    notify({ title: t('app.recruitment.contributions.rejected'), variant: 'success' })
                  })
                }
              >
                {t('app.recruitment.contributions.reject')}
              </Button>
            </div>
          </div>
        </div>
      ) : null}
      {showFollowUp ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md border border-slate-200 bg-white p-4 shadow-xl">
            <h3 className="font-semibold text-slate-900">Follow-up</h3>
            <input value={followUpTitle} onChange={(event) => setFollowUpTitle(event.target.value)} className="input mt-3" />
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="ghost" size="sm" onClick={() => setShowFollowUp(false)}>
                {t('common.cancel')}
              </Button>
              <Button
                variant="primary"
                size="sm"
                disabled={busy || !followUpTitle.trim()}
                onClick={() =>
                  void run(async () => {
                    await createRecruitmentApplicationFollowUp(application.id, { title: followUpTitle.trim() })
                    setShowFollowUp(false)
                    notify({ title: t('app.recruitment.contributions.reminder_created'), variant: 'success' })
                  })
                }
              >
                {t('common.save')}
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
