import { useCallback, useEffect, useState } from 'react'
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom'
import { IconArrowLeft } from '@tabler/icons-react'
import { convertClientLeadToClient, getLead, updateLeadStage } from '../../api/client'
import type { Lead } from '../../api/types'
import { clientAcquisitionChannelPath } from '../../app/clientAcquisitionPaths'
import ClientLeadDetailView from '../../components/leads/ClientLeadDetailView'
import SalesQuestionnairePanel from '../../components/leads/SalesQuestionnairePanel'
import LostReasonForLostStageModal from '../../components/leads/LostReasonForLostStageModal'
import { useToast } from '../../components/Toast'
import { useI18n, type LocaleCode } from '../../i18n'
import { usePlanLimitModal } from '../../contexts/PlanLimitModalContext'
import { getFriendlyErrorInfo } from '../../utils/friendlyError'
import { leadIntakeResolutionRejected } from '../../utils/intakeResolution'
import { leadSourceProfileId } from '../../utils/clientInquiryLead'
import { advanceSalesWorkSession, getSalesWorkSession, leadHref } from '../../services/salesWorkSession'

const LOCALE_TO_DATE: Record<LocaleCode, string> = {
  en: 'en-US',
  ru: 'ru-RU',
  pl: 'pl-PL',
}

function formatDateValue(iso: string | null | undefined, locale: LocaleCode): string {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString(LOCALE_TO_DATE[locale] ?? 'ru-RU', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function ClientInquiryWorkPage() {
  const { channelId = '', leadId = '' } = useParams<{ channelId: string; leadId: string }>()
  const { t, locale } = useI18n()
  const navigate = useNavigate()
  const { notify } = useToast()
  const planLimitModal = usePlanLimitModal()

  const [lead, setLead] = useState<Lead | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [converting, setConverting] = useState(false)
  const [patching, setPatching] = useState(false)
  const [lostStagePrompt, setLostStagePrompt] = useState(false)

  const loadLead = useCallback(async () => {
    if (!leadId) return
    setLoading(true)
    setNotFound(false)
    try {
      const row = await getLead(leadId)
      if (row.lead_type !== 'client' || row.lead_target_type !== 'client_lead') {
        setNotFound(true)
        setLead(null)
        return
      }
      const profileId = leadSourceProfileId(row)
      if (profileId && channelId && profileId !== channelId) {
        setNotFound(true)
        setLead(null)
        return
      }
      setLead(row)
    } catch {
      setNotFound(true)
      setLead(null)
    } finally {
      setLoading(false)
    }
  }, [channelId, leadId])

  useEffect(() => {
    void loadLead()
  }, [loadLead])

  const handleStageChange = useCallback(
    async (stage: string, extra?: { lost_reason_code?: string; lost_reason_note?: string }) => {
      if (!lead?.id) return
      setPatching(true)
      try {
        const updated = (await updateLeadStage(lead.id, {
          stage,
          ...extra,
        })) as Lead
        setLead(updated)
        notify({ title: t('app.leads.inbox.stage_updated', { defaultValue: 'Статус обновлён' }), variant: 'success' })
      } catch (err: unknown) {
        if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.leads.detail.stage_update_failed'))) return
        const info = getFriendlyErrorInfo(err, t('app.leads.detail.stage_update_failed'), t)
        notify({
          title: info.title,
          description: [info.detail, info.hint].filter(Boolean).join(' '),
          variant: 'error',
        })
      } finally {
        setPatching(false)
      }
    },
    [lead?.id, notify, planLimitModal, t],
  )

  const handleStage = useCallback(
    (stage: 'contacted' | 'qualified' | 'lost') => {
      if (!lead) return
      if (stage === 'lost') {
        if (leadIntakeResolutionRejected(lead)) return
        setLostStagePrompt(true)
        return
      }
      void handleStageChange(stage)
    },
    [handleStageChange, lead],
  )

  const handleConvert = useCallback(async () => {
    if (!lead?.id) return
    setConverting(true)
    try {
      const updated = await convertClientLeadToClient(lead.id)
      setLead(updated)
      notify({
        title: t('app.client_inquiry.client_created', { defaultValue: 'Компания сохранена в клиенты' }),
        variant: 'success',
      })
      const session = getSalesWorkSession()
      if (session && session.queue[session.index] === lead.id) {
        const nextId = advanceSalesWorkSession()
        if (nextId) {
          window.setTimeout(() => navigate(leadHref(nextId, channelId)), 600)
        }
      }
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
  }, [channelId, lead?.id, navigate, notify, planLimitModal, t])

  if (!channelId || !leadId) {
    return <Navigate to={clientAcquisitionChannelPath(channelId || '')} replace />
  }

  return (
    <div className="space-y-4" data-testid="m1-sales-inquiry-work">
      <Link
        to={clientAcquisitionChannelPath(channelId)}
        className="inline-flex items-center gap-1 text-sm text-slate-600 hover:text-brand-700"
      >
        <IconArrowLeft size={14} stroke={1.9} />
        {t('app.sales_inquiry.back_channel', { defaultValue: 'К привлечению клиентов' })}
      </Link>

      {loading ? <p className="text-sm text-slate-500">{t('common.loading')}</p> : null}

      {!loading && notFound ? (
        <section className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-600">
          <p>{t('app.sales_inquiry.not_found', { defaultValue: 'Запрос компании не найден в этом канале.' })}</p>
          <Link to={clientAcquisitionChannelPath(channelId)} className="mt-3 inline-block text-brand-700 hover:underline">
            {t('app.sales_inquiry.back_channel', { defaultValue: 'К привлечению клиентов' })}
          </Link>
        </section>
      ) : null}

      {!loading && lead ? (
        <>
          <SalesQuestionnairePanel lead={lead} onLeadUpdated={setLead} />
          <ClientLeadDetailView
            lead={lead}
            formatDate={(iso) => formatDateValue(iso, locale)}
            converting={converting}
            patching={patching}
            onConvert={() => void handleConvert()}
            onStage={(stage) => void handleStage(stage)}
          />
        </>
      ) : null}

      {lostStagePrompt ? (
        <LostReasonForLostStageModal
          open={lostStagePrompt}
          loading={patching}
          hintKey="app.sales_inquiry.lost_hint"
          onCancel={() => setLostStagePrompt(false)}
          onConfirm={(payload) => {
            setLostStagePrompt(false)
            void handleStageChange('lost', {
              lost_reason_code: payload.lost_reason_code,
              lost_reason_note: payload.lost_reason_note,
            })
          }}
        />
      ) : null}
    </div>
  )
}
