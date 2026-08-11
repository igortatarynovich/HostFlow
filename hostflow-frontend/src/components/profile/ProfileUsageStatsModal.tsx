import { memo, useState, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Modal } from '../Modal'
import { listVacancies, type Vacancy } from '../../api/vacancies'
import type { CandidateProfile } from '../../api/candidate_profiles'
import type { FieldConfig } from './ProfileFieldConstructor'
import ErrorRecoveryBanner from '../ErrorRecoveryBanner'
import { useI18n } from '../../i18n'

interface ProfileUsageStatsModalProps {
  profile: CandidateProfile
  onClose: () => void
}

function ProfileUsageStatsModal({ profile, onClose }: ProfileUsageStatsModalProps) {
  const { t } = useI18n()
  const [vacancies, setVacancies] = useState<Vacancy[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void loadUsageStats()
  }, [profile.id])

  const loadUsageStats = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await listVacancies({
        candidate_profile_id: profile.id,
        limit: 100,
      })
      setVacancies(data)
    } catch (err: any) {
      setError(
        err?.message ||
          t('app.profiles.usage.load_failed', { defaultValue: 'Failed to load usage stats' }),
      )
    } finally {
      setLoading(false)
    }
  }

  const stats = useMemo(() => {
    const fieldConfigs = (profile.config?.field_configs as FieldConfig[]) || []
    const stageConfigs = (profile.config?.stage_configs as any[]) || []
    const documentConfigs = (profile.config?.document_configs as any[]) || []

    return {
      fieldsCount: fieldConfigs.filter((f: any) => f.visible !== false).length,
      requiredFieldsCount: fieldConfigs.filter((f: any) => f.required === true).length,
      stagesCount: profile.funnel_id ? 1 : stageConfigs.filter((s: any) => s.active !== false).length,
      documentsCount: documentConfigs.filter((d: any) => d.enabled !== false).length,
      vacanciesCount: vacancies.length,
      activeVacanciesCount: vacancies.filter((v) => v.is_active).length,
      totalCandidates: vacancies.reduce((sum, v) => sum + (v.candidate_count || 0), 0),
    }
  }, [profile.config, vacancies, profile.funnel_id])

  return (
    <Modal
      open={true}
      onClose={onClose}
      title={t('app.profiles.usage.title', {
        defaultValue: 'Profile usage stats: "{name}"',
        values: { name: profile.name },
      })}
    >
      <div className="space-y-4">
        <div className="rounded border border-slate-200 bg-slate-50 p-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <span className="font-semibold text-slate-900">{profile.name}</span>
                <span className="rounded-md bg-slate-200 px-2 py-0.5 text-xs font-mono text-slate-600">
                  {profile.code}
                </span>
                {!profile.is_active && (
                  <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                    {t('app.profiles.usage.inactive', { defaultValue: 'Inactive' })}
                  </span>
                )}
                {profile.is_system && (
                  <span className="rounded-md bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800">
                    {t('app.profiles.usage.system', { defaultValue: 'System' })}
                  </span>
                )}
              </div>
              {profile.description && (
                <p className="text-sm text-slate-600 mb-2">{profile.description}</p>
              )}
              {profile.notes && <p className="text-xs text-slate-500">{profile.notes}</p>}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="rounded border border-blue-200 bg-blue-50 p-3">
            <div className="text-xs text-blue-700 mb-1">
              {t('app.profiles.usage.fields', { defaultValue: 'Fields' })}
            </div>
            <div className="text-lg font-semibold text-blue-900">{stats.fieldsCount}</div>
            {stats.requiredFieldsCount > 0 && (
              <div className="text-xs text-blue-600">
                {t('app.profiles.usage.required_count', {
                  defaultValue: '{count} required',
                  values: { count: stats.requiredFieldsCount },
                })}
              </div>
            )}
          </div>
          <div className="rounded border border-green-200 bg-green-50 p-3">
            <div className="text-xs text-green-700 mb-1">
              {t('app.profiles.usage.stages', { defaultValue: 'Stages' })}
            </div>
            <div className="text-lg font-semibold text-green-900">{stats.stagesCount}</div>
          </div>
          <div className="rounded border border-purple-200 bg-purple-50 p-3">
            <div className="text-xs text-purple-700 mb-1">
              {t('app.profiles.usage.documents', { defaultValue: 'Documents' })}
            </div>
            <div className="text-lg font-semibold text-purple-900">{stats.documentsCount}</div>
          </div>
          <div className="rounded border border-amber-200 bg-amber-50 p-3">
            <div className="text-xs text-amber-700 mb-1">
              {t('app.profiles.usage.vacancies', { defaultValue: 'Vacancies' })}
            </div>
            <div className="text-lg font-semibold text-amber-900">{stats.vacanciesCount}</div>
            {stats.activeVacanciesCount > 0 && (
              <div className="text-xs text-amber-600">
                {t('app.profiles.usage.active_count', {
                  defaultValue: '{count} active',
                  values: { count: stats.activeVacanciesCount },
                })}
              </div>
            )}
          </div>
        </div>

        {stats.totalCandidates > 0 && (
          <div className="rounded border border-slate-200 bg-slate-50 p-3">
            <div className="text-sm font-medium text-slate-900 mb-1">
              {t('app.profiles.usage.total_candidates', { defaultValue: 'Total candidates' })}
            </div>
            <div className="text-2xl font-bold text-slate-900">{stats.totalCandidates}</div>
            <div className="text-xs text-slate-500 mt-1">
              {t('app.profiles.usage.total_candidates_hint', {
                defaultValue: 'Candidates across all vacancies using this profile',
              })}
            </div>
          </div>
        )}

        <div className="border-t border-slate-200 pt-4">
          <h3 className="text-sm font-semibold text-slate-900 mb-3">
            {t('app.profiles.usage.vacancies_using', {
              defaultValue: 'Vacancies using profile ({count})',
              values: { count: vacancies.length },
            })}
          </h3>
          {error && (
            <div className="mb-3">
              <ErrorRecoveryBanner
                info={{
                  title: error,
                  hint: t('app.profiles.usage.retry_hint', {
                    defaultValue: 'Retry the action or refresh the page.',
                  }),
                }}
                onRetry={() => void loadUsageStats()}
                retryLabel={t('app.profiles.usage.retry', { defaultValue: 'Refresh' })}
                compact
              />
            </div>
          )}
          {loading ? (
            <div className="text-sm text-slate-500">
              {t('app.profiles.usage.loading_vacancies', { defaultValue: 'Loading vacancies…' })}
            </div>
          ) : vacancies.length === 0 ? (
            <div className="text-sm text-slate-500 text-center py-4">
              {t('app.profiles.usage.empty', {
                defaultValue: 'Profile is not used in any vacancy',
              })}
            </div>
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {vacancies.map((vacancy) => (
                <Link
                  key={vacancy.id}
                  to={`/vacancies/${vacancy.id}`}
                  className="block rounded-lg border border-slate-200 bg-white p-3 transition-colors hover:border-blue-300 hover:bg-blue-50"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="font-medium text-slate-900 mb-1">{vacancy.title}</div>
                      <div className="text-xs text-slate-500 space-y-1">
                        {vacancy.company_name && (
                          <div>
                            {t('app.profiles.usage.company', {
                              defaultValue: 'Company: {name}',
                              values: { name: vacancy.company_name },
                            })}
                          </div>
                        )}
                        {vacancy.location && (
                          <div>
                            {t('app.profiles.usage.location', {
                              defaultValue: 'Location: {value}',
                              values: { value: vacancy.location },
                            })}
                          </div>
                        )}
                        {vacancy.status && (
                          <div>
                            {t('app.profiles.usage.status', {
                              defaultValue: 'Status: {value}',
                              values: { value: vacancy.status },
                            })}
                          </div>
                        )}
                        {vacancy.candidate_count !== undefined && vacancy.candidate_count > 0 && (
                          <div>
                            {t('app.profiles.usage.candidates_count', {
                              defaultValue: 'Candidates: {count}',
                              values: { count: vacancy.candidate_count },
                            })}
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      {vacancy.is_active ? (
                        <span className="rounded-md bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">
                          {t('app.profiles.usage.vacancy_active', { defaultValue: 'Active' })}
                        </span>
                      ) : (
                        <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                          {t('app.profiles.usage.vacancy_inactive', { defaultValue: 'Inactive' })}
                        </span>
                      )}
                      {vacancy.is_archived && (
                        <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                          {t('app.profiles.usage.vacancy_archived', { defaultValue: 'Archived' })}
                        </span>
                      )}
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        <div className="flex justify-end border-t border-slate-200 pt-4">
          <button type="button" onClick={onClose} className="btn-secondary">
            {t('common.close', { defaultValue: 'Close' })}
          </button>
        </div>
      </div>
    </Modal>
  )
}

export default memo(ProfileUsageStatsModal)
