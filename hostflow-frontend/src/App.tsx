import { useMemo } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './store/useAuth'
import Login from './pages/Login'
import { AppShell } from './app/AppShell'
import { APP_ROUTES, NAV_ITEMS } from './app/routes'
import { RoutePermissionGuard } from './app/RoutePermissionGuard'
import { usePermissions } from './hooks/usePermissions'
import PublicIntakeStart from './pages/public/PublicIntakeStart'
import PublicApplyPage from './pages/public/PublicApplyPage'
import PublicPortalLanding from './pages/public/PublicPortalLanding'
import PublicStatusPage from './pages/public/PublicStatusPage'
import PublicScanPage from './pages/public/PublicScanPage'
import EntityListShellDemoPublicPage from './pages/dev/EntityListShellDemoPublicPage'
import { useI18n } from './i18n'

export default function App(){
  const { me, loading, logout } = useAuth()
  const { can } = usePermissions()
  const { t } = useI18n()
  const isSuperAdmin = (me?.role || '').toLowerCase() === 'superadmin'

  const navItems = useMemo(
    () =>
      NAV_ITEMS.filter((item) => {
        if (item.superadminOnly && !isSuperAdmin) return false
        return !item.permission || can(item.permission)
      }),
    [can, isSuperAdmin]
  )

  if (loading) {
    return <div className="grid h-screen place-items-center text-gray-500">{t('common.loading')}</div>
  }

  return (
    <Routes>
      <Route path="/public" element={<PublicPortalLanding />} />
      <Route path="/public/portal" element={<PublicPortalLanding />} />
      <Route path="/public/intake" element={<PublicIntakeStart />} />
      <Route path="/public/apply/:token" element={<PublicApplyPage />} />
      <Route path="/public/scan" element={<PublicScanPage />} />
      <Route path="/public/scan-sessions" element={<Navigate to="/public/scan" replace />} />
      <Route path="/public/status/:token" element={<PublicStatusPage />} />

      {import.meta.env.DEV ? (
        <Route path="/dev/entity-list-shell" element={<EntityListShellDemoPublicPage />} />
      ) : null}

      {!me && (
        <>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </>
      )}

      {me && (
        <>
          <Route path="/login" element={<Navigate to="/app/overview" replace />} />
          <Route path="/app" element={<AppShell me={me} navItems={navItems} onLogout={logout} />}>
            <Route index element={<Navigate to="overview" replace />} />
            {APP_ROUTES.map(({ key, path, Component, permission }) => (
              <Route
                key={key}
                path={path}
                element={
                  <RoutePermissionGuard permission={permission}>
                    <Component />
                  </RoutePermissionGuard>
                }
              />
            ))}
          </Route>
          <Route path="/" element={<Navigate to="/app/overview" replace />} />
          <Route path="*" element={<Navigate to="/app/overview" replace />} />
        </>
      )}
    </Routes>
  )
}
