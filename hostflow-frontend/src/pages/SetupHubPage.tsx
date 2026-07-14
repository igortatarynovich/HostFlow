import { Link, useNavigate } from 'react-router-dom'
import { IconArrowRight, IconChecklist } from '@tabler/icons-react'
import { useI18n } from '../i18n'
import { PageHeader } from '../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../components/layout'
import { SetupStatusPanel } from '../components/onboarding/SetupStatusPanel'
import { useSetupReadiness } from '../hooks/useSetupReadiness'
import { CRM_APP_PATHS } from '../app/crmAppPaths'

export default function SetupHubPage() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const { snapshot, loading, ready, refresh } = useSetupReadiness()

  return (
    <PageShell data-testid="m1-setup-hub">
      <PageShellHeader>
        <PageHeader
          title={t('app.onboarding.setup_status.page_title', {
            defaultValue: 'Настройка Recruitment',
          })}
          subtitle={t('app.onboarding.setup_status.page_subtitle_launchpad', {
            defaultValue:
              'Запуск приложения Recruitment. Когда всё готово — вернитесь в Launchpad и откройте модуль.',
          })}
          kind="browse"
          secondaryActions={
            <Link
              to={CRM_APP_PATHS.launchpad}
              className="btn-secondary btn-sm"
              data-testid="m1-setup-back-launchpad"
            >
              {t('app.launchpad.back', { defaultValue: '← Вернуться в Launchpad' })}
            </Link>
          }
        />
      </PageShellHeader>
      <div className="mx-auto flex min-h-0 w-full max-w-3xl flex-1 flex-col gap-4 overflow-y-auto px-4 pb-4">
      <section className="rounded-2xl border border-slate-200 bg-white px-6 py-4 shadow-sm">
        <div className="inline-flex items-center gap-1 rounded-md bg-brand-50 px-2 py-1 text-xs font-medium text-brand-700">
          <IconChecklist size={14} stroke={1.9} />
          {t('app.onboarding.setup_status.hub_badge', { defaultValue: 'Setup' })}
        </div>
      </section>

      <SetupStatusPanel
        snapshot={snapshot}
        loading={loading}
        onActionNavigate={() => {
          void refresh()
        }}
      />

      {ready && snapshot ? (
        <section
          className="rounded-2xl border border-emerald-200 bg-emerald-50/40 p-6 shadow-sm"
          data-testid="m1-route-summary"
        >
          <h2 className="text-sm font-semibold text-slate-900">
            {t('app.onboarding.setup_status.route_summary_title', {
              defaultValue: 'Recruitment готов к работе',
            })}
          </h2>
          <p className="mt-2 text-sm text-slate-700">
            {t('app.onboarding.setup_status.route_summary_body', {
              defaultValue:
                'Кандидаты могут появляться в системе выбранным способом. Откройте Recruitment из Launchpad.',
            })}
          </p>
          <button
            type="button"
            data-testid="m1-action-health-check"
            className="sr-only"
            aria-hidden
            onClick={() => void refresh()}
          />
        </section>
      ) : null}

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-xs text-slate-500">
          {t('app.onboarding.setup_status.health_check_hint', {
            defaultValue: 'Health Check is this screen — gate status and one next action below.',
          })}
        </p>
        {ready ? (
          <div className="mt-4 flex justify-end">
            <button
              type="button"
              onClick={() => navigate(CRM_APP_PATHS.launchpad, { replace: true })}
              data-testid="m1-setup-go-launchpad"
              className="inline-flex items-center gap-1 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
            >
              {t('app.onboarding.setup_status.go_launchpad', {
                defaultValue: 'Вернуться в Launchpad',
              })}
              <IconArrowRight size={14} stroke={1.9} />
            </button>
          </div>
        ) : (
          <p className="mt-2 text-xs text-slate-600">
            {t('app.onboarding.setup_status.legacy_paths_note', {
              defaultValue: 'Legacy onboarding shortcuts redirect here.',
            })}{' '}
            <Link to={CRM_APP_PATHS.setup} className="text-brand-700 hover:underline">
              {CRM_APP_PATHS.setup}
            </Link>
          </p>
        )}
      </section>
      </div>
    </PageShell>
  )
}
