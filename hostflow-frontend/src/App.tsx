import { Suspense, lazy, useMemo } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './store/useAuth'
import Login from './pages/Login'
import { AppShell } from './app/AppShell'
import { WorkAreaLayout } from './app/WorkAreaLayout'
import { WorkPathAliasRedirect } from './app/WorkPathAliasRedirect'
import {
  CommunicationsCalendarPage,
  HrComplianceDocumentsPage,
  HrDashboardPage,
  HrDocumentsHubPage,
  HrEmployeeDetailPage,
  HrEmployeesPage,
  HrHandoffDetailPage,
  HrInboxPage,
  HrTasksPage,
  HrWorkspaceLayout,
  HrZusWorkspacePage,
  RemindersPage,
} from './app/appRoutePages'
import WorkOrganizerPage from './pages/WorkOrganizerPage'
import CommunicationsFeatureGate from './components/communications/CommunicationsFeatureGate'
import { ACTIVATION_PATHS } from './app/activationRoutes'
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
import SetupHubPage from './pages/SetupHubPage'
import LaunchpadPage from './pages/LaunchpadPage'
import PlatformSetupPage from './pages/platform/PlatformSetupPage'
import SetupFirstClientPage from './pages/setup/SetupFirstClientPage'
import SetupFirstVacancyPage from './pages/setup/SetupFirstVacancyPage'
import SetupProcessDefaultsPage from './pages/setup/SetupProcessDefaultsPage'
import SetupCandidateIntakePage from './pages/setup/SetupCandidateIntakePage'
import CreateSearchWizardPage from './pages/recruitment/CreateSearchWizardPage'
import SearchHomePage from './pages/recruitment/SearchHomePage'
import SearchWorkspaceLayout from './pages/recruitment/SearchWorkspaceLayout'
import AcquisitionLayout from './pages/recruitment/AcquisitionLayout'
import AcquisitionActivitiesPage from './pages/recruitment/AcquisitionActivitiesPage'
import AcquisitionAudiencePage from './pages/recruitment/AcquisitionAudiencePage'
import AcquisitionJournalPage from './pages/recruitment/AcquisitionJournalPage'
import LaunchAcquisitionPage from './pages/recruitment/LaunchAcquisitionPage'
import SearchMetaSourcePage from './pages/recruitment/SearchMetaSourcePage'
import SearchesListPage from './pages/recruitment/SearchesListPage'
import CreateClientChannelWizardPage from './pages/client-acquisition/CreateClientChannelWizardPage'
import ClientChannelsListPage from './pages/client-acquisition/ClientChannelsListPage'
import ClientChannelWorkspaceLayout from './pages/client-acquisition/ClientChannelWorkspaceLayout'
import ClientChannelHomePage from './pages/client-acquisition/ClientChannelHomePage'
import ClientInquiryWorkPage from './pages/client-acquisition/ClientInquiryWorkPage'
import SalesInquiriesEntryPage from './pages/sales/SalesInquiriesEntryPage'
import SalesWorkspaceLayout from './pages/sales/SalesWorkspaceLayout'
import RecruitmentInboxEntryPage from './pages/recruitment/RecruitmentInboxEntryPage'
import SignupPage from './pages/SignupPage'
import { useI18n } from './i18n'
import {
  readSignupSuccessContextFromSessionStorage,
  signupContextToSearchParams,
} from './constants/signupContext'
import { DefaultAppEntryNavigate } from './components/nav/DefaultAppEntryNavigate'
import { CRM_APP_PATHS } from './app/crmAppPaths'

const PublicApplyPage = lazy(() => import('./pages/public/PublicApplyPage'))
const PublicIntakeNew = lazy(() => import('./pages/public/PublicIntakeNew'))
const CompanyIntakePage = lazy(() => import('./pages/public/CompanyIntakePage'))
const ClientInquiryLandingPage = lazy(() => import('./pages/public/ClientInquiryLandingPage'))
const ClientInquiryFormPage = lazy(() => import('./pages/public/ClientInquiryFormPage'))
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
    return <Navigate to={`${ACTIVATION_PATHS.platformSetup}?${params.toString()}`} replace />
  }
  return <Navigate to={ACTIVATION_PATHS.overview} replace />
}

function AuthedDefaultAppNavigate() {
  const { can } = usePermissions()
  return <DefaultAppEntryNavigate mode="href" canOpenTasks={can('notifications.view')} />
}

function AppShellIndexNavigate() {
  const { can } = usePermissions()
  return <DefaultAppEntryNavigate mode="segment" canOpenTasks={can('notifications.view')} />
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
        if (!item.permission) return true
        const perms = Array.isArray(item.permission) ? item.permission : [item.permission]
        return perms.some((p) => can(p))
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
      <Route path="/forms/company-intake/:publicToken" element={<LazyRoute loadingLabel={t('common.loading')}><CompanyIntakePage /></LazyRoute>} />
      <Route path="/forms/client-inquiry/:publicToken" element={<LazyRoute loadingLabel={t('common.loading')}><ClientInquiryLandingPage /></LazyRoute>} />
      <Route path="/forms/client-inquiry/:publicToken/apply" element={<LazyRoute loadingLabel={t('common.loading')}><ClientInquiryFormPage /></LazyRoute>} />
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
          <Route path={`${CRM_APP_PATHS.appShellPrefix}/*`} element={<Navigate to="/login" replace />} />
          <Route path="*" element={<PublicNotFoundPage />} />
        </>
      )}

      {me && (
        <>
          <Route path="/login" element={<AuthedDefaultAppNavigate />} />
          <Route path="/signup" element={<SignupRedirectForAuthed />} />
          <Route path={CRM_APP_PATHS.appShellPrefix} element={<AppShell me={me} navItems={navItems} onLogout={logout} />}>
            <Route index element={<AppShellIndexNavigate />} />
            <Route path="launchpad" element={<LaunchpadPage />} />
            <Route path="platform/setup" element={<PlatformSetupPage />} />
            <Route path="setup" element={<SetupHubPage />} />
            <Route path="setup/client" element={<SetupFirstClientPage />} />
            <Route path="setup/vacancy" element={<SetupFirstVacancyPage />} />
            <Route path="setup/process" element={<SetupProcessDefaultsPage />} />
            <Route path="setup/intake" element={<SetupCandidateIntakePage />} />
            <Route path="recruitment/searches" element={<SearchesListPage />} />
            <Route path="recruitment/searches/new" element={<CreateSearchWizardPage />} />
            <Route path="recruitment/searches/:searchId" element={<SearchWorkspaceLayout />}>
              <Route index element={<SearchHomePage />} />
              <Route path="acquisition" element={<AcquisitionLayout />}>
                <Route index element={<Navigate to="activities" replace />} />
                <Route path="activities" element={<AcquisitionActivitiesPage />} />
                <Route path="audience" element={<AcquisitionAudiencePage />} />
                <Route path="journal" element={<AcquisitionJournalPage />} />
                <Route path="analytics" element={<Navigate to="../journal" replace />} />
              </Route>
              <Route path="acquisition/new" element={<LaunchAcquisitionPage />} />
              <Route path="acquisition/meta" element={<SearchMetaSourcePage />} />
              <Route path="sources" element={<Navigate to="acquisition" replace />} />
              <Route path="sources/meta" element={<Navigate to="../acquisition/meta" replace />} />
            </Route>
            <Route path="sales" element={<SalesWorkspaceLayout />}>
              <Route index element={<SalesInquiriesEntryPage />} />
              <Route path="inquiries/:leadId" element={<SalesInquiriesEntryPage />} />
            </Route>
            <Route path="recruitment/inbox" element={<RecruitmentInboxEntryPage />} />
            <Route path="recruitment/inbox/:applicationId" element={<RecruitmentInboxEntryPage />} />
            <Route path="client-acquisition/channels" element={<ClientChannelsListPage />} />
            <Route path="client-acquisition/channels/new" element={<CreateClientChannelWizardPage />} />
            <Route path="client-acquisition/channels/:channelId" element={<ClientChannelWorkspaceLayout />}>
              <Route index element={<ClientChannelHomePage />} />
              <Route path="inquiries/:leadId" element={<ClientInquiryWorkPage />} />
            </Route>
            <Route path="onboarding/company" element={<Navigate to={CRM_APP_PATHS.platformSetup} replace />} />
            <Route path="onboarding/wizard" element={<Navigate to={CRM_APP_PATHS.setup} replace />} />
            <Route path="onboarding/getting-started" element={<Navigate to={CRM_APP_PATHS.setup} replace />} />
            <Route path="work" element={<WorkAreaLayout />}>
              <Route
                index
                element={
                  <RoutePermissionGuard>
                    <LazyRoute loadingLabel={t('common.loading')}>
                      <WorkOrganizerPage />
                    </LazyRoute>
                  </RoutePermissionGuard>
                }
              />
              <Route
                path="tasks"
                element={
                  <RoutePermissionGuard permission="notifications.view">
                    <LazyRoute loadingLabel={t('common.loading')}>
                      <RemindersPage />
                    </LazyRoute>
                  </RoutePermissionGuard>
                }
              />
              <Route
                path="calendar"
                element={
                  <RoutePermissionGuard permission="notifications.view">
                    <LazyRoute loadingLabel={t('common.loading')}>
                      <CommunicationsFeatureGate feature="calendar" fallbackPath={CRM_APP_PATHS.work}>
                        <CommunicationsCalendarPage />
                      </CommunicationsFeatureGate>
                    </LazyRoute>
                  </RoutePermissionGuard>
                }
              />
              <Route path="*" element={<WorkPathAliasRedirect />} />
            </Route>
            <Route
              path="hr"
              element={
                <RoutePermissionGuard permission="workforce.view">
                  <LazyRoute loadingLabel={t('common.loading')}>
                    <HrWorkspaceLayout />
                  </LazyRoute>
                </RoutePermissionGuard>
              }
            >
              <Route
                index
                element={
                  <LazyRoute loadingLabel={t('common.loading')}>
                    <HrDashboardPage />
                  </LazyRoute>
                }
              />
              <Route
                path="employees"
                element={
                  <LazyRoute loadingLabel={t('common.loading')}>
                    <HrEmployeesPage />
                  </LazyRoute>
                }
              />
              <Route
                path="employees/:employeeId"
                element={
                  <LazyRoute loadingLabel={t('common.loading')}>
                    <HrEmployeeDetailPage />
                  </LazyRoute>
                }
              />
              <Route
                path="inbox"
                element={
                  <LazyRoute loadingLabel={t('common.loading')}>
                    <HrInboxPage />
                  </LazyRoute>
                }
              />
              <Route
                path="tasks"
                element={
                  <LazyRoute loadingLabel={t('common.loading')}>
                    <HrTasksPage />
                  </LazyRoute>
                }
              />
              <Route
                path="compliance"
                element={
                  <LazyRoute loadingLabel={t('common.loading')}>
                    <HrComplianceDocumentsPage />
                  </LazyRoute>
                }
              />
              <Route
                path="documents"
                element={
                  <LazyRoute loadingLabel={t('common.loading')}>
                    <HrDocumentsHubPage />
                  </LazyRoute>
                }
              />
              <Route
                path="documents/missing"
                element={
                  <LazyRoute loadingLabel={t('common.loading')}>
                    <HrDocumentsHubPage />
                  </LazyRoute>
                }
              />
              <Route
                path="documents/expiring"
                element={
                  <LazyRoute loadingLabel={t('common.loading')}>
                    <HrDocumentsHubPage />
                  </LazyRoute>
                }
              />
              <Route
                path="documents/verification"
                element={
                  <LazyRoute loadingLabel={t('common.loading')}>
                    <HrDocumentsHubPage />
                  </LazyRoute>
                }
              />
              <Route
                path="handoffs/:id"
                element={
                  <LazyRoute loadingLabel={t('common.loading')}>
                    <HrHandoffDetailPage />
                  </LazyRoute>
                }
              />
              <Route
                path="zus"
                element={
                  <Navigate to="../zus-workspace" replace />
                }
              />
              <Route
                path="zus-workspace"
                element={
                  <LazyRoute loadingLabel={t('common.loading')}>
                    <HrZusWorkspacePage />
                  </LazyRoute>
                }
              />
            </Route>
            {APP_ROUTES.filter(
              (r) => r.key !== 'work' && r.key !== 'work-tasks' && !r.key.startsWith('hr-'),
            ).map(({ key, path, Component, permission }) => (
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
