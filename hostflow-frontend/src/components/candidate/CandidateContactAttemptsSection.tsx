import { memo, useCallback, useEffect, useState } from 'react'
import { useI18n } from '../../i18n'
import type { UUID } from '../../api/types'
import {
  listContactAttempts,
  getContactPolicy,
  createContactAttempt,
  type ContactAttemptOut,
  type ContactPolicyOut,
  type ContactAttemptCreate,
} from '../../api/contactAttempts'
import { formatDateTime } from '../../utils/dateFormat'
import { useToast } from '../Toast'

const CHANNEL_LABELS: Record<string, string> = {
  call: 'call',
  sms: 'SMS',
  email: 'Email',
  whatsapp: 'WhatsApp',
  messenger: 'Messenger',
}

const RESULT_LABELS: Record<string, string> = {
  no_answer: 'no_answer',
  answered: 'answered',
  wrong_number: 'wrong_number',
  unavailable: 'unavailable',
}

interface CandidateContactAttemptsSectionProps {
  candidateId: UUID
  onAttemptCreated?: () => void
  /** When this value changes, policy and attempts are refetched (e.g. after RODO sent) */
  refreshTrigger?: number
}

function CandidateContactAttemptsSection({
  candidateId,
  onAttemptCreated,
  refreshTrigger = 0,
}: CandidateContactAttemptsSectionProps) {
  const { t } = useI18n()
  const { notify } = useToast()
  const [policy, setPolicy] = useState<ContactPolicyOut | null>(null)
  const [attempts, setAttempts] = useState<ContactAttemptOut[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [form, setForm] = useState<ContactAttemptCreate>({
    channel: 'call',
    result: 'no_answer',
    note: '',
  })

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      const [pol, att] = await Promise.all([
        getContactPolicy(candidateId),
        listContactAttempts(candidateId),
      ])
      setPolicy(pol)
      setAttempts(att)
    } catch (e: any) {
      setPolicy(null)
      setAttempts([])
    } finally {
      setLoading(false)
    }
  }, [candidateId])

  useEffect(() => {
    void fetchData()
  }, [fetchData, refreshTrigger])

  const handleSubmit = async () => {
    setSubmitting(true)
    try {
      await createContactAttempt(candidateId, {
        ...form,
        note: form.note?.trim() || undefined,
      })
      setModalOpen(false)
      setForm({ channel: 'call', result: 'no_answer', note: '' })
      await fetchData()
      onAttemptCreated?.()
      notify({
        title: t('app.candidate_card.contact_attempts.registered', {
          defaultValue: 'Próba kontaktu zarejestrowana',
        }),
        variant: 'success',
      })
    } catch (e: any) {
      notify({
        title: e?.response?.data?.detail ?? 'Error',
        variant: 'error',
      })
    } finally {
      setSubmitting(false)
    }
  }

  if (loading || !policy) {
    return (
      <section className="card w-full p-4">
        <h3 className="text-sm font-medium text-slate-700">
          {t('app.candidate_card.contact_attempts.title', {
            defaultValue: 'Próby kontaktu',
          })}
        </h3>
        <p className="mt-1 text-sm text-slate-500">
          {loading ? t('common.loading', { defaultValue: 'Loading...' }) : '—'}
        </p>
      </section>
    )
  }

  if (!policy.enabled) {
    return null
  }

  const canAdd = attempts.length < policy.max_attempts
  const rodoRequired = !policy.rodo_sent

  return (
    <section className="card w-full p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-medium text-slate-700 flex items-center gap-2 min-w-0">
          {t('app.candidate_card.contact_attempts.title', {
            defaultValue: 'Próby kontaktu',
          })}
          <span className="inline-flex shrink-0 items-center rounded-md bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
            {attempts.length} / {policy.max_attempts}
          </span>
        </h3>
        {canAdd && (
          <button
            type="button"
            onClick={() => !rodoRequired && setModalOpen(true)}
            disabled={rodoRequired}
            className="btn-primary btn-sm shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {t('app.candidate_card.contact_attempts.register_btn', {
              defaultValue: 'Zarejestruj próbę kontaktu',
            })}
          </button>
        )}
      </div>
      {rodoRequired && (
        <p className="mt-2 text-sm text-amber-600">
          {t('app.candidate_card.contact_attempts.rodo_required', {
            defaultValue: 'Wyślij informację RODO kandydatowi przed rejestracją prób kontaktu.',
          })}
        </p>
      )}
      <div className="mt-2 space-y-2">
        {attempts.length === 0 ? (
          <p className="text-sm text-slate-500">
            {t('app.candidate_card.contact_attempts.no_attempts', {
              defaultValue: 'Brak prób',
            })}
          </p>
        ) : (
          attempts.map((a) => (
            <div
              key={a.id}
              className="flex flex-col gap-1 rounded border border-slate-100 bg-slate-50 px-3 py-2 text-sm sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0">
                <span className="font-medium">#{a.attempt_number}</span>
                <span className="text-slate-500">
                  {CHANNEL_LABELS[a.channel] ?? a.channel}
                </span>
                <span className="text-slate-600">
                  {RESULT_LABELS[a.result] ?? a.result}
                </span>
              </div>
              <span className="text-slate-500 shrink-0">{formatDateTime(a.attempted_at)}</span>
            </div>
          ))
        )}
      </div>
      {!canAdd && (
        <p className="mt-2 text-xs text-slate-500">
          {t('app.candidate_card.contact_attempts.max_reached', {
            defaultValue: 'Osiągnięto maksymalną liczbę prób',
            values: { max: policy.max_attempts },
          })}
        </p>
      )}

      {modalOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={() => !submitting && setModalOpen(false)}
        >
          <div
            className="card max-h-[90vh] w-full max-w-md overflow-auto p-4 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h4 className="text-lg font-medium text-slate-800">
              {t('app.candidate_card.contact_attempts.register_btn', {
                defaultValue: 'Zarejestruj próbę kontaktu',
              })}
            </h4>
            <div className="mt-4 space-y-3">
              <div>
                <label className="label">Kanał</label>
                <select
                  value={form.channel}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, channel: e.target.value as ContactAttemptCreate['channel'] }))
                  }
                  className="input mt-1"
                >
                  {(['call', 'sms', 'email', 'whatsapp', 'messenger'] as const).map((ch) => (
                    <option key={ch} value={ch}>
                      {CHANNEL_LABELS[ch]}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label">Wynik</label>
                <select
                  value={form.result}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, result: e.target.value as ContactAttemptCreate['result'] }))
                  }
                  className="input mt-1"
                >
                  {(['no_answer', 'answered', 'wrong_number', 'unavailable'] as const).map(
                    (r) => (
                      <option key={r} value={r}>
                        {RESULT_LABELS[r]}
                      </option>
                    )
                  )}
                </select>
              </div>
              <div>
                <label className="label">Notatka</label>
                <textarea
                  value={form.note ?? ''}
                  onChange={(e) => setForm((f) => ({ ...f, note: e.target.value }))}
                  rows={2}
                  className="textarea mt-1"
                />
              </div>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                disabled={submitting}
                className="btn-secondary"
              >
                {t('common.cancel', { defaultValue: 'Anuluj' })}
              </button>
              <button
                type="button"
                onClick={handleSubmit}
                disabled={submitting}
                className="btn-primary disabled:opacity-50"
              >
                {submitting
                  ? t('common.saving', { defaultValue: 'Zapisywanie...' })
                  : t('common.save', { defaultValue: 'Zapisz' })}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}

export default memo(CandidateContactAttemptsSection)
