import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'

/**
 * ToastProvider — lightweight top-of-screen notification stack.
 *
 * UX contract (docs/specs/ux/error_handling.md):
 *   - success  → green card, auto-dismiss after TOAST_DEFAULT_TTL_MS
 *   - info     → neutral card, auto-dismiss after TOAST_DEFAULT_TTL_MS
 *   - warning  → amber card, auto-dismiss after TOAST_DEFAULT_TTL_MS
 *   - error    → red card, auto-dismiss after TOAST_ERROR_TTL_MS (longer so users can read)
 *
 * Call `notify()` directly for hand-crafted toasts, or use the helpers from
 * `utils/toastFromError` to render a consistent API-error toast.
 */

type ToastVariant = 'info' | 'success' | 'error' | 'warning'

const TOAST_DEFAULT_TTL_MS = 4000
const TOAST_ERROR_TTL_MS = 7000

export type ToastMessage = {
  id: string
  title: string
  description?: ReactNode
  variant?: ToastVariant
  /**
   * Optional action button rendered next to the title. Clicking it dismisses
   * the toast and fires `onClick`. Use sparingly — primarily for "Retry" or
   * "Open Billing" CTAs on error toasts.
   */
  action?: {
    label: string
    onClick: () => void
  }
  /**
   * Auto-dismiss timeout in ms. Set to 0 to keep the toast visible until the
   * user closes it manually. If omitted, defaults to 4s (7s for errors).
   */
  ttlMs?: number
}

type ToastInput = Omit<ToastMessage, 'id'>

type ToastContextValue = {
  notify: (message: ToastInput) => string
  dismiss: (id: string) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

function defaultTtlFor(variant: ToastVariant | undefined): number {
  return variant === 'error' ? TOAST_ERROR_TTL_MS : TOAST_DEFAULT_TTL_MS
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([])
  const timersRef = useRef<Map<string, number>>(new Map())

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id))
    const timer = timersRef.current.get(id)
    if (timer !== undefined) {
      window.clearTimeout(timer)
      timersRef.current.delete(id)
    }
  }, [])

  const notify = useCallback(
    (message: ToastInput) => {
      const id = crypto.randomUUID()
      const variant = message.variant ?? 'info'
      const ttl = message.ttlMs ?? defaultTtlFor(variant)
      setToasts((prev) => [...prev, { ...message, id, variant }])
      if (ttl > 0) {
        const timer = window.setTimeout(() => dismiss(id), ttl)
        timersRef.current.set(id, timer)
      }
      return id
    },
    [dismiss],
  )

  const value = useMemo(() => ({ notify, dismiss }), [notify, dismiss])

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 top-4 z-[1000] flex flex-col items-center gap-2 px-4">
        {toasts.map((toast) => {
          const variantClasses =
            toast.variant === 'success'
              ? 'border-green-200 bg-green-50/95 text-green-900'
              : toast.variant === 'error'
                ? 'border-red-200 bg-red-50/95 text-red-900'
                : toast.variant === 'warning'
                  ? 'border-amber-200 bg-amber-50/95 text-amber-900'
                  : 'border-slate-200 bg-white/95 text-slate-900'
          const actionClasses =
            toast.variant === 'error'
              ? 'border-red-300 text-red-800 hover:bg-red-100'
              : toast.variant === 'warning'
                ? 'border-amber-300 text-amber-800 hover:bg-amber-100'
                : toast.variant === 'success'
                  ? 'border-green-300 text-green-800 hover:bg-green-100'
                  : 'border-slate-300 text-slate-800 hover:bg-slate-100'
          return (
            <div
              key={toast.id}
              role="status"
              aria-live={toast.variant === 'error' ? 'assertive' : 'polite'}
              className={[
                'pointer-events-auto w-full max-w-md rounded-2xl border px-4 py-3 shadow-lg transition',
                variantClasses,
              ].join(' ')}
            >
              <div className="flex items-start gap-3">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold">{toast.title}</p>
                  {toast.description && (
                    <div className="mt-0.5 text-xs opacity-90">{toast.description}</div>
                  )}
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  {toast.action && (
                    <button
                      type="button"
                      className={[
                        'rounded-md border bg-white px-2 py-1 text-xs font-medium',
                        actionClasses,
                      ].join(' ')}
                      onClick={() => {
                        try {
                          toast.action?.onClick()
                        } finally {
                          dismiss(toast.id)
                        }
                      }}
                    >
                      {toast.action.label}
                    </button>
                  )}
                  <button
                    type="button"
                    aria-label="Dismiss"
                    className="rounded-md px-1 py-0.5 text-xs opacity-60 hover:opacity-100"
                    onClick={() => dismiss(toast.id)}
                  >
                    ×
                  </button>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext)
  if (!ctx) {
    throw new Error('useToast must be used within ToastProvider')
  }
  return ctx
}
