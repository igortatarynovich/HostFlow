import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  confirmLeadQuestionnaireInviteSent,
  createLeadQuestionnaireInvite,
  getLead,
  getLeadQuestionnaireInvite,
  listLeadQuestionnaireForms,
  type LeadQuestionnaireFormOption,
} from '../../api/client'
import type { ApplicationContact } from '../../api/types/application'
import type { Lead } from '../../api/types'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'
import { useToast } from '../Toast'
import {
  absoluteApplyUrl,
  isWaitingForQuestionnaireResponse,
  readSalesQuestionnaireStatus,
  whatsAppShareUrl,
} from '../../utils/salesQuestionnaire'
import type { QuestionnaireSendChannel } from '../../utils/questionnaireMessageTemplates'
import { draftHasIntakeForm, type OutboundCommunicationDraft } from '../../utils/communicationModel'
import {
  pickPrimaryQuestionnaireForm,
  SALES_SERVICE_LABEL,
} from '../../utils/communicationFormConstants'
import { resolveLeadCommunicationMenu } from '../../utils/resolveLeadCommunicationMenu'
import { ClientCommunicationComposer, openClientMail } from './ClientCommunicationComposer'

type Props = {
  lead: Lead
  contact: ApplicationContact
  companyName?: string | null
  managerName?: string | null
  onLeadUpdated: (lead: Lead) => void
}

function text(value: unknown): string {
  if (value == null) return ''
  return String(value).trim()
}

function withLink(message: string, link: string | null): string {
  if (!link) return message
  return message.replaceAll('{ссылка}', link)
}

function resolveLeadFormIdForInvite(formId: string): string | undefined {
  return formId || undefined
}

export function SalesInquiryCommunicationSection({
  lead,
  contact,
  companyName,
  managerName,
  onLeadUpdated,
}: Props) {
  const { locale } = useI18n()
  const { notify } = useToast()
  const [busy, setBusy] = useState(false)
  const [loadingForms, setLoadingForms] = useState(true)
  const [forms, setForms] = useState<LeadQuestionnaireFormOption[]>([])
  const [selectedFormId, setSelectedFormId] = useState('')
  const [applyUrl, setApplyUrl] = useState<string | null>(null)
  const [inviteId, setInviteId] = useState<string | null>(null)

  const phone = text(contact.phone) || text(lead.normalized?.phone)
  const email = text(contact.email) || text(lead.normalized?.email)
  const communicationMenu = useMemo(
    () => resolveLeadCommunicationMenu({ lead, forms, module: 'sales' }),
    [forms, lead],
  )

  const submitted = readSalesQuestionnaireStatus(lead) === 'submitted'
  const waiting = isWaitingForQuestionnaireResponse(text(lead.normalized?.sales_questionnaire_status))
  const questionnaireConfigured = forms.length > 0

  useEffect(() => {
    let cancelled = false
    setLoadingForms(true)
    void listLeadQuestionnaireForms()
      .then((rows) => {
        if (cancelled) return
        setForms(rows)
        const primary = pickPrimaryQuestionnaireForm(rows)
        if (primary) {
          setSelectedFormId((current) => (rows.some((row) => row.id === current) ? current : primary.id))
        } else {
          setSelectedFormId('')
        }
      })
      .catch(() => {
        if (!cancelled) {
          setForms([])
          setSelectedFormId('')
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingForms(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    if (!lead.id) return
    void getLeadQuestionnaireInvite(lead.id)
      .then((invite) => {
        if (cancelled || !invite?.apply_url) return
        setApplyUrl(absoluteApplyUrl(invite.apply_url))
        setInviteId(invite.id)
        if (invite.lead_form_id) setSelectedFormId(invite.lead_form_id)
      })
      .catch(() => {
        if (!cancelled) {
          setApplyUrl(null)
          setInviteId(null)
        }
      })
    return () => {
      cancelled = true
    }
  }, [lead.id])

  const ensureInvite = useCallback(
    async (formId: string, formLocale?: 'ru' | 'pl' | 'en'): Promise<{ url: string; id: string } | null> => {
      const apiFormId = resolveLeadFormIdForInvite(formId)
      if (applyUrl && inviteId && formId === selectedFormId) {
        return { url: applyUrl, id: inviteId }
      }
      const result = await createLeadQuestionnaireInvite(lead.id, {
        lead_form_id: apiFormId,
        form_locale: formLocale,
      })
      const url = absoluteApplyUrl(result.apply_url)
      setApplyUrl(url)
      setInviteId(result.id)
      setSelectedFormId(formId)
      return { url, id: result.id }
    },
    [applyUrl, inviteId, lead.id, selectedFormId],
  )

  const handleFormChange = useCallback((formId: string) => {
    setSelectedFormId(formId)
    setApplyUrl(null)
    setInviteId(null)
  }, [])

  const handleCopyLink = useCallback(async () => {
    setBusy(true)
    try {
      const invite = await ensureInvite(selectedFormId, undefined)
      if (!invite?.url) return
      await navigator.clipboard.writeText(invite.url)
      notify({ title: 'Ссылка скопирована', variant: 'success' })
    } catch (err: unknown) {
      notify({ title: (err as Error)?.message || 'Не удалось скопировать ссылку', variant: 'error' })
    } finally {
      setBusy(false)
    }
  }, [ensureInvite, notify, selectedFormId])

  const handlePreviewForm = useCallback(async () => {
    setBusy(true)
    try {
      const invite = await ensureInvite(selectedFormId, undefined)
      if (!invite?.url) return
      window.open(invite.url, '_blank', 'noopener,noreferrer')
    } catch (err: unknown) {
      notify({ title: (err as Error)?.message || 'Не удалось открыть форму', variant: 'error' })
    } finally {
      setBusy(false)
    }
  }, [ensureInvite, notify, selectedFormId])

  const handleSend = useCallback(
    async (channel: QuestionnaireSendChannel, draft: OutboundCommunicationDraft) => {
      setBusy(true)
      try {
        let link = applyUrl
        let activeInviteId = inviteId

        if (draft.purpose === 'obtain_information' && draftHasIntakeForm(draft)) {
          const formId = draft.formVariantId || selectedFormId
          const invite = await ensureInvite(formId, draft.formLocale)
          if (!invite) return
          link = invite.url
          activeInviteId = invite.id
        }

        const message = withLink(draft.text, link)

        if (channel === 'email') {
          if (!email) {
            notify({ title: 'У заявки нет email', variant: 'error' })
            return
          }
          openClientMail(email, draft.emailSubject || '', message)
        } else if (channel === 'whatsapp') {
          const wa = whatsAppShareUrl(phone, message)
          if (!wa) {
            notify({ title: 'У заявки нет телефона', variant: 'error' })
            return
          }
          window.open(wa, '_blank', 'noopener,noreferrer')
        } else {
          notify({ title: 'Выберите WhatsApp или Email для отправки', variant: 'error' })
          return
        }

        if (draft.purpose === 'obtain_information' && draftHasIntakeForm(draft) && activeInviteId) {
          await confirmLeadQuestionnaireInviteSent(lead.id, {
            invite_id: activeInviteId,
            channel,
          })
          onLeadUpdated(await getLead(lead.id))
          notify({ title: 'Сообщение отправлено — ожидаем ответ', variant: 'success' })
        }
      } catch (err: unknown) {
        notify({ title: (err as Error)?.message || 'Не удалось отправить', variant: 'error' })
      } finally {
        setBusy(false)
      }
    },
    [applyUrl, email, ensureInvite, inviteId, lead.id, notify, onLeadUpdated, phone, selectedFormId],
  )

  const statusLine = useMemo(() => {
    if (submitted) return 'Клиент ответил — ответы справа в блоке «Информация от клиента».'
    if (waiting) return 'Ожидаем ответ на запрос информации.'
    return null
  }, [submitted, waiting])

  if (loadingForms) {
    return <p className="text-sm text-slate-500">Загрузка…</p>
  }

  return (
    <div className="space-y-3" data-testid="sales-inquiry-communication">
      {statusLine ? <p className="text-xs text-slate-600">{statusLine}</p> : null}
      {!questionnaireConfigured ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50/80 p-4 text-sm text-rose-950" role="alert">
          <p className="font-medium">Процесс «{SALES_SERVICE_LABEL}» не настроен</p>
          <p className="mt-1 text-rose-900">
            Для отправки анкеты клиенту нужна хотя бы одна рабочая анкета. Создайте первую анкету в настройках
            процесса.
          </p>
          <div className="mt-3">
            <Link to={CRM_APP_PATHS.settingsLeadForms} className="btn-secondary btn-sm">
              Создать первую анкету
            </Link>
          </div>
        </div>
      ) : (
        <ClientCommunicationComposer
          menu={communicationMenu}
          selectedFormId={selectedFormId}
          onFormChange={handleFormChange}
          applyUrl={applyUrl}
          contactEmail={email}
          contactPhone={phone}
          contactName={text(contact.name) || undefined}
          companyName={text(companyName) || undefined}
          managerName={managerName}
          locale={locale}
          busy={busy}
          onSend={(channel, draft) => void handleSend(channel, draft)}
          onCopyLink={() => void handleCopyLink()}
          onPreviewForm={() => void handlePreviewForm()}
        />
      )}
    </div>
  )
}
