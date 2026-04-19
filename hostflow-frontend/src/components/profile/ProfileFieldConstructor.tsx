import { useCallback, useEffect, useMemo, useState, memo } from 'react'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core'
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { getProfileLimits, type ProfileLimits } from '../../api/candidate_profiles'
import {
  listCustomFieldDefinitions,
  createCustomFieldDefinition,
  type CustomFieldDefinition,
  type CustomFieldType,
} from '../../api/custom_fields'
import { Modal } from '../Modal'
import { useI18n } from '../../i18n'

export interface FieldConfig {
  field_key: string
  field_type: string
  required: boolean
  order: number
  visible: boolean
  label?: string
  custom_field_id?: string // For custom fields
  field_category?: string // Category for grouping (personal, contact, experience, documents, etc.)
}

interface ProfileFieldConstructorProps {
  value: FieldConfig[]
  onChange: (fields: FieldConfig[]) => void
  disabled?: boolean
}

// Field categories for grouping
export const FIELD_CATEGORIES = {
  personal: {
    labelKey: 'app.settings.candidate_profiles.field_constructor.groups.personal',
    defaultLabel: 'Личные данные',
    icon: '👤',
    order: 1,
  },
  contact: {
    labelKey: 'app.settings.candidate_profiles.field_constructor.groups.contact',
    defaultLabel: 'Контакты',
    icon: '📞',
    order: 2,
  },
  experience: {
    labelKey: 'app.settings.candidate_profiles.field_constructor.groups.experience',
    defaultLabel: 'Опыт работы',
    icon: '💼',
    order: 3,
  },
  documents: {
    labelKey: 'app.settings.candidate_profiles.field_constructor.groups.documents',
    defaultLabel: 'Документы',
    icon: '📄',
    order: 4,
  },
  status: {
    labelKey: 'app.settings.candidate_profiles.field_constructor.groups.status',
    defaultLabel: 'Статус',
    icon: '🛂',
    order: 5,
  },
  other: {
    labelKey: 'app.settings.candidate_profiles.field_constructor.groups.other',
    defaultLabel: 'Прочее',
    icon: '📝',
    order: 6,
  },
} as const

// System fields (always available, free)
const SYSTEM_FIELDS: Array<{
  key: string
  type: string
  labelKey: string
  defaultLabel: string
  category: string
  field_category: keyof typeof FIELD_CATEGORIES
}> = [
  {
    key: 'first_name',
    type: 'text',
    labelKey: 'app.settings.candidate_profiles.field_constructor.system_fields.first_name',
    defaultLabel: 'Имя',
    category: 'system',
    field_category: 'personal',
  },
  {
    key: 'last_name',
    type: 'text',
    labelKey: 'app.settings.candidate_profiles.field_constructor.system_fields.last_name',
    defaultLabel: 'Фамилия',
    category: 'system',
    field_category: 'personal',
  },
  {
    key: 'birth_date',
    type: 'date',
    labelKey: 'app.settings.candidate_profiles.field_constructor.system_fields.birth_date',
    defaultLabel: 'Дата рождения',
    category: 'simple',
    field_category: 'personal',
  },
  {
    key: 'citizenship',
    type: 'select',
    labelKey: 'app.settings.candidate_profiles.field_constructor.system_fields.citizenship',
    defaultLabel: 'Гражданство',
    category: 'medium',
    field_category: 'personal',
  },
  {
    key: 'address',
    type: 'address',
    labelKey: 'app.settings.candidate_profiles.field_constructor.system_fields.address',
    defaultLabel: 'Адрес',
    category: 'medium',
    field_category: 'personal',
  },
  {
    key: 'email',
    type: 'text',
    labelKey: 'app.settings.candidate_profiles.field_constructor.system_fields.email',
    defaultLabel: 'Email',
    category: 'system',
    field_category: 'contact',
  },
  {
    key: 'phone',
    type: 'text',
    labelKey: 'app.settings.candidate_profiles.field_constructor.system_fields.phone',
    defaultLabel: 'Телефон',
    category: 'system',
    field_category: 'contact',
  },
  {
    key: 'languages',
    type: 'multiselect',
    labelKey: 'app.settings.candidate_profiles.field_constructor.system_fields.languages',
    defaultLabel: 'Языки',
    category: 'medium',
    field_category: 'contact',
  },
  {
    key: 'license_number',
    type: 'text',
    labelKey: 'app.settings.candidate_profiles.field_constructor.system_fields.license_number',
    defaultLabel: 'Номер водительского удостоверения',
    category: 'simple',
    field_category: 'documents',
  },
  {
    key: 'license_categories',
    type: 'multiselect',
    labelKey: 'app.settings.candidate_profiles.field_constructor.system_fields.license_categories',
    defaultLabel: 'Категории прав',
    category: 'medium',
    field_category: 'documents',
  },
  {
    key: 'employment_history',
    type: 'employment_history',
    labelKey: 'app.settings.candidate_profiles.field_constructor.system_fields.employment_history',
    defaultLabel: 'История трудоустройства',
    category: 'resource',
    field_category: 'experience',
  },
]

// Component for grouped fields by category
const FieldCategoryGroup = memo(function FieldCategoryGroup({
  category,
  categoryInfo,
  fields,
  value,
  limits,
  onToggleRequired,
  onRemove,
  disabled,
}: {
  category: string
  categoryInfo: { labelKey: string; defaultLabel: string; icon: string; order: number }
  fields: FieldConfig[]
  value: FieldConfig[]
  limits: ProfileLimits | null
  onToggleRequired: (index: number) => void
  onRemove: (index: number) => void
  disabled?: boolean
}) {
  const { t } = useI18n()
  const [expanded, setExpanded] = useState(true)

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between rounded-t-lg border-b border-slate-200 bg-white px-4 py-2 text-left transition-colors hover:bg-slate-50"
      >
        <div className="flex items-center gap-2">
          <span className="text-lg">{categoryInfo.icon}</span>
          <span className="text-sm font-semibold text-slate-900">
            {t(categoryInfo.labelKey)}
          </span>
          <span className="rounded-md bg-slate-200 px-2 py-0.5 text-xs text-slate-600">{fields.length}</span>
        </div>
        <svg
          className={`h-5 w-5 text-slate-500 transition-transform ${expanded ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {expanded && (
        <div className="space-y-2 p-3">
          {fields.map((field, index) => {
            const globalIndex = value.findIndex((f) => f.field_key === field.field_key)
            return (
              <SortableFieldItem
                key={field.field_key}
                field={field}
                index={globalIndex}
                limits={limits}
                onToggleRequired={() => onToggleRequired(index)}
                onRemove={() => onRemove(index)}
                disabled={disabled}
              />
            )
          })}
        </div>
      )}
    </div>
  )
})

function SortableFieldItem({
  field,
  index,
  limits,
  onToggleRequired,
  onRemove,
  disabled,
}: {
  field: FieldConfig
  index: number
  limits: ProfileLimits | null
  onToggleRequired: () => void
  onRemove: () => void
  disabled?: boolean
}) {
  const { t } = useI18n()
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: field.field_key })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  const fieldCategory = limits?.field_categories[field.field_type] || 'simple'
  const isSystemField = ['first_name', 'last_name', 'email', 'phone'].includes(field.field_key)
  const categoryLabel = fieldCategory === 'simple'
    ? t('app.settings.candidate_profiles.field_constructor.category.simple')
    : fieldCategory === 'medium'
      ? t('app.settings.candidate_profiles.field_constructor.category.medium')
      : fieldCategory === 'resource'
        ? t('app.settings.candidate_profiles.field_constructor.category.resource')
        : t('app.settings.candidate_profiles.field_constructor.category.system')

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`rounded-lg border p-3 bg-white ${
        isDragging ? 'shadow-lg' : 'shadow-sm'
      } ${disabled ? 'opacity-50' : ''}`}
    >
      <div className="flex items-center gap-3">
        <div
          {...attributes}
          {...listeners}
          className="cursor-grab active:cursor-grabbing text-slate-400 hover:text-slate-600"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 8h16M4 16h16"
            />
          </svg>
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="font-medium text-slate-900">{field.label || field.field_key}</span>
            <span className="text-xs text-slate-500">({field.field_type})</span>
            {!isSystemField && (
              <span className="text-xs text-slate-400">
                {categoryLabel}
              </span>
            )}
            {isSystemField && (
              <span className="rounded-md bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800">
                {t('app.settings.candidate_profiles.field_constructor.category.system')}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-1">
            <input
              type="checkbox"
              checked={field.required}
              onChange={onToggleRequired}
              disabled={disabled || isSystemField}
              className="rounded border-slate-300"
            />
            <span className="text-xs text-slate-600">{t('common.required')}</span>
          </label>
          {!isSystemField && (
            <button
              type="button"
              onClick={onRemove}
              disabled={disabled}
              className="btn-danger btn-xs"
            >
              {t('common.actions.delete')}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default function ProfileFieldConstructor({
  value,
  onChange,
  disabled = false,
}: ProfileFieldConstructorProps) {
  const { t } = useI18n()
  const [limits, setLimits] = useState<ProfileLimits | null>(null)
  const [customFields, setCustomFields] = useState<CustomFieldDefinition[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateFieldModal, setShowCreateFieldModal] = useState(false)
  const [creatingField, setCreatingField] = useState(false)

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  useEffect(() => {
    const loadData = async () => {
      try {
        const [limitsData, customFieldsData] = await Promise.all([
          getProfileLimits(),
          listCustomFieldDefinitions({ scope: 'CANDIDATE', is_active: true }),
        ])
        setLimits(limitsData)
        setCustomFields(customFieldsData)
      } catch (err) {
        console.error('Failed to load profile limits or custom fields', err)
      } finally {
        setLoading(false)
      }
    }
    void loadData()
  }, [])

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event
      if (!over || active.id === over.id) return

      const oldIndex = value.findIndex((f) => f.field_key === active.id)
      const newIndex = value.findIndex((f) => f.field_key === over.id)

      if (oldIndex !== -1 && newIndex !== -1) {
        const newFields = arrayMove(value, oldIndex, newIndex)
        // Update order numbers
        const reordered = newFields.map((field, idx) => ({
          ...field,
          order: idx + 1,
        }))
        onChange(reordered)
      }
    },
    [value, onChange]
  )

  const calculateCurrentCounts = useCallback(() => {
    if (!limits) return { simple: 0, medium: 0, resource: 0, total: 0 }
    
    const counts = { simple: 0, medium: 0, resource: 0, total: 0 }
    
    value.forEach((field) => {
      // System fields don't count
      if (['first_name', 'last_name', 'email', 'phone'].includes(field.field_key)) {
        return
      }
      
      const category = limits.field_categories[field.field_type] || 'simple'
      counts.total += 1
      
      if (category === 'simple') {
        counts.simple += 1
      } else if (category === 'medium') {
        counts.medium += 1
      } else if (category === 'resource') {
        counts.resource += 1
      }
    })
    
    return counts
  }, [value, limits])

  const availableFields = useMemo(() => {
    const usedKeys = new Set(value.map((f) => f.field_key))
    const available: Array<{ key: string; type: string; label: string; category: string; field_category: keyof typeof FIELD_CATEGORIES }> = []

    // System fields (always available)
    SYSTEM_FIELDS.forEach((field) => {
      if (!usedKeys.has(field.key)) {
        available.push({
          key: field.key,
          type: field.type,
          label: t(field.labelKey),
          category: field.category,
          field_category: field.field_category,
        })
      }
    })

    // Custom fields
    customFields.forEach((cf) => {
      if (!usedKeys.has(`custom_${cf.id}`)) {
        const category = limits?.field_categories[cf.field_type.toLowerCase()] || 'simple'
        available.push({
          key: `custom_${cf.id}`,
          type: cf.field_type.toLowerCase(),
          label: cf.label,
          category: category,
          field_category: 'other', // Default category for custom fields
        })
      }
    })

    return available.sort((a, b) => a.label.localeCompare(b.label))
  }, [value, customFields, limits, t])

  const handleAddField = useCallback(
    (fieldKey: string, fieldType: string, label: string, category: string, fieldCategory?: keyof typeof FIELD_CATEGORIES) => {
      const currentCounts = calculateCurrentCounts()
      const fieldCategoryLimit = limits?.field_categories[fieldType] || category || 'simple'
      
      // Check limits
      if (limits) {
        const newSimple = fieldCategoryLimit === 'simple' ? currentCounts.simple + 1 : currentCounts.simple
        const newMedium = fieldCategoryLimit === 'medium' ? currentCounts.medium + 1 : currentCounts.medium
        const newResource = fieldCategoryLimit === 'resource' ? currentCounts.resource + 1 : currentCounts.resource
        const newTotal = currentCounts.total + 1
        
        const errors: string[] = []
        if (newSimple > limits.limits.simple.limit) {
          errors.push(`${t('app.settings.candidate_profiles.field_constructor.limits.simple').toLowerCase()}: ${newSimple}/${limits.limits.simple.limit}`)
        }
        if (newMedium > limits.limits.medium.limit) {
          errors.push(`${t('app.settings.candidate_profiles.field_constructor.limits.medium').toLowerCase()}: ${newMedium}/${limits.limits.medium.limit}`)
        }
        if (newResource > limits.limits.resource.limit) {
          errors.push(`${t('app.settings.candidate_profiles.field_constructor.limits.resource').toLowerCase()}: ${newResource}/${limits.limits.resource.limit}`)
        }
        if (newTotal > limits.limits.total_custom.limit) {
          errors.push(`${t('app.settings.candidate_profiles.field_constructor.limits.total_custom').toLowerCase()}: ${newTotal}/${limits.limits.total_custom.limit}`)
        }
        
        if (errors.length > 0) {
          alert(`${t('app.settings.candidate_profiles.field_constructor.limits_exceeded')}: ${errors.join(', ')}`)
          return
        }
      }

      const customField = customFields.find((cf) => `custom_${cf.id}` === fieldKey)
      const systemField = SYSTEM_FIELDS.find((f) => f.key === fieldKey)
      const newField: FieldConfig = {
        field_key: fieldKey,
        field_type: fieldType,
        required: false,
        order: value.length + 1,
        visible: true,
        label: label,
        custom_field_id: customField?.id,
        field_category: fieldCategory || systemField?.field_category || 'other',
      }

      onChange([...value, newField])
    },
    [value, onChange, limits, customFields, calculateCurrentCounts, t]
  )

  const handleToggleRequired = useCallback(
    (index: number) => {
      const newFields = [...value]
      newFields[index] = { ...newFields[index], required: !newFields[index].required }
      onChange(newFields)
    },
    [value, onChange]
  )

  const handleRemove = useCallback(
    (index: number) => {
      const newFields = value.filter((_, i) => i !== index)
      // Reorder
      const reordered = newFields.map((field, idx) => ({
        ...field,
        order: idx + 1,
      }))
      onChange(reordered)
    },
    [value, onChange]
  )

  const currentCounts = calculateCurrentCounts()

  if (loading) {
    return <div className="text-sm text-slate-500">{t('common.loading')}</div>
  }

  return (
    <div className="space-y-4">
      {/* Limits display */}
      {limits && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
          <div className="mb-2 text-sm font-semibold text-blue-900">
            {t('app.settings.candidate_profiles.field_constructor.limits_title')} ({t('common.plan')}: {limits.plan})
          </div>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <div>
              <div className="text-xs text-blue-700">{t('app.settings.candidate_profiles.field_constructor.limits.simple')}</div>
              <div className="text-sm font-medium text-blue-900">
                {limits.limits.simple.used + currentCounts.simple}/{limits.limits.simple.limit}
              </div>
              <div className="text-xs text-blue-600">{t('common.available')}: {Math.max(0, limits.limits.simple.available - currentCounts.simple)}</div>
            </div>
            <div>
              <div className="text-xs text-blue-700">{t('app.settings.candidate_profiles.field_constructor.limits.medium')}</div>
              <div className="text-sm font-medium text-blue-900">
                {limits.limits.medium.used + currentCounts.medium}/{limits.limits.medium.limit}
              </div>
              <div className="text-xs text-blue-600">{t('common.available')}: {Math.max(0, limits.limits.medium.available - currentCounts.medium)}</div>
            </div>
            <div>
              <div className="text-xs text-blue-700">{t('app.settings.candidate_profiles.field_constructor.limits.resource')}</div>
              <div className="text-sm font-medium text-blue-900">
                {limits.limits.resource.used + currentCounts.resource}/{limits.limits.resource.limit}
              </div>
              <div className="text-xs text-blue-600">{t('common.available')}: {Math.max(0, limits.limits.resource.available - currentCounts.resource)}</div>
            </div>
            <div>
              <div className="text-xs text-blue-700">{t('app.settings.candidate_profiles.field_constructor.limits.total_custom')}</div>
              <div className="text-sm font-medium text-blue-900">
                {limits.limits.total_custom.used + currentCounts.total}/{limits.limits.total_custom.limit}
              </div>
              <div className="text-xs text-blue-600">{t('common.available')}: {Math.max(0, limits.limits.total_custom.available - currentCounts.total)}</div>
            </div>
          </div>
          {(limits.limits.simple.available - currentCounts.simple < 0 ||
            limits.limits.medium.available - currentCounts.medium < 0 ||
            limits.limits.resource.available - currentCounts.resource < 0 ||
            limits.limits.total_custom.available - currentCounts.total < 0) && (
            <div className="mt-2 rounded bg-rose-100 px-2 py-1 text-xs font-medium text-rose-800">
              {t('app.settings.candidate_profiles.field_constructor.limits_exceeded')}
            </div>
          )}
        </div>
      )}

      {/* Active fields (sortable, grouped by category) */}
      <div>
        <h3 className="mb-2 text-sm font-semibold text-slate-900">{t('app.settings.candidate_profiles.field_constructor.in_profile')}</h3>
        {value.length === 0 ? (
          <p className="text-sm text-slate-500">{t('app.settings.candidate_profiles.field_constructor.empty')}</p>
        ) : (() => {
          // Group fields by category
          const groupedFields = value.reduce((acc, field) => {
            const category = field.field_category || 'other'
            if (!acc[category]) {
              acc[category] = []
            }
            acc[category].push(field)
            return acc
          }, {} as Record<string, FieldConfig[]>)

          // Sort categories by order
          const sortedCategories = Object.keys(groupedFields).sort((a, b) => {
            const orderA = FIELD_CATEGORIES[a as keyof typeof FIELD_CATEGORIES]?.order || 999
            const orderB = FIELD_CATEGORIES[b as keyof typeof FIELD_CATEGORIES]?.order || 999
            return orderA - orderB
          })

          return (
            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              onDragEnd={handleDragEnd}
            >
              <SortableContext items={value.map((f) => f.field_key)} strategy={verticalListSortingStrategy}>
                <div className="space-y-4">
                  {sortedCategories.map((category) => {
                    const categoryInfo = FIELD_CATEGORIES[category as keyof typeof FIELD_CATEGORIES] || FIELD_CATEGORIES.other
                    const fieldsInCategory = groupedFields[category]
                    return (
                      <FieldCategoryGroup
                        key={category}
                        category={category}
                        categoryInfo={categoryInfo}
                        fields={fieldsInCategory}
                        value={value}
                        limits={limits}
                        onToggleRequired={(index) => {
                          const globalIndex = value.findIndex((f) => f.field_key === fieldsInCategory[index].field_key)
                          handleToggleRequired(globalIndex)
                        }}
                        onRemove={(index) => {
                          const globalIndex = value.findIndex((f) => f.field_key === fieldsInCategory[index].field_key)
                          handleRemove(globalIndex)
                        }}
                        disabled={disabled}
                      />
                    )
                  })}
                </div>
              </SortableContext>
            </DndContext>
          )
        })()}
      </div>

      {/* Create new custom field button */}
      <div className="mb-4">
        <button
          type="button"
          onClick={() => setShowCreateFieldModal(true)}
          disabled={disabled}
          className="btn-secondary text-sm"
        >
          + {t('app.settings.candidate_profiles.field_constructor.create_new')}
        </button>
      </div>

      {/* Available fields */}
      <div>
        <h3 className="mb-2 text-sm font-semibold text-slate-900">{t('app.settings.candidate_profiles.field_constructor.available')}</h3>
        {availableFields.length === 0 ? (
          <p className="text-sm text-slate-500">{t('app.settings.candidate_profiles.field_constructor.all_added')}</p>
        ) : (
          <div className="grid grid-cols-1 gap-2 md:grid-cols-2 lg:grid-cols-3">
            {availableFields.map((field) => {
              if (!limits) {
                return (
                  <button
                    key={field.key}
                    type="button"
                    onClick={() => handleAddField(field.key, field.type, field.label, field.category, field.field_category)}
                    disabled={disabled}
                    className="rounded-lg border border-slate-200 bg-white p-2 text-left text-sm transition-colors hover:border-blue-300 hover:bg-blue-50"
                  >
                    <div className="font-medium text-slate-900">{field.label}</div>
                    <div className="text-xs text-slate-500">{field.type}</div>
                  </button>
                )
              }
              
              const fieldCategory = limits.field_categories[field.type] || field.category || 'simple'
              const counts = calculateCurrentCounts()
              
              let canAdd = true
              const newSimple = fieldCategory === 'simple' ? counts.simple + 1 : counts.simple
              const newMedium = fieldCategory === 'medium' ? counts.medium + 1 : counts.medium
              const newResource = fieldCategory === 'resource' ? counts.resource + 1 : counts.resource
              const newTotal = counts.total + 1
              
              canAdd = (
                newSimple <= limits.limits.simple.limit &&
                newMedium <= limits.limits.medium.limit &&
                newResource <= limits.limits.resource.limit &&
                newTotal <= limits.limits.total_custom.limit
              )
              
              const categoryLabel = fieldCategory === 'simple'
                ? t('app.settings.candidate_profiles.field_constructor.category.simple')
                : fieldCategory === 'medium'
                  ? t('app.settings.candidate_profiles.field_constructor.category.medium')
                  : fieldCategory === 'resource'
                    ? t('app.settings.candidate_profiles.field_constructor.category.resource')
                    : t('app.settings.candidate_profiles.field_constructor.category.system')
              
              return (
                <button
                  key={field.key}
                  type="button"
                  onClick={() => handleAddField(field.key, field.type, field.label, field.category, field.field_category)}
                  disabled={disabled || !canAdd}
                  className={`rounded-lg border p-2 text-left text-sm transition-colors ${
                    canAdd
                      ? 'border-slate-200 bg-white hover:border-blue-300 hover:bg-blue-50'
                      : 'border-slate-100 bg-slate-50 opacity-50 cursor-not-allowed'
                  }`}
                >
                  <div className="font-medium text-slate-900">{field.label}</div>
                  <div className="text-xs text-slate-500">
                    {field.type} • {categoryLabel}
                  </div>
                </button>
              )
            })}
          </div>
        )}
      </div>

      {/* Create new custom field modal */}
      {showCreateFieldModal && (
        <CreateCustomFieldModal
          onClose={() => setShowCreateFieldModal(false)}
          onCreate={async (fieldData) => {
            setCreatingField(true)
            try {
              // Create custom field definition
              const newFieldDef = await createCustomFieldDefinition({
                scope: 'CANDIDATE',
                key: fieldData.key,
                label: fieldData.label,
                field_type: fieldData.field_type as CustomFieldType,
                required: fieldData.required || false,
                options: fieldData.options || null,
                help_text: fieldData.help_text || null,
                is_active: true,
                order: 0,
              })
              
              // Reload custom fields list
              const updatedCustomFields = await listCustomFieldDefinitions({ scope: 'CANDIDATE', is_active: true })
              setCustomFields(updatedCustomFields)
              
              // Add field to profile
              const fieldCategory = limits?.field_categories[fieldData.field_type.toLowerCase()] || 'simple'
              const customField = updatedCustomFields.find((cf) => cf.id === newFieldDef.id)
              if (customField) {
                handleAddField(
                  `custom_${customField.id}`,
                  fieldData.field_type.toLowerCase(),
                  customField.label,
                  fieldCategory,
                  'other' // Custom fields go to "other" category by default
                )
              }
              
              setShowCreateFieldModal(false)
            } catch (err: any) {
              alert(t('app.settings.candidate_profiles.field_constructor.errors.create_failed') + `: ${err?.message || t('common.errors.unknown')}`)
            } finally {
              setCreatingField(false)
            }
          }}
          disabled={creatingField || disabled}
        />
      )}
    </div>
  )
}

// Modal for creating a new custom field with user-defined name
function CreateCustomFieldModal({
  onClose,
  onCreate,
  disabled,
}: {
  onClose: () => void
  onCreate: (data: {
    key: string
    label: string
    field_type: string
    required?: boolean
    options?: string[]
    help_text?: string
  }) => Promise<void>
  disabled?: boolean
}) {
  const { t } = useI18n()
  const [key, setKey] = useState('')
  const [label, setLabel] = useState('')
  const [fieldType, setFieldType] = useState<CustomFieldType>('TEXT')
  const [required, setRequired] = useState(false)
  const [helpText, setHelpText] = useState('')
  const [options, setOptions] = useState<string[]>([])
  const [newOption, setNewOption] = useState('')

  const fieldTypeOptions: Array<{ value: CustomFieldType; label: string }> = [
    { value: 'TEXT', label: t('app.settings.candidate_profiles.field_constructor.types.text') },
    { value: 'TEXTAREA', label: t('app.settings.candidate_profiles.field_constructor.types.textarea') },
    { value: 'NUMBER', label: t('app.settings.candidate_profiles.field_constructor.types.number') },
    { value: 'DATE', label: t('app.settings.candidate_profiles.field_constructor.types.date') },
    { value: 'CHECKBOX', label: t('app.settings.candidate_profiles.field_constructor.types.checkbox') },
    { value: 'SELECT', label: t('app.settings.candidate_profiles.field_constructor.types.select') },
    { value: 'MULTISELECT', label: t('app.settings.candidate_profiles.field_constructor.types.multiselect') },
  ]

  const needsOptions = fieldType === 'SELECT' || fieldType === 'MULTISELECT'

  const handleSubmit = async () => {
    if (!key.trim() || !label.trim()) {
      alert(t('app.settings.candidate_profiles.field_constructor.errors.key_label_required'))
      return
    }

    // Generate key from label if not provided
    const finalKey = key.trim() || label.trim().toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '')

    await onCreate({
      key: finalKey,
      label: label.trim(),
      field_type: fieldType,
      required,
      options: needsOptions && options.length > 0 ? options : undefined,
      help_text: helpText.trim() || undefined,
    })
  }

  const handleAddOption = () => {
    if (newOption.trim() && !options.includes(newOption.trim())) {
      setOptions([...options, newOption.trim()])
      setNewOption('')
    }
  }

  const handleRemoveOption = (index: number) => {
    setOptions(options.filter((_, i) => i !== index))
  }

  return (
    <Modal open={true} onClose={onClose} title={t('app.settings.candidate_profiles.field_constructor.modal.title')}>
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            {t('app.settings.candidate_profiles.field_constructor.modal.field_label')}
          </label>
          <input
            type="text"
            value={label}
            onChange={(e) => {
              setLabel(e.target.value)
              // Auto-generate key from label if key is empty
              if (!key.trim()) {
                const autoKey = e.target.value
                  .trim()
                  .toLowerCase()
                  .replace(/\s+/g, '_')
                  .replace(/[^a-z0-9_]/g, '')
                setKey(autoKey)
              }
            }}
            className="input w-full"
            placeholder={t('app.settings.candidate_profiles.field_constructor.modal.field_label_placeholder')}
            disabled={disabled}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            {t('app.settings.candidate_profiles.field_constructor.modal.key_label')}
          </label>
          <input
            type="text"
            value={key}
            onChange={(e) => setKey(e.target.value.trim().toLowerCase().replace(/[^a-z0-9_]/g, '_'))}
            className="input w-full font-mono text-sm"
            placeholder={t('app.settings.candidate_profiles.field_constructor.key_placeholder')}
            disabled={disabled}
          />
          <p className="mt-1 text-xs text-slate-500">{t('app.settings.candidate_profiles.field_constructor.modal.key_hint')}</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            {t('app.settings.candidate_profiles.field_constructor.modal.type_label')}
          </label>
          <select
            value={fieldType}
            onChange={(e) => setFieldType(e.target.value as CustomFieldType)}
            className="input w-full"
            disabled={disabled}
          >
            {fieldTypeOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {needsOptions && (
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              {t('app.settings.candidate_profiles.field_constructor.modal.options_label')}
            </label>
            <div className="space-y-2">
              {options.map((opt, index) => (
                <div key={index} className="flex items-center gap-2">
                  <input
                    type="text"
                    value={opt}
                    onChange={(e) => {
                      const newOptions = [...options]
                      newOptions[index] = e.target.value
                      setOptions(newOptions)
                    }}
                    className="input flex-1"
                    disabled={disabled}
                  />
                  <button
                    type="button"
                    onClick={() => handleRemoveOption(index)}
                    disabled={disabled}
                    className="btn-danger btn-xs"
                  >
                    {t('common.actions.delete')}
                  </button>
                </div>
              ))}
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={newOption}
                  onChange={(e) => setNewOption(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      handleAddOption()
                    }
                  }}
                  className="input flex-1"
                  placeholder={t('app.settings.candidate_profiles.field_constructor.modal.add_option_placeholder')}
                  disabled={disabled}
                />
                <button
                  type="button"
                  onClick={handleAddOption}
                  disabled={disabled || !newOption.trim()}
                  className="btn-secondary text-sm"
                >
                  {t('common.actions.add')}
                </button>
              </div>
            </div>
          </div>
        )}

        <div>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={required}
              onChange={(e) => setRequired(e.target.checked)}
              disabled={disabled}
              className="rounded border-slate-300"
            />
            <span className="text-sm text-slate-700">{t('app.settings.candidate_profiles.field_constructor.modal.required_label')}</span>
          </label>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            {t('app.settings.candidate_profiles.field_constructor.modal.help_label')}
          </label>
          <textarea
            value={helpText}
            onChange={(e) => setHelpText(e.target.value)}
            className="input w-full"
            rows={2}
            placeholder={t('app.settings.candidate_profiles.field_constructor.modal.help_placeholder')}
            disabled={disabled}
          />
        </div>

        <div className="flex gap-2 justify-end pt-4">
          <button
            type="button"
            onClick={onClose}
            disabled={disabled}
            className="btn-secondary"
          >
            {t('common.actions.cancel')}
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={disabled || !label.trim() || !key.trim()}
            className="btn-primary"
          >
            {disabled
              ? t('app.settings.candidate_profiles.field_constructor.modal.creating')
              : t('app.settings.candidate_profiles.field_constructor.modal.create')}
          </button>
        </div>
      </div>
    </Modal>
  )
}
