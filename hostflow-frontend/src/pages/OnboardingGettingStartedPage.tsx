import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  IconArrowRight,
  IconBrandTelegram,
  IconBrandWhatsapp,
  IconCheck,
  IconChecklist,
  IconClock,
  IconGitBranch,
  IconMail,
  IconPhoto,
  IconUserPlus,
  IconUsers,
} from '@tabler/icons-react'
import { useI18n } from '../i18n'
import { getOnboardingStatus, type OnboardingStatus } from '../api/client'
import { usePermissions, type Permission } from '../hooks/usePermissions'
import { useBusinessTerminology } from '../hooks/useBusinessTerminology'
import { ACTIVATION_PATHS, getBusinessHomePath, getBusinessNextActionPath } from '../app/activationRoutes'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { resolveBrandingSetupHref } from '../nav/workspaceQuickSetupNav'
import { PageBreadcrumb } from '../components/nav/PageBreadcrumb'
type OnboardingStepCard = {
  key: string
  done: boolean
  title: string
  desc: string
  href: string
  permission?: Permission
  openLabel?: string
}

export default function OnboardingGettingStartedPage() {
  const { t } = useI18n()
  const { entitySingular, openEntityLabel } = useBusinessTerminology()
  const navigate = useNavigate()
  const { can } = usePermissions()
  const [status, setStatus] = useState<OnboardingStatus | null>(null)
  const businessType = status?.business_type ?? 'agency'

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const data = await getOnboardingStatus()
        if (!cancelled) setStatus(data)
      } catch {
        if (!cancelled) setStatus(null)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const steps = useMemo(
    () => {
      const companyHref = getBusinessHomePath(businessType)
      const typeStep: OnboardingStepCard =
        businessType === 'employer'
          ? {
              key: 'vacancy',
              done: Boolean(status?.steps?.first_vacancy_created),
              title: t('app.onboarding.getting_started.step_employer.title'),
              desc: t('app.onboarding.getting_started.step_employer.desc'),
              href: ACTIVATION_PATHS.vacancies,
              permission: 'vacancies.view',
            }
          : businessType === 'services'
            ? {
                key: 'first_client_services',
                done: Boolean(status?.steps?.first_client_created || status?.steps?.first_lead_created),
                title: t('app.onboarding.getting_started.step_services_client.title'),
                desc: t('app.onboarding.getting_started.step_services_client.desc'),
                href: ACTIVATION_PATHS.clients,
                permission: 'companies.view',
              }
            : {
                key: 'first_client',
                done: Boolean(status?.steps?.first_client_created),
                title: t('app.onboarding.getting_started.step_agency.title_dynamic', {
                  values: { entity: entitySingular.toLowerCase() },
                }),
                desc: t('app.onboarding.getting_started.step_agency.desc_dynamic', {
                  values: { entity: entitySingular.toLowerCase() },
                }),
                href: ACTIVATION_PATHS.clients,
                permission: 'companies.view',
              }
      const nextSteps: OnboardingStepCard[] = [
        {
          key: 'company',
          done: Boolean(status?.steps?.company_created),
          title: t('app.onboarding.getting_started.step0.title'),
          desc: t('app.onboarding.getting_started.step0.desc'),
          href: companyHref,
          permission: businessType === 'employer' ? 'vacancies.view' : 'companies.view',
        },
        typeStep,
        {
          key: 'action',
          done: Boolean(status?.steps?.next_action_created),
          title: t('app.onboarding.getting_started.step3.title'),
          desc:
            businessType === 'services'
              ? t('app.onboarding.getting_started.step3_services.desc')
              : t('app.onboarding.getting_started.step3.desc'),
          href: businessType === 'services' ? ACTIVATION_PATHS.leads : getBusinessNextActionPath(businessType),
          permission:
            businessType === 'services'
              ? 'leads.view'
              : businessType === 'employer'
                ? 'vacancies.view'
                : 'companies.view',
        },
      ]
      return nextSteps.map((step) => {
        const accessible = !step.permission || can(step.permission)
        return {
          ...step,
          href: accessible ? step.href : ACTIVATION_PATHS.overview,
          openLabel: accessible
            ? step.href === ACTIVATION_PATHS.clients
              ? openEntityLabel
              : t('app.onboarding.getting_started.open')
            : t('app.onboarding.getting_started.open_fallback'),
        }
      })
    },
    [status, businessType, t, can, entitySingular, openEntityLabel],
  )

  const brandingSetupHref = useMemo(() => resolveBrandingSetupHref(can), [can])

  const primaryLaunchAction = useMemo(() => {
    if (businessType === 'employer') {
      return {
        href: ACTIVATION_PATHS.vacancies,
        title: t('app.onboarding.getting_started.primary_cta_employer.title'),
        desc: t('app.onboarding.getting_started.primary_cta_employer.desc'),
      }
    }
    if (businessType === 'services') {
      return {
        href: ACTIVATION_PATHS.leads,
        title: t('app.onboarding.getting_started.primary_cta_services.title'),
        desc: t('app.onboarding.getting_started.primary_cta_services.desc'),
      }
    }
    return {
      href: ACTIVATION_PATHS.clients,
      title: t('app.onboarding.getting_started.primary_cta_agency.title'),
      desc: t('app.onboarding.getting_started.primary_cta_agency.desc'),
    }
  }, [businessType, t])

  const doneCount = steps.filter((step) => step.done).length
  const totalCount = steps.length
  const completed = doneCount >= totalCount
  const stepVisuals = [
    {
      pendingIcon: IconUsers,
      bgClass: 'bg-blue-50 text-blue-700',
    },
    {
      pendingIcon: IconUserPlus,
      bgClass: 'bg-emerald-50 text-emerald-700',
    },
    {
      pendingIcon: IconChecklist,
      bgClass: 'bg-amber-50 text-amber-700',
    },
  ] as const

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <section className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="inline-flex items-center gap-1 rounded-md bg-brand-50 px-2 py-1 text-xs font-medium text-brand-700">
          <IconChecklist size={14} stroke={1.9} />
          {t('app.onboarding.getting_started.badge')}
        </div>
        <h1 className="mt-3 text-2xl font-semibold text-slate-900">
          {t('app.onboarding.getting_started.title')}
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          {t('app.onboarding.getting_started.subtitle')}
        </p>
        <p className="mt-2 text-xs font-medium text-brand-700">
          {t('app.onboarding.getting_started.progress', {
            values: { done: doneCount, total: totalCount },
          })}
        </p>
        <div className="mt-4 rounded-xl border border-brand-200 bg-brand-50/70 p-4">
          <div className="text-sm font-semibold text-slate-900">{primaryLaunchAction.title}</div>
          <div className="mt-1 text-xs text-slate-600">{primaryLaunchAction.desc}</div>
          <div className="mt-3">
            <button
              type="button"
              className="btn-primary"
              onClick={() => navigate(primaryLaunchAction.href)}
            >
              {t('app.onboarding.getting_started.primary_cta_launch')}
            </button>
          </div>
        </div>
      </section>

      <PageBreadcrumb className="max-w-3xl" />

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900">
          {t('app.onboarding.getting_started.quick_setup_title')}
        </h2>
        <p className="mt-1 text-xs text-slate-600">
          {t('app.onboarding.getting_started.quick_setup_subtitle')}
        </p>
        <ul className="mt-4 space-y-2 text-sm">
          <li>
            <Link
              to={brandingSetupHref}
              className="flex items-start gap-2 rounded-lg border border-transparent px-2 py-1.5 hover:border-slate-200 hover:bg-slate-50"
            >
              <IconPhoto size={18} stroke={1.8} className="mt-0.5 shrink-0 text-slate-500" />
              <span>
                <span className="font-medium text-slate-800">
                  {t('app.onboarding.getting_started.checklist.logo')}
                </span>
                <span className="mt-0.5 block text-xs text-slate-500">
                  {t('app.onboarding.getting_started.checklist.logo_desc')}
                </span>
              </span>
            </Link>
          </li>
          <li>
            <Link
              to={CRM_APP_PATHS.myAvailability}
              className="flex items-start gap-2 rounded-lg border border-transparent px-2 py-1.5 hover:border-slate-200 hover:bg-slate-50"
            >
              <IconClock size={18} stroke={1.8} className="mt-0.5 shrink-0 text-slate-500" />
              <span>
                <span className="font-medium text-slate-800">
                  {t('app.onboarding.getting_started.checklist.hours')}
                </span>
                <span className="mt-0.5 block text-xs text-slate-500">
                  {t('app.onboarding.getting_started.checklist.hours_desc')}
                </span>
              </span>
            </Link>
          </li>
          <li>
            <Link
              to={CRM_APP_PATHS.settingsUsers}
              className="flex items-start gap-2 rounded-lg border border-transparent px-2 py-1.5 hover:border-slate-200 hover:bg-slate-50"
            >
              <IconUsers size={18} stroke={1.8} className="mt-0.5 shrink-0 text-slate-500" />
              <span>
                <span className="font-medium text-slate-800">
                  {t('app.onboarding.getting_started.checklist.team')}
                </span>
                <span className="mt-0.5 block text-xs text-slate-500">
                  {t('app.onboarding.getting_started.checklist.team_desc')}
                </span>
              </span>
            </Link>
          </li>
          <li>
            <Link
              to={CRM_APP_PATHS.settingsFunnels}
              className="flex items-start gap-2 rounded-lg border border-transparent px-2 py-1.5 hover:border-slate-200 hover:bg-slate-50"
            >
              <IconGitBranch size={18} stroke={1.8} className="mt-0.5 shrink-0 text-slate-500" />
              <span>
                <span className="font-medium text-slate-800">
                  {t('app.onboarding.getting_started.checklist.pipeline')}
                </span>
                <span className="mt-0.5 block text-xs text-slate-500">
                  {t('app.onboarding.getting_started.checklist.pipeline_desc')}
                </span>
              </span>
            </Link>
          </li>
        </ul>
        <div className="mt-4 border-t border-slate-100 pt-4">
          <p className="text-xs font-medium text-slate-700">
            {t('app.onboarding.getting_started.deferred_legal_title')}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {t('app.onboarding.getting_started.deferred_legal_desc')}
          </p>
          <Link to={ACTIVATION_PATHS.legal} className="mt-2 inline-flex text-xs font-medium text-brand-700 hover:underline">
            {t('app.onboarding.getting_started.deferred_legal_link')}
          </Link>
        </div>
        <div className="mt-4 border-t border-slate-100 pt-4">
          <p className="text-xs font-medium text-slate-700">
            {t('app.onboarding.getting_started.comms_title')}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {t('app.onboarding.getting_started.comms_subtitle')}
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            <Link
              to={CRM_APP_PATHS.settingsIntegrations}
              className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700 hover:border-slate-300"
            >
              <IconBrandTelegram size={14} stroke={1.8} />
              {t('app.onboarding.getting_started.comms_telegram')}
            </Link>
            <Link
              to={CRM_APP_PATHS.settingsIntegrations}
              className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700 hover:border-slate-300"
            >
              <IconMail size={14} stroke={1.8} />
              {t('app.onboarding.getting_started.comms_email')}
            </Link>
            <Link
              to={CRM_APP_PATHS.settingsIntegrations}
              className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700 hover:border-slate-300"
            >
              <IconBrandWhatsapp size={14} stroke={1.8} />
              {t('app.onboarding.getting_started.comms_whatsapp')}
            </Link>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {steps.map((step, idx) => {
          const visual = stepVisuals[idx] ?? stepVisuals[0]
          const PendingIcon = visual.pendingIcon
          return (
            <article
              key={step.key}
              className={`cursor-pointer rounded-xl border bg-white p-5 shadow-sm transition hover:border-brand-300 ${step.done ? 'border-emerald-200' : 'border-slate-200'}`}
              role="link"
              tabIndex={0}
              onClick={() => navigate(step.href)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault()
                  navigate(step.href)
                }
              }}
            >
              <div className={`inline-flex rounded-lg p-2 ${visual.bgClass}`}>
                {step.done ? <IconCheck size={18} stroke={2} className="text-emerald-700" /> : <PendingIcon size={18} stroke={1.9} />}
              </div>
              <h2 className="mt-3 text-base font-semibold text-slate-900">
                {step.title}
              </h2>
              <p className="mt-1 text-sm text-slate-600">
                {step.desc}
              </p>
              <Link
                to={step.href}
                className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-brand-700 hover:underline"
                onClick={(event) => event.stopPropagation()}
              >
                {step.openLabel}
                <IconArrowRight size={14} stroke={1.9} />
              </Link>
            </article>
          )
        })}
      </section>

      <div className="flex justify-end">
        <button
          type="button"
          onClick={() => navigate(ACTIVATION_PATHS.overview, { replace: true })}
          className={`inline-flex items-center gap-1 rounded-lg px-4 py-2 text-sm font-medium text-white ${completed ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-brand-600 hover:bg-brand-700'}`}
        >
          {completed
            ? t('app.onboarding.getting_started.done')
            : t('app.onboarding.getting_started.go_dashboard')}
          <IconArrowRight size={14} stroke={1.9} />
        </button>
      </div>
    </div>
  )
}
