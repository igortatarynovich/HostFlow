import { createContext, useContext, type PropsWithChildren } from 'react'
import type { TenantRecord } from '../api/types'

/** Full current tenant record (including type). */
const TenantInfoContext = createContext<TenantRecord | null>(null)

export function TenantInfoProvider({
  tenant,
  children,
}: PropsWithChildren<{ tenant: TenantRecord | null }>) {
  return <TenantInfoContext.Provider value={tenant}>{children}</TenantInfoContext.Provider>
}

export function useTenantInfo(): TenantRecord | null {
  return useContext(TenantInfoContext)
}

