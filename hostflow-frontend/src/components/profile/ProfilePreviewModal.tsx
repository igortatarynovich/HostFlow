import { memo, useMemo, useState, useEffect } from 'react'
import type { CandidateProfile } from '../../api/candidate_profiles'
import type { FieldConfig } from './ProfileFieldConstructor'
import { getFunnel, type FunnelStage } from '../../api/funnels'
import { Modal } from '../Modal'
import { useI18n } from '../../i18n'

interface ProfilePreviewModalProps {
  profile: CandidateProfile
  onClose: () => void
  onDuplicate?: () => void
  onExport?: () => void
}

function ProfilePreviewModal({ profile, onClose, onDuplicate, onExport }: ProfilePreviewModalProps) {
  const { t } = useI18n()
  const fieldConfigs = useMemo<FieldConfig[]>(() => {
    if (!profile.config?.field_configs) return []
    return profile.config.field_configs as FieldConfig[]
  }, [profile.config])

  const [funnelStages, setFunnelStages] = useState<FunnelStage[]>([])
  useEffect(() => {
    if (!profile.funnel_id) {
      setFunnelStages([])
      return
    }
    getFunnel(profile.funnel_id)
      .then((f) => setFunnelStages(f.stages || []))
      .catch(() => setFunnelStages([]))
  }, [profile.funnel_id])

  const stageConfigs = profile.funnel_id && funnelStages.length > 0
    ? funnelStages.map((s) => ({
        stage_code: s.code,
        stage_label: s.label,
        order: s.order,
        active: !s.is_terminal,
      }))
    : ((profile.config?.stage_configs as Array<{
        stage_code: string
        stage_label: string
        order: number
        active?: boolean
      }>) || [])

  const documentConfigs = useMemo(() => {
    if (!profile.config?.document_configs) return []
    return profile.config.document_configs as Array<{
      document_type_id: string
      document_type_code: string
      required: boolean
      enabled: boolean
      alert_days_before_expiry: number | null
      order: number
    }>
  }, [profile.config])

  const visibleFields = useMemo(() => {
    return fieldConfigs.filter((f) => f.visible !== false)
  }, [fieldConfigs])

  const requiredFields = useMemo(() => {
    return fieldConfigs.filter((f) => f.required === true)
  }, [fieldConfigs])

  const activeStages = useMemo(() => {
    return stageConfigs.filter((s) => (s as any).active !== false)
  }, [stageConfigs])

  const enabledDocuments = useMemo(() => {
    return documentConfigs.filter((d) => d.enabled !== false)
  }, [documentConfigs])

  return (
    <Modal
      open={true}
      onClose={onClose}
      title={t('app.profiles.preview.title', {
        defaultValue: 'Profile preview: {name}',
        values: { name: profile.name },
      })}
    >
      <div className="space-y-4">
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-900">
            {t('app.profiles.preview.general', { defaultValue: 'General information' })}
          </h3>
          <div className="space-y-2 text-sm">
            <div className="flex items-center gap-2">
              <span className="font-medium text-slate-700">
                {t('app.profiles.preview.code', { defaultValue: 'Code:' })}
              </span>
              <span className="font-mono text-slate-600">{profile.code}</span>
            </div>
            {profile.description && (
              <div>
                <span className="font-medium text-slate-700">
                  {t('app.profiles.preview.description', { defaultValue: 'Description:' })}
                </span>
                <p className="mt-1 text-slate-600">{profile.description}</p>
              </div>
            )}
            {profile.notes && (
              <div>
                <span className="font-medium text-slate-700">
                  {t('app.profiles.preview.notes', { defaultValue: 'Notes:' })}
                </span>
                <p className="mt-1 text-xs text-slate-500">{profile.notes}</p>
              </div>
            )}
            <div className="flex items-center gap-2">
              <span className="font-medium text-slate-700">
                {t('app.profiles.preview.status', { defaultValue: 'Status:' })}
              </span>
              <span
                className={`rounded-md px-2 py-0.5 text-xs font-medium ${
                  profile.is_active
                    ? 'bg-green-100 text-green-800'
                    : 'bg-slate-100 text-slate-600'
                }`}
              >
                {profile.is_active
                  ? t('app.profiles.preview.active', { defaultValue: 'Active' })
                  : t('app.profiles.preview.inactive', { defaultValue: 'Inactive' })}
              </span>
              {profile.is_system && (
                <span className="rounded-md bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800">
                  {t('app.profiles.preview.system', { defaultValue: 'System' })}
                </span>
              )}
              {profile.usage_count != null && profile.usage_count > 0 && (
                <span className="rounded-md bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-800">
                  {t('app.profiles.preview.used_in', {
                    defaultValue: 'Used in {count} vacancies',
                    values: { count: profile.usage_count },
                  })}
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-center">
            <div className="text-2xl font-bold text-blue-900">{visibleFields.length}</div>
            <div className="text-xs text-blue-700">
              {t('app.profiles.preview.fields_stat', { defaultValue: 'Fields' })}
            </div>
            <div className="mt-1 text-xs text-blue-600">
              {t('app.profiles.preview.required_count', {
                defaultValue: '{count} required',
                values: { count: requiredFields.length },
              })}
            </div>
          </div>
          <div className="rounded-lg border border-green-200 bg-green-50 p-3 text-center">
            <div className="text-2xl font-bold text-green-900">
              {profile.funnel_id ? funnelStages.length || activeStages.length : activeStages.length}
            </div>
            <div className="text-xs text-green-700">
              {profile.funnel_id
                ? t('app.profiles.preview.stages_funnel', { defaultValue: 'Stages (funnel)' })
                : t('app.profiles.preview.stages_stat', { defaultValue: 'Stages' })}
            </div>
          </div>
          <div className="rounded-lg border border-purple-200 bg-purple-50 p-3 text-center">
            <div className="text-2xl font-bold text-purple-900">{enabledDocuments.length}</div>
            <div className="text-xs text-purple-700">
              {t('app.profiles.preview.documents_stat', { defaultValue: 'Documents' })}
            </div>
          </div>
        </div>

        {visibleFields.length > 0 && (
          <div>
            <h3 className="mb-2 text-sm font-semibold text-slate-900">
              {t('app.profiles.preview.fields_heading', {
                defaultValue: 'Fields ({count})',
                values: { count: visibleFields.length },
              })}
            </h3>
            <div className="max-h-60 space-y-1 overflow-y-auto rounded-lg border border-slate-200 bg-white p-3">
              {visibleFields.map((field, index) => (
                <div
                  key={field.field_key || index}
                  className="flex items-center justify-between rounded bg-slate-50 p-2 text-sm"
                >
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-slate-900">
                      {field.label || field.field_key}
                    </span>
                    <span className="text-xs text-slate-500">({field.field_type})</span>
                    {field.required && (
                      <span className="rounded-md bg-red-100 px-1.5 py-0.5 text-xs font-medium text-red-800">
                        {t('app.profiles.preview.required_field', { defaultValue: 'Required' })}
                      </span>
                    )}
                  </div>
                  <span className="text-xs text-slate-400">#{field.order || index + 1}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {(activeStages.length > 0 || funnelStages.length > 0) && (
          <div>
            <h3 className="mb-2 text-sm font-semibold text-slate-900">
              {t('app.profiles.preview.stages_heading', {
                defaultValue: 'Funnel stages ({count})',
                values: { count: funnelStages.length || activeStages.length },
              })}
            </h3>
            <div className="max-h-60 space-y-1 overflow-y-auto rounded-lg border border-slate-200 bg-white p-3">
              {(funnelStages.length > 0 ? funnelStages : activeStages)
                .sort((a, b) => ((a as any).order || 0) - ((b as any).order || 0))
                .map((stage, index) => (
                  <div
                    key={(stage as any).stage_code || (stage as FunnelStage).code || index}
                    className="flex items-center justify-between rounded bg-slate-50 p-2 text-sm"
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-slate-900">
                        {(stage as FunnelStage).label || (stage as any).stage_label}
                      </span>
                      <span className="font-mono text-xs text-slate-500">
                        ({(stage as FunnelStage).code || (stage as any).stage_code})
                      </span>
                    </div>
                    <span className="text-xs text-slate-400">
                      #{(stage as any).order ?? (stage as FunnelStage).order ?? index + 1}
                    </span>
                  </div>
                ))}
            </div>
          </div>
        )}

        {enabledDocuments.length > 0 && (
          <div>
            <h3 className="mb-2 text-sm font-semibold text-slate-900">
              {t('app.profiles.preview.documents_heading', {
                defaultValue: 'Documents ({count})',
                values: { count: enabledDocuments.length },
              })}
            </h3>
            <div className="max-h-60 space-y-1 overflow-y-auto rounded-lg border border-slate-200 bg-white p-3">
              {enabledDocuments
                .sort((a, b) => (a.order || 0) - (b.order || 0))
                .map((doc, index) => (
                  <div
                    key={doc.document_type_id || index}
                    className="flex items-center justify-between rounded bg-slate-50 p-2 text-sm"
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-slate-900">
                        {doc.document_type_code}
                      </span>
                      {doc.required && (
                        <span className="rounded-md bg-red-100 px-1.5 py-0.5 text-xs font-medium text-red-800">
                          {t('app.profiles.preview.required_doc', { defaultValue: 'Required' })}
                        </span>
                      )}
                      {doc.alert_days_before_expiry && (
                        <span className="text-xs text-slate-500">
                          {t('app.profiles.preview.alert_days', {
                            defaultValue: 'Reminder {days} days before',
                            values: { days: doc.alert_days_before_expiry },
                          })}
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-slate-400">#{doc.order || index + 1}</span>
                  </div>
                ))}
            </div>
          </div>
        )}

        <div className="flex gap-2 justify-end border-t border-slate-200 pt-4">
          {onExport && !profile.is_system && (
            <button type="button" onClick={onExport} className="btn-secondary">
              {t('app.profiles.preview.export', { defaultValue: 'Export' })}
            </button>
          )}
          {onDuplicate && (
            <button type="button" onClick={onDuplicate} className="btn-secondary">
              {t('app.profiles.preview.duplicate', { defaultValue: 'Duplicate' })}
            </button>
          )}
          <button type="button" onClick={onClose} className="btn-primary">
            {t('common.close', { defaultValue: 'Close' })}
          </button>
        </div>
      </div>
    </Modal>
  )
}

export default memo(ProfilePreviewModal)
