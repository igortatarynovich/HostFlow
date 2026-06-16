import type { CandidateProfile } from '../api/candidate_profiles'
import type { EffectiveCardLayout } from '../api/fieldRegistry'
import {
  layoutFieldLabel,
  layoutFieldRequired,
  layoutFieldVisible,
} from './fieldLayoutUtils'

export interface FieldConfig {
  field_key: string
  field_type: string
  required: boolean
  order: number
  visible: boolean
  label?: string
  custom_field_id?: string
  field_category?: string // Category for grouping (personal, contact, experience, documents, etc.)
}

export interface DocumentConfig {
  document_type_id: string
  required: boolean
  alert_days_before_expiry?: number | null
  label?: string
}

const DRIVER_CE_DEFAULT_CODE = 'driver_ce_default'

/** Профиль по умолчанию с пустым конфигом полей = показывать все поля (как без профиля). */
export function isDefaultProfileWithEmptyConfig(profile: CandidateProfile | null | undefined): boolean {
  if (!profile || profile.code !== DRIVER_CE_DEFAULT_CODE) return false
  const fc = profile.config?.field_configs
  return !fc || !Array.isArray(fc) || fc.length === 0
}

/** Профиль по умолчанию с пустым конфигом документов = показывать все документы по ruleset (как без профиля). */
export function isDefaultProfileWithEmptyDocumentConfig(profile: CandidateProfile | null | undefined): boolean {
  if (!profile || profile.code !== DRIVER_CE_DEFAULT_CODE) return false
  const dc = profile.config?.document_configs
  return !dc || !Array.isArray(dc) || dc.length === 0
}

/**
 * Получить конфигурацию полей из профиля
 */
export function getFieldConfigs(profile: CandidateProfile | null | undefined): FieldConfig[] {
  if (!profile?.config?.field_configs) {
    return []
  }
  return (profile.config.field_configs as FieldConfig[]).sort((a, b) => (a.order || 0) - (b.order || 0))
}

/**
 * Получить конфигурацию документов из профиля. Для driver_ce_default с пустым конфигом = [] (чеклист из API/ruleset).
 */
export function getDocumentConfigs(profile: CandidateProfile | null | undefined): DocumentConfig[] {
  if (!profile?.config?.document_configs) {
    return []
  }
  const dc = profile.config.document_configs
  if (!Array.isArray(dc) || dc.length === 0) {
    return []
  }
  return dc as DocumentConfig[]
}

/**
 * Проверить, должно ли поле быть видимым
 */
export function isFieldVisible(
  profile: CandidateProfile | null | undefined,
  fieldKey: string,
  effectiveLayout?: EffectiveCardLayout | null,
): boolean {
  return layoutFieldVisible(profile, fieldKey, effectiveLayout, _isFieldVisibleFromProfile)
}

function _isFieldVisibleFromProfile(profile: CandidateProfile | null | undefined, fieldKey: string): boolean {
  if (!profile) {
    return true // Если профиля нет, показываем все поля
  }
  // Профиль по умолчанию с пустым конфигом = те же права что без профиля (все поля видимы)
  if (isDefaultProfileWithEmptyConfig(profile)) {
    return true
  }
  const configs = getFieldConfigs(profile)
  const config = configs.find((c) => c.field_key === fieldKey)
  return config ? config.visible !== false : false
}

/**
 * Проверить, является ли поле обязательным
 */
export function isFieldRequired(
  profile: CandidateProfile | null | undefined,
  fieldKey: string,
  effectiveLayout?: EffectiveCardLayout | null,
): boolean {
  return layoutFieldRequired(profile, fieldKey, effectiveLayout, _isFieldRequiredFromProfile)
}

function _isFieldRequiredFromProfile(profile: CandidateProfile | null | undefined, fieldKey: string): boolean {
  if (!profile) {
    return false
  }
  if (isDefaultProfileWithEmptyConfig(profile)) {
    return false
  }
  const configs = getFieldConfigs(profile)
  const config = configs.find((c) => c.field_key === fieldKey)
  return config ? config.required === true : false
}

/**
 * Получить метку поля из профиля
 */
export function getFieldLabel(
  profile: CandidateProfile | null | undefined,
  fieldKey: string,
  defaultLabel: string,
  effectiveLayout?: EffectiveCardLayout | null,
): string {
  return layoutFieldLabel(profile, fieldKey, defaultLabel, effectiveLayout, _getFieldLabelFromProfile)
}

function _getFieldLabelFromProfile(
  profile: CandidateProfile | null | undefined,
  fieldKey: string,
  defaultLabel: string,
): string {
  if (!profile) {
    return defaultLabel
  }
  if (isDefaultProfileWithEmptyConfig(profile)) {
    return defaultLabel
  }
  const configs = getFieldConfigs(profile)
  const config = configs.find((c) => c.field_key === fieldKey)
  const profileLabel = config?.label?.trim()
  if (!profileLabel) {
    return defaultLabel
  }
  // Prevent mixed-language UI when legacy profile labels are Cyrillic
  // but the current translated default label is Latin script (PL/EN).
  const hasCyrillic = (value: string) => /[А-Яа-яЁё]/.test(value)
  if (hasCyrillic(profileLabel) && !hasCyrillic(defaultLabel)) {
    return defaultLabel
  }
  return profileLabel
}

/**
 * Получить список требуемых документов из профиля
 */
export function getRequiredDocumentTypeIds(profile: CandidateProfile | null | undefined): string[] {
  if (!profile) {
    return []
  }
  const configs = getDocumentConfigs(profile)
  return configs.filter((c) => c.required === true).map((c) => c.document_type_id)
}

/**
 * Получить конфигурацию документа по типу
 */
export function getDocumentConfig(profile: CandidateProfile | null | undefined, documentTypeId: string): DocumentConfig | null {
  if (!profile) {
    return null
  }
  const configs = getDocumentConfigs(profile)
  return configs.find((c) => c.document_type_id === documentTypeId) || null
}

/**
 * Валидация обязательных полей из профиля
 * Возвращает список полей, которые обязательны, но не заполнены
 */
export function validateRequiredFields(
  profile: CandidateProfile | null | undefined,
  model: { [key: string]: any } | null,
  extra: { [key: string]: any } | null
): Array<{ fieldKey: string; label: string }> {
  if (!profile || !model) {
    return []
  }
  if (isDefaultProfileWithEmptyConfig(profile)) {
    return []
  }

  const configs = getFieldConfigs(profile)
  const requiredFields = configs.filter((c) => c.required === true)
  const missing: Array<{ fieldKey: string; label: string }> = []

  for (const config of requiredFields) {
    const fieldKey = config.field_key
    const label = config.label || fieldKey
    let value: any = null

    // Проверяем значение в model или extra в зависимости от поля
    if (fieldKey === 'first_name' || fieldKey === 'last_name' || fieldKey === 'email' || fieldKey === 'phone') {
      value = model[fieldKey]
    } else if (fieldKey === 'birth_date') {
      value = extra?.birth_date
    } else if (fieldKey === 'citizenship') {
      value = extra?.citizenship
    } else if (fieldKey === 'address') {
      value = extra?.address
    } else if (fieldKey === 'languages') {
      value = extra?.languages
    } else if (fieldKey === 'license_number') {
      value = extra?.license_number
    } else if (fieldKey === 'license_categories') {
      value = extra?.license_categories
    } else if (fieldKey === 'in_poland') {
      value = extra?.in_poland
    } else if (fieldKey === 'poland_stay_basis') {
      value = extra?.poland_stay_basis
    } else if (fieldKey === 'current_location') {
      value = extra?.current_location
    } else if (fieldKey === 'experience_eu_years') {
      value = extra?.experience_eu_years
    } else if (fieldKey === 'experience_non_eu_years') {
      value = extra?.experience_non_eu_years
    } else if (fieldKey === 'intl_experience') {
      value = extra?.intl_experience
    } else if (fieldKey === 'eu_routes') {
      value = extra?.eu_routes
    } else if (fieldKey === 'frigo_experience') {
      value = extra?.frigo_experience
    } else if (fieldKey === 'has_adr') {
      value = extra?.has_adr
    } else if (fieldKey === 'trailer_types') {
      value = extra?.trailer_types
    } else if (fieldKey === 'route_types') {
      value = extra?.route_types
    } else if (fieldKey === 'employment_history') {
      value = extra?.employment_history
    } else if (fieldKey.startsWith('custom_')) {
      // Для кастомных полей проверяем в extra
      // fieldKey уже имеет формат custom_${customFieldId}
      value = extra?.[fieldKey]
    }

    // Проверяем, заполнено ли поле
    const isEmpty =
      value === null ||
      value === undefined ||
      value === '' ||
      (Array.isArray(value) && value.length === 0) ||
      (typeof value === 'object' && Object.keys(value).length === 0)

    if (isEmpty) {
      missing.push({ fieldKey, label })
    }
  }

  return missing
}
