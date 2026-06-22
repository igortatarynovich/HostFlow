import { useCallback, useEffect, useRef, useState } from 'react'
import type {
  IntakeAgreements,
  IntakeContacts,
  IntakeData,
  IntakeEmployment,
  IntakeExperience,
  IntakePersonal,
  PublicIntakeState,
  PublicIntakeSubmitPayload,
} from '../../api/publicIntake'
import { getPublicIntake, submitPublicIntake, updatePublicIntake } from '../../api/publicIntake'
import { useI18n } from '../../i18n'

function formatApiError(err: any, fallback: string): string {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((item) => (typeof item === 'string' ? item : item?.msg || item?.message || JSON.stringify(item)))
      .join('; ')
  }
  if (detail && typeof detail === 'object') {
    return detail.msg || detail.message || JSON.stringify(detail)
  }
  return err?.message || fallback
}

const DRAFT_NAME = 'candidate draft'

const cleanFullName = (value?: string | null): string | null => {
  if (!value) return null
  const trimmed = value.trim()
  if (!trimmed) return null
  if (trimmed.toLowerCase() === DRAFT_NAME) return null
  return value
}

const EMPTY_DATA: IntakeData = {
  contacts: {},
  personal: { in_poland: null },
  experience: { trailer_types: [], route_types: [] },
  employments: [],
  agreements: { general: false, employer_share: false, terms_acceptance: false, cookies_accepted: false },
}

function cloneData(input?: IntakeData | null): IntakeData {
  if (!input) return { ...EMPTY_DATA, experience: { ...EMPTY_DATA.experience }, employments: [] }
  const lf = input.lead_form
  return {
    contacts: { ...(input.contacts ?? {}) },
    personal: {
      ...(input.personal ?? {}),
      full_name: cleanFullName(input.personal?.full_name),
    },
    experience: {
      years_ce: input.experience?.years_ce ?? null,
      intl_experience: input.experience?.intl_experience ?? null,
      trailer_types: [...(input.experience?.trailer_types ?? [])],
      route_types: [...(input.experience?.route_types ?? [])],
    },
    employments: [...(input.employments ?? [])],
    agreements: {
      general: Boolean(input.agreements?.general ?? input.agreements?.privacy),
      employer_share: Boolean(input.agreements?.employer_share ?? input.agreements?.contact),
      terms_acceptance: Boolean(input.agreements?.terms_acceptance),
      cookies_accepted: Boolean(input.agreements?.cookies_accepted),
    },
    client_company: input.client_company ? { ...input.client_company } : null,
    application_kind: input.application_kind ?? null,
    lead_form: lf && typeof lf === 'object' ? { ...(lf as Record<string, unknown>) } : lf ?? null,
    presentation_values: input.presentation_values ? { ...input.presentation_values } : undefined,
  }
}

export type PublicIntakeHook = {
  loading: boolean
  saving: boolean
  submitting: boolean
  error: string | null
  state: PublicIntakeState | null
  formData: IntakeData
  refresh: () => Promise<void>
  updateContacts: (next: Partial<IntakeContacts>) => void
  updatePersonal: (next: Partial<IntakePersonal>) => void
  updateExperience: (updater: (current: IntakeExperience) => IntakeExperience) => void
  upsertEmployment: (index: number, value: IntakeEmployment) => void
  removeEmployment: (index: number) => void
  updateAgreements: (next: Partial<IntakeAgreements>) => void
  updatePresentationValues: (values: Record<string, string>) => void
  submit: (payload: PublicIntakeSubmitPayload) => Promise<void>
}

export function usePublicIntake(token?: string): PublicIntakeHook {
  const { t } = useI18n()
  const [state, setState] = useState<PublicIntakeState | null>(null)
  const [formData, setFormData] = useState<IntakeData>(cloneData(EMPTY_DATA))
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const pendingSave = useRef<IntakeData | null>(null)
  const debounceTimer = useRef<number | null>(null)

  const refresh = useCallback(async () => {
    if (!token) return
    setLoading(true)
    setError(null)
    try {
      const data = await getPublicIntake(token)
      setState(data)
      setFormData(cloneData(data.data))
    } catch (err: any) {
      setError(formatApiError(err, t('public.intake.api.load_error')))
    } finally {
      setLoading(false)
    }
  }, [token, t])

  const commitPending = useCallback(async () => {
    if (!token) return
    if (debounceTimer.current) {
      window.clearTimeout(debounceTimer.current)
      debounceTimer.current = null
    }
    if (!pendingSave.current) return
    setSaving(true)
    try {
      const latest = pendingSave.current
      const response = await updatePublicIntake(token, latest)
      setState(response)
      pendingSave.current = null
      setError(null)
    } catch (err: any) {
      const message = formatApiError(err, t('public.intake.api.save_error'))
      setError(message)
      throw err
    } finally {
      setSaving(false)
    }
  }, [token, t])

  const scheduleSave = useCallback(() => {
    if (!token) return
    if (debounceTimer.current) {
      window.clearTimeout(debounceTimer.current)
    }
    if (!pendingSave.current) return
    debounceTimer.current = window.setTimeout(() => {
      void commitPending()
    }, 1200)
  }, [token, commitPending])

  useEffect(() => {
    refresh()
    return () => {
      if (debounceTimer.current) {
        window.clearTimeout(debounceTimer.current)
      }
    }
  }, [refresh])

  const markDirty = useCallback((updated: IntakeData) => {
    pendingSave.current = updated
    scheduleSave()
  }, [scheduleSave])

  const updateContacts = useCallback((next: Partial<IntakeContacts>) => {
    setFormData((prev) => {
      const updated = { ...prev, contacts: { ...prev.contacts, ...next } }
      markDirty(updated)
      return updated
    })
  }, [markDirty])

  const updatePersonal = useCallback((next: Partial<IntakePersonal>) => {
    setFormData((prev) => {
      const updated = { ...prev, personal: { ...prev.personal, ...next } }
      markDirty(updated)
      return updated
    })
  }, [markDirty])

  const updateExperience = useCallback((updater: (current: IntakeExperience) => IntakeExperience) => {
    setFormData((prev) => {
      const updatedExp = updater(prev.experience)
      const updated = { ...prev, experience: { ...updatedExp } }
      markDirty(updated)
      return updated
    })
  }, [markDirty])

  const upsertEmployment = useCallback((index: number, value: IntakeEmployment) => {
    setFormData((prev) => {
      const list = [...prev.employments]
      list[index] = value
      const updated = { ...prev, employments: list.slice(0, 3) }
      markDirty(updated)
      return updated
    })
  }, [markDirty])

  const removeEmployment = useCallback((index: number) => {
    setFormData((prev) => {
      const list = prev.employments.filter((_, idx) => idx !== index)
      const updated = { ...prev, employments: list }
      markDirty(updated)
      return updated
    })
  }, [markDirty])

  const updateAgreements = useCallback((next: Partial<IntakeAgreements>) => {
    setFormData((prev) => {
      const updated = { ...prev, agreements: { ...prev.agreements, ...next } }
      markDirty(updated)
      return updated
    })
  }, [markDirty])

  const updatePresentationValues = useCallback((values: Record<string, string>) => {
    setFormData((prev) => {
      const updated = {
        ...prev,
        presentation_values: { ...(prev.presentation_values || {}), ...values },
      }
      markDirty(updated)
      return updated
    })
  }, [markDirty])

  const submit = useCallback(async (payload: PublicIntakeSubmitPayload) => {
    if (!token) return
    setSubmitting(true)
    setError(null)
    try {
      await commitPending()
      const response = await submitPublicIntake(token, payload)
      setState(response)
    // keep local form values untouched; state updated for timeline/status
    } catch (err: any) {
      const message = formatApiError(err, t('public.intake.api.submit_error'))
      setError(message)
      throw err
    } finally {
      setSubmitting(false)
    }
  }, [token, commitPending, t])

  return {
    loading,
    saving,
    submitting,
    error,
    state,
    formData,
    refresh,
    updateContacts,
    updatePersonal,
    updateExperience,
    upsertEmployment,
    removeEmployment,
    updateAgreements,
    updatePresentationValues,
    submit,
  }
}
