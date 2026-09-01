import clsx from 'clsx'
import { useState } from 'react'
import { IconPhone } from '@tabler/icons-react'

import { logLeadCallResult, type LeadCallResultCode } from '../../api/client'
import type { Lead } from '../../api/types'
import { usePlanLimitModal } from '../../contexts/PlanLimitModalContext'
import { useI18n } from '../../i18n'
import { getFriendlyErrorInfo } from '../../utils/friendlyError'
import { leadRodoSatisfied } from '../../utils/intakeResolution'
import {
  LEAD_CALL_NO_ANSWER_CODES,
  LEAD_CALL_REACHED_CODES,
  leadCallResultHistory,
  leadLatestCallResult,
} from '../../utils/leadCallResult'
import { useToast } from '../Toast'

type Props = {
  lead: Lead
  onLeadUpdated: (lead: Lead) => void
  /** When false, the tel: button lives in the identity header instead. */
  showTelButton?: boolean
}

function digitsPhone(raw: unknown): string {
  return String(raw || '').replace(/\s/g, '')
}

function hasCallablePhone(raw: unknown): boolean {
  return digitsPhone(raw).replace(/\D/g, '').length > 0
}

function toDatetimeLocalValue(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function formatWhen(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString()
}

function fromDatetimeLocalValue(raw: string): string | null {
  const s = raw.trim()
  if (!s) return null
  const d = new Date(s)
  if (Number.isNaN(d.getTime())) return null
  return d.toISOString()
}

export default function LeadIntakeCallStep({ lead, onLeadUpdated, showTelButton = true }: Props) {
  const { t } = useI18n()
  const { notify } = useToast()
  const planLimitModal = usePlanLimitModal()
  const latest = leadLatestCallResult(lead)
  const history = leadCallResultHistory(lead)
  const rodoOk = leadRodoSatisfied(lead)
  const phone = lead.normalized && typeof lead.normalized === 'object' ? (lead.normalized as Record<string, unknown>).phone : null
  const canTel = hasCallablePhone(phone)

  const [callResult, setCallResult] = useState<LeadCallResultCode>(
    (latest?.result as LeadCallResultCode) || 'no_answer',
  )
  const [callNote, setCallNote] = useState('')
  const [nextContact, setNextContact] = useState(toDatetimeLocalValue(latest?.next_contact_at))
  const [saving, setSaving] = useState(false)

  const needsCallbackTime = callResult === 'callback_requested'
  const resultLabel = (code: string) => t(`app.leads.detail.call_result.results.${code}`, { defaultValue: code })

  const latestLine = latest
    ? latest.note
      ? `${resultLabel(String(latest.result))} — ${latest.note}`
      : resultLabel(String(latest.result))
    : null

  const handleSave = async () => {
    if (saving) return
    if (needsCallbackTime && !fromDatetimeLocalValue(nextContact)) {
      notify({
        title: t('app.leads.intake_workspace.call.next_contact_required', {
          defaultValue: 'Pick a date and time to call back.',
        }),
        variant: 'error',
      })
      return
    }
    setSaving(true)
    try {
      const updated = (await logLeadCallResult(lead.id, {
        result: callResult,
        note: callNote.trim() || null,
        next_contact_at: fromDatetimeLocalValue(nextContact),
      })) as Lead
      onLeadUpdated(updated)
      setCallNote('')
      notify({
        title: t('app.leads.detail.call_result.saved', { defaultValue: 'Call result saved' }),
        variant: 'success',
      })
    } catch (err: unknown) {
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.leads.detail.call_result.save_failed'))) {
        return
      }
      const info = getFriendlyErrorInfo(err, t('app.leads.detail.call_result.save_failed'), t)
      notify({ title: info.title, variant: 'error' })
    } finally {
      setSaving(false)
    }
  }

  const renderGroup = (titleKey: string, codes: LeadCallResultCode[]) => (
    <fieldset className="space-y-1.5">
      <legend className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
        {t(titleKey)}
      </legend>
      <div className="flex flex-wrap gap-1.5">
        {codes.map((code) => {
          const active = callResult === code
          return (
            <button
              key={code}
              type="button"
              disabled={saving}
              onClick={() => setCallResult(code)}
              className={clsx(
                'rounded-lg px-2.5 py-1.5 text-xs font-semibold ring-1 transition-colors disabled:opacity-50',
                active
                  ? 'bg-slate-900 text-white ring-slate-900'
                  : 'bg-white text-slate-700 ring-slate-200 hover:bg-slate-50',
              )}
            >
              {resultLabel(code)}
            </button>
          )
        })}
      </div>
    </fieldset>
  )

  return (
    <section className="space-y-3" aria-labelledby="decision-rail-call">
      <div>
        <h2 id="decision-rail-call" className="text-[11px] font-bold uppercase tracking-wide text-slate-800">
          {t('app.leads.intake_workspace.decision_rail.block_call')}
        </h2>
        <p className="mt-1 text-[11px] leading-tight text-slate-500">
          {t('app.leads.intake_workspace.call.hint', {
            defaultValue: 'Log the outcome after the call. This is activity, not a lead stage.',
          })}
        </p>
      </div>

      {latestLine ? (
        <p className="rounded-lg bg-emerald-500/[0.08] px-3 py-2 text-sm font-medium text-emerald-950">
          {t('app.leads.intake_workspace.decision_rail.call_latest', { values: { result: latestLine } })}
        </p>
      ) : null}

      {showTelButton ? (
        <div className="flex flex-wrap gap-2">
          {canTel ? (
            <a
              href={`tel:${digitsPhone(phone)}`}
              className="btn-primary inline-flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm font-semibold"
            >
              <IconPhone size={18} stroke={1.75} aria-hidden />
              {t('app.leads.inbox.action_call', { defaultValue: 'Call' })}
            </a>
          ) : (
            <p className="text-sm text-amber-800">{t('app.leads.intake_workspace.decision_rail.call_no_phone')}</p>
          )}
        </div>
      ) : null}

      {!rodoOk ? (
        <p className="text-[11px] text-slate-500">
          {t('app.leads.intake_workspace.call.rodo_later', {
            defaultValue: 'RODO is still required before creating a candidate. You can log this call now.',
          })}
        </p>
      ) : null}

      {renderGroup('app.leads.intake_workspace.call.reached', LEAD_CALL_REACHED_CODES)}
      {renderGroup('app.leads.intake_workspace.call.not_reached', LEAD_CALL_NO_ANSWER_CODES)}

      {needsCallbackTime ? (
        <label className="block text-xs font-medium text-slate-500">
          <span className="mb-1.5 block">
            {t('app.leads.intake_workspace.call.next_contact', { defaultValue: 'Next contact' })}
          </span>
          <input
            type="datetime-local"
            className="input w-full rounded-xl border-0 bg-slate-500/[0.06] px-3 py-2 text-sm ring-1 ring-slate-900/[0.06]"
            value={nextContact}
            disabled={saving}
            onChange={(e) => setNextContact(e.target.value)}
          />
        </label>
      ) : null}

      <label className="block text-xs font-medium text-slate-500">
        <span className="mb-1.5 block">{t('app.leads.detail.call_result.fields.note')}</span>
        <textarea
          className="input min-h-[4rem] w-full rounded-xl border-0 bg-slate-500/[0.06] px-3 py-2 text-sm ring-1 ring-slate-900/[0.06]"
          value={callNote}
          disabled={saving}
          maxLength={2000}
          placeholder={t('app.leads.detail.call_result.fields.note_placeholder')}
          onChange={(e) => setCallNote(e.target.value)}
        />
      </label>

      <button
        type="button"
        className="w-full rounded-xl border border-slate-200 bg-white py-3 text-sm font-semibold text-slate-900 shadow-sm hover:bg-slate-50 disabled:opacity-50"
        disabled={saving}
        onClick={() => void handleSave()}
      >
        {saving ? t('common.loading') : t('app.leads.detail.call_result.save')}
      </button>

      {history.length > 0 ? (
        <ul className="space-y-1.5 text-[11px] text-slate-600">
          {history.slice(0, 8).map((item, idx) => (
            <li key={`${item.at || idx}-${item.result}`}>
              <span className="font-medium text-slate-800">{resultLabel(String(item.result))}</span>
              {item.note ? ` — ${item.note}` : ''}
              {item.at ? <span className="text-slate-400"> · {formatWhen(item.at)}</span> : null}
              {item.next_contact_at ? (
                <span className="text-slate-400">
                  {' '}
                  · {t('app.leads.intake_workspace.call.next_contact', { defaultValue: 'Next contact' })} {formatWhen(item.next_contact_at)}
                </span>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  )
}
