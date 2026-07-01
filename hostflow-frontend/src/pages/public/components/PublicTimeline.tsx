import type { PublicTimelineEntry } from '../../../api/publicIntake'
import type { TranslateFn } from '../../../i18n'
import { useI18n } from '../../../i18n'

type PublicTimelineProps = {
  entries: PublicTimelineEntry[]
}

export function PublicTimeline({ entries }: PublicTimelineProps) {
  const { t, locale } = useI18n()
  if (!entries.length) {
    return (
      <p className="text-sm text-slate-500">
        {t('public.timeline.empty')}
      </p>
    )
  }

  // Вычисляем общий прогресс
  const totalSteps = entries.length
  const completedSteps = entries.filter((e) => e.status === 'done').length
  const progressPercentage = totalSteps > 0 ? (completedSteps / totalSteps) * 100 : 0

  return (
    <div className="space-y-4">
      {/* Progress bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs text-slate-600">
          <span>{t('public.timeline.progress.label', { defaultValue: 'Общий прогресс' })}</span>
          <span className="font-semibold">{Math.round(progressPercentage)}%</span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
          <div
            className="h-full bg-gradient-to-r from-blue-500 to-green-500 transition-all duration-500 ease-out"
            style={{ width: `${progressPercentage}%` }}
          />
        </div>
      </div>

      {/* Timeline entries */}
      <ol className="space-y-3">
        {entries.map((entry, index) => {
          const title = t(`public.timeline.${entry.key}.title`, {
            defaultValue: entry.title || entry.key,
          })
          const description = t(`public.timeline.${entry.key}.description`, {
            defaultValue: entry.description || '',
          })
          
          // Вычисляем прогресс для документов
          const docProgress =
            entry.meta &&
            typeof entry.meta.ready_required === 'number' &&
            typeof entry.meta.required_total === 'number'
              ? (entry.meta.ready_required / entry.meta.required_total) * 100
              : null

          return (
            <li key={entry.key} className="flex gap-3 rounded-xl border border-slate-100 bg-white/80 p-3">
              <div className="flex flex-col items-center">
                <TimelineStatusDot status={entry.status} />
                {index < entries.length - 1 && (
                  <div
                    className={`mt-1 h-8 w-0.5 ${
                      entry.status === 'done' ? 'bg-green-500' : 'bg-slate-200'
                    }`}
                  />
                )}
              </div>
              <div className="flex-1 space-y-1">
                <p className="text-sm font-semibold text-slate-900">{title}</p>
                {description && <p className="text-xs text-slate-500">{description}</p>}
                {docProgress !== null && (
                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-xs text-slate-600">
                      <span>
                        {t('public.timeline.documents.progress', {
                          values: {
                            ready: entry.meta!.ready_required,
                            total: entry.meta!.required_total,
                          },
                        })}
                      </span>
                      <span className="font-semibold">{Math.round(docProgress)}%</span>
                    </div>
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
                      <div
                        className="h-full bg-blue-500 transition-all duration-300"
                        style={{ width: `${docProgress}%` }}
                      />
                    </div>
                  </div>
                )}
                {entry.completed_at && (
                  <p className="text-[11px] uppercase tracking-wide text-slate-400">
                    {new Date(entry.completed_at).toLocaleDateString(locale)}
                  </p>
                )}
              </div>
            </li>
          )
        })}
      </ol>
    </div>
  )
}

function TimelineStatusDot({ status }: { status: string }) {
  const style = statusColor(status)
  return <span className={`mt-1 h-3 w-3 rounded-full ${style}`} />
}

function statusColor(status: string) {
  if (status === 'done') return 'bg-green-500'
  if (status === 'current') return 'bg-blue-500 animate-pulse'
  return 'bg-slate-300'
}

export function buildFallbackTimeline(
  params: {
  createdAt?: string | null
  submittedAt?: string | null
  profileReady: boolean
  documentsReady: boolean
  readyRequiredCount: number
  requiredTotal: number
  },
  t: TranslateFn,
): PublicTimelineEntry[] {
  const entries: PublicTimelineEntry[] = [
    {
      key: 'intake_created',
      title: t('public.timeline.created.title'),
      status: params.createdAt ? 'done' : 'pending',
      description: t('public.timeline.created.description'),
      completed_at: params.createdAt || undefined,
    },
    {
      key: 'profile_data',
      title: t('public.timeline.profile.title'),
      status: params.profileReady ? 'done' : 'pending',
      description: t('public.timeline.profile.description'),
    },
    {
      key: 'documents_upload',
      title: t('public.timeline.documents.title'),
      status: params.documentsReady ? 'done' : 'pending',
      description: t('public.timeline.documents.description'),
      meta: {
        ready_required: params.readyRequiredCount,
        required_total: params.requiredTotal,
      },
    },
    {
      key: 'submitted',
      title: t('public.timeline.submitted.title'),
      status: params.submittedAt ? 'done' : 'pending',
      description: t('public.timeline.submitted.description'),
      completed_at: params.submittedAt || undefined,
    },
  ]

  let currentChosen = false
  return entries.map((entry) => {
    if (entry.status === 'done') {
      return entry
    }
    if (!currentChosen) {
      currentChosen = true
      return { ...entry, status: 'current' }
    }
    return { ...entry, status: 'pending' }
  })
}
