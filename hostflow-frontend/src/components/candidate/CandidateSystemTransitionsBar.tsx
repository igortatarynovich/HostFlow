import { useState } from 'react'
import type { FunnelTransition } from '../../api/funnels'
import { fireCandidateSystemTransition } from '../../api/candidateSystemTransitions'
import { useI18n } from '../../i18n'
import { getFriendlyErrorInfo } from '../../utils/friendlyError'

type Props = {
  candidateId: string
  transitions: FunnelTransition[]
  lifecycleStatus?: string | null
  canEdit?: boolean
  onFired?: (result: { catalog_key: string; employee_id?: string | null }) => void
}

const LABEL_FALLBACK: Record<string, string> = {
  handoff_to_hr: 'Handoff to HR',
  handoff_to_client: 'Handoff to client',
  close_success: 'Close successfully',
  close_declined: 'Close declined',
}

export default function CandidateSystemTransitionsBar({
  candidateId,
  transitions,
  lifecycleStatus,
  canEdit = true,
  onFired,
}: Props) {
  const { t } = useI18n()
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const closed = ['closed', 'archived'].includes(String(lifecycleStatus || '').toLowerCase())
  if (!transitions.length) return null

  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50/60 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wide text-amber-900">
            {t('candidates.system_transitions.title', { defaultValue: 'System transitions' })}
          </div>
          <p className="mt-0.5 text-xs text-amber-800/80">
            {t('candidates.system_transitions.help', {
              defaultValue: 'Locked exits — not board stages. Firing closes the candidate operationally.',
            })}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {transitions.map((tr) => (
            <button
              key={tr.id || tr.catalog_key}
              type="button"
              disabled={!canEdit || closed || Boolean(busy)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-xs font-medium text-amber-950 hover:bg-amber-100 disabled:opacity-50"
              onClick={async () => {
                setError(null)
                setBusy(tr.catalog_key)
                try {
                  const res = await fireCandidateSystemTransition(candidateId, tr.catalog_key)
                  onFired?.({ catalog_key: res.catalog_key, employee_id: res.employee_id })
                } catch (e) {
                  const info = getFriendlyErrorInfo(e)
                  setError(info.message || String(e))
                } finally {
                  setBusy(null)
                }
              }}
            >
              <span className="rounded border border-amber-300 px-1 text-[9px] uppercase">locked</span>
              {tr.label || LABEL_FALLBACK[tr.catalog_key] || tr.catalog_key}
              {busy === tr.catalog_key ? '…' : null}
            </button>
          ))}
        </div>
      </div>
      {closed ? (
        <p className="mt-2 text-xs text-slate-600">
          {t('candidates.system_transitions.already_closed', {
            defaultValue:
              'Candidate is closed — pick an active funnel stage on the board to reopen, or leave closed.',
          })}
        </p>
      ) : null}
      {error ? <p className="mt-2 text-xs text-red-700">{error}</p> : null}
    </div>
  )
}
