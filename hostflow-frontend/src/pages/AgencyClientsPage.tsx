import { Navigate } from 'react-router-dom'
import { CRM_APP_PATHS } from '../app/crmAppPaths'

/** Legacy list URL — canonical client workspace is the CRM directory. */
export default function AgencyClientsPage() {
  return <Navigate to={CRM_APP_PATHS.clientsDirectory} replace />
}
