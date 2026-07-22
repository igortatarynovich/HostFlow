/**
 * Deprecated operator surface: /app/recruitment/searches*.
 * Acquisition → shell Marketing Workspace; process context → Vacancy workspace.
 */
import { useEffect } from 'react'
import { Navigate, useParams } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import {
  buildModuleAbsoluteUrl,
  isShellDeployHost,
  resolveDeployHost,
} from '../../platform/deployHosts'

function shellMarketingHref(pathAndQuery: string = CRM_APP_PATHS.marketing): string {
  const host = resolveDeployHost()
  if (isShellDeployHost(host)) return pathAndQuery
  return buildModuleAbsoluteUrl('shell', pathAndQuery)
}

/** List + create + acquisition/Meta → shell Marketing (SoT for attraction). */
export function RecruitmentSearchesToMarketingRedirect() {
  const href = shellMarketingHref(CRM_APP_PATHS.marketing)

  useEffect(() => {
    if (/^https?:\/\//i.test(href) && typeof window !== 'undefined') {
      window.location.replace(href)
    }
  }, [href])

  if (/^https?:\/\//i.test(href)) {
    return (
      <div className="grid h-40 place-items-center text-sm text-slate-500">
        Redirecting to Marketing…
      </div>
    )
  }
  return <Navigate to={href} replace />
}

/** Search id was always vacancy id → Vacancy detail (recruitment process). */
export function RecruitmentSearchToVacancyRedirect() {
  const { searchId } = useParams<{ searchId: string }>()
  const id = String(searchId || '').trim()
  if (!id) return <Navigate to={CRM_APP_PATHS.vacancies} replace />
  return <Navigate to={`${CRM_APP_PATHS.vacancies}/${encodeURIComponent(id)}`} replace />
}
