import { useCallback, useEffect, useState } from 'react'
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
import { useI18n } from '../../i18n'
import { getFriendlyErrorInfo } from '../../utils/friendlyError'
import { ContextRail } from '../context-rail'
import {
  APPLICATION_STATUS_BADGE,
  APPLICATION_STATUS_TEXT,
  applicationInitial,
} from './applicationDisplay'
import { resolveRecruitmentApplicationDecision } from './resolveRecruitmentApplicationDecision'

const REJECT_REASONS = [
  { code: 'insufficient_experience', label: 'Не подходит' },
  { code: 'no_response', label: 'Не отвечает' },
  { code: 'duplicate_spam', label: 'Дубликат' },
  { code: 'invalid_contact', label: 'Спам' },
  { code: 'other', label: 'Другое' },
] as const

function recruitmentActionErrorMessage(err: unknown, t: (key: string, options?: Record<string, unknown>) => string): string {
  const info = getFriendlyErrorInfo(err, 'Не удалось выполнить действие', t)
  const code = info.code || ''
  const byCode: Record<string, string> = {
    INTAKE_INFO_REQUESTED: 'Ранее запросили данные у кандидата. Повторите «Создать кандидата» после обновления.',
    VACANCY_NOT_CONFIRMED: 'Сначала привяжите подбор в блоке «Вакансия».',
    INTAKE_ROUTING_INCOMPLETE: 'Не хватает маршрутизации: привяжите подбор.',
    LEAD_RODO_REQUIRED: 'Нужно подтвердить RODO перед этим действием.',
    LEAD_INTAKE_ALREADY_REJECTED: 'Отклик уже закрыт.',
    INTAKE_REJECT_REASON_REQUIRED: 'Укажите причину отклонения.',
    LEAD_SOURCE_INTAKE_DECISION_UNSUPPORTED: 'Это действие недоступно для данного источника.',
  }
  const mapped = byCode[code]
  return [mapped || info.title, info.detail, info.hint].filter(Boolean).join(' ')
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
  const [followUpTitle, setFollowUpTitle] = useState('Перезвонить кандидату')
  const [assigneeId, setAssigneeId] = useState(application.assignee_id || '')

  const contactName = application.contact.name || application.title || 'Кандидат'
  const statusKey = application.status
  const vacancyTitle = String(application.extensions?.vacancy_title || application.subtitle || '')
  const candidateId =
    application.outcome_entity_type === 'candidate' ? String(application.outcome_entity_id || '').trim() : ''
  const candidateHref = candidateId ? candidateDetailPath(candidateId) : undefined
  const openCardLabel = t('app.candidates.detail.open_full_profile', { defaultValue: 'Открыть полную карточку' })

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
      const result = await processRecruitmentApplication(application.id)
      notify({ title: 'Кандидат создан', variant: 'success' })
      if (result.candidate_id) {
        navigate(candidateDetailPath(String(result.candidate_id)))
      }
    })
  }, [application.id, navigate, notify, run])

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

  const meta = application.source
    ? `${application.source}${application.created_at ? ` · ${new Date(application.created_at).toLocaleString()}` : ''}`
    : undefined

  const actionDisabled = patching || busy

  return (
    <>
      <ContextRail
        railKind="recruitment"
        header={{
          title: contactName,
          titleHref: candidateHref,
          subtitle: vacancyTitle || 'Новый отклик',
          meta,
          statusLabel: APPLICATION_STATUS_TEXT[statusKey],
          statusClassName: `rounded-full px-2.5 py-0.5 text-xs font-semibold ${APPLICATION_STATUS_BADGE[statusKey]}`,
          entityWorkspaceHref: candidateHref,
          entityWorkspaceLabel: openCardLabel,
        }}
        decision={decision}
        onClose={onClose}
        closeLabel={t('common.close', { defaultValue: 'Закрыть' })}
        contextSlots={{
          vacancy: (
            <div>
              <select
                value={selectedVacancyId}
                onChange={(e) => setSelectedVacancyId(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              >
                <option value="">Выберите подбор</option>
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
                    await confirmRecruitmentApplicationVacancy(application.id, { vacancy_id: selectedVacancyId })
                    notify({ title: 'Подбор привязан', variant: 'success' })
                  })
                }
                className="mt-2 rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium hover:bg-slate-50 disabled:opacity-50"
              >
                Привязать к подбору
              </button>
            </div>
          ),
          assignee: (
            <div className="flex gap-2">
              <input
                value={assigneeId}
                onChange={(e) => setAssigneeId(e.target.value)}
                className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm"
                placeholder="ID пользователя"
              />
              <button
                type="button"
                disabled={!assigneeId.trim() || actionDisabled}
                onClick={() =>
                  void run(async () => {
                    await assignRecruitmentApplication(application.id, { assignee_id: assigneeId.trim() })
                    notify({ title: 'Ответственный назначен', variant: 'success' })
                  })
                }
                className="rounded-lg bg-slate-800 px-3 py-2 text-sm font-medium text-white hover:bg-slate-900 disabled:opacity-50"
              >
                Назначить
              </button>
            </div>
          ),
          outcome: candidateHref ? (
            <Link to={candidateHref} className="text-sm font-semibold text-brand-700 hover:underline" data-entity-link="primary">
              {openCardLabel}
            </Link>
          ) : null,
          contacts: (
            <div className="flex items-center gap-3">
              <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-100 text-sm font-bold text-brand-800">
                {applicationInitial(application)}
              </span>
              <span className="text-sm text-slate-600">{contactName}</span>
            </div>
          ),
        }}
      />

      {showReject ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-5 shadow-xl">
            <h3 className="font-semibold text-slate-900">Отклонить отклик</h3>
            <select
              value={rejectCode}
              onChange={(e) => setRejectCode(e.target.value)}
              className="mt-3 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            >
              {REJECT_REASONS.map((r) => (
                <option key={r.code} value={r.code}>
                  {r.label}
                </option>
              ))}
            </select>
            <textarea
              value={rejectNote}
              onChange={(e) => setRejectNote(e.target.value)}
              placeholder="Комментарий"
              className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              rows={3}
            />
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" onClick={() => setShowReject(false)} className="rounded-lg px-3 py-2 text-sm">
                Отмена
              </button>
              <button
                type="button"
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
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white"
              >
                Отклонить
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {showFollowUp ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-5 shadow-xl">
            <h3 className="font-semibold text-slate-900">Follow-up</h3>
            <input
              value={followUpTitle}
              onChange={(e) => setFollowUpTitle(e.target.value)}
              className="mt-3 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            />
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" onClick={() => setShowFollowUp(false)} className="rounded-lg px-3 py-2 text-sm">
                Отмена
              </button>
              <button
                type="button"
                disabled={busy || !followUpTitle.trim()}
                onClick={() =>
                  void run(async () => {
                    await createRecruitmentApplicationFollowUp(application.id, { title: followUpTitle.trim() })
                    setShowFollowUp(false)
                    notify({ title: 'Напоминание создано', variant: 'success' })
                  })
                }
                className="rounded-lg bg-brand-700 px-4 py-2 text-sm font-semibold text-white"
              >
                Сохранить
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  )
}
