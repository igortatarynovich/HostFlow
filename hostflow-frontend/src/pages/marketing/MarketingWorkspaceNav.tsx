import { Link, useLocation } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'

function tabClass(active: boolean): string {
  return `rounded px-3 py-2 text-sm ${active ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-700'}`
}

function pathIsSources(pathname: string): boolean {
  return (
    pathname === CRM_APP_PATHS.marketingSources ||
    pathname.startsWith(`${CRM_APP_PATHS.marketingSources}/`)
  )
}

function pathIsCampaigns(pathname: string): boolean {
  if (pathIsSources(pathname)) return false
  if (pathname.startsWith(CRM_APP_PATHS.marketingDiagnostics)) return false
  if (pathname.startsWith(CRM_APP_PATHS.marketingForms)) return false
  return pathname === CRM_APP_PATHS.marketing || pathname.startsWith(`${CRM_APP_PATHS.marketing}/`)
}

/** In-page Marketing ops nav. Sources stay off the agency rail (C-3). */
export function MarketingWorkspaceNav() {
  const { t } = useI18n()
  const { pathname } = useLocation()
  const sourcesOn = pathIsSources(pathname)
  const campaignsOn = pathIsCampaigns(pathname)

  return (
    <nav
      className="mt-2 flex flex-wrap gap-2"
      aria-label={t('app.marketing.workspace.nav_aria')}
      data-testid="marketing-workspace-nav"
    >
      <Link
        to={CRM_APP_PATHS.marketing}
        className={tabClass(campaignsOn)}
        data-testid="marketing-workspace-nav-campaigns"
      >
        {t('app.marketing.workspace.campaigns')}
      </Link>
      <Link
        to={CRM_APP_PATHS.marketingSources}
        className={tabClass(sourcesOn)}
        data-testid="marketing-workspace-nav-sources"
      >
        {t('app.marketing.workspace.sources')}
      </Link>
    </nav>
  )
}
