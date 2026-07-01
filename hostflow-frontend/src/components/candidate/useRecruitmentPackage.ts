import { useCallback, useEffect, useState } from 'react'
import { getCandidateRecruitmentPackage, type RecruitmentPackageReadiness } from '../../api/candidates'

export function useRecruitmentPackage(candidateId: string | null | undefined, refreshTrigger = 0) {
  const [pkg, setPkg] = useState<RecruitmentPackageReadiness | null>(null)
  const [loading, setLoading] = useState(false)

  const reload = useCallback(async () => {
    const id = String(candidateId || '').trim()
    if (!id) {
      setPkg(null)
      return
    }
    setLoading(true)
    try {
      const data = await getCandidateRecruitmentPackage(id)
      setPkg(data)
    } catch {
      setPkg(null)
    } finally {
      setLoading(false)
    }
  }, [candidateId])

  useEffect(() => {
    void reload()
  }, [reload, refreshTrigger])

  return { pkg, loading, reload }
}
