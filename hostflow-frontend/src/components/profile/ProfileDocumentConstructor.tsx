import { useCallback, useEffect, useMemo, useState } from 'react'
import { getDocumentTypes, type DocType } from '../../api/documents'

export interface DocumentConfig {
  document_type_id: string
  document_type_code: string
  required: boolean
  enabled: boolean
  alert_days_before_expiry: number | null
  order: number
}

interface ProfileDocumentConstructorProps {
  value: DocumentConfig[]
  onChange: (configs: DocumentConfig[]) => void
  disabled?: boolean
}

export default function ProfileDocumentConstructor({
  value,
  onChange,
  disabled = false,
}: ProfileDocumentConstructorProps) {
  const [documentTypes, setDocumentTypes] = useState<DocType[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadDocumentTypes = async () => {
      try {
        const types = await getDocumentTypes()
        setDocumentTypes(types)
      } catch (err) {
        console.error('Failed to load document types', err)
      } finally {
        setLoading(false)
      }
    }
    void loadDocumentTypes()
  }, [])

  const availableDocumentTypes = useMemo(() => {
    const usedIds = new Set(value.map((d) => d.document_type_id))
    return documentTypes.filter((dt) => {
      const id = dt.id || dt.code
      return id && !usedIds.has(id)
    })
  }, [documentTypes, value])

  const handleAddDocument = useCallback(
    (docType: DocType) => {
      const id = docType.id || docType.code
      if (!id) return

      const newConfig: DocumentConfig = {
        document_type_id: id,
        document_type_code: docType.code,
        required: false,
        enabled: true,
        alert_days_before_expiry: null,
        order: value.length + 1,
      }
      onChange([...value, newConfig])
    },
    [value, onChange]
  )

  const handleRemoveDocument = useCallback(
    (index: number) => {
      const newConfigs = value.filter((_, i) => i !== index)
      // Reorder
      const reordered = newConfigs.map((config, idx) => ({
        ...config,
        order: idx + 1,
      }))
      onChange(reordered)
    },
    [value, onChange]
  )

  const handleUpdateDocument = useCallback(
    (index: number, patch: Partial<DocumentConfig>) => {
      const newConfigs = [...value]
      newConfigs[index] = { ...newConfigs[index], ...patch }
      onChange(newConfigs)
    },
    [value, onChange]
  )

  if (loading) {
    return <div className="text-sm text-slate-500">Загрузка типов документов...</div>
  }

  return (
    <div className="space-y-4">
      {/* Available documents */}
      <div>
        <h4 className="mb-2 text-sm font-medium text-slate-700">Доступные документы</h4>
        {availableDocumentTypes.length === 0 ? (
          <p className="text-sm text-slate-500">Все документы добавлены</p>
        ) : (
          <div className="grid grid-cols-1 gap-2 md:grid-cols-2 lg:grid-cols-3">
            {availableDocumentTypes.map((docType) => (
              <button
                key={docType.id || docType.code}
                type="button"
                onClick={() => handleAddDocument(docType)}
                disabled={disabled}
                className="rounded-lg border border-slate-200 bg-white p-2 text-left text-sm transition-colors hover:border-blue-300 hover:bg-blue-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <div className="font-medium text-slate-900">{docType.name || docType.code}</div>
                {docType.description && (
                  <div className="text-xs text-slate-500">{docType.description}</div>
                )}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Configured documents */}
      <div>
        <h4 className="mb-2 text-sm font-medium text-slate-700">Документы в профиле</h4>
        {value.length === 0 ? (
          <p className="text-sm text-slate-500">Нет документов. Добавьте документы из списка выше.</p>
        ) : (
          <div className="space-y-2">
            {value.map((config, index) => {
              const docType = documentTypes.find(
                (dt) => (dt.id || dt.code) === config.document_type_id
              )
              const docTypeName = docType?.name || docType?.code || config.document_type_code

              return (
                <div
                  key={`${config.document_type_id}-${index}`}
                  className="rounded-lg border border-slate-200 bg-white p-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 space-y-2">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-slate-900">{docTypeName}</span>
                        {config.required && (
                          <span className="rounded-md bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                            Обязательный
                          </span>
                        )}
                        {!config.enabled && (
                          <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                            Отключен
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-4">
                        <label className="flex items-center gap-1">
                          <input
                            type="checkbox"
                            checked={config.enabled}
                            onChange={(e) =>
                              handleUpdateDocument(index, { enabled: e.target.checked })
                            }
                            disabled={disabled}
                            className="rounded border-slate-300"
                          />
                          <span className="text-xs text-slate-600">Включен</span>
                        </label>
                        <label className="flex items-center gap-1">
                          <input
                            type="checkbox"
                            checked={config.required}
                            onChange={(e) =>
                              handleUpdateDocument(index, { required: e.target.checked })
                            }
                            disabled={disabled}
                            className="rounded border-slate-300"
                          />
                          <span className="text-xs text-slate-600">Обязательный</span>
                        </label>
                        <label className="flex items-center gap-1">
                          <span className="text-xs text-slate-600">Оповещение за:</span>
                          <input
                            type="number"
                            min="1"
                            max="365"
                            value={config.alert_days_before_expiry || ''}
                            onChange={(e) => {
                              const val = e.target.value
                              handleUpdateDocument(index, {
                                alert_days_before_expiry: val ? parseInt(val, 10) : null,
                              })
                            }}
                            disabled={disabled}
                            className="w-16 rounded border-slate-300 px-2 py-1 text-xs"
                            placeholder="дней"
                          />
                          <span className="text-xs text-slate-600">дней</span>
                        </label>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleRemoveDocument(index)}
                      disabled={disabled}
                      className="btn-danger btn-xs disabled:opacity-50"
                    >
                      ✕
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
