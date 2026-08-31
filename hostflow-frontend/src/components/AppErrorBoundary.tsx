import { useEffect, type ReactNode } from 'react'
import * as Sentry from '@sentry/react'
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
 * can be assumed available.
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

const ERROR_BOUNDARY_COPY = {
  en: {
    title: 'Something went wrong',
    body: 'We recorded the error. Refresh the page or try again — if it keeps happening, contact support.',
    reload: 'Refresh page',
    retry: 'Try again',
  },
  ru: {
    title: 'Что-то пошло не так',
    body: 'Мы уже записали ошибку. Обновите страницу или попробуйте ещё раз — если проблема повторится, напишите в поддержку.',
    reload: 'Обновить страницу',
    retry: 'Попробовать ещё раз',
  },
  pl: {
    title: 'Coś poszło nie tak',
    body: 'Zapisaliśmy błąd. Odśwież stronę lub spróbuj ponownie — jeśli problem wróci, skontaktuj się z pomocą.',
    reload: 'Odśwież stronę',
    retry: 'Spróbuj ponownie',
  },
} as const

function errorBoundaryCopy() {
  if (typeof window === 'undefined') return ERROR_BOUNDARY_COPY.en
  const stored = window.localStorage.getItem('hf:ui:lang')
  if (stored === 'ru' || stored === 'pl' || stored === 'en') return ERROR_BOUNDARY_COPY[stored]
  return ERROR_BOUNDARY_COPY.en
}

function DefaultErrorFallback({ error, resetError }: { error?: unknown; resetError: () => void }) {
  const copy = errorBoundaryCopy()
  useEffect(() => {
    attemptStaleChunkReload(error)
  }, [error])

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
        <h1 style={{ fontSize: '1.5rem', marginBottom: '0.75rem' }}>{copy.title}</h1>
        <p style={{ color: '#475569', marginBottom: '1.5rem' }}>{copy.body}</p>
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
            {copy.reload}
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
            {copy.retry}
          </button>
        </div>
      </div>
    </div>
  )
}
