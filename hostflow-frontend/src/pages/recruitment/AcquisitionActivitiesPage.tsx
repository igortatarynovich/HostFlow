import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { performAcquisitionActivityAction } from '../../api/searchAcquisition'
import { useI18n } from '../../i18n'
import { useToast } from '../../components/Toast'
import { useSearchWorkspace } from './SearchWorkspaceLayout'
import { AcquisitionActivityCard } from '../../components/recruitment/AcquisitionActivityCard'
import { useAcquisitionOutlet } from './useAcquisitionOutlet'

export default function AcquisitionActivitiesPage() {
  const { t } = useI18n()
  const { notify } = useToast()
  const { searchId, refreshPulse } = useSearchWorkspace()
  const { snapshot, loading, refresh } = useAcquisitionOutlet()
  const [searchParams] = useSearchParams()
  const highlightId = searchParams.get('highlight')
  const [busyId, setBusyId] = useState<string | null>(null)

  const activities = snapshot?.activities ?? []

  useEffect(() => {
    if (!highlightId) return
    const el = document.getElementById(`activity-${highlightId}`)
    el?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }, [highlightId, activities.length])

  async function runAction(activityId: string, action: string) {
    setBusyId(activityId)
    try {
      await performAcquisitionActivityAction(searchId, activityId, action)
      await refresh()
      await refreshPulse()
      notify({
        title: t('app.acquisition.action_done', { defaultValue: 'Готово' }),
        variant: 'success',
      })
    } catch {
      notify({
        title: t('app.acquisition.action_failed', { defaultValue: 'Не удалось выполнить действие' }),
        variant: 'error',
      })
    } finally {
      setBusyId(null)
    }
  }

  const sorted = useMemo(
    () =>
      [...activities].sort((a, b) => {
        const order = { meta: 0, public_link: 1, qr: 2 }
        const ta = order[(a.channel_type || a.type) as keyof typeof order] ?? 5
        const tb = order[(b.channel_type || b.type) as keyof typeof order] ?? 5
        return ta - tb
      }),
    [activities],
  )

  if (loading) {
    return <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Загрузка…' })}</p>
  }

  if (sorted.length === 0) {
    return (
      <section className="rounded-xl border border-dashed border-slate-200 bg-white p-8 text-center">
        <p className="text-sm text-slate-600">
          {t('app.acquisition.empty_activities_legacy', {
            defaultValue:
              'Исторических активностей нет. Новые запуски создаются только в Marketing (Campaign → Flight).',
          })}
        </p>
      </section>
    )
  }

  return (
    <div className="space-y-3" data-testid="m1-acquisition-activities">
      {sorted.map((activity) => (
        <AcquisitionActivityCard
          key={activity.id}
          activity={activity}
          highlighted={highlightId === activity.id}
          busy={busyId === activity.id}
          onPause={() => void runAction(activity.id, 'pause')}
          onResume={() => void runAction(activity.id, 'resume')}
          onArchive={() => {
            if (
              window.confirm(
                t('app.acquisition.archive_confirm', { defaultValue: 'Архивировать эту активность?' }),
              )
            ) {
              void runAction(activity.id, 'archive')
            }
          }}
        />
      ))}
    </div>
  )
}
