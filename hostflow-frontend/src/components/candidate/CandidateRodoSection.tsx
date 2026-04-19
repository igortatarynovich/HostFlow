import { memo, useEffect, useState } from 'react'
import { IconCheck } from '@tabler/icons-react'
import { useI18n } from '../../i18n'
import type { UUID } from '../../api/types'
import { getRodoStatus, sendRodo } from '../../api/legalDocuments'
import { formatDateTime } from '../../utils/dateFormat'
import { explainWhyRodoNotSentYet } from '../../utils/contactAttemptRodoHints'
import ErrorRecoveryBanner from '../ErrorRecoveryBanner'

interface CandidateRodoSectionProps {
  candidateId: UUID
  onSent?: () => void
  refreshTrigger?: number
}

function CandidateRodoSection({ candidateId, onSent, refreshTrigger = 0 }: CandidateRodoSectionProps) {
  const { t } = useI18n()
  const [status, setStatus] = useState<{
    sent: boolean
    sent_at: string | null
    sent_by_user_id: string | null
    recipient: string | null
    rodo_version_id: string | null
    can_send: boolean
  } | null>(null)
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function fetchStatus() {
      try {
        setLoading(true)
        setError(null)
        const s = await getRodoStatus(candidateId)
        if (!cancelled) setStatus(s)
      } catch (e: any) {
        if (!cancelled) setError(e?.response?.data?.detail ?? e?.message ?? 'Error')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void fetchStatus()
    return () => { cancelled = true }
  }, [candidateId, refreshTrigger])

  const handleSend = async () => {
    if (!status?.can_send || sending) return
    setSending(true)
    setError(null)
    try {
      await sendRodo(candidateId)
      const s = await getRodoStatus(candidateId)
      setStatus(s)
      onSent?.()
    } catch (e: any) {
      const detail = e?.response?.data?.detail ?? e?.message ?? 'Error'
      setError(detail)
      if (String(detail).toLowerCase().includes('already sent')) {
        try {
          const latest = await getRodoStatus(candidateId)
          setStatus(latest)
          if (latest.sent) onSent?.()
        } catch {
          // keep original error if status refresh fails
        }
      }
    } finally {
      setSending(false)
    }
  }

  if (loading || !status) {
    return (
      <section className="card w-full p-4">
        <h3 className="text-sm font-medium text-slate-700">
          {t('app.candidate_card.rodo.title')}
        </h3>
        <p className="mt-1 text-sm text-slate-500">
          {loading ? t('common.loading') : '—'}
        </p>
      </section>
    )
  }

  return (
    <section className="card w-full p-4">
      <h3 className="text-sm font-medium text-slate-700 flex items-center gap-2">
        {t('app.candidate_card.rodo.title')}
        {status.sent && (
          <span className="inline-flex items-center gap-1 rounded-md bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800">
            <IconCheck size={12} />
            {t('app.candidate_card.rodo.badge_sent')}
          </span>
        )}
      </h3>
      {error && (
        <div className="mt-2">
          <ErrorRecoveryBanner
            info={{
              title: error,
              hint: t('app.common.retry_hint'),
            }}
            onRetry={() => setError(null)}
            retryLabel={t('common.actions.close', { defaultValue: 'Close' })}
            compact
          />
        </div>
      )}
      {status.sent ? (
        <div className="mt-2 space-y-1 text-sm text-slate-600">
          <p>
            {t('app.candidate_card.rodo.sent_at')}:{' '}
            {status.sent_at ? formatDateTime(status.sent_at) : '—'}
          </p>
          {status.recipient && (
            <p>
              {t('app.candidate_card.rodo.to')}: {status.recipient}
            </p>
          )}
          {status.rodo_version_id && (
            <p className="text-xs text-slate-500">v. {status.rodo_version_id}</p>
          )}
        </div>
      ) : (
        <div className="mt-2">
          <button
            type="button"
            onClick={handleSend}
            disabled={!status.can_send || sending}
            className="btn-primary btn-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {sending
              ? t('common.sending')
              : t('app.candidate_card.rodo.send_btn')}
          </button>
          {!status.can_send ? (
            <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-amber-900/95">
              {explainWhyRodoNotSentYet(status, t).map((line, idx) => (
                <li key={idx}>{line}</li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-xs text-slate-600">
              {t('app.candidate_card.rodo.ready_to_send_hint', {
                defaultValue: 'You can send the RODO information email from here.',
              })}
            </p>
          )}
        </div>
      )}
    </section>
  )
}

export default memo(CandidateRodoSection)
