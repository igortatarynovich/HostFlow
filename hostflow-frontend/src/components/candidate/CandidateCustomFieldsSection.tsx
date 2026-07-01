import { memo, useMemo, useEffect, useState, useCallback } from 'react'
import type { RefObject } from 'react'
import { IconClipboardList } from '@tabler/icons-react'
import type { CandidateProfile } from '../../api/candidate_profiles'
import type { EffectiveCardLayout } from '../../api/fieldRegistry'
import type { CandidateExtra } from '../../api/types'
import type { CustomFieldDefinition } from '../../api/custom_fields'
import { listCustomFieldDefinitions } from '../../api/custom_fields'
import { getFieldConfigs, isFieldVisible, isFieldRequired, getFieldLabel } from '../../utils/profileUtils'
import { Input, Checkbox, SearchableSelect, CheckboxMultiSelect } from './shared/FormComponents'
import { useI18n } from '../../i18n'

interface CandidateCustomFieldsSectionProps {
  extra: CandidateExtra
  customFieldsRef: RefObject<HTMLDivElement>
  candidateProfile: CandidateProfile | null
  effectiveLayout?: EffectiveCardLayout | null
  selectTexts: {
    empty: string
    search: string
    noResults: string
    multiNone: string
    multiSelected: (count: number) => string
  }
  onExtraChange: (patch: Partial<CandidateExtra>) => void
}

function CandidateCustomFieldsSection({
  extra,
  customFieldsRef,
  candidateProfile,
  effectiveLayout,
  selectTexts,
  onExtraChange,
}: CandidateCustomFieldsSectionProps) {
  const { t } = useI18n()
  const layoutVisible = (fieldKey: string) => isFieldVisible(candidateProfile, fieldKey, effectiveLayout)
  const layoutRequired = (fieldKey: string) => isFieldRequired(candidateProfile, fieldKey, effectiveLayout)
  const layoutLabel = (fieldKey: string, defaultLabel: string) =>
    getFieldLabel(candidateProfile, fieldKey, defaultLabel, effectiveLayout)
  const [customFieldDefinitions, setCustomFieldDefinitions] = useState<CustomFieldDefinition[]>([])
  const [loading, setLoading] = useState(true)

  // Получаем список кастомных полей из профиля
  const profileCustomFields = useMemo(() => {
    if (!candidateProfile) return []
    const configs = getFieldConfigs(candidateProfile)
    return configs.filter((c) => c.field_key.startsWith('custom_') && c.custom_field_id)
  }, [candidateProfile])

  // Загружаем определения кастомных полей
  useEffect(() => {
    const loadDefinitions = async () => {
      if (profileCustomFields.length === 0) {
        setLoading(false)
        return
      }

      try {
        const definitionIds = profileCustomFields
          .map((f) => f.custom_field_id)
          .filter((id): id is string => Boolean(id))

        // Загружаем все определения кастомных полей для кандидатов
        const allDefinitions = await listCustomFieldDefinitions({
          scope: 'CANDIDATE',
          is_active: true,
        })

        // Фильтруем только те, которые есть в профиле
        const relevantDefinitions = allDefinitions.filter((def) =>
          definitionIds.includes(def.id)
        )

        setCustomFieldDefinitions(relevantDefinitions)
      } catch (err) {
        console.error('[CandidateCustomFieldsSection] Failed to load custom field definitions', err)
      } finally {
        setLoading(false)
      }
    }

    void loadDefinitions()
  }, [profileCustomFields])

  // Создаем маппинг field_key -> CustomFieldDefinition
  const fieldDefinitionMap = useMemo(() => {
    const map = new Map<string, CustomFieldDefinition>()
    profileCustomFields.forEach((fieldConfig) => {
      if (fieldConfig.custom_field_id) {
        const definition = customFieldDefinitions.find((def) => def.id === fieldConfig.custom_field_id)
        if (definition) {
          map.set(fieldConfig.field_key, definition)
        }
      }
    })
    return map
  }, [profileCustomFields, customFieldDefinitions])

  // Получаем значение кастомного поля
  const getFieldValue = useCallback(
    (fieldKey: string): any => {
      return (extra as any)?.[fieldKey] ?? null
    },
    [extra]
  )

  // Устанавливаем значение кастомного поля
  const setFieldValue = useCallback(
    (fieldKey: string, value: any) => {
      onExtraChange({ [fieldKey]: value } as Partial<CandidateExtra>)
    },
    [onExtraChange]
  )

  // Если нет кастомных полей в профиле, не показываем секцию
  if (!candidateProfile || profileCustomFields.length === 0) {
    return null
  }

  // Фильтруем только видимые поля
  const visibleFields = profileCustomFields.filter((fieldConfig) =>
    layoutVisible(fieldConfig.field_key)
  )

  if (visibleFields.length === 0) {
    return null
  }

  if (loading) {
    return (
      <section
        ref={customFieldsRef}
        id="section-custom-fields"
        className="group app-surface p-4 scroll-mt-24 transition-shadow hover:shadow-xl"
      >
        <div className="text-sm text-slate-500">{t('common.loading')}</div>
      </section>
    )
  }

  return (
    <section
      ref={customFieldsRef}
      id="section-custom-fields"
      className="group app-surface p-4 scroll-mt-24 transition-shadow hover:shadow-xl"
    >
      <div className="flex items-center gap-3">
        <IconClipboardList size={22} className="text-slate-600" />
        <div>
          <h2 className="text-lg font-semibold text-slate-900">
            {t('app.candidate_card.sections.custom_fields.title')}
          </h2>
          <p className="text-sm text-slate-500">
            {t('app.candidate_card.sections.custom_fields.description')}
          </p>
        </div>
      </div>
      <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
        {visibleFields.map((fieldConfig) => {
          const definition = fieldDefinitionMap.get(fieldConfig.field_key)
          if (!definition) return null

          const fieldKey = fieldConfig.field_key
          const label = layoutLabel(fieldKey, definition.label)
          const required = layoutRequired(fieldKey)
          const value = getFieldValue(fieldKey)

          switch (definition.field_type) {
            case 'TEXT':
              return (
                <Input
                  key={fieldKey}
                  label={label}
                  value={value || ''}
                  onChange={(e) => setFieldValue(fieldKey, e.target.value)}
                  required={required}
                  hint={definition.help_text || undefined}
                />
              )

            case 'TEXTAREA':
              return (
                <label key={fieldKey} className="block md:col-span-2">
                  <div className="label">
                    {label}
                    {required && <span className="text-red-600">*</span>}
                  </div>
                  <textarea
                    className="input min-h-[100px] resize-y"
                    value={value || ''}
                    onChange={(e) => setFieldValue(fieldKey, e.target.value)}
                    required={required}
                    placeholder={definition.help_text || undefined}
                  />
                  {definition.help_text && <p className="mt-1 text-xs text-slate-500">{definition.help_text}</p>}
                </label>
              )

            case 'NUMBER':
              return (
                <Input
                  key={fieldKey}
                  label={label}
                  type="number"
                  value={value || ''}
                  onChange={(e) => setFieldValue(fieldKey, e.target.value ? Number(e.target.value) : null)}
                  required={required}
                  hint={definition.help_text || undefined}
                />
              )

            case 'DATE':
              return (
                <Input
                  key={fieldKey}
                  label={label}
                  type="date"
                  value={value || ''}
                  onChange={(e) => setFieldValue(fieldKey, e.target.value || null)}
                  required={required}
                  hint={definition.help_text || undefined}
                />
              )

            case 'CHECKBOX':
              return (
                <div key={fieldKey} className="block md:col-span-2">
                  <Checkbox
                    label={label}
                    checked={Boolean(value)}
                    onChange={(checked) => setFieldValue(fieldKey, checked)}
                  />
                  {definition.help_text && <p className="mt-1 text-xs text-slate-500">{definition.help_text}</p>}
                </div>
              )

            case 'SELECT': {
              const selectOptions =
                definition.options?.map((opt) => ({ value: opt, label: opt })) || []
              return (
                <label key={fieldKey} className="block">
                  <div className="label">
                    {label}
                    {required && <span className="text-red-600">*</span>}
                  </div>
                  <SearchableSelect
                    options={selectOptions}
                    value={value || ''}
                    onChange={(v) => setFieldValue(fieldKey, v || null)}
                    placeholder={selectTexts.empty}
                    searchPlaceholder={selectTexts.search}
                    noResultsLabel={selectTexts.noResults}
                  />
                  {definition.help_text && <p className="mt-1 text-xs text-slate-500">{definition.help_text}</p>}
                </label>
              )
            }

            case 'MULTISELECT': {
              const multiSelectOptions =
                definition.options?.map((opt) => ({ value: opt, label: opt })) || []
              const multiSelectValues = Array.isArray(value) ? value : []
              return (
                <div key={fieldKey} className="block">
                  <div className="label">
                    {label}
                    {required && <span className="text-red-600">*</span>}
                  </div>
                  <CheckboxMultiSelect
                    options={multiSelectOptions}
                    values={multiSelectValues}
                    onChange={(vals) => setFieldValue(fieldKey, vals)}
                    placeholder={selectTexts.multiNone}
                    searchPlaceholder={selectTexts.search}
                    noResultsLabel={selectTexts.noResults}
                    multiSelectedLabel={selectTexts.multiSelected}
                  />
                  {definition.help_text && <p className="mt-1 text-xs text-slate-500">{definition.help_text}</p>}
                </div>
              )
            }

            default:
              return null
          }
        })}
      </div>
    </section>
  )
}

export default memo(CandidateCustomFieldsSection)
