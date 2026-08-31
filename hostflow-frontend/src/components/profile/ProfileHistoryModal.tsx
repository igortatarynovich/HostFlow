import { memo, useState, useEffect } from 'react'
import { Modal } from '../Modal'
import { getProfileHistory, type ProfileHistoryEntry } from '../../api/candidate_profiles'
import type { CandidateProfile } from '../../api/candidate_profiles'
import ErrorRecoveryBanner from '../ErrorRecoveryBanner'
import { useI18n } from '../../i18n'

interface ProfileHistoryModalProps {
  profile: CandidateProfile
  onClose: () => void
}

const ACTION_COLORS: Record<string, string> = {
  created: 'bg-green-100 text-green-800',
  updated: 'bg-blue-100 text-blue-800',
  deleted: 'bg-red-100 text-red-800',
  activated: 'bg-green-100 text-green-800',
  deactivated: 'bg-slate-100 text-slate-800',
}

function formatDate(dateString: string | null, locale: string): string {
  if (!dateString) return '—'
  try {
    const date = new Date(dateString)
    const localeTag = locale === 'ru' ? 'ru-RU' : locale === 'pl' ? 'pl-PL' : 'en-US'
    return new Intl.DateTimeFormat(localeTag, {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date)
  } catch {
    return dateString
  }
}

function ProfileHistoryModal({ profile, onClose }: ProfileHistoryModalProps) {
  const { t, locale } = useI18n()
  const [history, setHistory] = useState<ProfileHistoryEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadHistory()
  }, [profile.id])

  const loadHistory = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await getProfileHistory(profile.id, 100)
      setHistory(data)
    } catch (err: any) {
      setError(err?.message || t('admin.candidate_profiles_page.history.load_failed'))
    } finally {
      setLoading(false)
    }
  }

  const renderChanges = (changes: Record<string, any> | null) => {
    if (!changes || Object.keys(changes).length === 0) {
      return <span className="text-xs text-slate-500">{t('admin.candidate_profiles_page.history.no_changes')}</span>
    }

    return (
      <div className="space-y-2">
        {Object.entries(changes).map(([key, value]) => {
          const oldVal = value?.old
          const newVal = value?.new

          // Skip if values are the same
          if (oldVal === newVal) return null

          // Format values for display
          const formatValue = (val: any): string => {
            if (val === null || val === undefined) return '—'
            if (typeof val === 'boolean') return val ? t('common.yes') : t('common.no')
            if (typeof val === 'object') return JSON.stringify(val, null, 2)
            return String(val)
          }

          const fieldLabels: Record<string, string> = {
            code: t('admin.candidate_profiles_page.history.field.code'),
            name: t('admin.candidate_profiles_page.history.field.name'),
            description: t('admin.candidate_profiles_page.history.field.description'),
            client_id: t('admin.candidate_profiles_page.history.field.client_id'),
            config: t('admin.candidate_profiles_page.history.field.config'),
            is_active: t('admin.candidate_profiles_page.history.field.is_active'),
            is_system: t('admin.candidate_profiles_page.history.field.is_system'),
            owner_user_id: t('admin.candidate_profiles_page.history.field.owner_user_id'),
            notes: t('admin.candidate_profiles_page.history.field.notes'),
          }

          return (
            <div key={key} className="rounded border border-slate-200 bg-slate-50 p-2 text-xs">
              <div className="font-medium text-slate-700 mb-1">
                {fieldLabels[key] || key}
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <div className="text-slate-500 mb-1">{t('admin.candidate_profiles_page.history.was')}</div>
                  <div className="rounded bg-white p-1 font-mono text-slate-800 break-words">
                    {formatValue(oldVal)}
                  </div>
                </div>
                <div>
                  <div className="text-slate-500 mb-1">{t('admin.candidate_profiles_page.history.became')}</div>
                  <div className="rounded bg-blue-50 p-1 font-mono text-blue-900 break-words">
                    {formatValue(newVal)}
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    )
  }

  return (
    <Modal
      open={true}
      onClose={onClose}
      title={t('admin.candidate_profiles_page.history.title', { values: { name: profile.name } })}
    >
      <div className="space-y-4">
        {/* Profile Info */}
        <div className="rounded border border-slate-200 bg-slate-50 p-3">
          <div className="flex items-center gap-2 mb-2">
            <span className="font-semibold text-slate-900">{profile.name}</span>
            <span className="rounded-md bg-slate-200 px-2 py-0.5 text-xs font-mono text-slate-600">
              {profile.code}
            </span>
          </div>
        </div>

        {/* History List */}
        {error && (
          <ErrorRecoveryBanner
            info={{ title: error, hint: t('admin.candidate_profiles_page.apply_modal.retry_hint') }}
            onRetry={() => void loadHistory()}
            retryLabel={t('common.refresh')}
            compact
          />
        )}

        {loading ? (
          <div className="text-sm text-slate-500 text-center py-4">
            {t('admin.candidate_profiles_page.history.loading')}
          </div>
        ) : history.length === 0 ? (
          <div className="text-sm text-slate-500 text-center py-4">
            {t('admin.candidate_profiles_page.history.empty')}
          </div>
        ) : (
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {history.map((entry) => (
              <div
                key={entry.id}
                className="rounded-lg border border-slate-200 bg-white p-4"
              >
                <div className="flex items-start justify-between gap-4 mb-3">
                  <div className="flex items-center gap-2">
                    <span
                      className={`rounded-md px-2 py-1 text-xs font-medium ${
                        ACTION_COLORS[entry.action] || 'bg-slate-100 text-slate-800'
                      }`}
                    >
                      {t(`admin.candidate_profiles_page.history.action.${entry.action}`, {
                        defaultValue: entry.action,
                      })}
                    </span>
                    <span className="text-xs text-slate-500">
                      {formatDate(entry.created_at, locale)}
                    </span>
                  </div>
                  {entry.actor_name && (
                    <span className="text-xs text-slate-500">
                      {entry.actor_name}
                    </span>
                  )}
                </div>

                {entry.comment && (
                  <div className="mb-3 rounded bg-blue-50 p-2 text-xs text-blue-800">
                    {entry.comment}
                  </div>
                )}

                {entry.action === 'updated' && entry.changes && (
                  <div className="border-t border-slate-200 pt-3">
                    <div className="text-xs font-medium text-slate-700 mb-2">
                      {t('admin.candidate_profiles_page.history.changes')}
                    </div>
                    {renderChanges(entry.changes)}
                  </div>
                )}

                {entry.action === 'created' && entry.new_data && (
                  <div className="border-t border-slate-200 pt-3">
                    <div className="text-xs font-medium text-slate-700 mb-2">
                      {t('admin.candidate_profiles_page.history.initial_data')}
                    </div>
                    <div className="rounded bg-slate-50 p-2 font-mono text-xs text-slate-700 whitespace-pre-wrap break-words">
                      {JSON.stringify(entry.new_data, null, 2)}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end border-t border-slate-200 pt-4">
          <button
            type="button"
            onClick={onClose}
            className="btn-secondary"
          >
            {t('common.actions.close')}
          </button>
        </div>
      </div>
    </Modal>
  )
}

export default memo(ProfileHistoryModal)
