import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import {
  IconArrowRight,
  IconBuildingSkyscraper,
  IconCheck,
  IconCircleCheck,
  IconClipboardList,
  IconLink,
  IconSearch,
  IconTruck,
  IconUser,
} from '@tabler/icons-react'
import { useI18n } from '../i18n'
import { useAuth } from '../store/useAuth'
import { getOnboardingStatus } from '../api/client'
import { getBillingSubscriptionCached } from '../api/billingSubscriptionCache'
import type { BillingSubscription } from '../api/billing'
import { useSetupReadiness } from '../hooks/useSetupReadiness'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { getBusinessHomePath } from '../app/activationRoutes'
import { readLastLaunchSearchId } from '../services/launchSearchSession'
import type { ActivationBusinessType } from '../app/activationRoutes'

function trialDaysRemaining(trialEndsAt: string | null | undefined): number | null {
  if (!trialEndsAt) return null
  const end = new Date(trialEndsAt)
  if (Number.isNaN(end.getTime())) return null
  const diffMs = end.getTime() - Date.now()
  return Math.max(0, Math.ceil(diffMs / (1000 * 60 * 60 * 24)))
}

function FindStaffIllustration() {
  return (
    <div
      className="relative mx-auto flex h-36 w-full max-w-[220px] items-center justify-center rounded-xl bg-gradient-to-br from-brand-50 to-slate-50 sm:h-40"
      aria-hidden
    >
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-100 text-brand-700">
            <IconUser size={20} stroke={1.8} />
          </div>
          <div className="space-y-1.5">
            <div className="h-2 w-16 rounded bg-slate-200" />
            <div className="h-2 w-12 rounded bg-slate-100" />
          </div>
        </div>
      </div>
      <div className="absolute -bottom-2 -right-2 flex h-10 w-10 items-center justify-center rounded-full border-2 border-white bg-emerald-500 text-white shadow-md">
        <IconLink size={18} stroke={2} />
      </div>
    </div>
  )
}

function CompanyInquiriesIllustration() {
  return (
    <div
      className="relative mx-auto flex h-28 w-full max-w-[180px] items-center justify-center rounded-xl bg-gradient-to-br from-slate-50 to-slate-100 sm:h-32"
      aria-hidden
    >
      <div className="flex h-16 w-16 items-center justify-center rounded-xl border border-slate-200 bg-white text-brand-700 shadow-sm">
        <IconBuildingSkyscraper size={30} stroke={1.5} />
      </div>
    </div>
  )
}

type ModuleCardProps = {
  icon: ReactNode
  title: string
  status: 'ready' | 'configure' | 'locked'
  statusLabel: string
  description: string
  actionLabel: string
  actionTo: string
  testId: string
  actionTestId: string
}

function ModuleCard({
  icon,
  title,
  status,
  statusLabel,
  description,
  actionLabel,
  actionTo,
  testId,
  actionTestId,
}: ModuleCardProps) {
  const locked = status === 'locked'
  const ready = status === 'ready'

  return (
    <article
      data-testid={testId}
      data-module-status={status}
      className={`flex h-full flex-col rounded-xl border p-4 shadow-sm transition ${
        locked
          ? 'border-slate-200 bg-slate-50/80 opacity-80'
          : 'border-slate-200 bg-white hover:border-slate-300'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div
          className={`flex h-10 w-10 items-center justify-center rounded-xl ${
            ready ? 'bg-brand-50 text-brand-700' : 'bg-slate-100 text-slate-500'
          }`}
        >
          {icon}
        </div>
        <span
          className={`rounded-full px-3 py-0.5 text-xs font-medium ${
            ready
              ? 'bg-emerald-50 text-emerald-700'
              : locked
                ? 'bg-slate-100 text-slate-500'
                : 'bg-amber-50 text-amber-800'
          }`}
        >
          {statusLabel}
        </span>
      </div>
      <h3 className="mt-4 font-semibold text-slate-900">{title}</h3>
      <p className="mt-1 flex-1 text-sm text-slate-600">{description}</p>
      <Link
        to={actionTo}
        data-testid={actionTestId}
        className={`mt-4 inline-flex w-full items-center justify-center gap-1 rounded-lg px-4 py-2 text-sm font-medium sm:w-auto ${
          locked
            ? 'pointer-events-none bg-slate-100 text-slate-400'
            : ready
              ? 'bg-brand-600 text-white hover:bg-brand-700'
              : 'border border-brand-200 bg-brand-50 text-brand-800 hover:bg-brand-100'
        }`}
      >
        {actionLabel}
        {!locked ? <IconArrowRight size={14} stroke={1.9} aria-hidden /> : null}
      </Link>
    </article>
  )
}

export default function LaunchpadPage() {
  const { t } = useI18n()
  const { me } = useAuth()
  const { snapshot, loading: readinessLoading } = useSetupReadiness()
  const [onboardingStatus, setOnboardingStatus] = useState<Awaited<ReturnType<typeof getOnboardingStatus>> | null>(
    null,
  )
  const [billing, setBilling] = useState<BillingSubscription | null>(null)

  const displayName = useMemo(() => {
    const name = String(me?.full_name || me?.email || '').trim()
    if (!name) return ''
    return name.split(/\s+/)[0] || name
  }, [me?.email, me?.full_name])

  useEffect(() => {
    void getOnboardingStatus().then(setOnboardingStatus).catch(() => setOnboardingStatus(null))
    void getBillingSubscriptionCached().then(setBilling).catch(() => setBilling(null))
  }, [])

  const recruitmentReady = Boolean(snapshot?.ready)
  const recruitmentWorkspaceAvailable =
    recruitmentReady || Boolean(onboardingStatus && onboardingStatus.activation_required === false)
  const platformConfigured = Boolean(onboardingStatus && !onboardingStatus.onboarding_required)
  const businessType = (onboardingStatus?.business_type ?? 'agency') as ActivationBusinessType
  const hasActiveSearch = Boolean(onboardingStatus?.steps?.first_vacancy_created)

  const lastSearchId = readLastLaunchSearchId()
  const recruitmentOpenPath =
    lastSearchId && hasActiveSearch
      ? `${CRM_APP_PATHS.vacancies}/${encodeURIComponent(lastSearchId)}`
      : hasActiveSearch
        ? CRM_APP_PATHS.vacancies
        : getBusinessHomePath(businessType)
  const recruitmentModulePath =
    recruitmentWorkspaceAvailable && hasActiveSearch
      ? recruitmentOpenPath
      : CRM_APP_PATHS.marketingNew
  const recruitmentModuleActionLabel =
    recruitmentWorkspaceAvailable && hasActiveSearch
      ? t('app.launchpad.open_vacancy', { defaultValue: 'Открыть вакансию' })
      : t('app.launchpad.create_campaign', { defaultValue: 'Создать кампанию' })

  const setupPassed = snapshot?.gates.filter((gate) => gate.applicable && gate.status === 'pass').length ?? 0
  const setupTotal = snapshot?.gates.filter((gate) => gate.applicable).length ?? 0
  const setupProgress = setupTotal > 0 ? Math.round((setupPassed / setupTotal) * 100) : 0
  const trialDays = trialDaysRemaining(billing?.trial_ends_at)
  const showTrial = Boolean(billing?.gate?.trial_active || billing?.status === 'trialing' || trialDays !== null)
  const setupContinuePath = snapshot?.next_action?.handler_ref?.startsWith('/')
    ? snapshot.next_action.handler_ref
    : CRM_APP_PATHS.setup

  return (
    <div className="mx-auto max-w-6xl space-y-8 px-1 sm:px-0" data-testid="m1-launchpad">
      <header>
        <h1 className="text-2xl font-semibold text-slate-900 sm:text-3xl">
          {displayName
            ? t('app.launchpad.welcome_named', {
                defaultValue: 'Добро пожаловать, {name}',
                values: { name: displayName },
              })
            : t('app.launchpad.welcome', { defaultValue: 'Добро пожаловать' })}
        </h1>
        <p className="mt-2 text-sm text-slate-600 sm:text-base">
          {t('app.launchpad.subtitle_today', {
            defaultValue: 'Что вы хотите сделать сегодня?',
          })}
        </p>
      </header>

      <section
        className="flex flex-col gap-4 lg:flex-row lg:items-stretch lg:gap-4"
        data-testid="m1-launchpad-tasks"
      >
        <article
          className="flex flex-1 flex-col rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6 lg:flex-[1.35]"
          data-testid="m1-launchpad-task-find-staff"
        >
          <div className="flex flex-1 flex-col gap-4 md:flex-row md:items-center">
            <div className="shrink-0 md:w-[220px]">
              <FindStaffIllustration />
            </div>
            <div className="min-w-0 flex-1">
              <h2 className="text-xl font-semibold text-slate-900 sm:text-2xl">
                {t('app.launchpad.task_find_staff_title', { defaultValue: 'Найти сотрудников' })}
              </h2>
              <p className="mt-2 text-sm text-slate-600 sm:text-base">
                {t('app.launchpad.task_find_staff_body', {
                  defaultValue: 'Создайте подбор и получите ссылку для кандидатов.',
                })}
              </p>
              <ul className="mt-4 space-y-2 text-sm text-slate-700">
                {[
                  t('app.launchpad.task_find_staff_role_driver', { defaultValue: 'Ищете водителей' }),
                  t('app.launchpad.task_find_staff_role_warehouse', { defaultValue: 'Ищете работников склада' }),
                  t('app.launchpad.task_find_staff_role_office', { defaultValue: 'Ищете офисных сотрудников' }),
                ].map((item) => (
                  <li key={item} className="flex items-center gap-2">
                    <IconCircleCheck size={18} className="shrink-0 text-emerald-600" aria-hidden />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
          <Link
            to={
              lastSearchId && hasActiveSearch
                ? `${CRM_APP_PATHS.vacancies}/${encodeURIComponent(lastSearchId)}`
                : CRM_APP_PATHS.marketingNew
            }
            data-testid="m1-launchpad-create-search"
            className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-brand-600 px-6 py-3 text-sm font-semibold text-white hover:bg-brand-700 sm:mt-6 sm:w-auto sm:self-start sm:text-base"
          >
            {lastSearchId && hasActiveSearch
              ? t('app.launchpad.open_vacancy', { defaultValue: 'Открыть вакансию' })
              : t('app.launchpad.create_campaign', { defaultValue: 'Создать кампанию' })}
            <IconArrowRight size={16} stroke={2} aria-hidden />
          </Link>
        </article>

        <article
          className="flex flex-1 flex-col rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6 lg:max-w-sm lg:flex-1"
          data-testid="m1-launchpad-task-company-inquiries"
        >
          <CompanyInquiriesIllustration />
          <h3 className="mt-4 text-lg font-semibold text-slate-900">
            {t('app.launchpad.task_find_clients_title', {
              defaultValue: 'Найти новых клиентов',
            })}
          </h3>
          <p className="mt-2 flex-1 text-sm text-slate-600">
            {t('app.launchpad.task_find_clients_body', {
              defaultValue: 'Компании сами оставляют заявки на подбор персонала — вы получаете готовую ссылку и QR.',
            })}
          </p>
          <div className="mt-4 space-y-3">
            <Link
              to={CRM_APP_PATHS.clientAcquisitionChannelsNew}
              data-testid="m1-launchpad-create-client-channel"
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-brand-300 bg-white px-4 py-3 text-sm font-semibold text-brand-800 hover:bg-brand-50 sm:w-auto"
            >
              {t('app.launchpad.create_client_channel', {
                defaultValue: 'Начать привлечение клиентов',
              })}
              <IconArrowRight size={14} stroke={1.9} aria-hidden />
            </Link>
          </div>
        </article>
      </section>

      <section>
        <h2 className="mb-4 text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t('app.launchpad.modules_title', { defaultValue: 'Ваши модули' })}
        </h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <ModuleCard
            icon={<IconSearch size={20} stroke={1.8} />}
            title={t('app.launchpad.module_recruitment', { defaultValue: 'Recruitment' })}
            status={
              readinessLoading ? 'configure' : recruitmentReady && hasActiveSearch ? 'ready' : 'configure'
            }
            statusLabel={
              readinessLoading
                ? t('common.loading')
                : recruitmentReady && hasActiveSearch
                  ? t('app.launchpad.recruitment_ready', { defaultValue: 'Готов' })
                  : recruitmentWorkspaceAvailable && !hasActiveSearch
                    ? t('app.launchpad.recruitment_create_first', {
                        defaultValue: 'Создайте первый подбор',
                      })
                    : recruitmentWorkspaceAvailable
                      ? t('app.launchpad.recruitment_open', { defaultValue: 'Доступен' })
                      : t('app.launchpad.recruitment_configure', { defaultValue: 'Не настроен' })
            }
            description={t('app.launchpad.module_recruitment_desc', {
              defaultValue: 'Подбор сотрудников и управление кандидатами',
            })}
            actionLabel={recruitmentModuleActionLabel}
            actionTo={recruitmentModulePath}
            testId="m1-launchpad-module-recruitment"
            actionTestId="m1-launchpad-open-recruitment"
          />

          <ModuleCard
            icon={<IconUser size={20} stroke={1.8} />}
            title="HR"
            status="locked"
            statusLabel={t('app.launchpad.coming_soon', { defaultValue: 'Скоро' })}
            description={t('app.launchpad.module_hr_desc', {
              defaultValue: 'Управление сотрудниками и процессами',
            })}
            actionLabel={t('app.launchpad.coming_soon', { defaultValue: 'Скоро' })}
            actionTo="#"
            testId="m1-launchpad-module-hr"
            actionTestId="m1-launchpad-module-hr-action"
          />

          <ModuleCard
            icon={<IconTruck size={20} stroke={1.8} />}
            title="Fleet"
            status="locked"
            statusLabel={t('app.launchpad.coming_soon', { defaultValue: 'Скоро' })}
            description={t('app.launchpad.module_fleet_desc', {
              defaultValue: 'Транспорт и назначения',
            })}
            actionLabel={t('app.launchpad.coming_soon', { defaultValue: 'Скоро' })}
            actionTo="#"
            testId="m1-launchpad-module-fleet"
            actionTestId="m1-launchpad-module-fleet-action"
          />

          <ModuleCard
            icon={<IconClipboardList size={20} stroke={1.8} />}
            title="Orders"
            status="locked"
            statusLabel={t('app.launchpad.coming_soon', { defaultValue: 'Скоро' })}
            description={t('app.launchpad.module_orders_desc', {
              defaultValue: 'Заказы и документы',
            })}
            actionLabel={t('app.launchpad.coming_soon', { defaultValue: 'Скоро' })}
            actionTo="#"
            testId="m1-launchpad-module-orders"
            actionTestId="m1-launchpad-module-orders-action"
          />
        </div>
      </section>

      <section
        className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-4"
        data-testid="m1-launchpad-status-footer"
      >
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="grid flex-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 lg:gap-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('app.launchpad.platform_title', { defaultValue: 'Платформа' })}
              </p>
              <ul className="mt-2 space-y-1.5 text-sm text-slate-800">
                <li className="flex items-center gap-2">
                  <IconCheck size={16} className="text-emerald-600" aria-hidden />
                  {t('app.launchpad.platform_account_active', { defaultValue: 'Аккаунт активен' })}
                </li>
                <li className="flex items-center gap-2">
                  {platformConfigured ? (
                    <IconCheck size={16} className="text-emerald-600" aria-hidden />
                  ) : (
                    <span className="inline-block h-4 w-4 rounded-full border-2 border-amber-400" aria-hidden />
                  )}
                  {t('app.launchpad.platform_business_account', { defaultValue: 'Бизнес-аккаунт' })}
                </li>
              </ul>
            </div>

            {showTrial ? (
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {t('app.launchpad.current_plan', { defaultValue: 'Текущий план' })}
                </p>
                <p className="mt-2 text-sm font-semibold text-slate-900">
                  {t('app.launchpad.trial_plan', { defaultValue: 'Trial' })}
                </p>
                {trialDays !== null ? (
                  <p className="text-sm text-slate-600">
                    {t('app.launchpad.trial_days_left', {
                      defaultValue: '{days} дней',
                      values: { days: trialDays },
                    })}
                  </p>
                ) : null}
              </div>
            ) : null}

            <div className="sm:col-span-2 lg:col-span-1">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('app.launchpad.company_setup', { defaultValue: 'Настройка компании' })}
              </p>
              <p className="mt-2 text-sm text-slate-700">
                {readinessLoading
                  ? t('common.loading')
                  : t('app.launchpad.setup_steps_progress', {
                      defaultValue: '{passed}/{total} шагов пройдено',
                      values: { passed: setupPassed, total: setupTotal || 8 },
                    })}
              </p>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full rounded-full bg-brand-600 transition-all"
                  style={{ width: `${setupProgress}%` }}
                  role="progressbar"
                  aria-valuenow={setupPassed}
                  aria-valuemin={0}
                  aria-valuemax={setupTotal || 8}
                />
              </div>
            </div>
          </div>

          <Link
            to={setupContinuePath}
            data-testid="m1-launchpad-continue-setup"
            className="inline-flex w-full shrink-0 items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-semibold text-slate-800 hover:bg-slate-50 lg:w-auto"
          >
            {t('app.launchpad.continue_setup', { defaultValue: 'Продолжить настройку' })}
          </Link>
        </div>
      </section>
    </div>
  )
}
