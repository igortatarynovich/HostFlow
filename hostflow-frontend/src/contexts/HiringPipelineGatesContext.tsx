import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { getHiringPipelineGates } from '../api/tenants'
import type { HiringPipelineGatesPublic } from '../api/types'

type Ctx = {
  gates: HiringPipelineGatesPublic | null
  loading: boolean
  refetch: () => Promise<void>
}

const HiringPipelineGatesContext = createContext<Ctx>({
  gates: null,
  loading: true,
  refetch: async () => {},
})

export function HiringPipelineGatesProvider({
  tenantId,
  children,
}: {
  tenantId: string | null
  children: ReactNode
}) {
  const [gates, setGates] = useState<HiringPipelineGatesPublic | null>(null)
  const [loading, setLoading] = useState(true)

  const refetch = useCallback(async () => {
    if (!tenantId) {
      setGates(null)
      setLoading(false)
      return
    }
    setLoading(true)
    try {
      const g = await getHiringPipelineGates({ tenantId })
      setGates(g)
    } catch {
      setGates(null)
    } finally {
      setLoading(false)
    }
  }, [tenantId])

  useEffect(() => {
    void refetch()
  }, [refetch])

  const value = useMemo(() => ({ gates, loading, refetch }), [gates, loading, refetch])

  return <HiringPipelineGatesContext.Provider value={value}>{children}</HiringPipelineGatesContext.Provider>
}

export function useHiringPipelineGates() {
  return useContext(HiringPipelineGatesContext)
}
