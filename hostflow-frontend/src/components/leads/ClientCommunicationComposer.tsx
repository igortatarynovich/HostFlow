import { useEffect, useMemo, useState } from 'react'
import { IconBrandWhatsapp, IconChevronDown, IconExternalLink, IconMail } from '@tabler/icons-react'
import {
  buildQuestionnaireMailtoUrl,
  type QuestionnaireSendChannel,
} from '../../utils/questionnaireMessageTemplates'
import {
  buildAttachmentsFromSelectedActions,
  type CommunicationPurpose,
  type LeadCommunicationMenu,
  type OutboundCommunicationDraft,
} from '../../utils/communicationModel'
import { findQuestionnaireAction } from '../../utils/resolveLeadCommunicationMenu'
import { resolveCommunicationTemplates } from '../../utils/resolveCommunicationTemplates'

type Props = {
  menu: LeadCommunicationMenu
  selectedFormId: string
  onFormChange: (formId: string) => void
  applyUrl: string | null
  contactEmail: string
  contactPhone: string
  contactName?: string
  companyName?: string
  managerName?: string
  locale?: string
  busy?: boolean
  onSend: (channel: QuestionnaireSendChannel, draft: OutboundCommunicationDraft) => void
  onCopyLink?: () => void | Promise<void>
  onPreviewForm?: () => void | Promise<void>
}

const FORM_LOCALES: Array<{ id: 'ru' | 'pl' | 'en'; label: string }> = [
  { id: 'pl', label: 'Polski' },
  { id: 'ru', label: 'Русский' },
  { id: 'en', label: 'English' },
]

const SEND_CHANNELS: Array<{ id: QuestionnaireSendChannel; label: string; icon: typeof IconMail }> = [
  { id: 'whatsapp', label: 'WhatsApp', icon: IconBrandWhatsapp },
  { id: 'email', label: 'Email', icon: IconMail },
]

function defaultPurpose(menu: LeadCommunicationMenu): CommunicationPurpose {
  const preferred = menu.purposes.find((row) => row.id === 'obtain_information' && row.enabled)
  if (preferred) return preferred.id
  return 'write_message'
}

function defaultSelectedActions(menu: LeadCommunicationMenu, purpose: CommunicationPurpose): string[] {
  if (purpose !== 'obtain_information') return []
  const first = menu.obtainInformation.find((action) => action.enabled)
  return first ? [first.id] : []
}

export function ClientCommunicationComposer({
  menu,
  selectedFormId,
  onFormChange,
  applyUrl,
  contactEmail,
  contactPhone,
  contactName,
  companyName,
  managerName,
  locale,
  busy = false,
  onSend,
  onCopyLink,
  onPreviewForm,
}: Props) {
  const [channel, setChannel] = useState<QuestionnaireSendChannel>('whatsapp')
  const [purpose, setPurpose] = useState<CommunicationPurpose>(() => defaultPurpose(menu))
  const [formLocale, setFormLocale] = useState<'ru' | 'pl' | 'en'>(() =>
    locale === 'ru' || locale === 'en' ? locale : 'pl',
  )
  const [selectedActionIds, setSelectedActionIds] = useState<string[]>(() =>
    defaultSelectedActions(menu, defaultPurpose(menu)),
  )
  const [showMoreActions, setShowMoreActions] = useState(false)

  const questionnaireAction = useMemo(() => findQuestionnaireAction(menu), [menu])
  const activeActions =
    purpose === 'obtain_information'
      ? menu.obtainInformation
      : purpose === 'send_outbound'
        ? menu.sendOutbound
        : []

  const formVariantId = useMemo(() => {
    if (!questionnaireAction) return null
    const variants = questionnaireAction.variants ?? []
    if (variants.length <= 1) {
      return questionnaireAction.resolvedVariant?.id ?? variants[0]?.id ?? null
    }
    const match = variants.find((row) => row.id === selectedFormId)
    return match?.id ?? questionnaireAction.resolvedVariant?.id ?? variants[0]?.id ?? null
  }, [questionnaireAction, selectedFormId])

  const showQuestionnairePicker =
    purpose === 'obtain_information' &&
    selectedActionIds.includes('fill_questionnaire') &&
    (questionnaireAction?.variants?.length ?? 0) > 1

  const attachments = useMemo(
    () =>
      buildAttachmentsFromSelectedActions({
        menu,
        purpose,
        selectedActionIds,
        formVariantId,
        applyUrl,
      }),
    [applyUrl, formVariantId, menu, purpose, selectedActionIds],
  )

  const templateContext = useMemo(
    () => ({
      applyUrl: applyUrl || '{ссылка}',
      contactName,
      companyName,
      managerName,
    }),
    [applyUrl, contactName, companyName, managerName],
  )

  const infoTemplates = useMemo(
    () =>
      resolveCommunicationTemplates({
        purpose: 'obtain_information_questionnaire',
        locale: formLocale,
        context: templateContext,
      }),
    [formLocale, templateContext],
  )

  const [emailSubject, setEmailSubject] = useState(infoTemplates.emailSubject)
  const [emailBody, setEmailBody] = useState(infoTemplates.emailBody)
  const [whatsappMessage, setWhatsappMessage] = useState(infoTemplates.whatsAppMessage)
  const [freeText, setFreeText] = useState('')

  useEffect(() => {
    if (purpose !== 'obtain_information') return
    setEmailSubject(infoTemplates.emailSubject)
    setEmailBody(infoTemplates.emailBody)
    setWhatsappMessage(infoTemplates.whatsAppMessage)
  }, [infoTemplates, purpose])

  const toggleAction = (actionId: string) => {
    setSelectedActionIds((prev) => {
      if (prev.includes(actionId)) {
        const next = prev.filter((item) => item !== actionId)
        return next.length > 0 ? next : [actionId]
      }
      return [...prev, actionId]
    })
  }

  const needsQuestionnairePicker = showQuestionnairePicker

  const messageText =
    purpose === 'write_message'
      ? freeText
      : channel === 'email'
        ? emailBody
        : whatsappMessage

  const hasSendChannel =
    (channel === 'email' && contactEmail) || (channel === 'whatsapp' && contactPhone)

  const hasTemplateText = messageText.trim().length > 0

  const canSend =
    !busy &&
    hasSendChannel &&
    (purpose === 'write_message'
      ? freeText.trim().length > 0
      : purpose === 'obtain_information' || purpose === 'send_outbound'
        ? hasTemplateText &&
          selectedActionIds.length > 0 &&
          attachments.length > 0 &&
          (!selectedActionIds.includes('fill_questionnaire') || Boolean(formVariantId))
        : false)

  const sendButtonLabel =
    channel === 'whatsapp' ? 'Отправить в WhatsApp' : channel === 'email' ? 'Отправить email' : 'Отправить'

  return (
    <div className="space-y-4 rounded-xl border border-slate-200 bg-slate-50/60 p-4" data-testid="client-communication-composer">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Зачем вы связываетесь?</p>
        <div className="mt-2 grid gap-2 sm:grid-cols-2">
          {menu.purposes.map((item) => (
            <label
              key={item.id}
              className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm ${
                purpose === item.id ? 'border-brand-300 bg-brand-50/60' : 'border-slate-200 bg-white'
              } ${!item.enabled ? 'cursor-not-allowed opacity-50' : ''}`}
            >
              <input
                type="radio"
                name="communication-purpose"
                disabled={!item.enabled}
                checked={purpose === item.id}
                onChange={() => {
                  setPurpose(item.id)
                  if (item.id === 'obtain_information') {
                    setSelectedActionIds(defaultSelectedActions(menu, item.id))
                  } else if (item.id === 'send_outbound') {
                    const first = menu.sendOutbound.find((action) => action.enabled)
                    setSelectedActionIds(first ? [first.id] : [])
                  } else {
                    setSelectedActionIds([])
                  }
                }}
              />
              {item.label}
              {!item.enabled ? <span className="text-xs text-slate-400">(скоро)</span> : null}
            </label>
          ))}
        </div>
      </div>

      {purpose === 'obtain_information' || purpose === 'send_outbound' ? (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {purpose === 'obtain_information' ? 'Можно запросить' : 'Можно отправить'}
          </p>
          <div className="mt-2 grid gap-2 sm:grid-cols-2">
            {activeActions.map((action) => (
              <label
                key={action.id}
                className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm ${
                  selectedActionIds.includes(action.id) ? 'border-brand-300 bg-brand-50/60' : 'border-slate-200 bg-white'
                } ${!action.enabled ? 'cursor-not-allowed opacity-50' : ''}`}
              >
                <input
                  type="checkbox"
                  disabled={!action.enabled}
                  checked={selectedActionIds.includes(action.id)}
                  onChange={() => toggleAction(action.id)}
                />
                {action.label}
                {!action.enabled ? <span className="text-xs text-slate-400">(скоро)</span> : null}
              </label>
            ))}
          </div>
        </div>
      ) : null}

      {needsQuestionnairePicker && questionnaireAction ? (
        <label className="block text-sm">
          <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
            {questionnaireAction.variantPickerLabel || 'Анкета'}
          </span>
          <select
            className="input w-full"
            value={formVariantId || ''}
            onChange={(e) => onFormChange(e.target.value)}
            disabled={busy}
          >
            {questionnaireAction.variants?.map((variant) => (
              <option key={variant.id} value={variant.id}>
                {variant.label}
              </option>
            ))}
          </select>
        </label>
      ) : null}

      {purpose === 'obtain_information' && selectedActionIds.includes('fill_questionnaire') ? (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Язык анкеты для клиента</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {FORM_LOCALES.map((item) => (
              <button
                key={item.id}
                type="button"
                className={`inline-flex h-8 items-center rounded-lg px-3 text-xs font-medium ${
                  formLocale === item.id ? 'bg-brand-600 text-white' : 'bg-white text-slate-700 ring-1 ring-slate-200'
                }`}
                onClick={() => setFormLocale(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Канал отправки</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {SEND_CHANNELS.map((item) => {
            const Icon = item.icon
            const active = channel === item.id
            const disabled =
              (item.id === 'email' && !contactEmail) || (item.id === 'whatsapp' && !contactPhone)
            return (
              <button
                key={item.id}
                type="button"
                disabled={disabled}
                className={`inline-flex h-8 items-center gap-1.5 rounded-lg px-3 text-xs font-medium ${
                  active ? 'bg-brand-600 text-white' : 'bg-white text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50'
                } ${disabled ? 'cursor-not-allowed opacity-40' : ''}`}
                onClick={() => setChannel(item.id)}
              >
                <Icon size={14} stroke={1.75} aria-hidden />
                {item.label}
              </button>
            )
          })}
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between gap-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Текст сообщения</p>
          {purpose === 'obtain_information' ? (
            <span className="text-xs text-slate-500">Шаблон — можно отредактировать</span>
          ) : null}
        </div>
        {purpose === 'write_message' ? (
          <textarea
            className="input mt-2 min-h-[140px] w-full"
            value={freeText}
            onChange={(e) => setFreeText(e.target.value)}
            placeholder="Напишите сообщение клиенту…"
          />
        ) : null}
        {purpose === 'obtain_information' && channel === 'email' ? (
          <div className="mt-2 space-y-2">
            <input className="input w-full" value={emailSubject} onChange={(e) => setEmailSubject(e.target.value)} placeholder="Тема" />
            <textarea className="input min-h-[140px] w-full" value={emailBody} onChange={(e) => setEmailBody(e.target.value)} />
          </div>
        ) : null}
        {purpose === 'obtain_information' && channel === 'whatsapp' ? (
          <textarea className="input mt-2 min-h-[140px] w-full" value={whatsappMessage} onChange={(e) => setWhatsappMessage(e.target.value)} />
        ) : null}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          className="btn-primary"
          disabled={!canSend}
          onClick={() =>
            onSend(channel, {
              purpose,
              channel,
              text: messageText,
              emailSubject: purpose === 'obtain_information' && channel === 'email' ? emailSubject : undefined,
              selectedActionIds,
              attachments,
              formVariantId: formVariantId || undefined,
              formLocale: purpose === 'obtain_information' && selectedActionIds.includes('fill_questionnaire') ? formLocale : undefined,
            })
          }
        >
          {busy ? 'Отправка…' : sendButtonLabel}
        </button>

        {(onCopyLink || onPreviewForm) && purpose === 'obtain_information' ? (
          <div className="relative">
            <button
              type="button"
              className="btn-secondary inline-flex items-center gap-1"
              onClick={() => setShowMoreActions((open) => !open)}
            >
              Ещё
              <IconChevronDown size={14} aria-hidden />
            </button>
            {showMoreActions ? (
              <div className="absolute left-0 top-full z-10 mt-1 min-w-[12rem] rounded-lg border border-slate-200 bg-white py-1 shadow-lg">
                {onCopyLink ? (
                  <button
                    type="button"
                    className="block w-full px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"
                    onClick={() => {
                      setShowMoreActions(false)
                      void onCopyLink()
                    }}
                  >
                    Скопировать ссылку
                  </button>
                ) : null}
                {onPreviewForm ? (
                  <button
                    type="button"
                    className="flex w-full items-center gap-1.5 px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"
                    onClick={() => {
                      setShowMoreActions(false)
                      void onPreviewForm()
                    }}
                  >
                    <IconExternalLink size={14} aria-hidden />
                    Предпросмотр формы
                  </button>
                ) : null}
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  )
}

export function openClientMail(email: string, subject: string, body: string): void {
  window.location.href = buildQuestionnaireMailtoUrl(email, subject, body)
}
