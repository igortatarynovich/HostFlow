import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { CRM_APP_PATHS } from './app/crmAppPaths'
import { AuthProvider } from './store/auth'
import { I18nProvider } from './i18n'
import { ToastProvider } from './components/Toast'
import { AppErrorBoundary } from './components/AppErrorBoundary'
import { PlanLimitModalProvider } from './contexts/PlanLimitModalContext'
import { installStaleChunkReloadRecovery } from './utils/staleChunkReload'
import { initSentry } from './lib/observability'

import './styles/components.css'
import './index.css'

initSentry()
installStaleChunkReloadRecovery()

const hash = window.location.hash || ''
if (hash.startsWith('#/')) {
  const target = `${CRM_APP_PATHS.appShellPrefix}${hash.slice(1)}`
  if (window.location.pathname + window.location.search !== target) {
    window.location.replace(target)
  }
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AppErrorBoundary>
      <BrowserRouter>
        <I18nProvider>
          <PlanLimitModalProvider>
            <AuthProvider>
              <ToastProvider>
                <App />
              </ToastProvider>
            </AuthProvider>
          </PlanLimitModalProvider>
        </I18nProvider>
      </BrowserRouter>
    </AppErrorBoundary>
  </StrictMode>
)
