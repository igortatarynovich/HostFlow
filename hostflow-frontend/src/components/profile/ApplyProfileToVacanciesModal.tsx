import { memo, useState, useEffect, useMemo } from 'react'
import { Modal } from '../Modal'
import { listVacancies, updateVacancy, type Vacancy } from '../../api/vacancies'
import type { CandidateProfile } from '../../api/candidate_profiles'
import ErrorRecoveryBanner from '../ErrorRecoveryBanner'
import { useI18n } from '../../i18n'

interface ApplyProfileToVacanciesModalProps {
  profile: CandidateProfile
  onClose: () => void
  onSuccess?: () => void
}

function ApplyProfileToVacanciesModal({ profile, onClose, onSuccess }: ApplyProfileToVacanciesModalProps) {
  const { t } = useI18n()
  const [vacancies, setVacancies] = useState<Vacancy[]>([])
  const [loading, setLoading] = useState(true)
  const [applying, setApplying] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [searchQuery, setSearchQuery] = useState('')
  const [filterActive, setFilterActive] = useState<boolean | null>(null)

  useEffect(() => {
    loadVacancies()
  }, [])

  const loadVacancies = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await listVacancies({ is_archived: false })
      setVacancies(data)
    } catch (err: any) {
      setError(err?.message || t('admin.candidate_profiles_page.apply_modal.load_failed'))
    } finally {
      setLoading(false)
    }
  }

  const filteredVacancies = useMemo(() => {
    return vacancies.filter((vacancy) => {
      // Фильтр по поисковому запросу
      if (searchQuery) {
        const query = searchQuery.toLowerCase()
        const matchesTitle = vacancy.title?.toLowerCase().includes(query)
        const matchesCompany = vacancy.company_name?.toLowerCase().includes(query)
        if (!matchesTitle && !matchesCompany) return false
      }
      // Фильтр по активности
      if (filterActive !== null) {
        if (filterActive && !vacancy.is_active) return false
        if (!filterActive && vacancy.is_active) return false
      }
      return true
    })
  }, [vacancies, searchQuery, filterActive])

  const handleSelectAll = () => {
    if (selectedIds.size === filteredVacancies.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(filteredVacancies.map((v) => v.id)))
    }
  }

  const handleToggleSelect = (vacancyId: string) => {
    const newSelected = new Set(selectedIds)
    if (newSelected.has(vacancyId)) {
      newSelected.delete(vacancyId)
    } else {
      newSelected.add(vacancyId)
    }
    setSelectedIds(newSelected)
  }

  const handleApply = async () => {
    if (selectedIds.size === 0) {
      setError(t('admin.candidate_profiles_page.apply_modal.pick_one'))
      return
    }

    setApplying(true)
    setError(null)
    try {
      // Update vacancies one by one with progress tracking
      const vacancyIds = Array.from(selectedIds)
      const results: { success: number; failed: number; errors: string[] } = {
        success: 0,
        failed: 0,
        errors: [],
      }

      for (const vacancyId of vacancyIds) {
        try {
          await updateVacancy(vacancyId, {
            candidate_profile_id: profile.id,
          })
          results.success++
        } catch (err: any) {
          results.failed++
          results.errors.push(
            `${vacancyId}: ${err?.message || t('admin.candidate_profiles_page.apply_modal.unknown_error')}`,
          )
        }
      }

      if (results.failed > 0) {
        setError(
          t('admin.candidate_profiles_page.apply_modal.partial', {
            values: { success: results.success, failed: results.failed },
          }) +
            (results.errors.length > 0
              ? ` ${t('admin.candidate_profiles_page.apply_modal.partial_details', {
                  values: { details: results.errors.slice(0, 3).join('; ') },
                })}`
              : ''),
        )
      } else {
        onSuccess?.()
        onClose()
      }
    } catch (err: any) {
      setError(err?.message || t('admin.candidate_profiles_page.apply_modal.apply_failed'))
    } finally {
      setApplying(false)
    }
  }

  const alreadyHasProfile = (vacancy: Vacancy) => vacancy.candidate_profile_id === profile.id

  return (
    <Modal
      open={true}
      onClose={onClose}
      title={t('admin.candidate_profiles_page.apply_modal.title', { values: { name: profile.name } })}
    >
      <div className="space-y-4">
        <div className="rounded border border-blue-200 bg-blue-50 p-3 text-sm text-blue-700">
          <div className="font-semibold mb-1">{t('admin.candidate_profiles_page.apply_modal.info_title')}</div>
          <ul className="list-disc list-inside space-y-1 text-xs">
            <li>{t('admin.candidate_profiles_page.apply_modal.info_1')}</li>
            <li>{t('admin.candidate_profiles_page.apply_modal.info_2')}</li>
            <li>{t('admin.candidate_profiles_page.apply_modal.info_3')}</li>
          </ul>
        </div>

        {/* Поиск и фильтры */}
        <div className="space-y-2">
          <input
            type="text"
            placeholder={t('admin.candidate_profiles_page.apply_modal.search_placeholder')}
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

        {error && (
          <ErrorRecoveryBanner
            info={{ title: error, hint: t('admin.candidate_profiles_page.apply_modal.retry_hint') }}
            onRetry={() => void loadVacancies()}
            retryLabel={t('common.refresh')}
            compact
          />
        )}

        {/* Список вакансий */}
        {loading ? (
          <div className="text-sm text-slate-500">{t('admin.candidate_profiles_page.apply_modal.loading')}</div>
        ) : filteredVacancies.length === 0 ? (
          <div className="text-sm text-slate-500">{t('admin.candidate_profiles_page.apply_modal.empty')}</div>
        ) : (
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {/* Select All */}
            <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
              <input
                type="checkbox"
                checked={selectedIds.size === filteredVacancies.length && filteredVacancies.length > 0}
                onChange={handleSelectAll}
                className="h-4 w-4 cursor-pointer"
                disabled={applying}
              />
              <span className="text-sm font-semibold text-slate-700">
                {t('admin.candidate_profiles_page.apply_modal.select_all', {
                  values: { selected: selectedIds.size, total: filteredVacancies.length },
                })}
              </span>
            </div>

            {/* Vacancies List */}
            {filteredVacancies.map((vacancy) => {
              const isSelected = selectedIds.has(vacancy.id)
              const hasProfile = alreadyHasProfile(vacancy)

              return (
                <div
                  key={vacancy.id}
                  className={`flex items-center gap-3 rounded-lg border p-3 transition-colors ${
                    hasProfile
                      ? 'border-green-200 bg-green-50'
                      : isSelected
                        ? 'border-blue-300 bg-blue-50'
                        : 'border-slate-200 bg-white hover:bg-slate-50'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => handleToggleSelect(vacancy.id)}
                    disabled={applying || hasProfile}
                    className="h-4 w-4 cursor-pointer"
                  />
                  <div className="flex-1">
                    <div className="font-medium text-slate-900">{vacancy.title}</div>
                    <div className="text-xs text-slate-500">
                      {vacancy.company_name || t('admin.candidate_profiles_page.apply_modal.no_company')}
                      {vacancy.location && ` • ${vacancy.location}`}
                      {vacancy.candidate_count !== undefined &&
                        ` • ${t('admin.candidate_profiles_page.apply_modal.candidates_count', {
                          values: { count: vacancy.candidate_count },
                        })}`}
                    </div>
                    {hasProfile && (
                      <div className="mt-1 text-xs font-medium text-green-700">
                        ✓ {t('admin.candidate_profiles_page.apply_modal.already_applied')}
                      </div>
                    )}
                    {vacancy.candidate_profile_name && vacancy.candidate_profile_id !== profile.id && (
                      <div className="mt-1 text-xs text-amber-700">
                        ⚠ {t('admin.candidate_profiles_page.apply_modal.current_profile', {
                          values: { name: vacancy.candidate_profile_name },
                        })}
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-between border-t border-slate-200 pt-4">
          <div className="text-sm text-slate-600">
            {t('admin.candidate_profiles_page.apply_modal.selected', {
              values: { count: selectedIds.size },
            })}
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onClose}
              disabled={applying}
              className="btn-secondary"
            >
              {t('common.cancel')}
            </button>
            <button
              type="button"
              onClick={handleApply}
              disabled={selectedIds.size === 0 || applying}
              className="btn-primary"
            >
              {applying
                ? t('admin.candidate_profiles_page.apply_modal.applying')
                : t('admin.candidate_profiles_page.apply_modal.apply_n', {
                    values: { count: selectedIds.size },
                  })}
            </button>
          </div>
        </div>
      </div>
    </Modal>
  )
}

export default memo(ApplyProfileToVacanciesModal)
