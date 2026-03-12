import { Suspense, lazy, useMemo } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './store/useAuth'
import Login from './pages/Login'
import { AppShell } from './app/AppShell'
import { APP_ROUTES, NAV_ITEMS } from './app/routes'
import { RoutePermissionGuard } from './app/RoutePermissionGuard'
import { usePermissions } from './hooks/usePermissions'
import PublicIntakeStart from './pages/public/PublicIntakeStart'
import PublicPortalLanding from './pages/public/PublicPortalLanding'
import PublicLanding from './pages/public/PublicLanding'
import CrmLandingPage from './pages/public/CrmLandingPage'
import PublicNotFoundPage from './pages/public/PublicNotFoundPage'
import FeatureCandidatePipelinePage from './pages/public/FeatureCandidatePipelinePage'
import FeatureDocumentControlPage from './pages/public/FeatureDocumentControlPage'
import UseCaseTruckingRecruitmentPage from './pages/public/UseCaseTruckingRecruitmentPage'
import UseCaseHighVolumeOnboardingPage from './pages/public/UseCaseHighVolumeOnboardingPage'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import ResetPasswordPage from './pages/ResetPasswordPage'
import InviteAcceptPage from './pages/InviteAcceptPage'
import OnboardingCompanyPage from './pages/OnboardingCompanyPage'
import OnboardingGettingStartedPage from './pages/OnboardingGettingStartedPage'
import SignupPage from './pages/SignupPage'
import { useI18n } from './i18n'

const PublicApplyPage = lazy(() => import('./pages/public/PublicApplyPage'))
const PublicIntakeNew = lazy(() => import('./pages/public/PublicIntakeNew'))
const PublicStatusPage = lazy(() => import('./pages/public/PublicStatusPage'))
const PublicScanPage = lazy(() => import('./pages/public/PublicScanPage'))
const ClientPortalPage = lazy(() => import('./pages/ClientPortalPage'))

function LazyRoute({ children, loadingLabel }: { children: JSX.Element; loadingLabel: string }) {
  return <Suspense fallback={<div className="grid h-screen place-items-center text-slate-500">{loadingLabel}</div>}>{children}</Suspense>
}

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
    return <div className="grid h-screen place-items-center text-slate-500">{t('common.loading')}</div>
  }

  return (
    <Routes>
      <Route path="/public" element={<Navigate to="/public/intake" replace />} />
      <Route path="/public/portal" element={<PublicPortalLanding />} />
      <Route path="/public/intake" element={<PublicIntakeStart />} />
      <Route path="/public/apply/:token" element={<LazyRoute loadingLabel={t('common.loading')}><PublicIntakeNew /></LazyRoute>} />
      <Route path="/public/apply-old/:token" element={<LazyRoute loadingLabel={t('common.loading')}><PublicApplyPage /></LazyRoute>} />
      <Route path="/public/scan" element={<LazyRoute loadingLabel={t('common.loading')}><PublicScanPage /></LazyRoute>} />
      <Route path="/public/scan-sessions" element={<Navigate to="/public/scan" replace />} />
      <Route path="/public/status/:token" element={<LazyRoute loadingLabel={t('common.loading')}><PublicStatusPage /></LazyRoute>} />
      <Route path="/client-portal" element={<LazyRoute loadingLabel={t('common.loading')}><ClientPortalPage /></LazyRoute>} />

      {!me && (
        <>
          <Route path="/" element={<CrmLandingPage />} />
          <Route path="/pricing" element={<CrmLandingPage />} />
          <Route path="/features/candidate-pipeline" element={<FeatureCandidatePipelinePage />} />
          <Route path="/features/document-control" element={<FeatureDocumentControlPage />} />
          <Route path="/use-cases/trucking-recruitment" element={<UseCaseTruckingRecruitmentPage />} />
          <Route path="/use-cases/high-volume-onboarding" element={<UseCaseHighVolumeOnboardingPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route path="/login" element={<Login />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route path="/invite/accept" element={<InviteAcceptPage />} />
          <Route path="*" element={<PublicNotFoundPage />} />
        </>
      )}

      {me && (
        <>
          <Route path="/login" element={<Navigate to="/app/overview" replace />} />
          <Route path="/signup" element={<Navigate to="/app/overview" replace />} />
          <Route path="/app" element={<AppShell me={me} navItems={navItems} onLogout={logout} />}>
            <Route index element={<Navigate to="overview" replace />} />
            <Route path="onboarding/company" element={<OnboardingCompanyPage />} />
            <Route path="onboarding/getting-started" element={<OnboardingGettingStartedPage />} />
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
