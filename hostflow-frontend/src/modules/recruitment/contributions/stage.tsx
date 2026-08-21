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

const REJECT_REASONS = [
  { code: 'insufficient_experience', label: 'Не подходит' },
  { code: 'no_response', label: 'Не отвечает' },
  { code: 'duplicate_spam', label: 'Дубликат' },
  { code: 'invalid_contact', label: 'Спам' },
  { code: 'other', label: 'Другое' },
] as const

function recruitmentActionErrorMessage(err: unknown, t: (key: string, options?: Record<string, unknown>) => string): string {
  const info = getFriendlyErrorInfo(err, 'Не удалось выполнить действие', t)
  const code = String(info.code || '').toUpperCase()
  const byCode: Record<string, string> = {
    INTAKE_INFO_REQUESTED: 'Ранее запросили данные у кандидата. Повторите «Создать кандидата» после обновления.',
    VACANCY_NOT_CONFIRMED: 'Сначала привяжите подбор в блоке «Вакансия».',
    INTAKE_ROUTING_INCOMPLETE: 'Не хватает маршрутизации: привяжите подбор.',
    INTAKE_POOL_PATH_REQUIRED: 'Сначала привяжите подбор в блоке «Вакансия», затем снова нажмите «Создать кандидата».',
    NO_INTAKE_CONTEXT:
      'Не удалось создать кандидата: у отклика нет полного intake-контекста. Привяжите актуальный подбор и повторите, либо откройте карточку лида для маршрутизации.',
    LEAD_RODO_REQUIRED: 'Нужно подтвердить согласие перед этим действием.',
    LEAD_INTAKE_ALREADY_REJECTED: 'Отклик уже закрыт.',
    INTAKE_REJECT_REASON_REQUIRED: 'Укажите причину отклонения.',
    LEAD_SOURCE_INTAKE_DECISION_UNSUPPORTED: 'Это действие недоступно для данного источника.',
  }
  const mapped = byCode[code]
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
  const [followUpTitle, setFollowUpTitle] = useState('Перезвонить кандидату')

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
      notify({ title: 'Кандидат создан', variant: 'success' })
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
    onFollowUp: () => setShowFollowUp(true),
    onReject: () => setShowReject(true),
    t,
  })

  return (
    <div data-capability-id="recruitment.stage" data-widget-class="decision_zone">
      <ContextRailDecisionZone decision={decision} />
      {showReject ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md border border-slate-200 bg-white p-4 shadow-xl">
            <h3 className="font-semibold text-slate-900">Отклонить отклик</h3>
            <select
              value={rejectCode}
              onChange={(event) => setRejectCode(event.target.value)}
              className="input mt-3"
            >
              {REJECT_REASONS.map((reason) => (
                <option key={reason.code} value={reason.code}>
                  {reason.label}
                </option>
              ))}
            </select>
            <textarea
              value={rejectNote}
              onChange={(event) => setRejectNote(event.target.value)}
              placeholder="Комментарий"
              className="textarea mt-2"
              rows={3}
            />
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="ghost" size="sm" onClick={() => setShowReject(false)}>
                Отмена
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
                    notify({ title: 'Отклик отклонён', variant: 'success' })
                  })
                }
              >
                Отклонить
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
                Отмена
              </Button>
              <Button
                variant="primary"
                size="sm"
                disabled={busy || !followUpTitle.trim()}
                onClick={() =>
                  void run(async () => {
                    await createRecruitmentApplicationFollowUp(application.id, { title: followUpTitle.trim() })
                    setShowFollowUp(false)
                    notify({ title: 'Напоминание создано', variant: 'success' })
                  })
                }
              >
                Сохранить
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
