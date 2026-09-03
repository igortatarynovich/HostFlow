import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconCheck, IconCircle, IconRocket } from '@tabler/icons-react'
import { useI18n } from '../i18n'
import { getOnboardingStatus, type OnboardingStatus } from '../api/client'
import { useBusinessTerminology } from '../hooks/useBusinessTerminology'
import { ACTIVATION_PATHS, getBusinessHomePath, getBusinessNextActionPath } from '../app/activationRoutes'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { usePermissions } from '../hooks/usePermissions'

type Props = {
  tenantId: string
}

export function OnboardingWizard({ tenantId: _tenantId }: Props) {
  const { t } = useI18n()
  const { can } = usePermissions()
  const { openEntityLabel } = useBusinessTerminology()
  const [status, setStatus] = useState<OnboardingStatus | null>(null)

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
  }, [_tenantId])

  const steps = useMemo(
    () => {
      const businessType = status?.business_type ?? 'agency'
      const companyHref = getBusinessHomePath(businessType)
      const typeStep =
        businessType === 'employer'
          ? {
              id: 'vacancy',
              done: Boolean(status?.steps?.first_vacancy_created),
              href: CRM_APP_PATHS.setupVacancy,
              label: t('app.onboarding.first_value.step_vacancy'),
            }
          : businessType === 'services'
            ? {
                id: 'first_client_services',
                done: Boolean(status?.steps?.first_client_created || status?.steps?.first_lead_created),
                href: ACTIVATION_PATHS.clients,
                label: t('app.onboarding.first_value.step_services_client'),
              }
            : {
                id: 'first_client',
                done: Boolean(status?.steps?.first_client_created),
                href: CRM_APP_PATHS.setupClient,
                label: t('app.onboarding.first_value.step_client'),
              }
      return [
        {
          id: 'company',
          done: Boolean(status?.steps?.company_created),
          href: companyHref,
          label: t('app.onboarding.first_value.step_company'),
        },
        typeStep,
        {
          id: 'next_action',
          done: Boolean(status?.steps?.next_action_created),
          href: businessType === 'services' ? ACTIVATION_PATHS.leads : getBusinessNextActionPath(businessType),
          label:
            businessType === 'services'
              ? t('app.onboarding.first_value.step_services_leads')
              : t('app.onboarding.first_value.step_next_action'),
        },
      ]
    },
    [status, t],
  )

  const doneCount = steps.filter((step) => step.done).length
  const isDone = doneCount >= steps.length
  if (isDone) return null

  return (
    <div className="card mb-6 border-brand-200 bg-brand-50/60 p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="mb-2 inline-flex items-center gap-1 rounded-md bg-white px-2 py-1 text-xs font-medium text-brand-700">
            <IconRocket size={14} stroke={1.9} />
            {t('app.onboarding.first_value.badge')}
          </div>
          <h3 className="text-lg font-semibold text-slate-900">
            {t('app.onboarding.first_value.title')}
          </h3>
          <p className="mt-1 text-sm text-slate-600">
            {t('app.onboarding.first_value.subtitle')}
          </p>
          <p className="mt-2 text-xs font-medium text-brand-700">
            {t('app.onboarding.first_value.progress', {
              values: { done: doneCount, total: steps.length },
            })}
          </p>
          <ol className="mt-4 space-y-2 text-sm">
            {steps.map((step, index) => (
              <li key={step.id} className="flex items-center justify-between gap-3 rounded-lg bg-white/70 px-3 py-2">
                <span className="inline-flex items-center gap-2">
                  {step.done ? (
                    <IconCheck size={16} stroke={2} className="text-emerald-600" />
                  ) : (
                    <IconCircle size={16} stroke={1.8} className="text-slate-500" />
                  )}
                  <span className="text-slate-800">{`${index + 1}. ${step.label}`}</span>
                </span>
                <Link to={step.href} className="text-xs font-medium text-brand-700 hover:underline">
                  {step.href === ACTIVATION_PATHS.clients || step.href === CRM_APP_PATHS.setupClient
                    ? openEntityLabel
                    : t('app.onboarding.first_value.open')}
                </Link>
              </li>
            ))}
          </ol>
          <p className="mt-4 border-t border-brand-100/90 pt-3 text-xs leading-relaxed text-slate-600">
            {can('settings.view') ? (
              <>
                {t('app.onboarding.first_value.footer_settings')}{' '}
                <Link to={CRM_APP_PATHS.settings} className="font-medium text-brand-800 hover:underline">
                  {t('app.onboarding.first_value.footer_settings_link')}
                </Link>
                <span className="mx-2 text-slate-300" aria-hidden>
                  |
                </span>
              </>
            ) : null}
            {t('app.onboarding.first_value.footer_checklist')}{' '}
            <Link to={CRM_APP_PATHS.onboardingGettingStarted} className="font-medium text-brand-800 hover:underline">
              {t('app.onboarding.first_value.footer_checklist_link')}
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
