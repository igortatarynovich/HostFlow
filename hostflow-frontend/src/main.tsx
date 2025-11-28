import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { AuthProvider } from './store/auth'
import { I18nProvider } from './i18n'
import { ToastProvider } from './components/Toast'

import './styles/components.css'
import './index.css'

const hash = window.location.hash || ''
if (hash.startsWith('#/')) {
  const target = `/app${hash.slice(1)}`
  if (window.location.pathname + window.location.search !== target) {
    window.location.replace(target)
  }
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <I18nProvider>
        <AuthProvider>
          <ToastProvider>
            <App />
          </ToastProvider>
        </AuthProvider>
      </I18nProvider>
    </BrowserRouter>
  </StrictMode>
)
