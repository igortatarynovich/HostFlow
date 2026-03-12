import { useCallback, useEffect, useRef, useState } from 'react'
import type { PublicStatusState } from '../../api/publicIntake'
import { getPublicStatus } from '../../api/publicIntake'
import { useI18n } from '../../i18n'

export type PublicStatusHook = {
  loading: boolean
  error: string | null
  state: PublicStatusState | null
  refreshing: boolean
  refresh: () => Promise<void>
}

// Интервал автообновления (30 секунд)
const AUTO_REFRESH_INTERVAL_MS = 30000

// Проверка видимости страницы
function isPageVisible(): boolean {
  if (typeof document === 'undefined') return true
  return !document.hidden
}

export function usePublicStatus(token?: string): PublicStatusHook {
  const { t } = useI18n()
  const [state, setState] = useState<PublicStatusState | null>(null)
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const intervalRef = useRef<number | null>(null)
  const lastRefreshRef = useRef<number>(0)

  const refresh = useCallback(async () => {
    if (!token) return
    const now = Date.now()
    // Предотвращаем слишком частые запросы (минимум 2 секунды между запросами)
    if (now - lastRefreshRef.current < 2000) return
    
    lastRefreshRef.current = now
    setRefreshing(true)
    setError(null)
    try {
      const data = await getPublicStatus(token)
      setState(data)
    } catch (err: any) {
      const errorMessage = err?.response?.data?.detail || err?.message || t('public.status_page.errors.load')
      setError(errorMessage)
      // Не сбрасываем state при ошибке, чтобы пользователь видел последние данные
    } finally {
      setRefreshing(false)
    }
  }, [token, t])

  // Первоначальная загрузка
  useEffect(() => {
    if (!token) return
    setLoading(true)
    refresh().finally(() => setLoading(false))
  }, [token, refresh])

  // Автообновление при видимости страницы
  useEffect(() => {
    if (!token) return

    const startPolling = () => {
      if (intervalRef.current) return // Уже запущено
      
      intervalRef.current = window.setInterval(() => {
        if (isPageVisible()) {
          refresh()
        }
      }, AUTO_REFRESH_INTERVAL_MS)
    }

    const stopPolling = () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }

    // Запускаем polling при видимости страницы
    if (isPageVisible()) {
      startPolling()
    }

    // Обработка изменения видимости страницы
    const handleVisibilityChange = () => {
      if (isPageVisible()) {
        startPolling()
        // Обновляем сразу при возвращении на страницу
        refresh()
      } else {
        stopPolling()
      }
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      stopPolling()
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [token, refresh])

  return {
    loading,
    error,
    state,
    refreshing,
    refresh,
  }
}
