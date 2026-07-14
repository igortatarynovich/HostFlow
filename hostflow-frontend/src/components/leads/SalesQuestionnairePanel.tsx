import { useCallback, useMemo, useState } from 'react'
import { IconBrandWhatsapp, IconCheck, IconCopy, IconSend } from '@tabler/icons-react'

import { createLeadQuestionnaireInvite } from '../../api/client'
import type { Lead } from '../../api/types'
import { useToast } from '../Toast'
import {
  absoluteApplyUrl,
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
  const { notify } = useToast()
  const [busy, setBusy] = useState(false)
  const [applyUrl, setApplyUrl] = useState<string | null>(null)

  const statusLabel = useMemo(() => salesQuestionnaireStatusLabel(lead), [lead])
  const phone = text(lead.normalized?.phone) || text(lead.payload?.phone)

  const sendInvite = useCallback(async () => {
    setBusy(true)
    try {
      const result = await createLeadQuestionnaireInvite(lead.id, { mark_sent: true })
      const url = absoluteApplyUrl(result.apply_url)
      setApplyUrl(url)
      onLeadUpdated({
        ...lead,
        normalized: {
          ...(lead.normalized || {}),
          sales_questionnaire_status: result.status,
        },
      })
      notify({ title: 'Link do ankiety utworzony', variant: 'success' })
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail ??
        (err as Error)?.message ??
        'Nie udało się utworzyć linku'
      notify({ title: typeof detail === 'string' ? detail : JSON.stringify(detail), variant: 'error' })
    } finally {
      setBusy(false)
    }
  }, [lead, notify, onLeadUpdated])

  const copyLink = useCallback(async () => {
    if (!applyUrl) return
    try {
      await navigator.clipboard.writeText(applyUrl)
      notify({ title: 'Skopiowano link', variant: 'success' })
    } catch {
      notify({ title: applyUrl, variant: 'info' })
    }
  }, [applyUrl, notify])

  const openWhatsApp = useCallback(() => {
    if (!applyUrl) return
    const wa = whatsAppShareUrl(phone, `Dzień dobry! Proszę wypełnić krótką ankietę: ${applyUrl}`)
    if (wa) window.open(wa, '_blank', 'noopener,noreferrer')
    else notify({ title: 'Brak numeru telefonu w leadzie', variant: 'error' })
  }, [applyUrl, notify, phone])

  return (
    <section className="rounded-xl border border-brand-100 bg-brand-50/40 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">Ankieta reklamowa</p>
          <p className="mt-1 text-sm text-slate-700">{statusLabel}</p>
        </div>
        <button
          type="button"
          className="btn-primary inline-flex h-9 items-center gap-2 rounded-lg px-3 text-sm font-semibold"
          disabled={busy}
          onClick={() => void sendInvite()}
        >
          <IconSend size={16} stroke={1.75} aria-hidden />
          {busy ? 'Tworzenie…' : 'Wyślij ankietę'}
        </button>
      </div>
      {applyUrl ? (
        <div className="mt-4 space-y-3 rounded-lg border border-slate-200 bg-white p-3">
          <p className="break-all font-mono text-xs text-slate-600">{applyUrl}</p>
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn-secondary inline-flex h-8 items-center gap-1 rounded-lg px-3 text-xs" onClick={() => void copyLink()}>
              <IconCopy size={14} stroke={1.75} aria-hidden />
              Kopiuj link
            </button>
            <button type="button" className="btn-secondary inline-flex h-8 items-center gap-1 rounded-lg px-3 text-xs" onClick={openWhatsApp}>
              <IconBrandWhatsapp size={14} stroke={1.75} aria-hidden />
              WhatsApp
            </button>
            <span className="inline-flex h-8 items-center gap-1 rounded-lg bg-emerald-50 px-3 text-xs font-medium text-emerald-800">
              <IconCheck size={14} stroke={1.75} aria-hidden />
              Wysłano
            </span>
          </div>
        </div>
      ) : null}
    </section>
  )
}
