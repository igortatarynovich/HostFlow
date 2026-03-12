import type { PropsWithChildren } from 'react'
import { Navigate } from 'react-router-dom'
import { useCommunicationsAccess, type CommunicationsFeatureKey } from '../../hooks/useCommunicationsAccess'

type Props = PropsWithChildren<{
  feature?: CommunicationsFeatureKey
  anyOf?: CommunicationsFeatureKey[]
  fallbackPath?: string
}>

export default function CommunicationsFeatureGate({
  feature,
  anyOf,
  fallbackPath = '/app/overview',
  children,
}: Props) {
  const { loading, canUseCommunicationsFeature } = useCommunicationsAccess()

  if (loading) {
    return <div className="p-6 text-sm text-slate-500">Loading...</div>
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

