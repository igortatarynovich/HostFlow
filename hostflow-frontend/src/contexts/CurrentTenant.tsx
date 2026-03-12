import { createContext, useContext, type PropsWithChildren } from 'react'

/** Current workspace tenant id (from getCurrentTenant / header). Use for list/analytics so X-Tenant-Id matches displayed workspace. */
const CurrentTenantContext = createContext<string | null>(null)

export function CurrentTenantProvider({ value, children }: PropsWithChildren<{ value: string | null }>) {
  return (
    <CurrentTenantContext.Provider value={value}>
      {children}
    </CurrentTenantContext.Provider>
  )
}

export function useCurrentTenantId(): string | null {
  return useContext(CurrentTenantContext)
}
