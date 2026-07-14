import { useCallback, useMemo, useState } from 'react'
import { IconBrandWhatsapp, IconCheck, IconCopy, IconEye, IconSend } from '@tabler/icons-react'

import { createLeadQuestionnaireInvite, type LeadQuestionnaireInviteResult } from '../../api/client'
import type { Lead } from '../../api/types'
import { useI18n } from '../../i18n'
import { useToast } from '../Toast'
import {
  absoluteApplyUrl,
  formatSalesQuestionnaireTimestamp,
  readSalesQuestionnaireStatus,
  salesQuestionnaireStatusLabel,
  whatsAppShareUrl,
  type SalesQuestionnaireStatus,
} from '../../utils/salesQuestionnaire'

type Props = {
  lead: Lead
  invite?: LeadQuestionnaireInviteResult | null
  inviteLoading?: boolean
  hasAnswers?: boolean
  onLeadUpdated: (lead: Lead, invite?: LeadQuestionnaireInviteResult | null) => void
  onError?: (message: string | null) => void
}

function text(value: unknown): string {
  if (value == null) return ''
  return String(value).trim()
}

function effectiveStatus(lead: Lead, invite?: LeadQuestionnaireInviteResult | null): SalesQuestionnaireStatus {
  const fromLead = readSalesQuestionnaireStatus(lead)
  const fromInvite = invite?.status
  const raw = fromLead || fromInvite || 'not_sent'
  if (raw === 'opened' || raw === 'in_progress' || raw === 'sent' || raw === 'submitted' || raw === 'expired') {
    return raw
  }
  return 'not_sent'
}

export default function SalesQuestionnairePanel({
  lead,
  invite = null,
  inviteLoading = false,
  hasAnswers = false,
  onLeadUpdated,
  onError,
}: Props) {
  const { t, locale } = useI18n()
  const { notify } = useToast()
  const [busy, setBusy] = useState(false)
  const [showAnswersHint, setShowAnswersHint] = useState(false)

  const status = useMemo(() => effectiveStatus(lead, invite), [invite, lead])
  const statusLabel = useMemo(() => salesQuestionnaireStatusLabel(lead, invite?.status), [invite?.status, lead])
  const phone = text(lead.normalized?.phone) || text(lead.payload?.phone)
  const applyUrl = useMemo(() => {
    if (invite?.apply_url) return absoluteApplyUrl(invite.apply_url)
    return null
  }, [invite?.apply_url])

  const sentAt = invite?.sent_at || null
  const openedAt = invite?.opened_at || null
  const submittedAt = invite?.submitted_at || null

  const sendInvite = useCallback(
    async (markSent: boolean) => {
      setBusy(true)
      onError?.(null)
      try {
        const result = await createLeadQuestionnaireInvite(lead.id, { mark_sent: markSent })
        const url = absoluteApplyUrl(result.apply_url)
        onLeadUpdated(
          {
            ...lead,
            normalized: {
              ...(lead.normalized || {}),
              sales_questionnaire_status: result.status,
            },
          },
          result,
        )
        notify({
          title: markSent
            ? t('app.sales_inquiry.questionnaire_sent', { defaultValue: 'Link do ankiety wysłany' })
            : t('app.sales_inquiry.questionnaire_created', { defaultValue: 'Link do ankiety utworzony' }),
          variant: 'success',
        })
        return url
      } catch (err: unknown) {
        const detail =
          (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail ??
          (err as Error)?.message ??
          t('app.sales_inquiry.questionnaire_invite_failed', { defaultValue: 'Nie udało się utworzyć linku' })
        const message = typeof detail === 'string' ? detail : JSON.stringify(detail)
        onError?.(message)
        notify({ title: message, variant: 'error' })
        return null
      } finally {
        setBusy(false)
      }
    },
    [lead, notify, onError, onLeadUpdated, t],
  )

  const copyLink = useCallback(async () => {
    if (!applyUrl) return
    try {
      await navigator.clipboard.writeText(applyUrl)
      notify({ title: t('app.sales_inquiry.link_copied', { defaultValue: 'Skopiowano link' }), variant: 'success' })
    } catch {
      notify({ title: applyUrl, variant: 'info' })
    }
  }, [applyUrl, notify, t])

  const openWhatsApp = useCallback(() => {
    if (!applyUrl) return
    const wa = whatsAppShareUrl(phone, `Dzień dobry! Proszę wypełnić krótką ankietę: ${applyUrl}`)
    if (wa) window.open(wa, '_blank', 'noopener,noreferrer')
    else notify({ title: t('app.sales_inquiry.no_phone', { defaultValue: 'Brak numeru telefonu w leadzie' }), variant: 'error' })
  }, [applyUrl, notify, phone, t])

  const primaryIsViewAnswers = status === 'submitted' || hasAnswers

  return (
    <section className="rounded-xl border border-brand-100 bg-brand-50/40 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">
            {t('app.sales_inquiry.questionnaire_title', { defaultValue: 'Ankieta klienta' })}
          </p>
          <p className="mt-1 text-sm text-slate-700">{statusLabel}</p>
          {sentAt ? (
            <p className="mt-1 text-xs text-slate-500">
              {t('app.sales_inquiry.questionnaire_sent_at', {
                defaultValue: 'Wysłano: {{date}}',
                date: formatSalesQuestionnaireTimestamp(sentAt, locale),
              })}
            </p>
          ) : null}
          {status === 'opened' && openedAt ? (
            <p className="mt-1 text-xs text-slate-500">
              {t('app.sales_inquiry.questionnaire_opened_at', {
                defaultValue: 'Otwarto: {{date}}',
                date: formatSalesQuestionnaireTimestamp(openedAt, locale),
              })}
            </p>
          ) : null}
          {status === 'submitted' && submittedAt ? (
            <p className="mt-1 text-xs text-slate-500">
              {t('app.sales_inquiry.questionnaire_submitted_at', {
                defaultValue: 'Wypełniono: {{date}}',
                date: formatSalesQuestionnaireTimestamp(submittedAt, locale),
              })}
            </p>
          ) : null}
        </div>

        {primaryIsViewAnswers ? (
          <button
            type="button"
            className="btn-primary inline-flex h-9 items-center gap-2 rounded-lg px-3 text-sm font-semibold"
            onClick={() => setShowAnswersHint((open) => !open)}
          >
            <IconEye size={16} stroke={1.75} aria-hidden />
            {t('app.sales_inquiry.view_answers', { defaultValue: 'Przeglądaj odpowiedzi' })}
          </button>
        ) : (
          <button
            type="button"
            className="btn-primary inline-flex h-9 items-center gap-2 rounded-lg px-3 text-sm font-semibold"
            disabled={busy || inviteLoading}
            onClick={() => void sendInvite(true)}
          >
            <IconSend size={16} stroke={1.75} aria-hidden />
            {busy || inviteLoading
              ? t('common.loading', { defaultValue: 'Ładowanie…' })
              : status === 'not_sent'
                ? t('app.sales_inquiry.send_questionnaire', { defaultValue: 'Wyślij ankietę' })
                : t('app.sales_inquiry.resend_questionnaire', { defaultValue: 'Wyślij ponownie' })}
          </button>
        )}
      </div>

      {showAnswersHint ? (
        <p className="mt-3 text-xs text-brand-800">
          {t('app.sales_inquiry.answers_below', { defaultValue: 'Odpowiedzi klienta są wyświetlone poniżej.' })}
        </p>
      ) : null}

      {applyUrl && status !== 'submitted' ? (
        <div className="mt-4 space-y-3 rounded-lg border border-slate-200 bg-white p-3">
          <p className="break-all font-mono text-xs text-slate-600">{applyUrl}</p>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="btn-secondary inline-flex h-8 items-center gap-1 rounded-lg px-3 text-xs"
              onClick={() => void copyLink()}
            >
              <IconCopy size={14} stroke={1.75} aria-hidden />
              {t('app.sales_inquiry.copy_link', { defaultValue: 'Kopiuj link' })}
            </button>
            <button type="button" className="btn-secondary inline-flex h-8 items-center gap-1 rounded-lg px-3 text-xs" onClick={openWhatsApp}>
              <IconBrandWhatsapp size={14} stroke={1.75} aria-hidden />
              WhatsApp
            </button>
            {status === 'sent' || status === 'opened' || status === 'in_progress' ? (
              <span className="inline-flex h-8 items-center gap-1 rounded-lg bg-emerald-50 px-3 text-xs font-medium text-emerald-800">
                <IconCheck size={14} stroke={1.75} aria-hidden />
                {status === 'in_progress'
                  ? t('app.sales_inquiry.status_in_progress', { defaultValue: 'W trakcie wypełniania' })
                  : status === 'opened'
                    ? t('app.sales_inquiry.status_opened', { defaultValue: 'Otwarta przez klienta' })
                    : t('app.sales_inquiry.status_sent', { defaultValue: 'Wysłano' })}
              </span>
            ) : null}
          </div>
        </div>
      ) : null}
    </section>
  )
}
