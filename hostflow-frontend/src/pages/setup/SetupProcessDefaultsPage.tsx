import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { IconCheck } from '@tabler/icons-react'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { SetupFlowChrome } from '../../components/setup/SetupFlowChrome'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'
import { applySetupVacancyDefaults } from '../../utils/setupVacancyDefaults'

export default function SetupProcessDefaultsPage() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const vacancyId = (searchParams.get('vacancyId') || '').trim()
  const companyId = (searchParams.get('companyId') || '').trim()

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [applied, setApplied] = useState<{ funnelName: string | null; profileName: string | null } | null>(
    null,
  )

  async function onContinue() {
    if (!vacancyId || !companyId) {
      navigate(CRM_APP_PATHS.setup, { replace: true })
      return
    }
    setLoading(true)
    setError(null)
    try {
      const result = await applySetupVacancyDefaults(vacancyId, companyId)
      setApplied({ funnelName: result.funnelName, profileName: result.profileName })
      navigate(CRM_APP_PATHS.setupIntake, { replace: true })
    } catch (err) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.onboarding.setup.process.errors.generic', {
            defaultValue: 'Could not apply standard settings.',
          }),
          t,
        ),
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <SetupFlowChrome
      testId="m1-setup-process-flow"
      stepLabel={t('app.onboarding.setup.process.badge', { defaultValue: 'Setup · Process' })}
      title={t('app.onboarding.setup.process.title', {
        defaultValue: 'Standard recruitment process',
      })}
      subtitle={t('app.onboarding.setup.process.subtitle', {
        defaultValue:
          'For this vacancy HostFlow will attach a ready funnel and requirements profile. You can change them later in settings.',
      })}
    >
      <div className="space-y-4">
        <ul className="space-y-3 text-sm text-slate-700">
          <li className="flex items-start gap-2">
            <IconCheck size={18} className="mt-0.5 shrink-0 text-emerald-600" aria-hidden />
            <span>
              {t('app.onboarding.setup.process.funnel_line', {
                defaultValue:
                  'A standard recruitment funnel will be used — stages from first contact to hire.',
              })}
            </span>
          </li>
          <li className="flex items-start gap-2">
            <IconCheck size={18} className="mt-0.5 shrink-0 text-emerald-600" aria-hidden />
            <span>
              {t('app.onboarding.setup.process.profile_line', {
                defaultValue:
                  'The candidate requirements profile will be applied automatically — documents and checks from the template.',
              })}
            </span>
          </li>
        </ul>

        {applied ? (
          <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
            {t('app.onboarding.setup.process.applied', {
              defaultValue: 'Connected: {funnel} · {profile}',
              values: {
                funnel: applied.funnelName ?? '—',
                profile: applied.profileName ?? '—',
              },
            })}
          </p>
        ) : null}

        {error ? <ErrorRecoveryBanner info={error} compact /> : null}

        <button
          type="button"
          data-testid="m1-funnel-save"
          disabled={loading}
          onClick={() => void onContinue()}
          className="btn-primary w-full rounded-lg py-3 font-medium disabled:opacity-50"
        >
          {loading
            ? t('common.loading')
            : t('app.onboarding.setup.process.continue', { defaultValue: 'Continue' })}
        </button>
      </div>
    </SetupFlowChrome>
  )
}
