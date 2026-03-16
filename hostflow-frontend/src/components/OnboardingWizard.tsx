import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconCheck, IconCircle, IconRocket } from '@tabler/icons-react'
import { useI18n } from '../i18n'
import { getOnboardingStatus, type OnboardingStatus } from '../api/client'
import { useBusinessTerminology } from '../hooks/useBusinessTerminology'
import { ACTIVATION_PATHS, getBusinessHomePath, getBusinessNextActionPath } from '../app/activationRoutes'

type Props = {
  tenantId: string
}

export function OnboardingWizard({ tenantId: _tenantId }: Props) {
  const { t } = useI18n()
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
              href: ACTIVATION_PATHS.vacancies,
              label: t('app.onboarding.first_value.step_vacancy', { defaultValue: 'Create first vacancy' }),
            }
          : businessType === 'services'
            ? {
                id: 'first_client_services',
                done: Boolean(status?.steps?.first_client_created || status?.steps?.first_lead_created),
                href: ACTIVATION_PATHS.clients,
                label: t('app.onboarding.first_value.step_services_client', { defaultValue: 'Create first client or capture lead (services mode)' }),
              }
            : {
                id: 'first_client',
                done: Boolean(status?.steps?.first_client_created),
                href: ACTIVATION_PATHS.clients,
                label: t('app.onboarding.first_value.step_client', { defaultValue: 'Create first client' }),
              }
      return [
        {
          id: 'company',
          done: Boolean(status?.steps?.company_created),
          href: companyHref,
          label: t('app.onboarding.first_value.step_company', { defaultValue: 'Company created' }),
        },
        typeStep,
        {
          id: 'next_action',
          done: Boolean(status?.steps?.next_action_created),
          href: businessType === 'services' ? ACTIVATION_PATHS.leads : getBusinessNextActionPath(businessType),
          label:
            businessType === 'services'
              ? t('app.onboarding.first_value.step_services_leads', {
                  defaultValue: 'Process ad leads (potential clients)',
                })
              : t('app.onboarding.first_value.step_next_action', { defaultValue: 'Create next action (task/reminder)' }),
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
            {t('app.onboarding.first_value.badge', { defaultValue: 'First Value Checklist' })}
          </div>
          <h3 className="text-lg font-semibold text-slate-900">
            {t('app.onboarding.first_value.title', { defaultValue: 'Start working in 5 minutes' })}
          </h3>
          <p className="mt-1 text-sm text-slate-600">
            {t('app.onboarding.first_value.subtitle', {
              defaultValue: 'No technical setup required. Complete these three business steps to get immediate value.',
            })}
          </p>
          <p className="mt-2 text-xs font-medium text-brand-700">
            {t('app.onboarding.first_value.progress', {
              defaultValue: 'Progress: {done}/{total}',
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
                  {step.href === ACTIVATION_PATHS.clients
                    ? openEntityLabel
                    : t('app.onboarding.first_value.open', { defaultValue: 'Open' })}
                </Link>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </div>
  )
}
