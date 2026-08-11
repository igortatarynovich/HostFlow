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
      setError(
        err?.message ||
          t('app.profiles.apply.load_failed', { defaultValue: 'Failed to load vacancies' }),
      )
    } finally {
      setLoading(false)
    }
  }

  const filteredVacancies = useMemo(() => {
    return vacancies.filter((vacancy) => {
      if (searchQuery) {
        const query = searchQuery.toLowerCase()
        const matchesTitle = vacancy.title?.toLowerCase().includes(query)
        const matchesCompany = vacancy.company_name?.toLowerCase().includes(query)
        if (!matchesTitle && !matchesCompany) return false
      }
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
      setError(
        t('app.profiles.apply.select_at_least_one', {
          defaultValue: 'Select at least one vacancy',
        }),
      )
      return
    }

    setApplying(true)
    setError(null)
    try {
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
            `${vacancyId}: ${
              err?.message ||
              t('app.profiles.apply.unknown_error', { defaultValue: 'Unknown error' })
            }`,
          )
        }
      }

      if (results.failed > 0) {
        const details =
          results.errors.length > 0
            ? t('app.profiles.apply.details_prefix', {
                defaultValue: 'Details: {details}',
                values: { details: results.errors.slice(0, 3).join('; ') },
              })
            : ''
        setError(
          t('app.profiles.apply.partial_result', {
            defaultValue: 'Applied to {success} vacancies. Errors: {failed}. {details}',
            values: {
              success: results.success,
              failed: results.failed,
              details,
            },
          }),
        )
      } else {
        onSuccess?.()
        onClose()
      }
    } catch (err: any) {
      setError(
        err?.message ||
          t('app.profiles.apply.apply_failed', {
            defaultValue: 'Failed to apply profile to vacancies',
          }),
      )
    } finally {
      setApplying(false)
    }
  }

  const alreadyHasProfile = (vacancy: Vacancy) => vacancy.candidate_profile_id === profile.id

  return (
    <Modal
      open={true}
      onClose={onClose}
      title={t('app.profiles.apply.title', {
        defaultValue: 'Apply profile "{name}" to vacancies',
        values: { name: profile.name },
      })}
    >
      <div className="space-y-4">
        <div className="rounded border border-blue-200 bg-blue-50 p-3 text-sm text-blue-700">
          <div className="font-semibold mb-1">
            {t('app.profiles.apply.info_title', { defaultValue: 'Information:' })}
          </div>
          <ul className="list-disc list-inside space-y-1 text-xs">
            <li>
              {t('app.profiles.apply.info_1', {
                defaultValue: 'The profile will be applied to the selected vacancies',
              })}
            </li>
            <li>
              {t('app.profiles.apply.info_2', {
                defaultValue: 'Vacancies that already use this profile will be marked',
              })}
            </li>
            <li>
              {t('app.profiles.apply.info_3', {
                defaultValue:
                  'The operation may take some time for a large number of vacancies',
              })}
            </li>
          </ul>
        </div>

        <div className="space-y-2">
          <input
            type="text"
            placeholder={t('app.profiles.apply.search_placeholder', {
              defaultValue: 'Search by title or company...',
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
            <option value="all">{t('app.profiles.apply.filter_all', { defaultValue: 'All' })}</option>
            <option value="active">
              {t('app.profiles.apply.filter_active', { defaultValue: 'Active' })}
            </option>
            <option value="inactive">
              {t('app.profiles.apply.filter_inactive', { defaultValue: 'Inactive' })}
            </option>
          </select>
        </div>

        {error && (
          <ErrorRecoveryBanner
            info={{
              title: error,
              hint: t('app.profiles.apply.retry_hint', {
                defaultValue: 'Retry the action or refresh the page.',
              }),
            }}
            onRetry={() => void loadVacancies()}
            retryLabel={t('app.profiles.apply.retry', { defaultValue: 'Refresh' })}
            compact
          />
        )}

        {loading ? (
          <div className="text-sm text-slate-500">
            {t('app.profiles.apply.loading', { defaultValue: 'Loading vacancies...' })}
          </div>
        ) : filteredVacancies.length === 0 ? (
          <div className="text-sm text-slate-500">
            {t('app.profiles.apply.empty', { defaultValue: 'No vacancies found' })}
          </div>
        ) : (
          <div className="space-y-2 max-h-96 overflow-y-auto">
            <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
              <input
                type="checkbox"
                checked={selectedIds.size === filteredVacancies.length && filteredVacancies.length > 0}
                onChange={handleSelectAll}
                className="h-4 w-4 cursor-pointer"
                disabled={applying}
              />
              <span className="text-sm font-semibold text-slate-700">
                {t('app.profiles.apply.select_all', {
                  defaultValue: 'Select all ({selected} of {total})',
                  values: { selected: selectedIds.size, total: filteredVacancies.length },
                })}
              </span>
            </div>

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
                      {vacancy.company_name ||
                        t('app.profiles.apply.no_company', { defaultValue: 'No company' })}
                      {vacancy.location && ` • ${vacancy.location}`}
                      {vacancy.candidate_count !== undefined &&
                        ` • ${t('app.profiles.apply.candidates_count', {
                          defaultValue: '{count} candidates',
                          values: { count: vacancy.candidate_count },
                        })}`}
                    </div>
                    {hasProfile && (
                      <div className="mt-1 text-xs font-medium text-green-700">
                        {t('app.profiles.apply.already_applied', {
                          defaultValue: '✓ Profile already applied',
                        })}
                      </div>
                    )}
                    {vacancy.candidate_profile_name && vacancy.candidate_profile_id !== profile.id && (
                      <div className="mt-1 text-xs text-amber-700">
                        {t('app.profiles.apply.current_profile', {
                          defaultValue: '⚠ Current profile: {name}',
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

        <div className="flex items-center justify-between border-t border-slate-200 pt-4">
          <div className="text-sm text-slate-600">
            {t('app.profiles.apply.selected', {
              defaultValue: 'Selected: {count} vacancies',
              values: { count: selectedIds.size },
            })}
          </div>
          <div className="flex gap-2">
            <button type="button" onClick={onClose} disabled={applying} className="btn-secondary">
              {t('app.profiles.apply.cancel', { defaultValue: 'Cancel' })}
            </button>
            <button
              type="button"
              onClick={handleApply}
              disabled={selectedIds.size === 0 || applying}
              className="btn-primary"
            >
              {applying
                ? t('app.profiles.apply.applying', { defaultValue: 'Applying...' })
                : t('app.profiles.apply.apply_to', {
                    defaultValue: 'Apply to {count} vacancies',
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
