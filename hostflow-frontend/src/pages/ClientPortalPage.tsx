import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getClientPortalByToken, type ClientPortalData } from '../api/tenantLinks'
import { useI18n } from '../i18n'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import { useRobotsMeta } from '../hooks/useRobotsMeta'

export default function ClientPortalPage() {
  useRobotsMeta({ index: false, follow: false })
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const { t } = useI18n()
  const [data, setData] = useState<ClientPortalData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [retryKey, setRetryKey] = useState(0)

  useEffect(() => {
    if (!token.trim()) {
      setError(t('app.client_portal.errors.missing_token', { defaultValue: 'Отсутствует ссылка.' }))
      setLoading(false)
      return
    }
    let cancelled = false
    getClientPortalByToken(token)
      .then((d) => {
        if (!cancelled) setData(d)
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? (e as Error)?.message ?? 'Error'
          setError(typeof msg === 'string' ? msg : 'Error')
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [token, t, retryKey])

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <p className="text-slate-500">{t('common.loading', { defaultValue: 'Загрузка...' })}</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
        <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <ErrorRecoveryBanner
            info={{
              title: error,
              hint: t('app.client_portal.errors.bad_link', { defaultValue: 'Ссылка недействительна или истекла.' }),
            }}
            onRetry={() => setRetryKey((prev) => prev + 1)}
            retryLabel={t('common.actions.retry', { defaultValue: 'Retry' })}
            compact
          />
        </div>
      </div>
    )
  }

  const name = data?.company_name ?? t('app.client_portal.title', { defaultValue: 'Портал клиента' })
  const candidates = data?.candidates ?? []

  return (
    <div className="min-h-screen bg-slate-50 py-8">
      <div className="mx-auto max-w-2xl px-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h1 className="text-xl font-semibold text-slate-900">{name}</h1>
          <p className="mt-1 text-sm text-slate-500">
            {t('app.client_portal.subtitle', { defaultValue: 'Переданные кандидаты (только просмотр).' })}
          </p>
          {candidates.length === 0 ? (
            <p className="mt-6 text-sm text-slate-500">
              {t('app.client_portal.empty', { defaultValue: 'Нет переданных кандидатов.' })}
            </p>
          ) : (
            <ul className="mt-6 space-y-3">
              {candidates.map((c) => (
                <li
                  key={c.id}
                  className="rounded-xl border border-slate-100 bg-slate-50/50 p-4"
                >
                  <div className="font-medium text-slate-900">
                    {[c.first_name, c.last_name].filter(Boolean).join(' ') || c.short_id || c.id}
                  </div>
                  {(c.stage || c.status) && (
                    <div className="mt-1 text-sm text-slate-500">
                      {c.stage ?? c.status}
                    </div>
                  )}
                  {(c.email || c.phone) && (
                    <div className="mt-1 text-sm text-slate-600">
                      {c.email}
                      {c.email && c.phone ? ' · ' : ''}
                      {c.phone}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
