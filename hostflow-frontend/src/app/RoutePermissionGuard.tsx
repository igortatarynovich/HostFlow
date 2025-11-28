import type { ReactNode } from 'react'
import type { Permission } from '../hooks/usePermissions'
import { usePermissions } from '../hooks/usePermissions'
import { useI18n } from '../i18n'

type RoutePermissionGuardProps = {
  permission?: Permission | Permission[]
  children: ReactNode
}

const toArray = (permission?: Permission | Permission[]): Permission[] => {
  if (!permission) return []
  return Array.isArray(permission) ? permission : [permission]
}

export function RoutePermissionGuard({ permission, children }: RoutePermissionGuardProps) {
  const { can } = usePermissions()
  const { t } = useI18n()

  if (!permission) {
    return <>{children}</>
  }

  const required = toArray(permission)
  const allowed = required.some((value) => can(value))
  if (allowed) {
    return <>{children}</>
  }

  return (
    <div className="rounded border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
      {t('common.access_denied')}
    </div>
  )
}
