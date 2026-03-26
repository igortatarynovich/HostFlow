import { useCallback, useEffect, useState } from 'react'
import { listOwnCompanies, ownCompanySettings, OWN_COMPANY_STORAGE_KEY } from '../api/client'
import { useAuth } from '../store/useAuth'

/**
 * Resolved display name for the active own-company (legal entity scope), for list headers.
 */
export function useActiveOwnCompanyLabel(): { label: string | null; loading: boolean } {
  const { me } = useAuth()
  const [label, setLabel] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const refresh = useCallback(async () => {
    if (!me?.tenant_id) {
      setLabel(null)
      return
    }
    setLoading(true)
    try {
      const data = await listOwnCompanies()
      const items = Array.isArray((data as any)?.items) ? (data as any).items : []
      const active =
        String((data as any)?.active_own_company_id || '').trim() ||
        String(ownCompanySettings.get() || '').trim()
      const hit = items.find((x: { id?: string }) => String(x?.id || '') === active)
      const name = hit
        ? String(hit.name || hit.legal_name || hit.id || '').trim() || null
        : null
      setLabel(name)
    } catch {
      setLabel(null)
    } finally {
      setLoading(false)
    }
  }, [me?.tenant_id])

  useEffect(() => {
    void refresh()
  }, [refresh])

  useEffect(() => {
    const onCustom = () => {
      void refresh()
    }
    const onStorage = (e: StorageEvent) => {
      if (e.key === OWN_COMPANY_STORAGE_KEY) void refresh()
    }
    window.addEventListener('hf:own-company-changed', onCustom)
    window.addEventListener('storage', onStorage)
    return () => {
      window.removeEventListener('hf:own-company-changed', onCustom)
      window.removeEventListener('storage', onStorage)
    }
  }, [refresh])

  return { label, loading }
}
