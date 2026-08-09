import { Link, useNavigate } from 'react-router-dom'
import { IconArrowRight } from '@tabler/icons-react'
import { useI18n } from '../i18n'
import { PageHeader } from '../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../components/layout'
import { SuccessPathReadinessPanel } from '../components/onboarding/SuccessPathReadinessPanel'
import { useSuccessPathReadiness } from '../hooks/useSuccessPathReadiness'
import { CRM_APP_PATHS } from '../app/crmAppPaths'

export default function SetupHubPage() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const { pathComplete, nextAction, refresh } = useSuccessPathReadiness()

  return (
    <PageShell data-testid="m1-setup-hub">
      <PageShellHeader>
        <PageHeader
          title={t('app.onboarding.success_path.page_title', {
            defaultValue: 'Начать работу',
          })}
          subtitle={t('app.onboarding.success_path.page_subtitle', {
            defaultValue: 'Один следующий шаг на экране — пока не будет заявки и контакта.',
          })}
          kind="browse"
          secondaryActions={
            <Link
              to={CRM_APP_PATHS.launchpad}
              className="btn-secondary btn-sm"
              data-testid="m1-setup-back-launchpad"
            >
              {t('app.launchpad.back', { defaultValue: '← К началу работы' })}
            </Link>
          }
        />
      </PageShellHeader>
      <div className="mx-auto flex min-h-0 w-full max-w-3xl flex-1 flex-col gap-4 overflow-y-auto px-4 pb-4">
        <SuccessPathReadinessPanel showWhenComplete />

        {pathComplete ? (
          <section
            className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-6 shadow-sm"
            data-testid="m1-route-summary"
          >
            <h2 className="text-base font-semibold text-slate-900">
              {t('app.onboarding.success_path.result_ready_title', {
                defaultValue: 'Готово к работе',
              })}
            </h2>
            <p className="mt-2 text-sm text-slate-700">
              {t('app.onboarding.success_path.result_ready_body', {
                defaultValue:
                  'Компания и первые шаги на месте. Откройте меню и продолжайте.',
              })}
            </p>
            <button
              type="button"
              data-testid="m1-action-health-check"
              className="sr-only"
              aria-hidden
              onClick={() => void refresh()}
            />
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => navigate(CRM_APP_PATHS.launchpad, { replace: true })}
                data-testid="m1-setup-go-launchpad"
                className="inline-flex items-center gap-1 rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700"
              >
                {t('app.onboarding.success_path.go_work', {
                  defaultValue: 'Go to work',
                })}
                <IconArrowRight size={14} stroke={1.9} />
              </button>
              <Link
                to={CRM_APP_PATHS.vacancies}
                className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-800 hover:bg-slate-50"
              >
                {t('app.onboarding.success_path.go_vacancies', {
                  defaultValue: 'Open vacancies',
                })}
              </Link>
            </div>
          </section>
        ) : nextAction ? (
          <p className="px-1 text-xs text-slate-500">
            {t('app.onboarding.success_path.hub_footer', {
              defaultValue: 'Finish the step above — that is all you need right now.',
            })}
          </p>
        ) : null}
      </div>
    </PageShell>
  )
}
