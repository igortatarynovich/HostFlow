import type { ReactNode } from 'react'
import * as Sentry from '@sentry/react'
import { IconAlertTriangle, IconRefresh } from '@tabler/icons-react'
import { useI18n } from '../i18n'

/**
 * SectionErrorBoundary — mid-granularity error boundary for dashboard widgets,
 * side panels, modals and tab contents.
 *
 * Why a separate boundary?
 *   - `AppErrorBoundary` covers the whole app and is intentionally minimal; any
 *     error there swaps the entire UI for the "Something went wrong" screen.
 *   - For recoverable areas (a dashboard card, a details tab, a drawer), we
 *     want to keep the rest of the page alive and show a small inline fallback.
 *
 * Behaviour:
 *   - Catches errors thrown during render of children.
 *   - Reports to Sentry with tag `boundary.scope = section` plus an optional
 *     `boundary.section` tag (pass `sectionTag`).
 *   - Renders a compact banner with Retry (calls `resetError()` from Sentry).
 *   - Accepts a custom `fallback` if the default look does not fit.
 *
 * This boundary must be rendered BELOW a valid `AppErrorBoundary` at the root.
 */
export function SectionErrorBoundary({
  children,
  sectionTag,
  fallback,
  title,
  hint,
}: {
  children: ReactNode
  /** Free-form tag attached to Sentry events for faster filtering. */
  sectionTag?: string
  fallback?: Sentry.ErrorBoundaryProps['fallback']
  title?: string
  hint?: string
}) {
  return (
    <Sentry.ErrorBoundary
      beforeCapture={(scope) => {
        scope.setTag('boundary.scope', 'section')
        if (sectionTag) scope.setTag('boundary.section', sectionTag)
      }}
      fallback={
        fallback ??
        (({ resetError }) => <SectionFallback title={title} hint={hint} onRetry={resetError} />)
      }
    >
      {children}
    </Sentry.ErrorBoundary>
  )
}

function SectionFallback({
  title,
  hint,
  onRetry,
}: {
  title?: string
  hint?: string
  onRetry: () => void
}) {
  const { t } = useI18n()
  const resolvedTitle =
    title ??
    t('app.errors.section_title', { defaultValue: 'This section is temporarily unavailable' })
  const resolvedHint =
    hint ??
    t('app.errors.section_hint', {
      defaultValue: 'Refresh this section or try again later — the rest of the page still works.',
    })

  return (
    <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-rose-900">
      <div className="flex items-start gap-2">
        <IconAlertTriangle size={16} className="mt-0.5 shrink-0 text-rose-700" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold">{resolvedTitle}</p>
          <p className="mt-1 text-xs text-rose-800">{resolvedHint}</p>
          <div className="mt-3">
            <button
              type="button"
              onClick={onRetry}
              className="inline-flex items-center gap-1 rounded-md border border-rose-300 bg-white px-2.5 py-1 text-xs text-rose-800 hover:bg-rose-100"
            >
              <IconRefresh size={12} />
              {t('common.try_again', { defaultValue: 'Try again' })}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SectionErrorBoundary
