import { useCallback, useEffect, useState } from 'react'

import {
  getLead,
  logLeadCallResult,
  type LeadCallResultCode,
} from '../../api/client'
import type { Lead } from '../../api/types'
import { useToast } from '../Toast'
import { usePlanLimitModal } from '../../contexts/PlanLimitModalContext'
import { useI18n } from '../../i18n'
import { getFriendlyErrorInfo } from '../../utils/friendlyError'
import { leadRodoSatisfied } from '../../utils/intakeResolution'
import {
  LEAD_CALL_RESULT_CODES,
  leadCallResultHistory,
  type LeadCallResultEntry,
} from '../../utils/leadCallResult'
import SalesInquiryRodoSection from './SalesInquiryRodoSection'

type Props = {
  leadId: string
  disabled?: boolean
  onSaved?: () => void
}

function formatAt(iso: string | null | undefined, locale: string): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString(locale, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** Call disposition + free-text comment for the sales manager. */
export default function SalesInquiryCallNotesSection({ leadId, disabled, onSaved }: Props) {
  const { t, locale } = useI18n()
  const { notify } = useToast()
  const planLimitModal = usePlanLimitModal()
  const [lead, setLead] = useState<Lead | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [callResult, setCallResult] = useState<LeadCallResultCode>('callback_requested')
  const [callNote, setCallNote] = useState('')

  const load = useCallback(async () => {
    if (!leadId) return
    setLoading(true)
    try {
      const next = await getLead(leadId)
      setLead(next)
    } catch {
      setLead(null)
    } finally {
      setLoading(false)
    }
  }, [leadId])

  useEffect(() => {
    void load()
  }, [load])

  const history = leadCallResultHistory(lead)
  const rodoOk = leadRodoSatisfied(lead)
  const noteRecommended =
    callResult === 'callback_requested' || callResult === 'answered' || callResult === 'interested'

  const resultLabel = (code: string) =>
    t(`app.leads.detail.call_result.results.${code}`, { defaultValue: code })

  const handleSave = async () => {
    if (!leadId || saving || disabled || !rodoOk) return
    setSaving(true)
    try {
      const updated = await logLeadCallResult(leadId, {
        result: callResult,
        note: callNote.trim() || null,
      })
      setLead(updated)
      setCallNote('')
      notify({
        title: t('app.leads.detail.call_result.saved', {
          defaultValue: 'Результат звонка сохранён',
        }),
        variant: 'success',
      })
      onSaved?.()
    } catch (err: unknown) {
      if (
        planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('app.leads.detail.call_result.save_failed', {
            defaultValue: 'Не удалось сохранить результат звонка',
          }),
        )
      ) {
        return
      }
      const info = getFriendlyErrorInfo(
        err,
        t('app.leads.detail.call_result.save_failed', {
          defaultValue: 'Не удалось сохранить результат звонка',
        }),
        t,
      )
      notify({
        title: info.title,
        description: [info.detail, info.hint].filter(Boolean).join(' '),
        variant: 'error',
      })
      void load()
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <p className="text-sm text-slate-500" data-testid="sales-call-notes-loading">
        {t('common.loading', { defaultValue: 'Ładowanie…' })}
      </p>
    )
  }

  return (
    <section className="space-y-3" data-testid="sales-call-notes">
      <SalesInquiryRodoSection
        leadId={leadId}
        lead={lead}
        disabled={disabled || saving}
        onUpdated={(next) => setLead(next)}
      />

      <div>
        <h3 className="text-sm font-semibold text-slate-900">
          {t('app.leads.detail.call_result.title', { defaultValue: 'Результат звонка' })}
        </h3>
        <p className="mt-0.5 text-xs text-slate-500">
          {t('app.leads.detail.call_result.subtitle', {
            defaultValue: 'Перезвонить или что ещё хотят / думают — зафиксируйте после разговора.',
          })}
        </p>
      </div>

      <label className="block text-sm">
        <span className="mb-1 block text-xs font-medium text-slate-600">
          {t('app.leads.detail.call_result.fields.result', { defaultValue: 'Результат' })}
        </span>
        <select
          className="input w-full"
          value={callResult}
          disabled={saving || disabled || !rodoOk}
          onChange={(e) => setCallResult(e.target.value as LeadCallResultCode)}
        >
          {LEAD_CALL_RESULT_CODES.map((code) => (
            <option key={code} value={code}>
              {resultLabel(code)}
            </option>
          ))}
        </select>
      </label>

      <label className="block text-sm">
        <span className="mb-1 block text-xs font-medium text-slate-600">
          {t('app.leads.detail.call_result.fields.note', {
            defaultValue: 'Комментарий',
          })}
          {noteRecommended ? (
            <span className="ml-1 font-normal text-slate-500">
              (
              {t('app.leads.detail.call_result.fields.note_recommended', {
                defaultValue: 'желательно',
              })}
              )
            </span>
          ) : null}
        </span>
        <textarea
          className="textarea mt-0 w-full"
          rows={3}
          maxLength={2000}
          disabled={saving || disabled || !rodoOk}
          value={callNote}
          onChange={(e) => setCallNote(e.target.value)}
          placeholder={t('app.leads.detail.call_result.fields.note_placeholder', {
            defaultValue: 'Например: перезвонить завтра в 15:00, спрашивает про ставку, думает…',
          })}
        />
      </label>

      <div className="flex justify-end">
        <button
          type="button"
          className="btn-primary rounded-lg px-3 py-2 text-sm font-semibold disabled:opacity-60"
          disabled={saving || disabled || !rodoOk}
          onClick={() => void handleSave()}
          title={
            !rodoOk
              ? t('app.leads.messages.process_blocked.LEAD_RODO_REQUIRED', {
                  defaultValue: 'Send RODO or mark covered at source before saving a call result.',
                })
              : undefined
          }
        >
          {saving
            ? t('common.saving', { defaultValue: 'Сохранение…' })
            : t('app.leads.detail.call_result.save', { defaultValue: 'Сохранить' })}
        </button>
      </div>

      {history.length > 0 ? (
        <div className="border-t border-slate-100 pt-3">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('app.leads.detail.call_result.history_title', { defaultValue: 'История звонков' })}
          </h4>
          <ul className="mt-2 space-y-2">
            {history.map((entry: LeadCallResultEntry, idx: number) => (
              <li
                key={`${entry.at || 'x'}-${entry.result}-${idx}`}
                className="rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 text-sm"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <span className="font-medium text-slate-800">{resultLabel(String(entry.result))}</span>
                  {entry.at ? (
                    <span className="text-xs text-slate-500">{formatAt(entry.at, locale)}</span>
                  ) : null}
                </div>
                {entry.note?.trim() ? (
                  <p className="mt-1.5 whitespace-pre-wrap border-t border-slate-100 pt-1.5 text-slate-700">
                    {entry.note.trim()}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  )
}
