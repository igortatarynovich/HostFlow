import clsx from 'clsx'
import { useState } from 'react'
import { logRecruitmentApplicationCallResult } from '../../../api/applications'
import type { Application } from '../../../api/types/application'
import { Button } from '../../../components/ui/Button'
import { FieldGrid } from '../../../components/ui/FieldGrid'
import { useToast } from '../../../components/Toast'
import { usePlanLimitModal } from '../../../contexts/PlanLimitModalContext'
import { useI18n } from '../../../i18n'
import { getFriendlyErrorInfo } from '../../../utils/friendlyError'
import type { WorkspaceCapabilityRenderContext } from '../../../platform/workspace-capability/renderContext'
import { applicationFormAnswerRows } from '../applicationFormAnswers'
import {
  APPLICATION_CALL_NO_ANSWER_CODES,
  APPLICATION_CALL_REACHED_CODES,
  applicationCallResultHistory,
  applicationLatestCallResult,
  type ApplicationCallResultCode,
} from '../applicationCallResult'

function toDatetimeLocalValue(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function fromDatetimeLocalValue(raw: string): string | null {
  const s = raw.trim()
  if (!s) return null
  const d = new Date(s)
  if (Number.isNaN(d.getTime())) return null
  return d.toISOString()
}

function formatWhen(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString()
}

function ApplicationAnswers({ application }: { application: Application }) {
  const { t } = useI18n()
  const rows = applicationFormAnswerRows(application)
  return (
    <section aria-labelledby="application-form-answers-heading">
      <h2 id="application-form-answers-heading" className="text-base font-semibold tracking-tight text-slate-900">
        {t('app.recruitment_inquiry.form_answers.title')}
      </h2>
      {rows.length === 0 ? (
        <p className="mt-2 text-sm text-slate-500">{t('app.recruitment_inquiry.form_answers.empty')}</p>
      ) : (
        <div className="mt-3 rounded-xl bg-white px-4 py-3 ring-1 ring-slate-900/[0.06]">
          <FieldGrid cols={1}>
            {rows.map((row) => (
              <div key={row.name}>
                <div className="text-sm text-slate-500">{row.label}</div>
                <div className="mt-0.5 text-base font-medium text-slate-900">{row.value}</div>
              </div>
            ))}
          </FieldGrid>
        </div>
      )}
    </section>
  )
}

function ApplicationCallLog({
  application,
  onRefresh,
}: {
  application: Application
  onRefresh: () => void
}) {
  const { t } = useI18n()
  const { notify } = useToast()
  const planLimitModal = usePlanLimitModal()
  const latest = applicationLatestCallResult(application)
  const history = applicationCallResultHistory(application)
  const resultLabel = (code: string) => t(`app.recruitment_inquiry.call_result.results.${code}`, { defaultValue: code })

  const [callResult, setCallResult] = useState<ApplicationCallResultCode>(
    (latest?.result as ApplicationCallResultCode) || 'no_answer',
  )
  const [callNote, setCallNote] = useState('')
  const [nextContact, setNextContact] = useState(toDatetimeLocalValue(latest?.next_contact_at))
  const [saving, setSaving] = useState(false)
  const needsCallbackTime = callResult === 'callback_requested'

  const latestLine = latest
    ? latest.note
      ? `${resultLabel(String(latest.result))} — ${latest.note}`
      : resultLabel(String(latest.result))
    : null

  const save = async () => {
    if (saving) return
    if (needsCallbackTime && !fromDatetimeLocalValue(nextContact)) {
      notify({ title: t('app.recruitment_inquiry.call_result.next_contact_required'), variant: 'error' })
      return
    }
    setSaving(true)
    try {
      await logRecruitmentApplicationCallResult(application.id, {
        result: callResult,
        note: callNote.trim() || null,
        next_contact_at: fromDatetimeLocalValue(nextContact),
      })
      setCallNote('')
      notify({ title: t('app.recruitment_inquiry.call_result.saved'), variant: 'success' })
      onRefresh()
    } catch (err: unknown) {
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.recruitment_inquiry.call_result.save_failed'))) {
        return
      }
      const info = getFriendlyErrorInfo(err, t('app.recruitment_inquiry.call_result.save_failed'), t)
      notify({ title: info.title, variant: 'error' })
    } finally {
      setSaving(false)
    }
  }

  const renderGroup = (titleKey: string, codes: readonly ApplicationCallResultCode[]) => (
    <fieldset className="space-y-1.5">
      <legend className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{t(titleKey)}</legend>
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
                active ? 'bg-slate-900 text-white ring-slate-900' : 'bg-white text-slate-700 ring-slate-200 hover:bg-slate-50',
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
    <section className="space-y-3" aria-labelledby="application-call-heading">
      <div>
        <h2 id="application-call-heading" className="text-[11px] font-bold uppercase tracking-wide text-slate-800">
          {t('app.recruitment_inquiry.call_result.title')}
        </h2>
        <p className="mt-1 text-[11px] leading-tight text-slate-500">{t('app.recruitment_inquiry.call_result.hint')}</p>
      </div>
      {latestLine ? (
        <p className="rounded-lg bg-emerald-500/[0.08] px-3 py-2 text-sm font-medium text-emerald-950">
          {t('app.recruitment_inquiry.call_result.latest', { values: { result: latestLine } })}
        </p>
      ) : null}
      {renderGroup('app.recruitment_inquiry.call_result.reached', APPLICATION_CALL_REACHED_CODES)}
      {renderGroup('app.recruitment_inquiry.call_result.not_reached', APPLICATION_CALL_NO_ANSWER_CODES)}
      {needsCallbackTime ? (
        <label className="block text-xs font-medium text-slate-500">
          <span className="mb-1.5 block">{t('app.recruitment_inquiry.call_result.next_contact')}</span>
          <input
            type="datetime-local"
            className="input w-full rounded-xl border-0 bg-slate-500/[0.06] px-3 py-2 text-sm ring-1 ring-slate-900/[0.06]"
            value={nextContact}
            disabled={saving}
            onChange={(event) => setNextContact(event.target.value)}
          />
        </label>
      ) : null}
      <label className="block text-xs font-medium text-slate-500">
        <span className="mb-1.5 block">{t('app.recruitment_inquiry.call_result.note')}</span>
        <textarea
          className="input min-h-[4rem] w-full rounded-xl border-0 bg-slate-500/[0.06] px-3 py-2 text-sm ring-1 ring-slate-900/[0.06]"
          value={callNote}
          disabled={saving}
          maxLength={2000}
          placeholder={t('app.recruitment_inquiry.call_result.note_placeholder')}
          onChange={(event) => setCallNote(event.target.value)}
        />
      </label>
      <Button variant="secondary" disabled={saving} onClick={() => void save()} className="w-full">
        {saving ? t('common.loading') : t('app.recruitment_inquiry.call_result.save')}
      </Button>
      {history.length > 0 ? (
        <ul className="space-y-1.5 text-[11px] text-slate-600">
          {history.slice(0, 8).map((item, idx) => (
            <li key={`${item.at || idx}-${item.result}`}>
              <span className="font-medium text-slate-800">{resultLabel(String(item.result))}</span>
              {item.note ? ` — ${item.note}` : ''}
              {item.at ? <span className="text-slate-400"> · {formatWhen(item.at)}</span> : null}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  )
}

/** Recruitment owns application answers and call outcome. Host only places this contribution. */
export function RecruitmentIntakeContribution({
  application,
  onRefresh,
}: WorkspaceCapabilityRenderContext) {
  if (!application) return null
  return (
    <div className="space-y-6" data-capability-id="recruitment.intake">
      <ApplicationAnswers application={application} />
      <ApplicationCallLog application={application} onRefresh={onRefresh} />
    </div>
  )
}
