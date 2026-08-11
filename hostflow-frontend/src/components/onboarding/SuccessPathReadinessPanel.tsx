import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  IconArrowRight,
  IconCheck,
  IconCircle,
  IconLoader2,
} from '@tabler/icons-react'

import {
  clearOnboardingDemoData,
  seedOnboardingDemo,
} from '../../api/client'
import { ACTIVATION_PATHS } from '../../app/activationRoutes'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
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

const FAQ_LAUNCH = '/faq#launch_troubleshooting'
const DOCS_START = '/docs/getting-started'

export function SuccessPathReadinessPanel({
  className = '',
  showWhenComplete = false,
}: SuccessPathReadinessPanelProps) {
  const { t } = useI18n()
  const {
    items,
    nextAction,
    doneCount,
    totalCount,
    pathComplete,
    loading,
    deferMeta,
    refresh,
    status,
    businessType,
  } = useSuccessPathReadiness()
  const [demoBusy, setDemoBusy] = useState(false)
  const [demoError, setDemoError] = useState<string | null>(null)

  const companyDone = Boolean(items.find((i) => i.id === 'company')?.done)
  const demoSeeded = Boolean(status?.demo_seeded)
  const showDemoActions = companyDone && !pathComplete
  const needsLeadEscape = nextAction?.id === 'lead' || nextAction?.id === 'meta'

  const handleSeedDemo = async () => {
    setDemoBusy(true)
    setDemoError(null)
    try {
      await seedOnboardingDemo()
      await refresh()
    } catch {
      setDemoError(
        t('app.onboarding.success_path.demo_seed_error', {
          defaultValue: 'Не удалось загрузить учебные данные. Нужны права администратора.',
        }),
      )
    } finally {
      setDemoBusy(false)
    }
  }

  const handleClearDemo = async () => {
    setDemoBusy(true)
    setDemoError(null)
    try {
      await clearOnboardingDemoData()
      await refresh()
    } catch {
      setDemoError(
        t('app.onboarding.success_path.demo_clear_error', {
          defaultValue: 'Не удалось удалить учебные данные. Нужны права администратора.',
        }),
      )
    } finally {
      setDemoBusy(false)
    }
  }

  if (loading && items.every((i) => !i.done)) {
    return (
      <section
        className={`rounded-xl border border-slate-200 bg-white p-6 shadow-sm ${className}`}
        aria-busy="true"
        data-testid="success-path-readiness-loading"
      >
        <div className="flex items-center gap-2 text-sm text-slate-600">
          <IconLoader2 size={18} className="animate-spin" aria-hidden />
          {t('app.onboarding.success_path.loading', { defaultValue: 'Готовим следующий шаг…' })}
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

  const titleKey = pathComplete
    ? `app.onboarding.success_path.title_done_${businessType}`
    : `app.onboarding.success_path.title_${businessType}`
  const subtitleKey = pathComplete
    ? `app.onboarding.success_path.subtitle_done_${businessType}`
    : `app.onboarding.success_path.subtitle_${businessType}`

  return (
    <section
      className={`rounded-xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8 ${className}`}
      data-testid="success-path-readiness"
      data-business-type={businessType}
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">
        {t('app.onboarding.success_path.badge', { defaultValue: 'С чего начать' })}
      </p>
      <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">
        {pathComplete
          ? t(titleKey, {
              defaultValue: t('app.onboarding.success_path.title_done', {
                defaultValue: 'Можно работать в системе',
              }),
            })
          : t(titleKey, {
              defaultValue: t('app.onboarding.success_path.title', {
                defaultValue: 'Первые шаги в HostFlow',
              }),
            })}
      </h2>
      <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-600">
        {pathComplete
          ? t(subtitleKey, {
              defaultValue: t('app.onboarding.success_path.subtitle_done', {
                defaultValue: 'База готова. Ведите людей по этапам дальше.',
              }),
            })
          : t(subtitleKey, {
              defaultValue: t('app.onboarding.success_path.subtitle', {
                defaultValue:
                  'Закройте шаги по одному: так появятся вакансия, заявка и контакт с человеком.',
              }),
            })}
      </p>

      {nextAction ? (
        <div className="mt-6 rounded-2xl border border-brand-200 bg-brand-50/60 p-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-800">
            {t('app.onboarding.success_path.next_title', { defaultValue: 'Сделайте сейчас' })}
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
                {t('app.onboarding.success_path.defer_meta', { defaultValue: 'Пока пропустить' })}
              </button>
            ) : null}
            {needsLeadEscape && !demoSeeded ? (
              <button
                type="button"
                data-testid="success-path-next-demo-seed"
                disabled={demoBusy}
                onClick={() => void handleSeedDemo()}
                className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-medium text-slate-800 hover:bg-slate-50 disabled:opacity-60"
              >
                {demoBusy
                  ? t('common.saving', { defaultValue: 'Working…' })
                  : t('app.onboarding.success_path.demo_seed', {
                      defaultValue: 'Загрузить учебные данные',
                    })}
              </button>
            ) : null}
            {needsLeadEscape && demoSeeded ? (
              <Link
                to={ACTIVATION_PATHS.leads}
                data-testid="success-path-next-open-leads"
                className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-medium text-slate-800 hover:bg-slate-50"
              >
                {t('app.onboarding.success_path.demo_open_leads', { defaultValue: 'Открыть заявки' })}
              </Link>
            ) : null}
            <Link
              to={FAQ_LAUNCH}
              className="rounded-xl px-4 py-3 text-sm font-medium text-brand-700 hover:underline"
            >
              {t('app.onboarding.success_path.open_faq', { defaultValue: 'Застряли? Открыть FAQ' })}
            </Link>
            <Link
              to={DOCS_START}
              className="rounded-xl px-4 py-3 text-sm font-medium text-brand-700 hover:underline"
            >
              {t('app.onboarding.success_path.open_docs', { defaultValue: 'Гайд «С чего начать»' })}
            </Link>
          </div>
          {demoError ? <p className="mt-2 text-xs text-rose-700">{demoError}</p> : null}
          {nextAction.id === 'lead' ? (
            <p className="mt-3 text-xs text-slate-600">
              {t('app.onboarding.success_path.lead_escape_hint', {
                defaultValue:
                  'Нет входящих? Загрузите учебные данные, выберите способ получения заявок или подключите источник позже.',
              })}
            </p>
          ) : null}
        </div>
      ) : !pathComplete ? (
        <div
          className="mt-6 rounded-2xl border border-amber-200 bg-amber-50/70 p-5"
          data-testid="success-path-recovery"
        >
          <p className="text-sm font-semibold text-slate-900">
            {t('app.onboarding.success_path.recovery_title', {
              defaultValue: 'Нужен выход?',
            })}
          </p>
          <p className="mt-1 text-sm text-slate-700">
            {t('app.onboarding.success_path.recovery_body', {
              defaultValue:
                'Откройте «Начать работу», загрузите учебные данные или FAQ по запуску. Следующий шаг всегда есть.',
            })}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Link to={CRM_APP_PATHS.setup} className="btn-primary btn-sm">
              {t('app.onboarding.success_path.recovery_setup', { defaultValue: 'Открыть чек-лист старта' })}
            </Link>
            <Link to={FAQ_LAUNCH} className="btn-secondary btn-sm">
              {t('app.onboarding.success_path.open_faq', { defaultValue: 'Застряли? Открыть FAQ' })}
            </Link>
            {!demoSeeded ? (
              <button
                type="button"
                className="btn-secondary btn-sm"
                disabled={demoBusy}
                onClick={() => void handleSeedDemo()}
              >
                {t('app.onboarding.success_path.demo_seed', { defaultValue: 'Загрузить учебные данные' })}
              </button>
            ) : null}
          </div>
        </div>
      ) : null}

      {showDemoActions ? (
        <div
          className="mt-4 rounded-xl border border-slate-200 bg-slate-50/80 px-4 py-3"
          data-testid="success-path-demo-pack"
        >
          <p className="text-sm font-semibold text-slate-900">
            {t('app.onboarding.success_path.demo_title', {
              defaultValue: 'Посмотреть на примерах',
            })}
          </p>
          <p className="mt-1 text-sm text-slate-600">
            {demoSeeded
              ? t('app.onboarding.success_path.demo_active_hint', {
                  defaultValue:
                    'Учебные данные загружены. Откройте заявки или удалите их перед реальной работой.',
                })
              : t('app.onboarding.success_path.demo_hint', {
                  defaultValue:
                    'Загрузите учебные заявки и кандидатов, чтобы понять экраны. Перед реальной работой удалите одним нажатием.',
                })}
          </p>
          {demoError ? <p className="mt-2 text-xs text-rose-700">{demoError}</p> : null}
          <div className="mt-3 flex flex-wrap gap-2">
            {demoSeeded ? (
              <>
                <Link
                  to={ACTIVATION_PATHS.leads}
                  className="btn-secondary btn-sm"
                  data-testid="success-path-demo-open-leads"
                >
                  {t('app.onboarding.success_path.demo_open_leads', { defaultValue: 'Открыть заявки' })}
                </Link>
                <button
                  type="button"
                  className="btn-secondary btn-sm"
                  data-testid="success-path-demo-clear"
                  disabled={demoBusy}
                  onClick={() => void handleClearDemo()}
                >
                  {demoBusy
                    ? t('common.saving', { defaultValue: 'Working…' })
                    : t('app.onboarding.success_path.demo_clear', {
                        defaultValue: 'Удалить учебные данные',
                      })}
                </button>
              </>
            ) : (
              <button
                type="button"
                className="btn-secondary btn-sm"
                data-testid="success-path-demo-seed"
                disabled={demoBusy}
                onClick={() => void handleSeedDemo()}
              >
                {demoBusy
                  ? t('common.saving', { defaultValue: 'Working…' })
                  : t('app.onboarding.success_path.demo_seed', {
                      defaultValue: 'Загрузить учебные данные',
                    })}
              </button>
            )}
            <Link to={FAQ_LAUNCH} className="btn-secondary btn-sm">
              {t('app.onboarding.success_path.open_faq_short', { defaultValue: 'FAQ' })}
            </Link>
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
                {!item.done ? (
                  <Link
                    to={item.href}
                    className="shrink-0 text-xs font-medium text-brand-700 hover:underline"
                    onClick={() => void refresh()}
                    data-testid={isNext ? `success-path-item-${item.id}-open-next` : undefined}
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
