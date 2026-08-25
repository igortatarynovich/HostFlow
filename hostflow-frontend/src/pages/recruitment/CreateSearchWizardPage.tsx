/**
 * C-7: create-подбор wizard retired — new launches only via Marketing Campaign setup.
 */
import { Navigate } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'

export default function CreateSearchWizardPage() {
  return <Navigate to={CRM_APP_PATHS.marketingNew} replace />
}
