import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'

type ToastVariant = 'info' | 'success' | 'error'

export type ToastMessage = {
  id: string
  title: string
  description?: string
  variant?: ToastVariant
}

type ToastContextValue = {
  notify: (message: Omit<ToastMessage, 'id'>) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([])

  const notify = useCallback((message: Omit<ToastMessage, 'id'>) => {
    const id = crypto.randomUUID()
    setToasts((prev) => [...prev, { ...message, id }])
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((toast) => toast.id !== id))
    }, 4000)
  }, [])

  const value = useMemo(() => ({ notify }), [notify])

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 top-4 z-[1000] flex flex-col items-center gap-2 px-4">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={[
              'w-full max-w-md rounded-2xl border px-4 py-3 shadow-lg transition',
              toast.variant === 'success'
                ? 'border-green-200 bg-green-50/90 text-green-900'
                : toast.variant === 'error'
                  ? 'border-red-200 bg-red-50/90 text-red-900'
                  : 'border-slate-200 bg-white/90 text-slate-900',
            ].join(' ')}
          >
            <p className="text-sm font-semibold">{toast.title}</p>
            {toast.description && <p className="text-xs text-slate-600">{toast.description}</p>}
          </div>
        ))}
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
