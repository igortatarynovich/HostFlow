/**
 * C-7: Подборы list retired as ad-launch surface — redirect to Marketing.
 * Deep links under `/app/recruitment/searches/:id/acquisition/*` stay for legacy read-only.
 */
import { Navigate } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'

export default function SearchesListPage() {
  return (
    <Navigate
      to={CRM_APP_PATHS.marketing}
      replace
      state={{ fromLegacySearches: true }}
    />
  )
}
