/**
 * C-2: legacy launch UI retired — redirect to Marketing Campaign setup
 * with vacancy target prefilled. Does not call searchAcquisition create.
 */
import { useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { CRM_APP_PATHS, marketingSetupWithVacancyTargetPath } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'
import { useSearchWorkspace } from './SearchWorkspaceLayout'

export default function LaunchAcquisitionPage() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const { searchId, searchName } = useSearchWorkspace()
  const marketingHref = marketingSetupWithVacancyTargetPath(searchId, {
    name: searchName || undefined,
  })

  useEffect(() => {
    navigate(marketingHref, { replace: true })
  }, [marketingHref, navigate])

  return (
    <div className="space-y-4" data-testid="m1-launch-acquisition-redirect">
      <section className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-sm text-amber-950">
        <h2 className="text-base font-semibold">
          {t('app.acquisition.legacy_launch_disabled_title', {
            defaultValue: 'Запуск рекламы перенесён в Marketing',
          })}
        </h2>
        <p className="mt-2 text-amber-900/90">
          {t('app.acquisition.legacy_launch_disabled_body', {
            defaultValue:
              'Новые запуски создаются только как Campaign → Flight. Подборы больше не создают acquisition activities.',
          })}
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Link to={marketingHref} className="btn-primary btn-sm" data-testid="legacy-launch-go-marketing">
            {t('app.acquisition.go_marketing_setup', { defaultValue: 'Открыть Marketing setup' })}
          </Link>
          <Link to={CRM_APP_PATHS.marketing} className="btn-secondary btn-sm">
            {t('app.nav.items.marketing', { defaultValue: 'Маркетинг' })}
          </Link>
        </div>
      </section>
    </div>
  )
}
