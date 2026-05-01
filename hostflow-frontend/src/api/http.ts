// src/api/http.ts
import axios from 'axios'
import { resolveApiBase, DEFAULT_TENANT } from './client'

// Приоритеты источников базового URL: Vite env → window.__API_BASE__ → локальный дефолт
const API_BASE: string = resolveApiBase()

// Определение tenant_id: localStorage → Vite env → дефолт
function resolveTenantId(): string {
  try {
    const fromLs =
      localStorage.getItem('tenant_id') ||
      localStorage.getItem('X-Tenant-Id') ||
      localStorage.getItem('tenant') ||
      ''
    if (fromLs) return fromLs
  } catch {}
  const fromEnv =
    (import.meta as any)?.env?.VITE_TENANT_ID ||
    DEFAULT_TENANT
  return fromEnv
}

let TENANT_ID = resolveTenantId()

/**
 * Пытаемся достать access_token:
 * 1) из cookie (основной вариант, axios с withCredentials сам отправит куку);
 * 2) если кука httpOnly и JS её не видит — используем localStorage как запасной вариант.
 */
function getAccessToken(): string | null {
  // 1) Попробуем localStorage — разные возможные ключи
  const lsKeys = ['access_token', 'token', 'auth_token', 'jwt', 'Authorization']
  for (const k of lsKeys) {
    try {
      const raw = localStorage.getItem(k)
      if (raw) {
        // убираем возможный префикс "Bearer "
        const val = raw.replace(/^Bearer\s+/i, '')
        if (val) return val
      }
    } catch {}
  }

  // 2) Куки — поддержим несколько популярных имен
  const cookieMatch =
    document.cookie.match(/(?:^|; )access_token=([^;]+)/) ||
    document.cookie.match(/(?:^|; )token=([^;]+)/) ||
    document.cookie.match(/(?:^|; )auth_token=([^;]+)/)
  if (cookieMatch) return decodeURIComponent(cookieMatch[1])

  return null
}

// Экспортируем вспомогалки для явной смены арендатора / токена при необходимости
export function setTenantId(id: string) {
  TENANT_ID = id
  try {
    localStorage.setItem('tenant_id', id)
    localStorage.setItem('X-Tenant-Id', id)
    localStorage.setItem('x-tenant-id', id)
  } catch {}
}

export const http = axios.create({
  baseURL: API_BASE,
  withCredentials: true, // отправляем cookie
  headers: {
    'X-Tenant-Id': TENANT_ID,
    'Accept': 'application/json',
  },
  timeout: 20000,
})

// Подставляем Authorization и актуальный X-Tenant-Id на каждый запрос (cookie >> localStorage)
http.interceptors.request.use((config) => {
  const token = getAccessToken()
  config.headers = config.headers ?? {}

  // Critical: let browser set correct boundary for FormData
  if (config.data instanceof FormData) {
    delete (config.headers as any)['Content-Type']
  }

  if (token) {
    (config.headers as any)['Authorization'] = `Bearer ${token}`
  } else {
    // не шлём пустой Authorization, чтобы не мешать куке
    delete (config.headers as any)['Authorization']
  }

  // читаем tenant из localStorage на каждый запрос (смена workspace без перезагрузки)
  ;(config.headers as any)['X-Tenant-Id'] = resolveTenantId()

  return config
})

// На 401 уведомляем приложение (например, для редиректа на логин)
http.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err?.response?.status === 401) {
      try { window.dispatchEvent(new CustomEvent('auth:unauthorized')) } catch {}
    }
    return Promise.reject(err)
  }
)

export default http
