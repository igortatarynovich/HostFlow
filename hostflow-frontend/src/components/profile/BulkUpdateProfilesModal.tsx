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

function BulkUpdateProfilesModal({ onClose, onSuccess: _onSuccess }: BulkUpdateProfilesModalProps) {
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
      setProfiles(data.filter((p) => !p.is_system))
    } catch (err: any) {
      setError(
        err?.message ||
          t('app.profiles.bulk_update.load_failed', { defaultValue: 'Failed to load profiles' }),
      )
    } finally {
      setLoading(false)
    }
  }

  const filteredProfiles = useMemo(() => {
    return profiles.filter((profile) => {
      if (searchQuery) {
        const query = searchQuery.toLowerCase()
        const matchesName = profile.name.toLowerCase().includes(query)
        const matchesCode = profile.code.toLowerCase().includes(query)
        if (!matchesName && !matchesCode) return false
      }
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
      setError(
        t('app.profiles.bulk_update.select_at_least_one', {
          defaultValue: 'Select at least one profile',
        }),
      )
      return
    }

    setError(
      t('app.profiles.bulk_update.wip_error', {
        defaultValue:
          'Bulk configuration update is under development. Edit each profile separately.',
      }),
    )
    return
  }

  return (
    <Modal
      open={true}
      onClose={onClose}
      title={t('app.profiles.bulk_update.title', { defaultValue: 'Bulk update profiles' })}
    >
      <div className="space-y-4">
        <div className="rounded border border-blue-200 bg-blue-50 p-3 text-sm text-blue-700">
          <div className="font-semibold mb-1">
            {t('app.profiles.bulk_update.info_title', { defaultValue: 'Information:' })}
          </div>
          <ul className="list-disc list-inside space-y-1 text-xs">
            <li>
              {t('app.profiles.bulk_update.info_1', {
                defaultValue: 'Select profiles to update',
              })}
            </li>
            <li>
              {t('app.profiles.bulk_update.info_2', {
                defaultValue: 'Specify changes: add/remove fields or stages',
              })}
            </li>
            <li>
              {t('app.profiles.bulk_update.info_3', {
                defaultValue: 'Changes will be applied to all selected profiles',
              })}
            </li>
          </ul>
        </div>

        <div className="space-y-2">
          <input
            type="text"
            placeholder={t('app.profiles.bulk_update.search_placeholder', {
              defaultValue: 'Search by name or code...',
            })}
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
            <option value="all">
              {t('app.profiles.bulk_update.filter_all', { defaultValue: 'All' })}
            </option>
            <option value="active">
              {t('app.profiles.bulk_update.filter_active', { defaultValue: 'Active' })}
            </option>
            <option value="inactive">
              {t('app.profiles.bulk_update.filter_inactive', { defaultValue: 'Inactive' })}
            </option>
          </select>
        </div>

        {loading ? (
          <div className="text-sm text-slate-500">
            {t('app.profiles.bulk_update.loading', { defaultValue: 'Loading profiles...' })}
          </div>
        ) : filteredProfiles.length === 0 ? (
          <div className="text-sm text-slate-500">
            {t('app.profiles.bulk_update.empty', { defaultValue: 'No profiles found' })}
          </div>
        ) : (
          <div className="space-y-2 max-h-60 overflow-y-auto border border-slate-200 rounded p-3">
            <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
              <input
                type="checkbox"
                checked={selectedIds.size === filteredProfiles.length && filteredProfiles.length > 0}
                onChange={handleSelectAll}
                className="h-4 w-4 cursor-pointer"
                disabled={updating}
              />
              <span className="text-sm font-semibold text-slate-700">
                {t('app.profiles.bulk_update.select_all', {
                  defaultValue: 'Select all ({selected} of {total})',
                  values: { selected: selectedIds.size, total: filteredProfiles.length },
                })}
              </span>
            </div>

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

        {selectedIds.size > 0 && (
          <div className="space-y-3 border-t border-slate-200 pt-4">
            <h3 className="text-sm font-semibold text-slate-900">
              {t('app.profiles.bulk_update.config_changes', {
                defaultValue: 'Configuration changes',
              })}
            </h3>
            <div className="rounded border border-amber-200 bg-amber-50 p-3 text-xs text-amber-700">
              ⚠️{' '}
              {t('app.profiles.bulk_update.wip_notice', {
                defaultValue:
                  'Bulk configuration update is under development. The current version lets you apply a profile to vacancies. To change profile configuration, edit each profile separately.',
              })}
            </div>
            <div className="text-sm text-slate-600">
              {t('app.profiles.bulk_update.selected_for_update', {
                defaultValue: 'Profiles selected for update: {count}',
                values: { count: selectedIds.size },
              })}
            </div>
          </div>
        )}

        {error && (
          <ErrorRecoveryBanner
            info={{
              title: error,
              hint: t('app.profiles.bulk_update.retry_hint', {
                defaultValue: 'Retry the action or refresh the page.',
              }),
            }}
            onRetry={() => void loadProfiles()}
            retryLabel={t('app.profiles.bulk_update.retry', { defaultValue: 'Refresh' })}
            compact
          />
        )}

        <div className="flex items-center justify-between border-t border-slate-200 pt-4">
          <div className="text-sm text-slate-600">
            {t('app.profiles.bulk_update.selected', {
              defaultValue: 'Selected: {count} profiles',
              values: { count: selectedIds.size },
            })}
          </div>
          <div className="flex gap-2">
            <button type="button" onClick={onClose} disabled={updating} className="btn-secondary">
              {t('app.profiles.bulk_update.cancel', { defaultValue: 'Cancel' })}
            </button>
            <button
              type="button"
              onClick={handleBulkUpdate}
              disabled={selectedIds.size === 0 || updating}
              className="btn-primary opacity-50 cursor-not-allowed"
              title={t('app.profiles.bulk_update.wip_title', {
                defaultValue: 'Feature in development',
              })}
            >
              {updating
                ? t('app.profiles.bulk_update.updating', { defaultValue: 'Updating...' })
                : t('app.profiles.bulk_update.apply_wip', {
                    defaultValue: 'Apply changes (in development)',
                  })}
            </button>
          </div>
        </div>
      </div>
    </Modal>
  )
}

export default memo(BulkUpdateProfilesModal)
