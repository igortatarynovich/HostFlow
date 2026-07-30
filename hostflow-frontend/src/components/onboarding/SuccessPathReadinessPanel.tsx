import { Link } from 'react-router-dom'
import {
  IconArrowRight,
  IconCheck,
  IconCircle,
  IconLoader2,
  IconRocket,
} from '@tabler/icons-react'

import { useI18n } from '../../i18n'
import {
  useSuccessPathReadiness,
  type SuccessPathItemId,
} from '../../hooks/useSuccessPathReadiness'

type SuccessPathReadinessPanelProps = {
  className?: string
  /** When false, only render if path is incomplete (default true = always show while loading/incomplete). */
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
          {t('app.onboarding.success_path.loading', { defaultValue: 'Checking your next steps…' })}
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
      className={`rounded-xl border border-brand-200 bg-brand-50/50 p-6 shadow-sm ${className}`}
      data-testid="success-path-readiness"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="inline-flex items-center gap-1 rounded-lg bg-white px-2 py-1 text-xs font-medium text-brand-700">
            <IconRocket size={14} stroke={1.9} aria-hidden />
            {t('app.onboarding.success_path.badge', { defaultValue: 'Getting started' })}
          </div>
          <h2 className="mt-3 text-lg font-semibold text-slate-900">
            {t('app.onboarding.success_path.title', { defaultValue: 'Your path to first value' })}
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            {t('app.onboarding.success_path.subtitle', {
              defaultValue: 'One clear next step at a time — stay in the product, no multi-step wizard.',
            })}
          </p>
          <p className="mt-2 text-xs font-medium text-brand-800">
            {t('app.onboarding.success_path.progress', {
              defaultValue: '{done} of {total} done',
              values: { done: doneCount, total: totalCount },
            })}
          </p>
        </div>
      </div>

      <ul className="mt-4 space-y-2" aria-label={t('app.onboarding.success_path.list_aria', { defaultValue: 'Success path checklist' })}>
        {items.map((item) => (
          <li
            key={item.id}
            data-testid={`success-path-item-${item.id}`}
            data-done={item.done ? '1' : '0'}
            className={`flex items-center justify-between gap-3 rounded-lg border px-3 py-2 text-sm ${
              item.done
                ? 'border-emerald-100 bg-white/90'
                : nextAction?.id === item.id
                  ? 'border-brand-300 bg-white'
                  : 'border-slate-100 bg-white/70'
            }`}
          >
            <span className="inline-flex min-w-0 items-center gap-2">
              {item.done ? (
                <IconCheck size={16} stroke={2} className="shrink-0 text-emerald-600" aria-hidden />
              ) : (
                <IconCircle size={16} stroke={1.8} className="shrink-0 text-slate-400" aria-hidden />
              )}
              <span className="text-slate-800">
                {t(`app.onboarding.success_path.items.${item.id}.label` as const, {
                  defaultValue: item.id,
                })}
                {item.optional ? (
                  <span className="ml-1 text-xs text-slate-500">
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
            {!item.done ? (
              <Link
                to={item.href}
                className="shrink-0 text-xs font-medium text-brand-700 hover:underline"
                onClick={() => void refresh()}
              >
                {t('app.onboarding.success_path.open', { defaultValue: 'Open' })}
              </Link>
            ) : null}
          </li>
        ))}
      </ul>

      {nextAction ? (
        <div className="mt-4 rounded-xl border border-brand-200 bg-white p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-800">
            {t('app.onboarding.success_path.next_title', { defaultValue: 'Next step' })}
          </p>
          <p className="mt-1 text-sm text-slate-800">
            {t(`app.onboarding.success_path.items.${nextAction.id}.hint`, {
              defaultValue: nextLabel ?? '',
            })}
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Link
              to={nextAction.href}
              data-testid="success-path-next-cta"
              onClick={() => void refresh()}
              className="inline-flex items-center gap-1 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
            >
              {nextLabel}
              <IconArrowRight size={14} stroke={1.9} aria-hidden />
            </Link>
            {nextAction.id === 'meta' ? (
              <button
                type="button"
                data-testid="success-path-defer-meta"
                onClick={() => deferMeta()}
                className="rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 hover:text-slate-900"
              >
                {t('app.onboarding.success_path.defer_meta', { defaultValue: 'Do this later' })}
              </button>
            ) : null}
          </div>
        </div>
      ) : (
        <p className="mt-4 text-sm font-medium text-emerald-800">
          {t('app.onboarding.success_path.complete', {
            defaultValue: 'Core path complete — keep working from Launchpad or Recruitment.',
          })}
        </p>
      )}
    </section>
  )
}

export default SuccessPathReadinessPanel

/** i18n key helper for exhaustiveness in editors */
export type SuccessPathI18nId = SuccessPathItemId
