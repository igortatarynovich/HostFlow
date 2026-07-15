import { useCallback, useEffect, useMemo, useState } from 'react'

import {
  confirmLeadQuestionnaireInviteSent,
  createLeadQuestionnaireInvite,
  getLead,
  getLeadQuestionnaireInvite,
  listLeadQuestionnaireForms,
  type LeadQuestionnaireFormOption,
} from '../../api/client'
import type { Lead } from '../../api/types'
import { useI18n } from '../../i18n'
import { useToast } from '../Toast'
import {
  absoluteApplyUrl,
  isWaitingForQuestionnaireResponse,
  readSalesQuestionnaireStatus,
  salesQuestionnaireStatusLabel,
  whatsAppShareUrl,
} from '../../utils/salesQuestionnaire'
import type { QuestionnaireSendChannel } from '../../utils/questionnaireMessageTemplates'
import { draftHasIntakeForm, type OutboundCommunicationDraft } from '../../utils/communicationModel'
import { pickPrimaryQuestionnaireForm } from '../../utils/communicationFormConstants'
import { resolveLeadCommunicationMenu } from '../../utils/resolveLeadCommunicationMenu'
import { ClientCommunicationComposer, openClientMail } from './ClientCommunicationComposer'

type Props = {
  lead: Lead
  contactEmail?: string | null
  contactPhone?: string | null
  contactName?: string | null
  companyName?: string | null
  managerName?: string | null
  onLeadUpdated: (lead: Lead) => void
}

function text(value: unknown): string {
  if (value == null) return ''
  return String(value).trim()
}

/** @deprecated Prefer SalesInquiryCommunicationSection in Sales Application Workspace */
export default function SalesQuestionnairePanel({
  lead,
  contactEmail,
  contactPhone,
  contactName,
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

  const phone = text(contactPhone) || text(lead.normalized?.phone) || text(lead.payload?.phone)
  const email = text(contactEmail) || text(lead.normalized?.email) || text(lead.payload?.email)
  const statusLabel = useMemo(() => salesQuestionnaireStatusLabel(lead, { locale }), [lead, locale])
  const waiting = isWaitingForQuestionnaireResponse(text(lead.normalized?.sales_questionnaire_status))
  const submitted = readSalesQuestionnaireStatus(lead) === 'submitted'

  useEffect(() => {
    let cancelled = false
    setLoadingForms(true)
    void listLeadQuestionnaireForms()
      .then((rows) => {
        if (cancelled) return
        setForms(rows)
        const primary = pickPrimaryQuestionnaireForm(rows)
        setSelectedFormId((current) =>
          primary ? (rows.some((row) => row.id === current) ? current : primary.id) : '',
        )
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
    if (!lead.id || submitted) return
    void getLeadQuestionnaireInvite(lead.id)
      .then((invite) => {
        if (cancelled || !invite?.apply_url) return
        setApplyUrl(absoluteApplyUrl(invite.apply_url))
        setInviteId(invite.id)
        if (invite.lead_form_id) setSelectedFormId(invite.lead_form_id)
      })
      .catch(() => undefined)
    return () => {
      cancelled = true
    }
  }, [lead.id, submitted])

  const communicationMenu = useMemo(
    () => resolveLeadCommunicationMenu({ lead, forms }),
    [forms, lead],
  )

  const ensureInvite = useCallback(
    async (formId: string, formLocale?: 'ru' | 'pl' | 'en') => {
      const apiFormId = formId || undefined
      if (applyUrl && inviteId && formId === selectedFormId) return { url: applyUrl, id: inviteId }
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

  const handleSend = useCallback(
    async (channel: QuestionnaireSendChannel, draft: OutboundCommunicationDraft) => {
      setBusy(true)
      try {
        let link = applyUrl
        let activeInviteId = inviteId

        if (draft.purpose === 'obtain_information' && draftHasIntakeForm(draft)) {
          const formId = draft.formVariantId || selectedFormId
          const invite = await ensureInvite(formId, draft.formLocale)
          link = invite.url
          activeInviteId = invite.id
        }

        const message = link ? draft.text.replaceAll('{ссылка}', link) : draft.text

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
          await confirmLeadQuestionnaireInviteSent(lead.id, { invite_id: activeInviteId, channel })
          onLeadUpdated(await getLead(lead.id))
        }
      } catch (err: unknown) {
        notify({ title: (err as Error)?.message || 'Ошибка отправки', variant: 'error' })
      } finally {
        setBusy(false)
      }
    },
    [applyUrl, email, ensureInvite, inviteId, lead.id, notify, onLeadUpdated, phone, selectedFormId],
  )

  if (loadingForms) return <p className="text-sm text-slate-500">Загрузка…</p>

  return (
    <div className="space-y-3" data-testid="sales-questionnaire-panel">
      <p className={`text-sm font-medium ${submitted ? 'text-emerald-800' : waiting ? 'text-amber-800' : 'text-slate-700'}`}>
        {submitted ? 'Клиент ответил на вопросы' : statusLabel}
      </p>
      {forms.length === 0 ? (
        <p className="text-sm text-amber-800">Нет доступных анкет для этой заявки.</p>
      ) : null}
      <ClientCommunicationComposer
        menu={communicationMenu}
        selectedFormId={selectedFormId}
        onFormChange={(id) => {
          setSelectedFormId(id)
          setApplyUrl(null)
          setInviteId(null)
        }}
        applyUrl={applyUrl}
        contactEmail={email}
        contactPhone={phone}
        contactName={text(contactName) || undefined}
        companyName={text(companyName) || undefined}
        managerName={managerName}
        locale={locale}
        busy={busy}
        onSend={(channel, draft) => void handleSend(channel, draft)}
      />
    </div>
  )
}
