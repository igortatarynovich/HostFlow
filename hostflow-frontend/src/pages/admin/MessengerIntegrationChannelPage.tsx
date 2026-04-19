import { Navigate, useParams } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import CommunicationsMessengerSettingsPage from './CommunicationsMessengerSettingsPage'
import { isMessengerChannel } from './communicationsMessengerChannels'

export default function MessengerIntegrationChannelPage() {
  const { messengerChannel } = useParams<{ messengerChannel: string }>()
  const key = messengerChannel?.toLowerCase()
  if (!isMessengerChannel(key)) {
    return <Navigate to={CRM_APP_PATHS.settingsIntegrations} replace />
  }
  return <CommunicationsMessengerSettingsPage lockedChannel={key} />
}
