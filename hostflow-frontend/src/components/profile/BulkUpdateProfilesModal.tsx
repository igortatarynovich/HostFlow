import { memo, useState, useEffect, useMemo } from 'react'
import { Modal } from '../Modal'
import ErrorRecoveryBanner from '../ErrorRecoveryBanner'
import {
  listCandidateProfiles,
  type CandidateProfile,
} from '../../api/candidate_profiles'
import { useI18n } from '../../i18n'

interface BulkUpdateProfilesModalProps {
  onClose: () => void
  onSuccess?: () => void
}

function BulkUpdateProfilesModal({ onClose, onSuccess }: BulkUpdateProfilesModalProps) {
  const { t } = useI18n()
  const [profiles, setProfiles] = useState<CandidateProfile[]>([])
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [searchQuery, setSearchQuery] = useState('')
  const [filterActive, setFilterActive] = useState<boolean | null>(null)


  useEffect(() => {
    loadProfiles()
  }, [])

  const loadProfiles = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await listCandidateProfiles({ is_active: undefined })
      setProfiles(data.filter((p) => !p.is_system)) // Exclude system profiles
    } catch (err: any) {
      setError(err?.message || t('admin.candidate_profiles_page.bulk_modal.load_failed'))
    } finally {
      setLoading(false)
    }
  }

  const filteredProfiles = useMemo(() => {
    return profiles.filter((profile) => {
      // Фильтр по поисковому запросу
      if (searchQuery) {
        const query = searchQuery.toLowerCase()
        const matchesName = profile.name.toLowerCase().includes(query)
        const matchesCode = profile.code.toLowerCase().includes(query)
        if (!matchesName && !matchesCode) return false
      }
      // Фильтр по активности
      if (filterActive !== null) {
        if (filterActive && !profile.is_active) return false
        if (!filterActive && profile.is_active) return false
      }
      return true
    })
  }, [profiles, searchQuery, filterActive])

  const handleSelectAll = () => {
    if (selectedIds.size === filteredProfiles.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(filteredProfiles.map((p) => p.id)))
    }
  }

  const handleToggleSelect = (profileId: string) => {
    const newSelected = new Set(selectedIds)
    if (newSelected.has(profileId)) {
      newSelected.delete(profileId)
    } else {
      newSelected.add(profileId)
    }
    setSelectedIds(newSelected)
  }

  const handleBulkUpdate = async () => {
    if (selectedIds.size === 0) {
      setError(t('admin.candidate_profiles_page.bulk_modal.pick_one'))
      return
    }

    // TODO: Реализовать массовое изменение конфигурации профилей
    // Пока что функционал находится в разработке
    setError(t('admin.candidate_profiles_page.bulk_modal.wip'))
    return
  }

  return (
    <Modal open={true} onClose={onClose} title={t('admin.candidate_profiles_page.bulk_modal.title')}>
      <div className="space-y-4">
        <div className="rounded border border-blue-200 bg-blue-50 p-3 text-sm text-blue-700">
          <div className="font-semibold mb-1">{t('admin.candidate_profiles_page.apply_modal.info_title')}</div>
          <ul className="list-disc list-inside space-y-1 text-xs">
            <li>{t('admin.candidate_profiles_page.bulk_modal.info_1')}</li>
            <li>{t('admin.candidate_profiles_page.bulk_modal.info_2')}</li>
            <li>{t('admin.candidate_profiles_page.bulk_modal.info_3')}</li>
          </ul>
        </div>

        {/* Поиск и фильтры */}
        <div className="space-y-2">
          <input
            type="text"
            placeholder={t('admin.candidate_profiles_page.bulk_modal.search_placeholder')}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input w-full"
          />
          <select
            value={filterActive === null ? 'all' : filterActive ? 'active' : 'inactive'}
            onChange={(e) => {
              const val = e.target.value
              setFilterActive(val === 'all' ? null : val === 'active')
            }}
            className="input"
          >
            <option value="all">{t('admin.candidate_profiles_page.filter_all')}</option>
            <option value="active">{t('admin.candidate_profiles_page.filter_active')}</option>
            <option value="inactive">{t('admin.candidate_profiles_page.filter_inactive')}</option>
          </select>
        </div>

        {/* Список профилей */}
        {loading ? (
          <div className="text-sm text-slate-500">{t('admin.candidate_profiles_page.bulk_modal.loading')}</div>
        ) : filteredProfiles.length === 0 ? (
          <div className="text-sm text-slate-500">{t('admin.candidate_profiles_page.bulk_modal.empty')}</div>
        ) : (
          <div className="space-y-2 max-h-60 overflow-y-auto border border-slate-200 rounded p-3">
            {/* Select All */}
            <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
              <input
                type="checkbox"
                checked={selectedIds.size === filteredProfiles.length && filteredProfiles.length > 0}
                onChange={handleSelectAll}
                className="h-4 w-4 cursor-pointer"
                disabled={updating}
              />
              <span className="text-sm font-semibold text-slate-700">
                {t('admin.candidate_profiles_page.bulk_modal.select_all', {
                  values: { selected: selectedIds.size, total: filteredProfiles.length },
                })}
              </span>
            </div>

            {/* Profiles List */}
            {filteredProfiles.map((profile) => {
              const isSelected = selectedIds.has(profile.id)
              return (
                <div
                  key={profile.id}
                  className={`flex items-center gap-3 rounded-lg border p-2 transition-colors ${
                    isSelected
                      ? 'border-blue-300 bg-blue-50'
                      : 'border-slate-200 bg-white hover:bg-slate-50'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => handleToggleSelect(profile.id)}
                    disabled={updating}
                    className="h-4 w-4 cursor-pointer"
                  />
                  <div className="flex-1">
                    <div className="font-medium text-slate-900">{profile.name}</div>
                    <div className="text-xs text-slate-500">{profile.code}</div>
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {/* Configuration changes - упрощенная версия */}
        {selectedIds.size > 0 && (
          <div className="space-y-3 border-t border-slate-200 pt-4">
            <h3 className="text-sm font-semibold text-slate-900">
              {t('admin.candidate_profiles_page.bulk_modal.config_changes')}
            </h3>
            <div className="rounded border border-amber-200 bg-amber-50 p-3 text-xs text-amber-700">
              ⚠️ {t('admin.candidate_profiles_page.bulk_modal.wip_banner')}
            </div>
            <div className="text-sm text-slate-600">
              {t('admin.candidate_profiles_page.bulk_modal.selected_for_change', {
                values: { count: selectedIds.size },
              })}
            </div>
          </div>
        )}

        {error && (
          <ErrorRecoveryBanner
            info={{ title: error, hint: t('admin.candidate_profiles_page.apply_modal.retry_hint') }}
            onRetry={() => void loadProfiles()}
            retryLabel={t('common.refresh')}
            compact
          />
        )}

        {/* Actions */}
        <div className="flex items-center justify-between border-t border-slate-200 pt-4">
          <div className="text-sm text-slate-600">
            {t('admin.candidate_profiles_page.bulk_modal.selected', {
              values: { count: selectedIds.size },
            })}
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onClose}
              disabled={updating}
              className="btn-secondary"
            >
              {t('common.cancel')}
            </button>
            <button
              type="button"
              onClick={handleBulkUpdate}
              disabled={selectedIds.size === 0 || updating}
              className="btn-primary opacity-50 cursor-not-allowed"
              title={t('admin.candidate_profiles_page.bulk_modal.wip_title')}
            >
              {updating
                ? t('admin.candidate_profiles_page.bulk_modal.updating')
                : t('admin.candidate_profiles_page.bulk_modal.apply_wip')}
            </button>
          </div>
        </div>
      </div>
    </Modal>
  )
}

export default memo(BulkUpdateProfilesModal)
