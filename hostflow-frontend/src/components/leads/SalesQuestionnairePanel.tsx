import { useCallback, useEffect, useMemo, useState } from 'react'
import { IconBrandWhatsapp, IconCheck, IconCopy, IconSend } from '@tabler/icons-react'

import {
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

export default function SalesQuestionnairePanel({ lead, onLeadUpdated }: Props) {
  const { t, locale } = useI18n()
  const { notify } = useToast()
  const [busy, setBusy] = useState(false)
  const [loadingForms, setLoadingForms] = useState(true)
  const [forms, setForms] = useState<LeadQuestionnaireFormOption[]>([])
  const [selectedFormId, setSelectedFormId] = useState<string>('')
  const [applyUrl, setApplyUrl] = useState<string | null>(null)

  const statusLabel = useMemo(() => salesQuestionnaireStatusLabel(lead, { locale }), [lead, locale])
  const phone = text(lead.normalized?.phone) || text(lead.payload?.phone)
  const questionnaireStatus = text(lead.normalized?.sales_questionnaire_status)
  const waitingForResponse = isWaitingForQuestionnaireResponse(questionnaireStatus)

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
      })
      .catch(() => {
        if (!cancelled) setApplyUrl(null)
      })
    return () => {
      cancelled = true
    }
  }, [lead.id, questionnaireStatus])

  const sendInvite = useCallback(async () => {
    setBusy(true)
    try {
      const result = await createLeadQuestionnaireInvite(lead.id, {
        mark_sent: true,
        lead_form_id: selectedFormId || undefined,
      })
      const url = absoluteApplyUrl(result.apply_url)
      setApplyUrl(url)
      const refreshed = await getLead(lead.id)
      onLeadUpdated(refreshed)
      notify({
        title: t('app.sales_questionnaire.sent_success', { defaultValue: 'Questionnaire link created' }),
        variant: 'success',
      })
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail ??
        (err as Error)?.message ??
        t('app.sales_questionnaire.send_failed', { defaultValue: 'Could not create questionnaire link' })
      notify({ title: typeof detail === 'string' ? detail : JSON.stringify(detail), variant: 'error' })
    } finally {
      setBusy(false)
    }
  }, [lead.id, notify, onLeadUpdated, selectedFormId, t])

  const copyLink = useCallback(async () => {
    if (!applyUrl) return
    try {
      await navigator.clipboard.writeText(applyUrl)
      notify({
        title: t('app.sales_questionnaire.link_copied', { defaultValue: 'Link copied' }),
        variant: 'success',
      })
    } catch {
      notify({ title: applyUrl, variant: 'info' })
    }
  }, [applyUrl, notify, t])

  const openWhatsApp = useCallback(() => {
    if (!applyUrl) return
    const message = t('app.sales_questionnaire.whatsapp_message', {
      defaultValue: 'Hello! Please complete this short questionnaire: {{url}}',
      url: applyUrl,
    })
    const wa = whatsAppShareUrl(phone, message)
    if (wa) window.open(wa, '_blank', 'noopener,noreferrer')
    else {
      notify({
        title: t('app.sales_questionnaire.no_phone', { defaultValue: 'No phone number on lead' }),
        variant: 'error',
      })
    }
  }, [applyUrl, notify, phone, t])

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
        <button
          type="button"
          className="btn-primary inline-flex h-9 items-center gap-2 rounded-lg px-3 text-sm font-semibold"
          disabled={busy || loadingForms || forms.length === 0}
          onClick={() => void sendInvite()}
        >
          <IconSend size={16} stroke={1.75} aria-hidden />
          {busy
            ? t('app.sales_questionnaire.sending', { defaultValue: 'Sending…' })
            : t('app.sales_questionnaire.send', { defaultValue: 'Send questionnaire' })}
        </button>
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

      {!loadingForms && forms.length === 0 ? (
        <p className="mt-3 text-sm text-amber-800">
          {t('app.sales_questionnaire.no_forms', {
            defaultValue: 'No B2B questionnaire forms are configured for this tenant.',
          })}
        </p>
      ) : null}

      {applyUrl ? (
        <div className="mt-4 space-y-3 rounded-lg border border-slate-200 bg-white p-3">
          <p className="break-all font-mono text-xs text-slate-600">{applyUrl}</p>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="btn-secondary inline-flex h-8 items-center gap-1 rounded-lg px-3 text-xs"
              onClick={() => void copyLink()}
            >
              <IconCopy size={14} stroke={1.75} aria-hidden />
              {t('app.sales_questionnaire.copy_link', { defaultValue: 'Copy link' })}
            </button>
            <button type="button" className="btn-secondary inline-flex h-8 items-center gap-1 rounded-lg px-3 text-xs" onClick={openWhatsApp}>
              <IconBrandWhatsapp size={14} stroke={1.75} aria-hidden />
              WhatsApp
            </button>
            {waitingForResponse ? (
              <span className="inline-flex h-8 items-center gap-1 rounded-lg bg-amber-50 px-3 text-xs font-medium text-amber-900">
                <IconCheck size={14} stroke={1.75} aria-hidden />
                {t('app.sales_questionnaire.waiting_badge', { defaultValue: 'Waiting for response' })}
              </span>
            ) : null}
          </div>
        </div>
      ) : null}
    </section>
  )
}
