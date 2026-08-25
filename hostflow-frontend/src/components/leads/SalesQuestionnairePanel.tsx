import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  IconBrandWhatsapp,
  IconCheck,
  IconChevronDown,
  IconCopy,
  IconExternalLink,
  IconMail,
  IconSend,
} from '@tabler/icons-react'
import { Link } from 'react-router-dom'

import {
  createLeadQuestionnaireInvite,
  getLead,
  getLeadQuestionnaireInvite,
  listLeadQuestionnaireForms,
  previewLeadQuestionnaireInviteEmail,
  sendLeadQuestionnaireInviteEmail,
  type LeadQuestionnaireFormOption,
} from '../../api/client'
import type { Lead } from '../../api/types'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'
import { useToast } from '../Toast'
import {
  absoluteApplyUrl,
  isWaitingForQuestionnaireResponse,
  salesQuestionnaireStatusLabel,
  whatsAppShareUrl,
} from '../../utils/salesQuestionnaire'

type Props = {
  lead: Lead
  onLeadUpdated: (lead: Lead) => void
}

function text(value: unknown): string {
  if (value == null) return ''
  return String(value).trim()
}

function detailMessage(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object') {
    const obj = detail as { message?: string; code?: string }
    if (obj.message) return obj.message
    if (obj.code) return obj.code
  }
  return (err as Error)?.message || fallback
}

function detailCode(err: unknown): string | null {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (detail && typeof detail === 'object' && 'code' in (detail as object)) {
    return String((detail as { code?: string }).code || '') || null
  }
  return null
}

export default function SalesQuestionnairePanel({ lead, onLeadUpdated }: Props) {
  const { t, locale } = useI18n()
  const { notify } = useToast()
  const [busy, setBusy] = useState(false)
  const [loadingForms, setLoadingForms] = useState(true)
  const [forms, setForms] = useState<LeadQuestionnaireFormOption[]>([])
  const [selectedFormId, setSelectedFormId] = useState<string>('')
  const [selectedLocale, setSelectedLocale] = useState<string>('pl')
  const [applyUrl, setApplyUrl] = useState<string | null>(null)
  const [emailOpen, setEmailOpen] = useState(false)
  const [moreOpen, setMoreOpen] = useState(false)
  const [forceNewInvite, setForceNewInvite] = useState(false)
  const [recipientEmail, setRecipientEmail] = useState('')
  const [emailSubject, setEmailSubject] = useState('')
  const [emailBody, setEmailBody] = useState('')
  const [emailConfigured, setEmailConfigured] = useState(true)
  const [clarificationRequired, setClarificationRequired] = useState(false)
  const [sendError, setSendError] = useState<string | null>(null)

  const statusLabel = useMemo(() => salesQuestionnaireStatusLabel(lead, { locale }), [lead, locale])
  const phone =
    text(lead.normalized?.phone) ||
    text(lead.payload?.phone) ||
    text((lead.normalized as { contact_person?: { phone?: string } } | undefined)?.contact_person?.phone) ||
    text((lead.normalized as { contact?: { phone?: string } } | undefined)?.contact?.phone)
  const leadEmail =
    text(lead.normalized?.email) ||
    text(lead.payload?.email) ||
    text((lead.normalized as { contact_person?: { email?: string } } | undefined)?.contact_person?.email) ||
    text((lead.payload as { contact_person?: { email?: string } } | undefined)?.contact_person?.email) ||
    text((lead.normalized as { contact?: { email?: string } } | undefined)?.contact?.email) ||
    text((lead.payload as { contact?: { email?: string } } | undefined)?.contact?.email)
  const questionnaireStatus = text(lead.normalized?.sales_questionnaire_status)
  const waitingForResponse = isWaitingForQuestionnaireResponse(questionnaireStatus)
  const answered = questionnaireStatus === 'submitted'

  useEffect(() => {
    let cancelled = false
    setLoadingForms(true)
    void listLeadQuestionnaireForms()
      .then((rows) => {
        if (cancelled) return
        setForms(rows)
        if (rows.length > 0) {
          setSelectedFormId((current) => current || rows[0].id)
        }
      })
      .catch(() => {
        if (!cancelled) setForms([])
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
    if (!lead.id || questionnaireStatus === 'submitted') {
      setApplyUrl(null)
      return
    }
    void getLeadQuestionnaireInvite(lead.id)
      .then((invite) => {
        if (cancelled || !invite?.apply_url) return
        setApplyUrl(absoluteApplyUrl(invite.apply_url))
        if (invite.lead_form_id) {
          setSelectedFormId(invite.lead_form_id)
        }
        if (invite.form_locale) {
          setSelectedLocale(String(invite.form_locale))
        }
      })
      .catch(() => {
        if (!cancelled) setApplyUrl(null)
      })
    return () => {
      cancelled = true
    }
  }, [lead.id, questionnaireStatus])

  useEffect(() => {
    if (!emailOpen) return
    setRecipientEmail((current) => current || leadEmail)
  }, [emailOpen, leadEmail])

  const refreshLead = useCallback(async () => {
    const refreshed = await getLead(lead.id)
    onLeadUpdated(refreshed)
    return refreshed
  }, [lead.id, onLeadUpdated])

  const openEmailCompose = useCallback(async () => {
    setBusy(true)
    setSendError(null)
    setEmailOpen(true)
    const mintNew = forceNewInvite || answered
    try {
      const preview = await previewLeadQuestionnaireInviteEmail(lead.id, {
        form_locale: selectedLocale,
        lead_form_id: selectedFormId || undefined,
        force_new_invite: mintNew,
        recipient_email: recipientEmail || leadEmail || undefined,
      })
      setApplyUrl(absoluteApplyUrl(preview.questionnaire_url || preview.invite.apply_url))
      setRecipientEmail(preview.recipient_email || leadEmail || '')
      setEmailSubject(preview.subject)
      setEmailBody(preview.body)
      setEmailConfigured(preview.email_configured)
      setClarificationRequired(Boolean(preview.clarification_required) || answered)
      setForceNewInvite(false)
      await refreshLead()
    } catch (err: unknown) {
      setEmailOpen(false)
      notify({
        title: detailMessage(
          err,
          t('app.sales_questionnaire.email_preview_failed', { defaultValue: 'Could not prepare email' }),
        ),
        variant: 'error',
      })
    } finally {
      setBusy(false)
    }
  }, [
    answered,
    forceNewInvite,
    lead.id,
    leadEmail,
    notify,
    recipientEmail,
    refreshLead,
    selectedFormId,
    selectedLocale,
    t,
  ])

  const sendEmail = useCallback(async () => {
    setBusy(true)
    setSendError(null)
    try {
      const result = await sendLeadQuestionnaireInviteEmail(lead.id, {
        form_locale: selectedLocale,
        lead_form_id: selectedFormId || undefined,
        force_new_invite: forceNewInvite || clarificationRequired,
        recipient_email: recipientEmail,
        subject: emailSubject,
        body: emailBody,
        save_email_to_lead: true,
      })
      setApplyUrl(absoluteApplyUrl(result.questionnaire_url || result.invite.apply_url))
      setForceNewInvite(false)
      setClarificationRequired(false)
      setEmailOpen(false)
      await refreshLead()
      notify({
        title: t('app.sales_questionnaire.email_sent_success', { defaultValue: 'Questionnaire email sent' }),
        variant: 'success',
      })
    } catch (err: unknown) {
      const code = detailCode(err)
      const message = detailMessage(
        err,
        t('app.sales_questionnaire.email_send_failed', { defaultValue: 'Could not send email' }),
      )
      setSendError(message)
      if (code === 'email_not_configured') {
        setEmailConfigured(false)
      }
      notify({ title: message, variant: 'error' })
    } finally {
      setBusy(false)
    }
  }, [
    clarificationRequired,
    emailBody,
    emailSubject,
    forceNewInvite,
    lead.id,
    notify,
    recipientEmail,
    refreshLead,
    selectedFormId,
    selectedLocale,
    t,
  ])

  const ensureLink = useCallback(async () => {
    if (applyUrl) return applyUrl
    setBusy(true)
    try {
      const result = await createLeadQuestionnaireInvite(lead.id, {
        mark_sent: true,
        lead_form_id: selectedFormId || undefined,
        form_locale: selectedLocale || undefined,
      })
      const url = absoluteApplyUrl(result.apply_url)
      setApplyUrl(url)
      await refreshLead()
      return url
    } catch (err: unknown) {
      notify({
        title: detailMessage(
          err,
          t('app.sales_questionnaire.send_failed', { defaultValue: 'Could not create questionnaire link' }),
        ),
        variant: 'error',
      })
      return null
    } finally {
      setBusy(false)
    }
  }, [applyUrl, lead.id, notify, refreshLead, selectedFormId, selectedLocale, t])

  const copyLink = useCallback(async () => {
    const url = await ensureLink()
    if (!url) return
    try {
      await navigator.clipboard.writeText(url)
      notify({
        title: t('app.sales_questionnaire.link_copied', { defaultValue: 'Link copied' }),
        variant: 'success',
      })
    } catch {
      notify({ title: url, variant: 'info' })
    }
  }, [ensureLink, notify, t])

  const openForm = useCallback(async () => {
    const url = await ensureLink()
    if (!url) return
    window.open(url, '_blank', 'noopener,noreferrer')
  }, [ensureLink])

  const openWhatsApp = useCallback(async () => {
    const url = await ensureLink()
    if (!url) return
    const message = t('app.sales_questionnaire.whatsapp_message', {
      defaultValue: 'Hello! Please complete this short questionnaire: {{url}}',
      url,
    })
    const wa = whatsAppShareUrl(phone, message)
    if (wa) window.open(wa, '_blank', 'noopener,noreferrer')
    else {
      notify({
        title: t('app.sales_questionnaire.no_phone', { defaultValue: 'No phone number on lead' }),
        variant: 'error',
      })
    }
  }, [ensureLink, notify, phone, t])

  const showFormPicker = forms.length > 1

  return (
    <section className="rounded-xl border border-brand-100 bg-brand-50/40 p-4" data-testid="sales-questionnaire-panel">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">
            {t('app.sales_questionnaire.title', { defaultValue: 'B2B questionnaire' })}
          </p>
          <p
            className={`mt-1 text-sm font-medium ${waitingForResponse ? 'text-amber-800' : 'text-slate-700'}`}
            data-testid="sales-questionnaire-status"
          >
            {statusLabel}
          </p>
        </div>
        {waitingForResponse ? (
          <span className="inline-flex h-8 items-center gap-1 rounded-lg bg-amber-50 px-3 text-xs font-medium text-amber-900">
            <IconCheck size={14} stroke={1.75} aria-hidden />
            {t('app.sales_questionnaire.waiting_badge', { defaultValue: 'Waiting for response' })}
          </span>
        ) : null}
      </div>

      {showFormPicker ? (
        <label className="mt-3 block text-sm text-slate-700">
          <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('app.sales_questionnaire.form_label', { defaultValue: 'Questionnaire form' })}
          </span>
          <select
            className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
            value={selectedFormId}
            onChange={(event) => setSelectedFormId(event.target.value)}
            disabled={busy}
            data-testid="sales-questionnaire-form-select"
          >
            {forms.map((form) => (
              <option key={form.id} value={form.id}>
                {form.title}
              </option>
            ))}
          </select>
        </label>
      ) : null}

      <div className="mt-3" data-testid="sales-questionnaire-locale-group">
        <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t('app.sales_questionnaire.locale_label', { defaultValue: 'Questionnaire language' })}
        </span>
        <div className="flex flex-wrap gap-2">
          {(['pl', 'en', 'ru'] as const).map((code) => (
            <button
              key={code}
              type="button"
              className={`inline-flex h-8 items-center rounded-lg px-3 text-xs font-semibold ${
                selectedLocale === code
                  ? 'bg-brand-700 text-white'
                  : 'border border-slate-200 bg-white text-slate-700'
              }`}
              disabled={busy}
              onClick={() => setSelectedLocale(code)}
              data-testid={`sales-questionnaire-locale-${code}`}
            >
              {code.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {!loadingForms && forms.length === 0 ? (
        <p className="mt-3 text-sm text-amber-800">
          {t('app.sales_questionnaire.no_forms', {
            defaultValue: 'No B2B questionnaire forms are configured for this tenant.',
          })}
        </p>
      ) : null}

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          className="btn-primary inline-flex h-9 items-center gap-2 rounded-lg px-3 text-sm font-semibold"
          disabled={busy || loadingForms || forms.length === 0}
          onClick={() => void openEmailCompose()}
          data-testid="sales-questionnaire-email-open"
        >
          <IconMail size={16} stroke={1.75} aria-hidden />
          {t('app.sales_questionnaire.send_email', { defaultValue: 'Send by email' })}
        </button>
        <button
          type="button"
          className="btn-secondary inline-flex h-9 items-center gap-2 rounded-lg px-3 text-sm"
          disabled={busy || loadingForms || forms.length === 0}
          onClick={() => void openWhatsApp()}
          data-testid="sales-questionnaire-whatsapp"
        >
          <IconBrandWhatsapp size={16} stroke={1.75} aria-hidden />
          WhatsApp
        </button>
        <div className="relative">
          <button
            type="button"
            className="btn-secondary inline-flex h-9 items-center gap-1 rounded-lg px-3 text-sm"
            disabled={busy || loadingForms || forms.length === 0}
            onClick={() => setMoreOpen((v) => !v)}
            data-testid="sales-questionnaire-more"
          >
            {t('app.sales_questionnaire.more', { defaultValue: 'More' })}
            <IconChevronDown size={14} stroke={1.75} aria-hidden />
          </button>
          {moreOpen ? (
            <div className="absolute right-0 z-10 mt-1 w-48 rounded-lg border border-slate-200 bg-white p-1 shadow-md">
              <button
                type="button"
                className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"
                onClick={() => {
                  setMoreOpen(false)
                  void copyLink()
                }}
              >
                <IconCopy size={14} stroke={1.75} aria-hidden />
                {t('app.sales_questionnaire.copy_link', { defaultValue: 'Copy link' })}
              </button>
              <button
                type="button"
                className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"
                onClick={() => {
                  setMoreOpen(false)
                  void openForm()
                }}
              >
                <IconExternalLink size={14} stroke={1.75} aria-hidden />
                {t('app.sales_questionnaire.open_form', { defaultValue: 'Open form' })}
              </button>
              {applyUrl ? (
                <button
                  type="button"
                  className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"
                  onClick={() => {
                    setForceNewInvite(true)
                    setMoreOpen(false)
                    notify({
                      title: t('app.sales_questionnaire.new_link_armed', {
                        defaultValue: 'Next email will create a new link',
                      }),
                      variant: 'info',
                    })
                  }}
                >
                  {t('app.sales_questionnaire.create_new_link', { defaultValue: 'Create new link' })}
                </button>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>

      {emailOpen ? (
        <div className="mt-4 space-y-3 rounded-lg border border-slate-200 bg-white p-3" data-testid="sales-questionnaire-email-compose">
          {clarificationRequired ? (
            <p className="text-sm text-amber-900" data-testid="sales-questionnaire-new-invite-banner">
              {t('app.sales_questionnaire.clarification_new_link', {
                defaultValue:
                  'Previous response is kept. This email uses a new personal link for clarification.',
              })}
            </p>
          ) : null}
          {!emailConfigured ? (
            <p className="text-sm text-amber-900">
              {t('app.sales_questionnaire.email_not_configured', {
                defaultValue: 'Connect email in settings',
              })}{' '}
              <Link className="font-semibold underline" to={CRM_APP_PATHS.settingsEmail}>
                {CRM_APP_PATHS.settingsEmail}
              </Link>
            </p>
          ) : null}
          <label className="block text-sm text-slate-700">
            <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t('app.sales_questionnaire.email_to', { defaultValue: 'To' })}
            </span>
            <input
              className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
              value={recipientEmail}
              onChange={(event) => setRecipientEmail(event.target.value)}
              disabled={busy}
              data-testid="sales-questionnaire-email-to"
            />
          </label>
          <label className="block text-sm text-slate-700">
            <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t('app.sales_questionnaire.email_subject', { defaultValue: 'Subject' })}
            </span>
            <input
              className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
              value={emailSubject}
              onChange={(event) => setEmailSubject(event.target.value)}
              disabled={busy}
              data-testid="sales-questionnaire-email-subject"
            />
          </label>
          <label className="block text-sm text-slate-700">
            <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t('app.sales_questionnaire.email_body', { defaultValue: 'Message' })}
            </span>
            <textarea
              className="min-h-[180px] w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
              value={emailBody}
              onChange={(event) => setEmailBody(event.target.value)}
              disabled={busy}
              data-testid="sales-questionnaire-email-body"
            />
          </label>
          {applyUrl ? (
            <p className="break-all text-xs text-slate-500" data-testid="sales-questionnaire-email-link">
              {applyUrl}
            </p>
          ) : null}
          {sendError ? <p className="text-sm text-red-700">{sendError}</p> : null}
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="btn-primary inline-flex h-9 items-center gap-2 rounded-lg px-3 text-sm font-semibold"
              disabled={busy || !emailConfigured || !recipientEmail || !emailSubject || !emailBody}
              onClick={() => void sendEmail()}
              data-testid="sales-questionnaire-email-send"
            >
              <IconSend size={16} stroke={1.75} aria-hidden />
              {busy
                ? t('app.sales_questionnaire.sending', { defaultValue: 'Sending…' })
                : sendError
                  ? t('app.sales_questionnaire.retry_email', { defaultValue: 'Retry' })
                  : t('app.sales_questionnaire.send_email_action', { defaultValue: 'Send email' })}
            </button>
            <button
              type="button"
              className="btn-secondary inline-flex h-9 items-center rounded-lg px-3 text-sm"
              disabled={busy}
              onClick={() => setEmailOpen(false)}
            >
              {t('common.cancel', { defaultValue: 'Cancel' })}
            </button>
          </div>
        </div>
      ) : null}
    </section>
  )
}
