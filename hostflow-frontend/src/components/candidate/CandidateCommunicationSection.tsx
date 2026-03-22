import { memo, useEffect, useMemo, useState } from 'react'
import { IconMessageCircle } from '@tabler/icons-react'
import { Link } from 'react-router-dom'
import { listCommunicationThreads, type CommunicationThread } from '../../api/communications'
import { useI18n } from '../../i18n'
import type { UUID } from '../../api/types'
import CandidateRodoSection from './CandidateRodoSection'
import CandidateContactAttemptsSection from './CandidateContactAttemptsSection'

interface CandidateCommunicationSectionProps {
  candidateId: UUID
  companyId: UUID | null
  onRodoSent?: () => void
  onAttemptCreated?: () => void
  refreshTrigger?: number
}

function CandidateCommunicationSection({
  candidateId,
  companyId,
  onRodoSent,
  onAttemptCreated,
  refreshTrigger,
}: CandidateCommunicationSectionProps) {
  const { t } = useI18n()
  const [threads, setThreads] = useState<CommunicationThread[]>([])
  const [loadingThreads, setLoadingThreads] = useState(false)

  useEffect(() => {
    let mounted = true
    const run = async () => {
      setLoadingThreads(true)
      try {
        const res = await listCommunicationThreads({ limit: 300, includeArchived: false })
        if (!mounted) return
        const items = Array.isArray(res.items) ? res.items : []
        const matched = items
          .filter((th) => String(th.channel || '').toLowerCase() !== 'email')
          .filter((th) => String(th.linked_candidate_id || '') === String(candidateId))
          .sort((a, b) => Date.parse(String(b.updated_at || b.last_message_at || 0)) - Date.parse(String(a.updated_at || a.last_message_at || 0)))
        setThreads(matched)
      } catch {
        if (mounted) setThreads([])
      } finally {
        if (mounted) setLoadingThreads(false)
      }
    }
    void run()
    return () => {
      mounted = false
    }
  }, [candidateId, refreshTrigger])

  const newestThread = useMemo(() => threads[0] || null, [threads])

  return (
    <section className="app-surface p-6">
      <div className="flex items-center gap-3 mb-6">
        <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 text-brand-700">
          <IconMessageCircle size={20} />
        </span>
        <div>
          <h2 className="text-lg font-semibold text-slate-900">
            {t('app.candidate_card.sections.communication.title')}
          </h2>
          <p className="text-sm text-slate-500">
            {t('app.candidate_card.sections.communication.description')}
          </p>
        </div>
      </div>
      <div className="space-y-4">
        <div className="alert-info p-4">
          <div className="mb-2 flex items-center justify-between gap-2">
            <div className="text-sm font-semibold text-slate-900">
              {t('app.candidate_card.communication.linked_messages', { defaultValue: 'Messages linked to candidate' })}
            </div>
            {newestThread ? (
              <Link
                to={`/app/messages?threadId=${newestThread.id}&candidateId=${candidateId}`}
                className="btn-secondary btn-sm"
              >
                {t('app.candidate_card.communication.open_latest_dialog', { defaultValue: 'Open latest dialog' })}
              </Link>
            ) : (
              <Link
                to={`/app/messages?candidateId=${candidateId}`}
                className="btn-secondary btn-sm"
              >
                {t('app.candidate_card.communication.open_inbox', { defaultValue: 'Open messages inbox' })}
              </Link>
            )}
          </div>
          {loadingThreads && (
            <div className="text-xs text-slate-500">
              {t('app.candidate_card.communication.loading_dialogs', { defaultValue: 'Loading dialogs...' })}
            </div>
          )}
          {!loadingThreads && threads.length === 0 && (
            <div className="text-xs text-slate-500">
              {t('app.candidate_card.communication.empty_dialogs', {
                defaultValue: 'No linked dialogs yet. Open Messages and link this candidate in dialog header.',
              })}
            </div>
          )}
          {!loadingThreads && threads.length > 0 && (
            <div className="space-y-2">
              {threads.slice(0, 4).map((th) => (
                <Link
                  key={th.id}
                  to={`/app/messages?threadId=${th.id}&candidateId=${candidateId}`}
                  className="block rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm hover:border-brand-300 hover:bg-brand-50/40"
                >
                  <div className="font-medium text-slate-900">{th.subject || th.last_message_preview || `${String(th.channel || '').toUpperCase()} dialog`}</div>
                  <div className="mt-1 text-xs text-slate-500">
                    {String(th.channel || '').toUpperCase()} · {th.assignee_id ? `assigned ${th.assignee_id}` : 'unassigned'}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
        <div className="border-b border-slate-200 pb-6">
          <CandidateRodoSection
            candidateId={candidateId}
            onSent={onRodoSent}
            refreshTrigger={refreshTrigger}
          />
        </div>
        <div>
          <CandidateContactAttemptsSection
            candidateId={candidateId}
            onAttemptCreated={onAttemptCreated}
            refreshTrigger={refreshTrigger}
          />
        </div>
      </div>
    </section>
  )
}

export default memo(CandidateCommunicationSection)
