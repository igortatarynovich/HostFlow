import { memo, useState, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Modal } from '../Modal'
import { listVacancies, type Vacancy } from '../../api/vacancies'
import type { CandidateProfile } from '../../api/candidate_profiles'
import type { FieldConfig } from './ProfileFieldConstructor'
import ErrorRecoveryBanner from '../ErrorRecoveryBanner'

interface ProfileUsageStatsModalProps {
  profile: CandidateProfile
  onClose: () => void
}

function ProfileUsageStatsModal({ profile, onClose }: ProfileUsageStatsModalProps) {
  const [vacancies, setVacancies] = useState<Vacancy[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadUsageStats()
  }, [profile.id])

  const loadUsageStats = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await listVacancies({ 
        candidate_profile_id: profile.id,
        limit: 100, // Get up to 100 vacancies using this profile
      })
      setVacancies(data)
    } catch (err: any) {
      setError(err?.message || 'Не удалось загрузить статистику использования')
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
  }, [profile.config, vacancies])

  return (
    <Modal open={true} onClose={onClose} title={`Статистика использования профиля "${profile.name}"`}>
      <div className="space-y-4">
        {/* Profile Info */}
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
                    Неактивен
                  </span>
                )}
                {profile.is_system && (
                  <span className="rounded-md bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800">
                    Системный
                  </span>
                )}
              </div>
              {profile.description && (
                <p className="text-sm text-slate-600 mb-2">{profile.description}</p>
              )}
              {profile.notes && (
                <p className="text-xs text-slate-500">{profile.notes}</p>
              )}
            </div>
          </div>
        </div>

        {/* Statistics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="rounded border border-blue-200 bg-blue-50 p-3">
            <div className="text-xs text-blue-700 mb-1">Поля</div>
            <div className="text-lg font-semibold text-blue-900">{stats.fieldsCount}</div>
            {stats.requiredFieldsCount > 0 && (
              <div className="text-xs text-blue-600">
                {stats.requiredFieldsCount} обязательных
              </div>
            )}
          </div>
          <div className="rounded border border-green-200 bg-green-50 p-3">
            <div className="text-xs text-green-700 mb-1">Этапы</div>
            <div className="text-lg font-semibold text-green-900">{stats.stagesCount}</div>
          </div>
          <div className="rounded border border-purple-200 bg-purple-50 p-3">
            <div className="text-xs text-purple-700 mb-1">Документы</div>
            <div className="text-lg font-semibold text-purple-900">{stats.documentsCount}</div>
          </div>
          <div className="rounded border border-amber-200 bg-amber-50 p-3">
            <div className="text-xs text-amber-700 mb-1">Вакансии</div>
            <div className="text-lg font-semibold text-amber-900">{stats.vacanciesCount}</div>
            {stats.activeVacanciesCount > 0 && (
              <div className="text-xs text-amber-600">
                {stats.activeVacanciesCount} активных
              </div>
            )}
          </div>
        </div>

        {stats.totalCandidates > 0 && (
          <div className="rounded border border-slate-200 bg-slate-50 p-3">
            <div className="text-sm font-medium text-slate-900 mb-1">Всего кандидатов</div>
            <div className="text-2xl font-bold text-slate-900">{stats.totalCandidates}</div>
            <div className="text-xs text-slate-500 mt-1">
              Кандидаты во всех вакансиях, использующих этот профиль
            </div>
          </div>
        )}

        {/* Vacancies List */}
        <div className="border-t border-slate-200 pt-4">
          <h3 className="text-sm font-semibold text-slate-900 mb-3">
            Вакансии, использующие профиль ({vacancies.length})
          </h3>
          {error && (
            <div className="mb-3">
              <ErrorRecoveryBanner
                info={{ title: error, hint: 'Повторите действие или обновите страницу.' }}
                onRetry={() => void loadUsageStats()}
                retryLabel="Обновить"
                compact
              />
            </div>
          )}
          {loading ? (
            <div className="text-sm text-slate-500">Загрузка вакансий...</div>
          ) : vacancies.length === 0 ? (
            <div className="text-sm text-slate-500 text-center py-4">
              Профиль не используется ни в одной вакансии
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
                          <div>Компания: {vacancy.company_name}</div>
                        )}
                        {vacancy.location && <div>Локация: {vacancy.location}</div>}
                        {vacancy.status && (
                          <div>
                            Статус: <span className="font-medium">{vacancy.status}</span>
                          </div>
                        )}
                        {vacancy.candidate_count !== undefined && vacancy.candidate_count > 0 && (
                          <div>
                            Кандидатов: <span className="font-medium">{vacancy.candidate_count}</span>
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      {vacancy.is_active ? (
                        <span className="rounded-md bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">
                          Активна
                        </span>
                      ) : (
                        <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                          Неактивна
                        </span>
                      )}
                      {vacancy.is_archived && (
                        <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                          В архиве
                        </span>
                      )}
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex justify-end border-t border-slate-200 pt-4">
          <button
            type="button"
            onClick={onClose}
            className="btn-secondary"
          >
            Закрыть
          </button>
        </div>
      </div>
    </Modal>
  )
}

export default memo(ProfileUsageStatsModal)
