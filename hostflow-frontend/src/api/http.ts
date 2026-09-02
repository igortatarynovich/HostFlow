// src/api/http.ts — thin wrapper over the canonical api client storage helpers.
import axios from 'axios'
import { getStoredAccessToken, resolveApiBase, settings } from './client'

const API_BASE: string = resolveApiBase()

export function setTenantId(id: string) {
  settings.set(id)
}

export const http = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
  headers: {
    Accept: 'application/json',
  },
  timeout: 20000,
})

function isAnonymousPublicIntakePath(url?: string): boolean {
  const path = String(url || '')
  return (
    path.includes('/public/apply/') ||
    path.includes('/public/status/') ||
    path.includes('/public/magic-link/')
  )
}

http.interceptors.request.use((config) => {
  config.headers = config.headers ?? {}

  // Critical: let browser set correct boundary for FormData
  if (config.data instanceof FormData) {
    delete (config.headers as any)['Content-Type']
  }

  // Public apply/status must not inherit the operator CRM session: leftover
  // X-Tenant-Id / Bearer can bind the wrong RLS tenant and 404 submit.
  if (isAnonymousPublicIntakePath(config.url)) {
    delete (config.headers as any)['Authorization']
    delete (config.headers as any)['X-Tenant-Id']
    config.withCredentials = false
    return config
  }

  const token = getStoredAccessToken()
  if (token) {
    ;(config.headers as any)['Authorization'] = `Bearer ${token}`
  } else {
    delete (config.headers as any)['Authorization']
  }

  ;(config.headers as any)['X-Tenant-Id'] = settings.get()

  return config
})

http.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err?.response?.status === 401) {
      try {
        window.dispatchEvent(new CustomEvent('auth:unauthorized'))
      } catch {}
    }
    return Promise.reject(err)
  },
)

export default http
