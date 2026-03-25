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
import ComparisonHostflowVsSpreadsheetsPage from './pages/public/ComparisonHostflowVsSpreadsheetsPage'
import ComparisonRecruitmentCrmVsAtsPage from './pages/public/ComparisonRecruitmentCrmVsAtsPage'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import ResetPasswordPage from './pages/ResetPasswordPage'
import InviteAcceptPage from './pages/InviteAcceptPage'
import OnboardingCompanyPage from './pages/OnboardingCompanyPage'
import OnboardingGettingStartedPage from './pages/OnboardingGettingStartedPage'
import SignupPage from './pages/SignupPage'
import { useI18n } from './i18n'
import {
  readSignupSuccessContextFromSessionStorage,
  signupContextToSearchParams,
} from './constants/signupContext'
import { resolveDefaultAppHomeHref, resolveDefaultAppHomeSegment } from './utils/defaultAppHome'

const PublicApplyPage = lazy(() => import('./pages/public/PublicApplyPage'))
const PublicIntakeNew = lazy(() => import('./pages/public/PublicIntakeNew'))
const PublicStatusPage = lazy(() => import('./pages/public/PublicStatusPage'))
const PublicDocumentsUploadPage = lazy(() => import('./pages/public/PublicDocumentsUploadPage'))
const ClientPortalPage = lazy(() => import('./pages/ClientPortalPage'))

function LazyRoute({ children, loadingLabel }: { children: JSX.Element; loadingLabel: string }) {
  return <Suspense fallback={<div className="grid h-screen place-items-center text-slate-500">{loadingLabel}</div>}>{children}</Suspense>
}

function SignupRedirectForAuthed() {
  const context = readSignupSuccessContextFromSessionStorage()
  if (context) {
    const params = signupContextToSearchParams(context)
    return <Navigate to={`/app/onboarding/company?${params.toString()}`} replace />
  }
  return <Navigate to="/app/overview" replace />
}

function AuthedDefaultAppNavigate() {
  const { can } = usePermissions()
  return <Navigate to={resolveDefaultAppHomeHref(can('notifications.view'))} replace />
}

function AppShellIndexNavigate() {
  const { can } = usePermissions()
  return <Navigate to={resolveDefaultAppHomeSegment(can('notifications.view'))} replace />
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
      <Route path="/public/documents/:token" element={<LazyRoute loadingLabel={t('common.loading')}><PublicDocumentsUploadPage /></LazyRoute>} />
      <Route path="/public/apply-old/:token" element={<LazyRoute loadingLabel={t('common.loading')}><PublicApplyPage /></LazyRoute>} />
      <Route path="/public/scan" element={<Navigate to="/public/intake" replace />} />
      <Route path="/public/scan-sessions" element={<Navigate to="/public/intake" replace />} />
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
          <Route path="/comparison/hostflow-vs-spreadsheets" element={<ComparisonHostflowVsSpreadsheetsPage />} />
          <Route path="/comparison/recruitment-crm-vs-ats" element={<ComparisonRecruitmentCrmVsAtsPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route path="/login" element={<Login />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route path="/invite/accept" element={<InviteAcceptPage />} />
          <Route path="/app/*" element={<Navigate to="/login" replace />} />
          <Route path="*" element={<PublicNotFoundPage />} />
        </>
      )}

      {me && (
        <>
          <Route path="/login" element={<AuthedDefaultAppNavigate />} />
          <Route path="/signup" element={<SignupRedirectForAuthed />} />
          <Route path="/app" element={<AppShell me={me} navItems={navItems} onLogout={logout} />}>
            <Route index element={<AppShellIndexNavigate />} />
            <Route path="onboarding/company" element={<OnboardingCompanyPage />} />
            <Route path="onboarding/getting-started" element={<OnboardingGettingStartedPage />} />
            {APP_ROUTES.map(({ key, path, Component, permission }) => (
              <Route
                key={key}
                path={path}
                element={
                  <RoutePermissionGuard permission={permission}>
                    <LazyRoute loadingLabel={t('common.loading')}>
                      <Component />
                    </LazyRoute>
                  </RoutePermissionGuard>
                }
              />
            ))}
          </Route>
          <Route path="/" element={<AuthedDefaultAppNavigate />} />
          <Route path="*" element={<AuthedDefaultAppNavigate />} />
        </>
      )}
    </Routes>
  )
}
