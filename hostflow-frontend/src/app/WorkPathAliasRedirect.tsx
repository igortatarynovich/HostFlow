import { Navigate, useLocation } from 'react-router-dom'

import { CRM_APP_PATHS } from './crmAppPaths'
import { isWorkShellAliasSuffix, normalizeAppPathSuffix } from '../nav/workShellAlias'

/**
 * Child of **`/app/work/*`**: forwards to the same resource under **`/app/...`** (query + hash preserved).
 */
export function WorkPathAliasRedirect() {
  const location = useLocation()
  const raw = location.pathname.replace(/^\/app\/work\/?/, '')
  const suffix = normalizeAppPathSuffix(raw)
  if (!suffix || !isWorkShellAliasSuffix(suffix)) {
    return <Navigate to={CRM_APP_PATHS.work} replace />
  }
  return (
    <Navigate
      to={{
        pathname: `${CRM_APP_PATHS.appShellPrefix}/${suffix}`,
        search: location.search,
        hash: location.hash,
      }}
      replace
    />
  )
}
