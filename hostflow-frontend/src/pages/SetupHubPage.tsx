import { Link, useNavigate } from 'react-router-dom'
import { IconArrowRight, IconChecklist } from '@tabler/icons-react'
import { useI18n } from '../i18n'
import { PageHeader } from '../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../components/layout'
import { SetupStatusPanel } from '../components/onboarding/SetupStatusPanel'
import { SuccessPathReadinessPanel } from '../components/onboarding/SuccessPathReadinessPanel'
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
          title={t('app.onboarding.success_path.page_title', {
            defaultValue: 'Get ready to hire',
          })}
          subtitle={t('app.onboarding.success_path.page_subtitle', {
            defaultValue:
              'Follow the checklist below. When the next step is done, come back here or continue from empty states in the product.',
          })}
          kind="browse"
          secondaryActions={
            <Link
              to={CRM_APP_PATHS.launchpad}
              className="btn-secondary btn-sm"
              data-testid="m1-setup-back-launchpad"
            >
              {t('app.launchpad.back', { defaultValue: '← Back to Launchpad' })}
            </Link>
          }
        />
      </PageShellHeader>
      <div className="mx-auto flex min-h-0 w-full max-w-3xl flex-1 flex-col gap-4 overflow-y-auto px-4 pb-4">
        <section className="rounded-xl border border-slate-200 bg-white px-6 py-4 shadow-sm">
          <div className="inline-flex items-center gap-1 rounded-lg bg-brand-50 px-2 py-1 text-xs font-medium text-brand-700">
            <IconChecklist size={14} stroke={1.9} />
            {t('app.onboarding.success_path.hub_badge', { defaultValue: 'Success path' })}
          </div>
        </section>

        <SuccessPathReadinessPanel showWhenComplete />

        <details className="rounded-xl border border-slate-200 bg-white shadow-sm open:pb-0">
          <summary className="cursor-pointer list-none px-6 py-4 text-sm font-semibold text-slate-800 marker:content-none [&::-webkit-details-marker]:hidden">
            {t('app.onboarding.setup_status.technical_gates_summary', {
              defaultValue: 'Technical Recruitment gates (advanced)',
            })}
            <span className="mt-1 block text-xs font-normal text-slate-500">
              {t('app.onboarding.setup_status.technical_gates_hint', {
                defaultValue: 'Operational G0–G8 health check — optional detail for admins.',
              })}
            </span>
          </summary>
          <div className="border-t border-slate-100 px-2 pb-2 pt-2 sm:px-4">
            <SetupStatusPanel
              snapshot={snapshot}
              loading={loading}
              onActionNavigate={() => {
                void refresh()
              }}
            />
          </div>
        </details>

        {ready && snapshot ? (
          <section
            className="rounded-xl border border-emerald-200 bg-emerald-50/40 p-6 shadow-sm"
            data-testid="m1-route-summary"
          >
            <h2 className="text-sm font-semibold text-slate-900">
              {t('app.onboarding.setup_status.route_summary_title', {
                defaultValue: 'Recruitment is ready to accept people',
              })}
            </h2>
            <p className="mt-2 text-sm text-slate-700">
              {t('app.onboarding.setup_status.route_summary_body', {
                defaultValue:
                  'Candidates can enter through your configured intake. Open Recruitment from Launchpad.',
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

        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          {ready ? (
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => navigate(CRM_APP_PATHS.launchpad, { replace: true })}
                data-testid="m1-setup-go-launchpad"
                className="inline-flex items-center gap-1 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
              >
                {t('app.onboarding.setup_status.go_launchpad', {
                  defaultValue: 'Back to Launchpad',
                })}
                <IconArrowRight size={14} stroke={1.9} />
              </button>
            </div>
          ) : (
            <p className="text-xs text-slate-600">
              {t('app.onboarding.success_path.hub_footer', {
                defaultValue: 'Use the primary button above for the single next step. Technical gates are optional detail.',
              })}
            </p>
          )}
        </section>
      </div>
    </PageShell>
  )
}
