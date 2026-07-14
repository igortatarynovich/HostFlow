import { useCallback, useEffect, useState } from 'react'
import { getVacancy } from '../../../api/vacancies'
import {
  getCandidateProfile,
  listCandidateProfiles,
  type CandidateProfile,
} from '../../../api/candidate_profiles'

const DEFAULT_PROFILE_CODE = 'driver_ce_default'

export function useCandidateEntityWorkspaceProfile(vacancyId: string | null | undefined) {
  const [candidateProfile, setCandidateProfile] = useState<CandidateProfile | null>(null)
  const [profileLoading, setProfileLoading] = useState(false)

  const loadDefaultProfile = useCallback(async () => {
    try {
      const profiles = await listCandidateProfiles()
      return profiles.find((p) => p.code === DEFAULT_PROFILE_CODE) ?? null
    } catch {
      return null
    }
  }, [])

  useEffect(() => {
    if (!vacancyId) {
      setCandidateProfile(null)
      return
    }

    let cancelled = false
    setProfileLoading(true)

    void (async () => {
      try {
        let vacancy: { candidate_profile_id?: string | null } | null = null
        try {
          vacancy = await getVacancy(vacancyId)
        } catch (err: unknown) {
          const status = Number((err as { response?: { status?: number } })?.response?.status || 0)
          if (status === 404 || status === 403) {
            const fallback = await loadDefaultProfile()
            if (!cancelled) setCandidateProfile(fallback)
            return
          }
          throw err
        }

        if (!vacancy?.candidate_profile_id) {
          const fallback = await loadDefaultProfile()
          if (!cancelled) setCandidateProfile(fallback)
          return
        }

        try {
          const profile = await getCandidateProfile(vacancy.candidate_profile_id)
          if (!cancelled) setCandidateProfile(profile)
        } catch {
          const fallback = await loadDefaultProfile()
          if (!cancelled) setCandidateProfile(fallback)
        }
      } catch {
        if (!cancelled) setCandidateProfile(null)
      } finally {
        if (!cancelled) setProfileLoading(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [loadDefaultProfile, vacancyId])

  return { candidateProfile, profileLoading }
}
