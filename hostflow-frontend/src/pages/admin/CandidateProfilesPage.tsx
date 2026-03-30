import { useCallback, useEffect, useMemo, useState } from 'react'
import { useI18n } from '../../i18n'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import {
  listCandidateProfiles,
  createCandidateProfile,
  updateCandidateProfile,
  deleteCandidateProfile,
  fixOrphanedVacancies,
  type CandidateProfile,
  type CandidateProfileCreate,
} from '../../api/candidate_profiles'
import ProfileFieldConstructor, { type FieldConfig } from '../../components/profile/ProfileFieldConstructor'
import ProfileDocumentConstructor from '../../components/profile/ProfileDocumentConstructor'
import FunnelSelector from '../../components/profile/FunnelSelector'
import ProfilePreviewModal from '../../components/profile/ProfilePreviewModal'
import type { FriendlyErrorInfo } from '../../utils/friendlyError'
import { friendlyErrorBannerSecondary } from '../../utils/friendlyError'
import ImportProfileModal from '../../components/profile/ImportProfileModal'
import ApplyProfileToVacanciesModal from '../../components/profile/ApplyProfileToVacanciesModal'
import BulkUpdateProfilesModal from '../../components/profile/BulkUpdateProfilesModal'
import ProfileUsageStatsModal from '../../components/profile/ProfileUsageStatsModal'
import ProfileHistoryModal from '../../components/profile/ProfileHistoryModal'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
// Field components (inline, similar to Companies.tsx)
function TextField({ label, value, onChange, placeholder, disabled, type, className }: {
  label: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
  disabled?: boolean
  type?: string
  className?: string
}) {
  return (
    <label className="block">
      <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <input
        type={type || 'text'}
        className={`input w-full ${className || ''}`}
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

export default function CandidateProfilesPage() {
  const { t } = useI18n()
  const [profiles, setProfiles] = useState<CandidateProfile[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [editingProfile, setEditingProfile] = useState<CandidateProfile | null>(null)
  const [newProfileMode, setNewProfileMode] = useState(false)
  const [previewProfile, setPreviewProfile] = useState<CandidateProfile | null>(null)
  const [usageStatsProfile, setUsageStatsProfile] = useState<CandidateProfile | null>(null)
  const [historyProfile, setHistoryProfile] = useState<CandidateProfile | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterActive, setFilterActive] = useState<boolean | null>(null)
  const [importMode, setImportMode] = useState(false)
  const [applyToVacanciesMode, setApplyToVacanciesMode] = useState<CandidateProfile | null>(null)
  const [bulkUpdateMode, setBulkUpdateMode] = useState(false)
  const [sortBy, setSortBy] = useState<'name' | 'code' | 'created_at' | 'fields_count' | 'stages_count' | 'usage_count'>('name')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc')

  const loadProfiles = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      // Загружаем все профили для фильтрации
      const profilesData = await listCandidateProfiles({ is_active: undefined })
      setProfiles(profilesData)
    } catch (err: any) {
      setError(err?.message || 'Не удалось загрузить профили')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadProfiles()
  }, [loadProfiles])

  const validateProfile = (payload: CandidateProfileCreate, isUpdate: boolean = false): string | null => {
    // Проверка обязательных полей
    if (!payload.code?.trim()) {
      return 'Код профиля обязателен'
    }
    if (!payload.name?.trim()) {
      return 'Название профиля обязательно'
    }

    // Проверка уникальности кода (только при создании)
    if (!isUpdate && profiles.some((p) => p.code === payload.code.trim())) {
      return `Профиль с кодом "${payload.code.trim()}" уже существует`
    }

    // Проверка формата кода (только латинские буквы, цифры и подчеркивание)
    if (!/^[a-z0-9_]+$/.test(payload.code.trim().toLowerCase())) {
      return 'Код может содержать только латинские буквы, цифры и подчеркивание'
    }

    // Предупреждения (не блокирующие, но важные)
    const warnings: string[] = []
    if (!payload.config?.field_configs || payload.config.field_configs.length === 0) {
      warnings.push('В профиле нет настроенных полей')
    }
    if (!payload.funnel_id && (!payload.config?.stage_configs || payload.config.stage_configs.length === 0)) {
      warnings.push('В профиле нет воронки и нет этапов (выберите воронку или добавьте этапы)')
    }
    if (!payload.config?.document_configs || payload.config.document_configs.length === 0) {
      warnings.push('В профиле нет настроенных документов')
    }

    // Сохраняем предупреждения в localStorage для отображения после сохранения
    if (warnings.length > 0) {
      localStorage.setItem('hf:profile-validation-warnings', JSON.stringify(warnings))
    } else {
      localStorage.removeItem('hf:profile-validation-warnings')
    }

    return null
  }

  const handleCreate = async (payload: CandidateProfileCreate) => {
    try {
      setError(null)
      
      // Валидация перед созданием
      const validationError = validateProfile(payload, false)
      if (validationError) {
        setError(validationError)
        throw new Error(validationError)
      }

      await createCandidateProfile(payload)
      
      // Проверяем предупреждения после успешного сохранения
      const warningsJson = localStorage.getItem('hf:profile-validation-warnings')
      if (warningsJson) {
        try {
          const warnings = JSON.parse(warningsJson) as string[]
          if (warnings.length > 0) {
            // Показываем предупреждения, но не блокируем сохранение
            console.warn('Предупреждения при создании профиля:', warnings.join(', '))
          }
          localStorage.removeItem('hf:profile-validation-warnings')
        } catch {
          // Игнорируем ошибки парсинга
        }
      }
      
      await loadProfiles()
      setNewProfileMode(false)
    } catch (err: any) {
      if (!err?.message?.includes('Код профиля') && !err?.message?.includes('Название профиля')) {
        setError(err?.message || 'Не удалось создать профиль')
      }
      throw err
    }
  }

  const handleUpdate = async (profileId: string, payload: CandidateProfileCreate) => {
    try {
      setError(null)
      
      // Валидация перед обновлением
      const validationError = validateProfile(payload, true)
      if (validationError) {
        setError(validationError)
        throw new Error(validationError)
      }

      await updateCandidateProfile(profileId, payload)
      
      // Проверяем предупреждения после успешного сохранения
      const warningsJson = localStorage.getItem('hf:profile-validation-warnings')
      if (warningsJson) {
        try {
          const warnings = JSON.parse(warningsJson) as string[]
          if (warnings.length > 0) {
            console.warn('Предупреждения при обновлении профиля:', warnings.join(', '))
          }
          localStorage.removeItem('hf:profile-validation-warnings')
        } catch {
          // Игнорируем ошибки парсинга
        }
      }
      
      await loadProfiles()
      setEditingProfile(null)
    } catch (err: any) {
      if (!err?.message?.includes('Код профиля') && !err?.message?.includes('Название профиля')) {
        setError(err?.message || 'Не удалось обновить профиль')
      }
      throw err
    }
  }

  const handleDelete = async (profileId: string) => {
    if (!confirm('Удалить этот профиль?')) return
    try {
      setError(null)
      await deleteCandidateProfile(profileId)
      await loadProfiles()
    } catch (err: any) {
      setError(err?.message || 'Не удалось удалить профиль')
    }
  }

  const handleDuplicate = async (profile: CandidateProfile) => {
    try {
      setError(null)
      // Генерируем новый код для копии
      const baseCode = profile.code
      let newCode = `${baseCode}_copy`
      let counter = 1
      
      // Проверяем, что код уникален
      while (profiles.some((p) => p.code === newCode)) {
        newCode = `${baseCode}_copy_${counter}`
        counter++
      }

      // Создаем копию профиля
      const duplicatePayload: CandidateProfileCreate = {
        code: newCode,
        name: `${profile.name} (копия)`,
        description: profile.description,
        client_id: profile.client_id,
        funnel_id: profile.funnel_id ?? undefined,
        config: profile.config || {},
        notes: profile.notes,
      }

      await createCandidateProfile(duplicatePayload)
      await loadProfiles()
    } catch (err: any) {
      setError(err?.message || 'Не удалось скопировать профиль')
    }
  }

  const handleExport = (profile: CandidateProfile) => {
    try {
      // Формируем объект для экспорта
      const exportData = {
        version: '1.0',
        exported_at: new Date().toISOString(),
        profile: {
          code: profile.code,
          name: profile.name,
          description: profile.description,
          notes: profile.notes,
          config: profile.config || {},
        },
      }

      // Создаем JSON строку
      const jsonString = JSON.stringify(exportData, null, 2)

      // Создаем blob и скачиваем файл
      const blob = new Blob([jsonString], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `profile_${profile.code}_${new Date().toISOString().split('T')[0]}.json`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
    } catch (err: any) {
      setError(err?.message || 'Не удалось экспортировать профиль')
    }
  }

  const handleImport = async (file: File) => {
    try {
      setError(null)
      const text = await file.text()
      const importData = JSON.parse(text)

      // Валидация структуры
      if (!importData.profile) {
        throw new Error('Неверный формат файла: отсутствует поле "profile"')
      }

      const importedProfile = importData.profile

      if (!importedProfile.code || !importedProfile.name) {
        throw new Error('Неверный формат файла: отсутствуют обязательные поля "code" или "name"')
      }

      // Проверяем, что код уникален
      if (profiles.some((p) => p.code === importedProfile.code)) {
        // Если профиль с таким кодом уже существует, предлагаем переименовать
        let newCode = `${importedProfile.code}_imported`
        let counter = 1
        while (profiles.some((p) => p.code === newCode)) {
          newCode = `${importedProfile.code}_imported_${counter}`
          counter++
        }
        importedProfile.code = newCode
        importedProfile.name = `${importedProfile.name} (импортирован)`
      }

      // Создаем профиль из импортированных данных
      const importPayload: CandidateProfileCreate = {
        code: importedProfile.code,
        name: importedProfile.name,
        description: importedProfile.description || null,
        client_id: importedProfile.client_id || null,
        config: importedProfile.config || {},
        notes: importedProfile.notes || null,
      }

      await createCandidateProfile(importPayload)
      await loadProfiles()
    } catch (err: any) {
      if (err instanceof SyntaxError) {
        setError('Неверный формат JSON файла')
      } else {
        setError(err?.message || 'Не удалось импортировать профиль')
      }
      throw err
    }
  }

  const profilesLoadErrorBanner = useMemo<FriendlyErrorInfo | null>(
    () =>
      error
        ? {
            title: error,
            hint: t('app.common.retry_hint', { defaultValue: 'Повторите действие или обновите страницу.' }),
          }
        : null,
    [error, t],
  )

  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <header className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-slate-900">Профили кандидатов</h2>
            <p className="text-sm text-slate-500">Управление профилями кандидатов для вакансий</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              className="btn-secondary btn-sm"
              type="button"
              onClick={async () => {
                try {
                  const { updated } = await fixOrphanedVacancies()
                  if (updated > 0) await loadProfiles()
                  alert(updated > 0 ? `Привязано вакансий: ${updated}` : 'Нет вакансий без профиля или с удалённым профилем.')
                } catch (e: any) {
                  alert(e?.response?.data?.detail ?? 'Ошибка')
                }
              }}
            >
              Привязать вакансии без профиля
            </button>
            <button
              className="btn-secondary"
              type="button"
              onClick={() => setImportMode(true)}
            >
              Импорт
            </button>
            <button
              className="btn-secondary"
              type="button"
              onClick={() => setBulkUpdateMode(true)}
            >
              Массовое изменение
            </button>
            <button
              className="btn-primary"
              type="button"
              onClick={() => {
                setNewProfileMode(true)
                setEditingProfile(null)
              }}
            >
              Создать профиль
            </button>
          </div>
        </header>

        {/* Поиск и фильтры */}
        {!newProfileMode && !editingProfile && profiles.length > 0 && (
          <div className="mb-4 space-y-2">
            <div className="flex gap-3">
              <input
                type="text"
                placeholder="Поиск по названию или коду..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="input flex-1"
              />
              <select
                value={filterActive === null ? 'all' : filterActive ? 'active' : 'inactive'}
                onChange={(e) => {
                  const val = e.target.value
                  setFilterActive(val === 'all' ? null : val === 'active')
                }}
                className="input"
              >
                <option value="all">Все</option>
                <option value="active">Активные</option>
                <option value="inactive">Неактивные</option>
              </select>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
                className="input"
              >
                <option value="name">Сортировка: Название</option>
                <option value="code">Сортировка: Код</option>
                <option value="created_at">Сортировка: Дата создания</option>
                <option value="fields_count">Сортировка: Количество полей</option>
                <option value="stages_count">Сортировка: Количество этапов</option>
                <option value="usage_count">Сортировка: Использование</option>
              </select>
              <button
                type="button"
                onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                className="btn-secondary btn-sm"
                title={sortOrder === 'asc' ? 'По возрастанию' : 'По убыванию'}
              >
                {sortOrder === 'asc' ? '↑' : '↓'}
              </button>
            </div>
            {(() => {
              // Фильтрация
              const filtered = profiles.filter((profile) => {
                if (searchQuery) {
                  const query = searchQuery.toLowerCase()
                  const matchesName = profile.name.toLowerCase().includes(query)
                  const matchesCode = profile.code.toLowerCase().includes(query)
                  const matchesDescription = profile.description?.toLowerCase().includes(query) || false
                  if (!matchesName && !matchesCode && !matchesDescription) return false
                }
                if (filterActive !== null) {
                  if (filterActive && !profile.is_active) return false
                  if (!filterActive && profile.is_active) return false
                }
                return true
              })

              // Сортировка
              const sorted = [...filtered].sort((a, b) => {
                let comparison = 0
                
                switch (sortBy) {
                  case 'name':
                    comparison = (a.name || '').localeCompare(b.name || '', undefined, { sensitivity: 'base' })
                    break
                  case 'code':
                    comparison = (a.code || '').localeCompare(b.code || '', undefined, { sensitivity: 'base' })
                    break
                  case 'created_at':
                    comparison = new Date(a.created_at || 0).getTime() - new Date(b.created_at || 0).getTime()
                    break
                  case 'fields_count': {
                    const aFieldsCount = (a.config?.field_configs as any[])?.length || 0
                    const bFieldsCount = (b.config?.field_configs as any[])?.length || 0
                    comparison = aFieldsCount - bFieldsCount
                    break
                  }
                  case 'stages_count': {
                    const aStagesCount = a.funnel_id ? 1 : (a.config?.stage_configs as any[])?.length || 0
                    const bStagesCount = b.funnel_id ? 1 : (b.config?.stage_configs as any[])?.length || 0
                    comparison = aStagesCount - bStagesCount
                    break
                  }
                  case 'usage_count':
                    comparison = (a.usage_count || 0) - (b.usage_count || 0)
                    break
                }
                
                return sortOrder === 'asc' ? comparison : -comparison
              })

              const filteredCount = filtered.length

              if (searchQuery || filterActive !== null) {
                return (
                  <div className="text-sm text-slate-500">
                    Найдено: {filteredCount} из {profiles.length} профилей
                  </div>
                )
              }
              return null
            })()}
          </div>
        )}

        {profilesLoadErrorBanner && (
          <div className="mb-4">
            <ErrorRecoveryBanner
              info={profilesLoadErrorBanner}
              onRetry={() => void loadProfiles()}
              retryLabel={t('common.actions.refresh', { defaultValue: 'Обновить' })}
              {...friendlyErrorBannerSecondary(
                profilesLoadErrorBanner,
                CRM_APP_PATHS.settingsCandidateProfiles,
                t('common.navigation.settings', { defaultValue: 'Настройки' }),
              )}
              compact
            />
          </div>
        )}

        {loading ? (
          <div className="text-sm text-slate-500">Загрузка...</div>
        ) : (
          <div className="space-y-4">
            {newProfileMode && (
              <ProfileForm
                onSave={handleCreate}
                onCancel={() => setNewProfileMode(false)}
                t={t}
                profiles={profiles}
              />
            )}
            {editingProfile && (
              <ProfileForm
                profile={editingProfile}
                onSave={(payload) => handleUpdate(editingProfile.id, payload)}
                onCancel={() => setEditingProfile(null)}
                t={t}
                profiles={profiles}
              />
            )}
            {!newProfileMode && !editingProfile && (() => {
              const filtered = profiles.filter((profile) => {
                // Фильтр по поисковому запросу
                if (searchQuery) {
                  const query = searchQuery.toLowerCase()
                  const matchesName = profile.name.toLowerCase().includes(query)
                  const matchesCode = profile.code.toLowerCase().includes(query)
                  const matchesDescription = profile.description?.toLowerCase().includes(query) || false
                  if (!matchesName && !matchesCode && !matchesDescription) {
                    return false
                  }
                }
                // Фильтр по активности
                if (filterActive !== null) {
                  if (filterActive && !profile.is_active) return false
                  if (!filterActive && profile.is_active) return false
                }
                return true
              })

              if (profiles.length === 0) {
                return (
                  <p className="text-sm text-slate-500">
                    Профили не созданы. Нажмите "Создать профиль" для создания.
                  </p>
                )
              }

              if (filtered.length === 0) {
                return (
                  <p className="text-sm text-slate-500">
                    Профили не найдены. Измените параметры поиска или фильтры.
                  </p>
                )
              }

              // Сортировка
              const sorted = [...filtered].sort((a, b) => {
                let comparison = 0
                
                switch (sortBy) {
                  case 'name':
                    comparison = (a.name || '').localeCompare(b.name || '', undefined, { sensitivity: 'base' })
                    break
                  case 'code':
                    comparison = (a.code || '').localeCompare(b.code || '', undefined, { sensitivity: 'base' })
                    break
                  case 'created_at':
                    comparison = new Date(a.created_at || 0).getTime() - new Date(b.created_at || 0).getTime()
                    break
                  case 'fields_count': {
                    const aFieldsCount = (a.config?.field_configs as any[])?.length || 0
                    const bFieldsCount = (b.config?.field_configs as any[])?.length || 0
                    comparison = aFieldsCount - bFieldsCount
                    break
                  }
                  case 'stages_count': {
                    const aStagesCount = a.funnel_id ? 1 : (a.config?.stage_configs as any[])?.length || 0
                    const bStagesCount = b.funnel_id ? 1 : (b.config?.stage_configs as any[])?.length || 0
                    comparison = aStagesCount - bStagesCount
                    break
                  }
                  case 'usage_count':
                    comparison = (a.usage_count || 0) - (b.usage_count || 0)
                    break
                }
                
                return sortOrder === 'asc' ? comparison : -comparison
              })

              return (
                <div className="space-y-3">
                  {sorted.map((profile: typeof profiles[0]) => (
                    <div key={profile.id} className="rounded-lg border border-slate-200 bg-white p-4">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 space-y-2">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-slate-900">{profile.name}</span>
                            <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-mono text-slate-600">
                              {profile.code}
                            </span>
                            {!profile.is_active && (
                              <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                                Неактивен
                              </span>
                            )}
                            {profile.is_system && (
                              <span className="rounded-md bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800">
                                Системный
                              </span>
                            )}
                            {profile.code === 'driver_ce_default' && (
                              <span className="rounded-md bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                                По умолчанию
                              </span>
                            )}
                            {(profile.usage_count ?? 0) > 0 && (
                              <span className="rounded-md bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">
                                Используется в {profile.usage_count} вакансиях
                              </span>
                            )}
                          </div>
                          {profile.description && (
                            <p className="text-sm text-slate-600">{profile.description}</p>
                          )}
                          {profile.notes && <p className="text-xs text-slate-500">{profile.notes}</p>}
                          {/* Краткая статистика профиля */}
                          {profile.config && (
                            <div className="flex gap-3 text-xs text-slate-500">
                              {profile.config.field_configs && Array.isArray(profile.config.field_configs) && (
                                <span>
                                  {profile.config.field_configs.filter((f: any) => f.visible !== false).length} полей
                                  {profile.config.field_configs.filter((f: any) => f.required === true).length > 0 && (
                                    <span className="ml-1 text-red-600">
                                      ({profile.config.field_configs.filter((f: any) => f.required === true).length} обязательных)
                                    </span>
                                  )}
                                </span>
                              )}
                                              {(profile.funnel_id || (profile.config.stage_configs && Array.isArray(profile.config.stage_configs))) && (
                                <span>
                                  {profile.funnel_id ? 'Воронка' : profile.config.stage_configs.filter((s: any) => s.active !== false).length + ' этапов'}
                                </span>
                              )}
                              {profile.config.document_configs && Array.isArray(profile.config.document_configs) && (
                                <span>
                                  {profile.config.document_configs.filter((d: any) => d.enabled !== false).length} документов
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            className="btn-secondary btn-sm"
                            type="button"
                            onClick={() => setPreviewProfile(profile)}
                            title="Предпросмотр профиля"
                          >
                            Просмотр
                          </button>
                          <button
                            className="btn-secondary btn-sm"
                            type="button"
                            onClick={() => setUsageStatsProfile(profile)}
                            title="Статистика использования профиля"
                          >
                            Статистика
                          </button>
                          <button
                            className="btn-secondary btn-sm"
                            type="button"
                            onClick={() => setHistoryProfile(profile)}
                            title="История изменений профиля"
                          >
                            История
                          </button>
                          {profile.is_system ? (
                            <button
                              className="btn-secondary btn-sm"
                              type="button"
                              onClick={() => handleDuplicate(profile)}
                              title="Создать копию профиля для редактирования"
                            >
                              Копировать
                            </button>
                          ) : (
                            <>
                              <button
                                className="btn-secondary btn-sm"
                                type="button"
                                onClick={() => setApplyToVacanciesMode(profile)}
                                title="Применить профиль к вакансиям"
                              >
                                Применить к вакансиям
                              </button>
                              <button
                                className="btn-secondary btn-sm"
                                type="button"
                                onClick={() => handleExport(profile)}
                                title={t('app.admin.candidate_profiles.actions.export_json', { defaultValue: 'Экспортировать профиль в JSON' })}
                              >
                                Экспорт
                              </button>
                              <button
                                className="btn-secondary btn-sm"
                                type="button"
                                onClick={() => handleDuplicate(profile)}
                                title="Скопировать профиль"
                              >
                                Копировать
                              </button>
                              <button
                                className="btn-secondary btn-sm disabled:opacity-50 disabled:cursor-not-allowed"
                                type="button"
                                onClick={() => setEditingProfile(profile)}
                                disabled={(profile.usage_count ?? 0) > 0}
                                title={(profile.usage_count ?? 0) > 0 ? 'Профиль используется в вакансиях. Создайте новый профиль для изменений.' : ''}
                              >
                                Редактировать
                              </button>
                              <button
                                className="btn-danger btn-sm disabled:opacity-50 disabled:cursor-not-allowed"
                                type="button"
                                onClick={() => handleDelete(profile.id)}
                                disabled={(profile.usage_count ?? 0) > 0}
                                title={(profile.usage_count ?? 0) > 0 ? 'Профиль используется в вакансиях. Нельзя удалить.' : ''}
                              >
                                Удалить
                              </button>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )
            })()}
          </div>
        )}
      </section>

      {/* Модальное окно предпросмотра профиля */}
      {previewProfile && (
        <ProfilePreviewModal
          profile={previewProfile}
          onClose={() => setPreviewProfile(null)}
          onDuplicate={() => {
            setPreviewProfile(null)
            handleDuplicate(previewProfile)
          }}
          onExport={() => {
            handleExport(previewProfile)
          }}
        />
      )}

      {/* Модальное окно импорта профиля */}
      {importMode && (
        <ImportProfileModal
          onClose={() => setImportMode(false)}
          onImport={async (file: File) => {
            try {
              await handleImport(file)
              setImportMode(false)
            } catch (err) {
              // Ошибка уже обработана в handleImport
            }
          }}
        />
      )}

      {/* Модальное окно применения профиля к вакансиям */}
      {applyToVacanciesMode && (
        <ApplyProfileToVacanciesModal
          profile={applyToVacanciesMode}
          onClose={() => setApplyToVacanciesMode(null)}
          onSuccess={() => {
            // Обновляем список профилей, чтобы обновить usage_count
            loadProfiles()
          }}
        />
      )}

      {/* Модальное окно массового изменения профилей */}
      {bulkUpdateMode && (
        <BulkUpdateProfilesModal
          onClose={() => setBulkUpdateMode(false)}
          onSuccess={() => {
            loadProfiles()
          }}
        />
      )}

      {/* Модальное окно статистики использования профиля */}
      {usageStatsProfile && (
        <ProfileUsageStatsModal
          profile={usageStatsProfile}
          onClose={() => setUsageStatsProfile(null)}
        />
      )}

      {/* Модальное окно истории изменений профиля */}
      {historyProfile && (
        <ProfileHistoryModal
          profile={historyProfile}
          onClose={() => setHistoryProfile(null)}
        />
      )}
    </div>
  )
}

function ProfileForm({
  profile,
  onSave,
  onCancel,
  t,
  profiles,
}: {
  profile?: CandidateProfile | null
  onSave: (payload: CandidateProfileCreate) => Promise<void>
  onCancel: () => void
  t: (key: string, opts?: { defaultValue?: string }) => string
  profiles?: CandidateProfile[]
}) {
  const [code, setCode] = useState(profile?.code || '')
  const [name, setName] = useState(profile?.name || '')
  const [description, setDescription] = useState(profile?.description || '')
  const [notes, setNotes] = useState(profile?.notes || '')
  const [codeError, setCodeError] = useState<string | null>(null)
  const [nameError, setNameError] = useState<string | null>(null)
  const [fieldConfigs, setFieldConfigs] = useState<FieldConfig[]>(() => {
    // Initialize from profile config or default fields
    if (profile?.config?.field_configs) {
      return profile.config.field_configs as FieldConfig[]
    }
    // Default: always include required system fields
    return [
      { field_key: 'first_name', field_type: 'text', required: true, order: 1, visible: true, label: 'Имя' },
      { field_key: 'last_name', field_type: 'text', required: true, order: 2, visible: true, label: 'Фамилия' },
      { field_key: 'email', field_type: 'text', required: false, order: 3, visible: true, label: 'Email' },
      { field_key: 'phone', field_type: 'text', required: false, order: 4, visible: true, label: 'Телефон' },
    ]
  })
  const [documentConfigs, setDocumentConfigs] = useState<Array<{
    document_type_id: string
    document_type_code: string
    required: boolean
    enabled: boolean
    alert_days_before_expiry: number | null
    order: number
  }>>(() => {
    // Initialize from profile config
    if (profile?.config?.document_configs) {
      return profile.config.document_configs as Array<{
        document_type_id: string
        document_type_code: string
        required: boolean
        enabled: boolean
        alert_days_before_expiry: number | null
        order: number
      }>
    }
    return []
  })
  const [funnelId, setFunnelId] = useState<string | null>(profile?.funnel_id ?? null)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  // Валидация кода в реальном времени
  const validateCode = (newCode: string) => {
    setCodeError(null)
    if (!newCode.trim()) {
      setCodeError('Код обязателен')
      return false
    }
    if (!/^[a-z0-9_]+$/.test(newCode.trim().toLowerCase())) {
      setCodeError('Код может содержать только латинские буквы, цифры и подчеркивание')
      return false
    }
    if (!profile && profiles && profiles.some((p) => p.code === newCode.trim())) {
      setCodeError(`Профиль с кодом "${newCode.trim()}" уже существует`)
      return false
    }
    return true
  }

  // Валидация названия
  const validateName = (newName: string) => {
    setNameError(null)
    if (!newName.trim()) {
      setNameError('Название обязательно')
      return false
    }
    return true
  }

  const handleCodeChange = (newCode: string) => {
    setCode(newCode)
    if (newCode.trim()) {
      validateCode(newCode)
    } else {
      setCodeError(null)
    }
  }

  const handleNameChange = (newName: string) => {
    setName(newName)
    if (newName.trim()) {
      validateName(newName)
    } else {
      setNameError(null)
    }
  }

  const handleSubmit = async () => {
    setCodeError(null)
    setNameError(null)
    setFormError(null)

    // Валидация перед сохранением
    const isCodeValid = validateCode(code)
    const isNameValid = validateName(name)

    if (!isCodeValid || !isNameValid) {
      return
    }

    // Проверка предупреждений
    const warnings: string[] = []
    if (fieldConfigs.length === 0) {
      warnings.push('В профиле нет настроенных полей')
    }
    if (!funnelId && !(profile?.config?.stage_configs as any[])?.length) {
      warnings.push('В профиле не выбрана воронка (выберите воронку в блоке ниже)')
    }
    if (documentConfigs.length === 0) {
      warnings.push('В профиле нет настроенных документов')
    }

    // Показываем предупреждения, но не блокируем сохранение
    if (warnings.length > 0) {
      const confirmed = window.confirm(
        `Предупреждение:\n\n${warnings.join('\n')}\n\nПродолжить сохранение?`
      )
      if (!confirmed) {
        return
      }
    }

    setSaving(true)
    try {
      await onSave({
        code: code.trim(),
        name: name.trim(),
        description: description || null,
        client_id: null, // Профиль привязан только к вакансии, не к клиенту
        notes: notes || null,
        funnel_id: funnelId,
        config: {
          ...(profile?.config || {}),
          field_configs: fieldConfigs,
          document_configs: documentConfigs,
        },
      })
    } catch (err: any) {
      setFormError(err?.message || 'Не удалось сохранить профиль')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
      <h3 className="mb-3 text-base font-semibold text-blue-800">
        {profile ? 'Редактировать профиль' : 'Создать профиль'}
      </h3>
      <div className="space-y-3">
        <div>
          <TextField
            label="Код (уникальный идентификатор)"
            value={code}
            onChange={handleCodeChange}
            disabled={!!profile || saving}
            placeholder={t('app.admin.candidate_profiles.form.code_placeholder', { defaultValue: 'driver_ce' })}
            className={codeError ? 'border-rose-300' : ''}
          />
          {codeError && <div className="mt-1 text-xs text-rose-600">{codeError}</div>}
          {!codeError && !profile && (
            <div className="mt-1 text-xs text-slate-500">
              Только латинские буквы, цифры и подчеркивание (например: driver_ce)
            </div>
          )}
        </div>
        <div>
          <TextField
            label="Название"
            value={name}
            onChange={handleNameChange}
            disabled={saving}
            placeholder={t('app.admin.candidate_profiles.form.name_placeholder', { defaultValue: 'Водитель CE' })}
            className={nameError ? 'border-rose-300' : ''}
          />
          {nameError && <div className="mt-1 text-xs text-rose-600">{nameError}</div>}
        </div>
        <TextareaField
          label="Описание"
          value={description}
          onChange={setDescription}
          rows={3}
          placeholder="Описание профиля..."
        />
        <TextareaField
          label="Заметки"
          value={notes}
          onChange={setNotes}
          rows={2}
          placeholder="Внутренние заметки..."
        />
        
        {/* Field Constructor */}
        <div className="mt-4">
          <h3 className="mb-3 text-base font-semibold text-slate-900">Конструктор полей профиля</h3>
          <ProfileFieldConstructor
            value={fieldConfigs}
            onChange={setFieldConfigs}
            disabled={saving}
          />
        </div>
        
        {/* Funnel selector */}
        <div className="mt-6">
          <h3 className="mb-3 text-base font-semibold text-slate-900">Воронка (этапы) профиля</h3>
          <FunnelSelector
            value={funnelId}
            onChange={setFunnelId}
            disabled={saving || !!profile?.is_system}
          />
        </div>
        
        {/* Document Constructor */}
        <div className="mt-6">
          <h3 className="mb-3 text-base font-semibold text-slate-900">Документы профиля</h3>
          <ProfileDocumentConstructor
            value={documentConfigs}
            onChange={setDocumentConfigs}
            disabled={saving || !!profile?.is_system}
          />
        </div>
        
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
