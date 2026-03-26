import type { PropsWithChildren } from 'react'
import { Navigate } from 'react-router-dom'
import { useCommunicationsAccess, type CommunicationsFeatureKey } from '../../hooks/useCommunicationsAccess'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'

type Props = PropsWithChildren<{
  feature?: CommunicationsFeatureKey
  anyOf?: CommunicationsFeatureKey[]
  fallbackPath?: string
}>

export default function CommunicationsFeatureGate({
  feature,
  anyOf,
  fallbackPath = CRM_APP_PATHS.overview,
  children,
}: Props) {
  const { t } = useI18n()
  const { loading, canUseCommunicationsFeature } = useCommunicationsAccess()

  if (loading) {
    return <div className="p-6 text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading...' })}</div>
  }

  const allowed = feature
    ? canUseCommunicationsFeature(feature)
    : Array.isArray(anyOf) && anyOf.length > 0
      ? anyOf.some((f) => canUseCommunicationsFeature(f))
      : true

  if (!allowed) {
    return <Navigate to={fallbackPath} replace />
  }

  return <>{children}</>
}
