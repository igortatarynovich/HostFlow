import { useEffect, type ReactNode } from 'react'
import * as Sentry from '@sentry/react'
import { detectStoredLocale, lookupScopedTranslation } from '../i18n'
import { attemptStaleChunkReload } from '../utils/staleChunkReload'

/**
 * React error boundary that reports rendering errors to Sentry (when enabled)
 * and shows a clean, minimal fallback instead of the white screen of death.
 *
 * Wrap the entire app tree once in `main.tsx`:
 *
 *     <AppErrorBoundary>
 *       <App />
 *     </AppErrorBoundary>
 *
 * Keep the fallback dependency-free — it must render even if the app bundle
 * crashed during evaluation, so no app-level providers (i18n, theme, router)
 * can be assumed available. Static i18n lookup is OK (JSON bundles already loaded).
 */
export function AppErrorBoundary({
  children,
  fallback,
}: {
  children: ReactNode
  fallback?: Sentry.ErrorBoundaryProps['fallback']
}) {
  return (
    <Sentry.ErrorBoundary fallback={fallback ?? DefaultErrorFallback} showDialog={false}>
      {children}
    </Sentry.ErrorBoundary>
  )
}

function DefaultErrorFallback({ error, resetError }: { error?: unknown; resetError: () => void }) {
  useEffect(() => {
    attemptStaleChunkReload(error)
  }, [error])

  const locale = detectStoredLocale()
  const title =
    lookupScopedTranslation(locale, 'app.errors', 'boundary_title') || 'Something went wrong'
  const body =
    lookupScopedTranslation(locale, 'app.errors', 'boundary_body') ||
    'We already logged the error. Reload the page or try again — if it keeps happening, contact support.'
  const reloadLabel = lookupScopedTranslation(locale, 'common', 'reload_page') || 'Reload page'
  const tryAgainLabel = lookupScopedTranslation(locale, 'common', 'try_again') || 'Try again'

  return (
    <div
      role="alert"
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem',
        background: '#f6f8fa',
        color: '#0f172a',
        fontFamily: 'Inter, system-ui, sans-serif',
      }}
    >
      <div style={{ maxWidth: 480, textAlign: 'center' }}>
        <h1 style={{ fontSize: '1.5rem', marginBottom: '0.75rem' }}>{title}</h1>
        <p style={{ color: '#475569', marginBottom: '1.5rem' }}>{body}</p>
        <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center' }}>
          <button
            type="button"
            onClick={() => window.location.reload()}
            style={{
              padding: '0.5rem 1.25rem',
              borderRadius: 8,
              background: '#0f172a',
              color: '#fff',
              border: 'none',
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            {reloadLabel}
          </button>
          <button
            type="button"
            onClick={resetError}
            style={{
              padding: '0.5rem 1.25rem',
              borderRadius: 8,
              background: '#fff',
              color: '#0f172a',
              border: '1px solid #cbd5e1',
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            {tryAgainLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
