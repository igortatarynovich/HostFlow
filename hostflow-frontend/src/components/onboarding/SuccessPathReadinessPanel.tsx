import { Link } from 'react-router-dom'
import {
  IconArrowRight,
  IconCheck,
  IconCircle,
  IconLoader2,
} from '@tabler/icons-react'

import { useI18n } from '../../i18n'
import {
  useSuccessPathReadiness,
  type SuccessPathItemId,
} from '../../hooks/useSuccessPathReadiness'

type SuccessPathReadinessPanelProps = {
  className?: string
  /** When false, hide the panel once the core path is complete. */
  showWhenComplete?: boolean
}

export function SuccessPathReadinessPanel({
  className = '',
  showWhenComplete = false,
}: SuccessPathReadinessPanelProps) {
  const { t } = useI18n()
  const { items, nextAction, doneCount, totalCount, pathComplete, loading, deferMeta, refresh } =
    useSuccessPathReadiness()

  if (loading && items.every((i) => !i.done)) {
    return (
      <section
        className={`rounded-xl border border-slate-200 bg-white p-6 shadow-sm ${className}`}
        aria-busy="true"
        data-testid="success-path-readiness-loading"
      >
        <div className="flex items-center gap-2 text-sm text-slate-600">
          <IconLoader2 size={18} className="animate-spin" aria-hidden />
          {t('app.onboarding.success_path.loading', { defaultValue: 'Preparing your next step…' })}
        </div>
      </section>
    )
  }

  if (pathComplete && !showWhenComplete) {
    return null
  }

  const nextLabel = nextAction
    ? t(`app.onboarding.success_path.items.${nextAction.id}.cta`, {
        defaultValue: t('app.onboarding.success_path.continue', { defaultValue: 'Continue' }),
      })
    : null

  return (
    <section
      className={`rounded-xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8 ${className}`}
      data-testid="success-path-readiness"
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">
        {t('app.onboarding.success_path.badge', { defaultValue: 'Result' })}
      </p>
      <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">
        {pathComplete
          ? t('app.onboarding.success_path.title_done', {
              defaultValue: 'You can close vacancies from here',
            })
          : t('app.onboarding.success_path.title', {
              defaultValue: 'Close vacancies faster — start here',
            })}
      </h2>
      <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-600">
        {pathComplete
          ? t('app.onboarding.success_path.subtitle_done', {
              defaultValue: 'The basics are done. Keep candidates moving in the pipeline.',
            })
          : t('app.onboarding.success_path.subtitle', {
              defaultValue:
                'One action at a time until applications land and you contact the first candidate.',
            })}
      </p>

      {nextAction ? (
        <div className="mt-6 rounded-2xl border border-brand-200 bg-brand-50/60 p-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-800">
            {t('app.onboarding.success_path.next_title', { defaultValue: 'Do this now' })}
          </p>
          <p className="mt-2 text-base font-semibold text-slate-900">
            {t(`app.onboarding.success_path.items.${nextAction.id}.label`, {
              defaultValue: nextLabel ?? '',
            })}
          </p>
          <p className="mt-1 text-sm text-slate-700">
            {t(`app.onboarding.success_path.items.${nextAction.id}.hint`, {
              defaultValue: '',
            })}
          </p>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <Link
              to={nextAction.href}
              data-testid="success-path-next-cta"
              onClick={() => void refresh()}
              className="inline-flex items-center gap-1.5 rounded-xl bg-brand-600 px-5 py-3 text-sm font-semibold text-white shadow-sm hover:bg-brand-700"
            >
              {nextLabel}
              <IconArrowRight size={16} stroke={1.9} aria-hidden />
            </Link>
            {nextAction.id === 'meta' ? (
              <button
                type="button"
                data-testid="success-path-defer-meta"
                onClick={() => deferMeta()}
                className="rounded-xl px-4 py-3 text-sm font-medium text-slate-600 hover:bg-white hover:text-slate-900"
              >
                {t('app.onboarding.success_path.defer_meta', { defaultValue: 'Skip for now' })}
              </button>
            ) : null}
          </div>
        </div>
      ) : null}

      <div className="mt-6">
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('app.onboarding.success_path.checklist_title', { defaultValue: 'Progress' })}
          </p>
          <p className="text-xs font-medium text-slate-500">
            {t('app.onboarding.success_path.progress', {
              defaultValue: '{done} of {total} done',
              values: { done: doneCount, total: totalCount },
            })}
          </p>
        </div>
        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100">
          <div
            className="h-full rounded-full bg-brand-600 transition-all"
            style={{ width: `${totalCount ? Math.round((doneCount / totalCount) * 100) : 0}%` }}
          />
        </div>
        <ul
          className="mt-3 space-y-1.5"
          aria-label={t('app.onboarding.success_path.list_aria', { defaultValue: 'Getting started checklist' })}
        >
          {items.map((item) => {
            const isNext = nextAction?.id === item.id
            return (
              <li
                key={item.id}
                data-testid={`success-path-item-${item.id}`}
                data-done={item.done ? '1' : '0'}
                className={`flex items-center justify-between gap-3 rounded-lg px-2 py-2 text-sm ${
                  isNext ? 'bg-slate-50' : ''
                }`}
              >
                <span className="inline-flex min-w-0 items-center gap-2">
                  {item.done ? (
                    <IconCheck size={16} stroke={2} className="shrink-0 text-emerald-600" aria-hidden />
                  ) : (
                    <IconCircle size={16} stroke={1.8} className="shrink-0 text-slate-300" aria-hidden />
                  )}
                  <span className={item.done ? 'text-slate-500 line-through decoration-slate-300' : 'text-slate-800'}>
                    {t(`app.onboarding.success_path.items.${item.id}.label`, {
                      defaultValue: item.id,
                    })}
                    {item.optional && !item.done ? (
                      <span className="ml-1 text-xs text-slate-400">
                        ({t('app.onboarding.success_path.optional', { defaultValue: 'optional' })})
                      </span>
                    ) : null}
                    {item.deferred ? (
                      <span className="ml-1 text-xs text-amber-700">
                        ({t('app.onboarding.success_path.deferred', { defaultValue: 'later' })})
                      </span>
                    ) : null}
                  </span>
                </span>
                {!item.done && !isNext ? (
                  <Link
                    to={item.href}
                    className="shrink-0 text-xs font-medium text-brand-700 hover:underline"
                    onClick={() => void refresh()}
                  >
                    {t('app.onboarding.success_path.open', { defaultValue: 'Open' })}
                  </Link>
                ) : null}
              </li>
            )
          })}
        </ul>
      </div>
    </section>
  )
}

export default SuccessPathReadinessPanel

export type SuccessPathI18nId = SuccessPathItemId
