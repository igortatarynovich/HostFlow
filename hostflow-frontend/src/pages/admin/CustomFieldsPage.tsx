import { useCallback, useEffect, useState } from 'react'
import { useI18n } from '../../i18n'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import {
  listCustomFieldDefinitions,
  createCustomFieldDefinition,
  updateCustomFieldDefinition,
  deleteCustomFieldDefinition,
  type CustomFieldDefinition,
  type CustomFieldDefinitionCreate,
  type CustomFieldScope,
  type CustomFieldType,
} from '../../api/custom_fields'
import { getDocumentTypes, type DocType } from '../../api/documents/catalog'

// Field components (inline, similar to Companies.tsx)
function TextField({ label, value, onChange, placeholder, disabled, type }: {
  label: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
  disabled?: boolean
  type?: string
}) {
  return (
    <label className="block">
      <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <input
        type={type || 'text'}
        className="input w-full"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
      />
    </label>
  )
}

function TextareaField({ label, value, onChange, placeholder, rows = 3 }: {
  label: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
  rows?: number
}) {
  return (
    <label className="block">
      <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <textarea
        className="input w-full min-h-[80px]"
        rows={rows}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
    </label>
  )
}

function SelectField({ label, value, onChange, options, allowEmpty = true }: {
  label: string
  value: string
  onChange: (value: string) => void
  options: Array<{ value: string; label: string }>
  allowEmpty?: boolean
}) {
  return (
    <label className="block">
      <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <select className="input w-full" value={value} onChange={(e) => onChange(e.target.value)}>
        {allowEmpty && <option value="">— не выбран —</option>}
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </label>
  )
}

function CheckboxField({ label, checked, onChange }: {
  label: string
  checked: boolean
  onChange: (checked: boolean) => void
}) {
  return (
    <label className="flex items-center gap-2">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="rounded border-slate-300"
      />
      <span className="text-sm text-slate-700">{label}</span>
    </label>
  )
}

function ArrayInputField({ label, value, onChange, placeholder }: {
  label: string
  value: string[]
  onChange: (value: string[]) => void
  placeholder?: string
}) {
  const [inputValue, setInputValue] = useState('')

  const handleAdd = () => {
    if (inputValue.trim()) {
      onChange([...value, inputValue.trim()])
      setInputValue('')
    }
  }

  const handleRemove = (index: number) => {
    onChange(value.filter((_, i) => i !== index))
  }

  return (
    <div className="block">
      <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="flex gap-2">
        <input
          type="text"
          className="input flex-1"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault()
              handleAdd()
            }
          }}
          placeholder={placeholder}
        />
        <button className="btn-secondary" type="button" onClick={handleAdd}>
          Добавить
        </button>
      </div>
      {value.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-2">
          {value.map((item, index) => (
            <span
              key={index}
              className="inline-flex items-center gap-1 rounded-md bg-blue-100 px-2 py-1 text-xs text-blue-800"
            >
              {item}
              <button
                type="button"
                className="text-blue-600 hover:text-blue-800"
                onClick={() => handleRemove(index)}
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

export default function CustomFieldsPage() {
  const { t } = useI18n()
  const [definitions, setDefinitions] = useState<CustomFieldDefinition[]>([])
  const [documentTypes, setDocumentTypes] = useState<DocType[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [editingDefinition, setEditingDefinition] = useState<CustomFieldDefinition | null>(null)
  const [newDefinitionMode, setNewDefinitionMode] = useState(false)
  const [scopeFilter, setScopeFilter] = useState<CustomFieldScope | ''>('')

  const loadDefinitions = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [defsData, typesData] = await Promise.all([
        listCustomFieldDefinitions(scopeFilter ? { scope: scopeFilter } : {}),
        getDocumentTypes(),
      ])
      setDefinitions(defsData)
      setDocumentTypes(typesData || [])
    } catch (err: any) {
      setError(err?.message || 'Не удалось загрузить определения полей')
    } finally {
      setLoading(false)
    }
  }, [scopeFilter])

  useEffect(() => {
    void loadDefinitions()
  }, [loadDefinitions])

  const handleCreate = async (payload: CustomFieldDefinitionCreate) => {
    try {
      setError(null)
      await createCustomFieldDefinition(payload)
      await loadDefinitions()
      setNewDefinitionMode(false)
    } catch (err: any) {
      setError(err?.message || 'Не удалось создать определение поля')
      throw err
    }
  }

  const handleUpdate = async (definitionId: string, payload: CustomFieldDefinitionCreate) => {
    try {
      setError(null)
      await updateCustomFieldDefinition(definitionId, payload)
      await loadDefinitions()
      setEditingDefinition(null)
    } catch (err: any) {
      setError(err?.message || 'Не удалось обновить определение поля')
      throw err
    }
  }

  const handleDelete = async (definitionId: string) => {
    if (!confirm('Удалить это определение поля?')) return
    try {
      setError(null)
      await deleteCustomFieldDefinition(definitionId)
      await loadDefinitions()
    } catch (err: any) {
      setError(err?.message || 'Не удалось удалить определение поля')
    }
  }

  const scopeOptions: Array<{ value: CustomFieldScope; label: string }> = [
    { value: 'CANDIDATE', label: 'Кандидат' },
    { value: 'DOCUMENT', label: 'Документ' },
  ]

  const fieldTypeOptions: Array<{ value: CustomFieldType; label: string }> = [
    { value: 'TEXT', label: 'Текст' },
    { value: 'TEXTAREA', label: 'Многострочный текст' },
    { value: 'NUMBER', label: 'Число' },
    { value: 'DATE', label: 'Дата' },
    { value: 'CHECKBOX', label: 'Чекбокс' },
    { value: 'SELECT', label: 'Выбор (один)' },
    { value: 'MULTISELECT', label: 'Выбор (несколько)' },
  ]

  const documentTypeOptions = documentTypes.map((dt) => ({
    value: dt.id || dt.code || '',
    label: dt.name || dt.code || dt.id || '',
  }))

  const filteredDefinitions = scopeFilter
    ? definitions.filter((d) => d.scope === scopeFilter)
    : definitions

  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <header className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-slate-900">Кастомные поля</h2>
            <p className="text-sm text-slate-500">Управление дополнительными полями для кандидатов и документов</p>
          </div>
          <button
            className="btn-primary"
            type="button"
            onClick={() => {
              setNewDefinitionMode(true)
              setEditingDefinition(null)
            }}
          >
            Создать поле
          </button>
        </header>

        <div className="mb-4">
          <SelectField
            label="Фильтр по области"
            value={scopeFilter}
            onChange={(value) => setScopeFilter(value as CustomFieldScope | '')}
            options={[{ value: '', label: 'Все' }, ...scopeOptions]}
            allowEmpty={false}
          />
        </div>

        {error && (
          <div className="mb-4">
            <ErrorRecoveryBanner
              info={{
                title: error,
                hint: t('app.common.retry_hint', { defaultValue: 'Повторите действие или обновите страницу.' }),
              }}
              onRetry={() => void loadDefinitions()}
              retryLabel={t('common.actions.refresh', { defaultValue: 'Обновить' })}
              secondaryTo="/app/settings/crm/custom-fields"
              secondaryLabel={t('common.navigation.settings', { defaultValue: 'Настройки' })}
              compact
            />
          </div>
        )}

        {loading ? (
          <div className="text-sm text-slate-500">Загрузка...</div>
        ) : (
          <div className="space-y-4">
            {newDefinitionMode && (
              <DefinitionForm
                documentTypes={documentTypeOptions}
                scopeOptions={scopeOptions}
                fieldTypeOptions={fieldTypeOptions}
                onSave={handleCreate}
                onCancel={() => setNewDefinitionMode(false)}
                t={t}
              />
            )}
            {editingDefinition && (
              <DefinitionForm
                definition={editingDefinition}
                documentTypes={documentTypeOptions}
                scopeOptions={scopeOptions}
                fieldTypeOptions={fieldTypeOptions}
                onSave={(payload) => handleUpdate(editingDefinition.id, payload)}
                onCancel={() => setEditingDefinition(null)}
                t={t}
              />
            )}
            {!newDefinitionMode && !editingDefinition && filteredDefinitions.length === 0 ? (
              <p className="text-sm text-slate-500">
                Определения полей не созданы. Нажмите "Создать поле" для создания.
              </p>
            ) : null}
            {!newDefinitionMode && !editingDefinition && filteredDefinitions.length > 0 ? (
              <div className="space-y-3">
                {filteredDefinitions.map((def) => {
                  const docType = documentTypes.find((dt) => (dt.id || dt.code) === def.document_type_id)
                  return (
                    <div key={def.id} className="rounded-lg border border-slate-200 bg-white p-4">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 space-y-2">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-slate-900">{def.label}</span>
                            <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-mono text-slate-600">
                              {def.key}
                            </span>
                            <span className="rounded-md bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800">
                              {def.scope === 'CANDIDATE' ? 'Кандидат' : 'Документ'}
                            </span>
                            <span className="rounded-md bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-800">
                              {fieldTypeOptions.find((opt) => opt.value === def.field_type)?.label || def.field_type}
                            </span>
                            {def.required && (
                              <span className="rounded-md bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                                Обязательно
                              </span>
                            )}
                            {!def.is_active && (
                              <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                                Неактивно
                              </span>
                            )}
                            {def.is_system && (
                              <span className="rounded-md bg-slate-900 px-2 py-0.5 text-xs font-medium text-white">
                                System
                              </span>
                            )}
                          </div>
                          {def.help_text && <p className="text-sm text-slate-600">{def.help_text}</p>}
                          {def.scope === 'DOCUMENT' && def.document_type_id && (
                            <p className="text-xs text-slate-500">
                              Тип документа: {docType?.name || docType?.code || def.document_type_id}
                            </p>
                          )}
                          {def.options && def.options.length > 0 && (
                            <p className="text-xs text-slate-500">
                              Варианты: {def.options.join(', ')}
                            </p>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            className="btn-secondary btn-sm"
                            type="button"
                            onClick={() => setEditingDefinition(def)}
                            disabled={def.is_system}
                          >
                            Редактировать
                          </button>
                          <button
                            className="btn-danger btn-sm"
                            type="button"
                            onClick={() => handleDelete(def.id)}
                            disabled={def.is_system}
                          >
                            Удалить
                          </button>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : null}
          </div>
        )}
      </section>
    </div>
  )
}

function DefinitionForm({
  definition,
  documentTypes,
  scopeOptions,
  fieldTypeOptions,
  onSave,
  onCancel,
  t,
}: {
  definition?: CustomFieldDefinition | null
  documentTypes: Array<{ value: string; label: string }>
  scopeOptions: Array<{ value: CustomFieldScope; label: string }>
  fieldTypeOptions: Array<{ value: CustomFieldType; label: string }>
  onSave: (payload: CustomFieldDefinitionCreate) => Promise<void>
  onCancel: () => void
  t: (key: string, opts?: { defaultValue?: string }) => string
}) {
  const [scope, setScope] = useState<CustomFieldScope>(definition?.scope || 'CANDIDATE')
  const [documentTypeId, setDocumentTypeId] = useState(definition?.document_type_id || '')
  const [key, setKey] = useState(definition?.key || '')
  const [label, setLabel] = useState(definition?.label || '')
  const [fieldType, setFieldType] = useState<CustomFieldType>(definition?.field_type || 'TEXT')
  const [required, setRequired] = useState(definition?.required ?? false)
  const [options, setOptions] = useState<string[]>(definition?.options || [])
  const [helpText, setHelpText] = useState(definition?.help_text || '')
  const [isActive, setIsActive] = useState(definition?.is_active ?? true)
  const [order, setOrder] = useState(definition?.order || 0)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const handleSubmit = async () => {
    if (!key.trim() || !label.trim()) {
      setFormError('Ключ и название обязательны')
      return
    }

    if (scope === 'DOCUMENT' && !documentTypeId) {
      setFormError('Тип документа обязателен для полей документов')
      return
    }

    if ((fieldType === 'SELECT' || fieldType === 'MULTISELECT') && (!options || options.length === 0)) {
      setFormError('Варианты выбора обязательны для полей типа SELECT/MULTISELECT')
      return
    }

    setSaving(true)
    setFormError(null)
    try {
      await onSave({
        scope,
        document_type_id: scope === 'DOCUMENT' ? documentTypeId : null,
        key: key.trim(),
        label: label.trim(),
        field_type: fieldType,
        required,
        options: (fieldType === 'SELECT' || fieldType === 'MULTISELECT') ? options : null,
        help_text: helpText || null,
        is_active: isActive,
        order,
      })
    } catch (err: any) {
      setFormError(err?.message || 'Не удалось сохранить определение поля')
    } finally {
      setSaving(false)
    }
  }

  const needsOptions = fieldType === 'SELECT' || fieldType === 'MULTISELECT'

  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
      <h3 className="mb-3 text-base font-semibold text-blue-800">
        {definition ? 'Редактировать определение поля' : 'Создать определение поля'}
      </h3>
      <div className="space-y-3">
        <SelectField
          label="Область"
          value={scope}
          onChange={(value) => {
            setScope(value as CustomFieldScope)
            if (value === 'CANDIDATE') {
              setDocumentTypeId('')
            }
          }}
          options={scopeOptions}
          allowEmpty={false}
          disabled={!!definition}
        />
        {scope === 'DOCUMENT' && (
          <SelectField
            label="Тип документа"
            value={documentTypeId}
            onChange={setDocumentTypeId}
            options={documentTypes}
            allowEmpty={false}
            disabled={!!definition}
          />
        )}
        <TextField
          label="Ключ (уникальный идентификатор)"
          value={key}
          onChange={setKey}
          disabled={!!definition}
          placeholder={t('admin.custom_fields.form.key_placeholder', { defaultValue: 'custom_field_key' })}
        />
        <TextField
          label="Название"
          value={label}
          onChange={setLabel}
          placeholder="Название поля"
        />
        <SelectField
          label="Тип поля"
          value={fieldType}
          onChange={(value) => {
            setFieldType(value as CustomFieldType)
            if (!needsOptions && (value === 'SELECT' || value === 'MULTISELECT')) {
              setOptions([])
            }
          }}
          options={fieldTypeOptions}
          allowEmpty={false}
        />
        {needsOptions && (
          <ArrayInputField
            label="Варианты выбора"
            value={options}
            onChange={setOptions}
            placeholder={t('admin.custom_fields.form.option_placeholder', { defaultValue: 'Введите вариант и нажмите Enter' })}
          />
        )}
        <CheckboxField
          label="Обязательное поле"
          checked={required}
          onChange={setRequired}
        />
        <TextareaField
          label="Подсказка"
          value={helpText}
          onChange={setHelpText}
          rows={2}
          placeholder="Текст подсказки для пользователя..."
        />
        <CheckboxField
          label="Активно"
          checked={isActive}
          onChange={setIsActive}
        />
        <TextField
          label="Порядок отображения"
          value={order.toString()}
          onChange={(value) => setOrder(parseInt(value, 10) || 0)}
          type="number"
        />
        {formError && <div className="text-sm text-rose-700">{formError}</div>}
        <div className="flex gap-2 justify-end">
          <button className="btn-secondary" type="button" onClick={onCancel} disabled={saving}>
            Отмена
          </button>
          <button className="btn-primary" type="button" onClick={handleSubmit} disabled={saving}>
            {saving ? 'Сохранение...' : 'Сохранить'}
          </button>
        </div>
      </div>
    </div>
  )
}
