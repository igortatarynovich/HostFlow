import clsx from 'clsx'
import { useCallback, useState } from 'react'
import { api } from '../../../api/client'
import type { OperationalRequirementRow } from '../../../api/candidateRequirements'
import { completeOperationalRequirementActivity } from '../../../api/candidateRequirements'
import { useI18n } from '../../../i18n'

type Props = {
  candidateId: string
  item: OperationalRequirementRow
  canEdit: boolean
  onCompleted: () => void
  className?: string
}

function operationalTitle(t: ReturnType<typeof useI18n>['t'], item: OperationalRequirementRow): string {
  const code = item.requirement_code
  return t(`app.candidate_requirements.workspace.operational.${code}`, {
    defaultValue: item.public_name || code.replace(/_/g, ' '),
  })
}

export default function RequirementActivityPane({
  candidateId,
  item,
  canEdit,
  onCompleted,
  className,
}: Props) {
  const { t } = useI18n()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const satisfied = item.status === 'satisfied'

  const recordCall = useCallback(async () => {
    if (!canEdit || satisfied) return
    setBusy(true)
    setError(null)
    try {
      const dueAt = new Date(Date.now() + 60 * 60 * 1000).toISOString()
      const activityType = item.cta?.default_activity_type || 'call'
      const { data: activity } = await api.post<{ id: string }>('/activities', {
        title: t('app.candidate_requirements.workspace.activity_call_title', {
          defaultValue: 'Call candidate',
        }),
        type: activityType,
        entity_type: 'candidate',
        entity_id: candidateId,
        due_at: dueAt,
      })
      await completeOperationalRequirementActivity(candidateId, item.requirement_code, {
        activity_id: String(activity.id),
      })
      onCompleted()
    } catch (err: unknown) {
      const ex = err as { response?: { data?: { detail?: string } }; message?: string }
      setError(ex?.response?.data?.detail || ex?.message || 'Failed to record contact')
    } finally {
      setBusy(false)
    }
  }, [canEdit, candidateId, item, onCompleted, satisfied, t])

  return (
    <section className={clsx('rounded-xl border border-slate-200 bg-white p-4 sm:p-5', className)}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-slate-900">{operationalTitle(t, item)}</h3>
          <p className="mt-1 text-sm text-slate-600">
            {t('app.candidate_requirements.workspace.activity_subtitle', {
              defaultValue: 'Record a call or contact attempt to close this operational requirement.',
            })}
          </p>
        </div>
        <span
          className={clsx(
            'rounded-full border px-2.5 py-0.5 text-xs font-medium',
            satisfied
              ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
              : 'border-amber-200 bg-amber-50 text-amber-950',
          )}
        >
          {satisfied
            ? t('app.candidate_requirements.workspace.activity_satisfied', { defaultValue: 'Completed' })
            : t('app.candidate_requirements.workspace.activity_open', { defaultValue: 'Open' })}
        </span>
      </div>

      {satisfied && item.satisfied_via === 'lead_continuity' ? (
        <p className="mt-3 text-sm text-slate-600">
          {t('app.candidate_requirements.workspace.activity_lead_continuity', {
            defaultValue: 'Already satisfied from lead intake — no duplicate first-contact task needed.',
          })}
        </p>
      ) : null}

      {satisfied && item.activity_id ? (
        <p className="mt-3 text-xs text-slate-500">
          {t('app.candidate_requirements.workspace.activity_linked', {
            defaultValue: 'Linked activity: {id}',
            id: item.activity_id,
          })}
        </p>
      ) : null}

      {error ? <p className="mt-3 text-sm text-rose-700">{error}</p> : null}

      {!satisfied && canEdit ? (
        <div className="mt-4">
          <button
            type="button"
            className="inline-flex items-center rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
            disabled={busy}
            onClick={() => void recordCall()}
          >
            {busy
              ? t('common.loading', { defaultValue: 'Loading…' })
              : t('app.candidate_requirements.workspace.activity_record_call', {
                  defaultValue: 'Record call',
                })}
          </button>
        </div>
      ) : null}

      {!canEdit && !satisfied ? (
        <p className="mt-3 text-xs text-slate-500">
          {t('app.candidate_requirements.workspace.read_only', {
            defaultValue: 'Recruitment locked — view only',
          })}
        </p>
      ) : null}
    </section>
  )
}
