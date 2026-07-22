/**
 * Deprecated operator surface: /app/recruitment/searches*.
 * Acquisition → Marketing Workspace; process context → Vacancy workspace.
 */
import { Navigate, useParams } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'

/** List + create wizard → Marketing (SoT for attraction). */
export function RecruitmentSearchesToMarketingRedirect() {
  return <Navigate to={CRM_APP_PATHS.marketing} replace />
}

/** Search id was always vacancy id → Vacancy detail. */
export function RecruitmentSearchToVacancyRedirect() {
  const { searchId } = useParams<{ searchId: string }>()
  const id = String(searchId || '').trim()
  if (!id) return <Navigate to={CRM_APP_PATHS.vacancies} replace />
  return <Navigate to={`${CRM_APP_PATHS.vacancies}/${encodeURIComponent(id)}`} replace />
}
