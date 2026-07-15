import { useCallback, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  convertSalesInquiryToClient,
  updateSalesInquiryStage,
} from '../../api/applications'
import LostReasonForLostStageModal from '../../components/leads/LostReasonForLostStageModal'
import { useToast } from '../../components/Toast'
import { useI18n } from '../../i18n'
import { usePlanLimitModal } from '../../contexts/PlanLimitModalContext'
import { getFriendlyErrorInfo } from '../../utils/friendlyError'
import { SALES_HOME_PATH, salesInquiryPath } from '../../app/salesPaths'
import { listSalesInquiries, getSalesInquiry } from '../../api/applications'
import { ApplicationWorkspace, advanceSalesWorkSession, getSalesWorkSession } from '../../platform/application-workspace/ApplicationWorkspace'
import { ApplicationSalesDetailPanel } from '../../platform/application-workspace/ApplicationSalesDetailPanel'
import type { ApplicationWorkspaceConfig } from '../../platform/application-workspace/types'
import { clientDetailPath } from '../../services/platformHandoff'

const SALES_TABS = [
  { id: 'all' as const, label: 'Все' },
  { id: 'new' as const, label: 'Новые' },
  { id: 'in_progress' as const, label: 'В работе' },
  { id: 'waiting' as const, label: 'Ожидают ответа' },
  { id: 'completed' as const, label: 'Завершённые' },
]

export function SalesApplicationWorkspace() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const { notify } = useToast()
  const planLimitModal = usePlanLimitModal()
  const [converting, setConverting] = useState(false)
  const [patching, setPatching] = useState(false)
  const [lostStagePrompt, setLostStagePrompt] = useState(false)
  const [lostTargetId, setLostTargetId] = useState<string | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)

  const handleStageChange = useCallback(
    async (
      applicationId: string,
      stage: string,
      extra?: { lost_reason_code?: string; lost_reason_note?: string },
    ) => {
      setPatching(true)
      try {
        await updateSalesInquiryStage(applicationId, {
          stage: stage as 'contacted' | 'qualified' | 'lost',
          ...extra,
        })
        setRefreshKey((k) => k + 1)
        notify({ title: t('app.leads.inbox.stage_updated', { defaultValue: 'Статус обновлён' }), variant: 'success' })
        if (stage === 'lost') {
          const session = getSalesWorkSession()
          if (session && session.queue[session.index] === applicationId) {
            const nextId = advanceSalesWorkSession()
            if (nextId) window.setTimeout(() => navigate(salesInquiryPath(nextId)), 600)
            else window.setTimeout(() => navigate(SALES_HOME_PATH), 600)
          }
        }
      } catch (err: unknown) {
        if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.leads.detail.stage_update_failed'))) return
        const info = getFriendlyErrorInfo(err, t('app.leads.detail.stage_update_failed'), t)
        notify({ title: info.title, description: [info.detail, info.hint].filter(Boolean).join(' '), variant: 'error' })
      } finally {
        setPatching(false)
      }
    },
    [navigate, notify, planLimitModal, t],
  )

  const config: ApplicationWorkspaceConfig = useMemo(
    () => ({
      module: 'sales',
      objectNamePlural: 'Обращения',
      homePath: SALES_HOME_PATH,
      applicationPath: salesInquiryPath,
      listApplications: listSalesInquiries,
      getApplication: getSalesInquiry,
      tabs: SALES_TABS,
      workSessionSurface: 'sales',
      workSessionKind: 'call',
      heroCallTitle: (count: number) => `Позвонить ${count} новым обращениям`,
      heroCallHint:
        'Откроем обращения по одному: позвонить → выяснить потребность → создать клиента → выбрать услугу.',
      heroEmptyText: 'Нет новых обращений для звонка',
      listKindLabel: 'B2B заявка',
      extensionBadge: (app) => (app.extensions?.service_label as string | undefined) || null,
      primaryEntityPath: (app) => {
        const id = String(app.outcome_entity_id || '').trim()
        return id ? clientDetailPath(id) : undefined
      },
      primaryEntityLabel: t('app.sales_inquiry.open_client_card', { defaultValue: 'Открыть карточку клиента' }),
      renderDetail: ({ application, onRefresh, onClose }) => (
        <ApplicationSalesDetailPanel
          key={`${application.id}-${refreshKey}`}
          application={application}
          converting={converting}
          patching={patching}
          onClose={onClose}
          onRefresh={onRefresh}
          onStage={(stage) => {
            if (stage === 'lost') {
              setLostTargetId(application.id)
              setLostStagePrompt(true)
              return
            }
            void handleStageChange(application.id, stage).then(onRefresh)
          }}
          onConvert={async () => {
            setConverting(true)
            try {
              const updated = await convertSalesInquiryToClient(application.id)
              onRefresh()
              notify({
                title: t('app.client_inquiry.client_created', { defaultValue: 'Компания сохранена в клиенты' }),
                variant: 'success',
              })
              const newClientId = String(updated.outcome_entity_id || '').trim()
              if (newClientId) window.setTimeout(() => navigate(clientDetailPath(newClientId)), 500)
            } catch (err: unknown) {
              if (planLimitModal?.showPlanLimitIfNeeded(err, 'Не удалось создать клиента')) return
              const detail =
                (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail ??
                (err as Error)?.message ??
                'Не удалось создать клиента'
              notify({ title: typeof detail === 'string' ? detail : JSON.stringify(detail), variant: 'error' })
            } finally {
              setConverting(false)
            }
          }}
        />
      ),
    }),
    [converting, patching, refreshKey, handleStageChange, navigate, notify, planLimitModal, t],
  )

  return (
    <>
      <ApplicationWorkspace config={config} routeParam="leadId" />
      {lostStagePrompt && lostTargetId ? (
        <LostReasonForLostStageModal
          open={lostStagePrompt}
          loading={patching}
          hintKey="app.sales_inquiry.lost_hint"
          onCancel={() => {
            setLostStagePrompt(false)
            setLostTargetId(null)
          }}
          onConfirm={(payload) => {
            setLostStagePrompt(false)
            const id = lostTargetId
            setLostTargetId(null)
            if (id) {
              void handleStageChange(id, 'lost', {
                lost_reason_code: payload.lost_reason_code,
                lost_reason_note: payload.lost_reason_note,
              })
            }
          }}
        />
      ) : null}
    </>
  )
}

export default SalesApplicationWorkspace
