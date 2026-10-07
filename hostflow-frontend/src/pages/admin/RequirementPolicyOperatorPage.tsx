import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  getRequirementPolicyOperator,
  putRequirementPolicyOperator,
  type RequirementPolicyEvalBlock,
  type RequirementPolicyOperatorView,
} from '../../api/requirementPolicyOperator'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'
import { useI18n } from '../../i18n'
import { usePermissions } from '../../hooks/usePermissions'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'

function linesToList(text: string): string[] {
  return text
    .split(/\r?\n/)
    .map((s) => s.trim().toLowerCase().replace(/-/g, '_'))
    .filter(Boolean)
}

function listToLines(items: string[] | undefined): string {
  return (items || []).join('\n')
}

function applicabilitySummary(block: RequirementPolicyEvalBlock | undefined): string {
  const rows = block?.applicability || []
  if (!rows.length) return '—'
  return rows
    .slice(0, 24)
    .map((row) => `${row.doc_type}: ${row.applicability}`)
    .join('\n')
}

export default function RequirementPolicyOperatorPage() {
  const { t } = useI18n()
  const { trustRole, can } = usePermissions()
  const canWrite =
    trustRole === 'administrator' || trustRole === 'superadmin' || can('*') || can('admin.ruleset')

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [conflict, setConflict] = useState(false)
  const [view, setView] = useState<RequirementPolicyOperatorView | null>(null)
  const [requireText, setRequireText] = useState('')
  const [removeText, setRemoveText] = useState('')
  const [reason, setReason] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    setConflict(false)
    try {
      const data = await getRequirementPolicyOperator()
      setView(data)
      setRequireText(listToLines(data.override?.require))
      setRemoveText(listToLines(data.override?.remove))
      setReason('')
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
      setView(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const revision = view?.revision ?? 0

  const onSave = useCallback(async () => {
    if (!canWrite) return
    setSaving(true)
    setError(null)
    setConflict(false)
    try {
      const data = await putRequirementPolicyOperator({
        require: linesToList(requireText),
        remove: linesToList(removeText),
        reason: reason.trim(),
        expected_revision: revision,
      })
      setView(data)
      setRequireText(listToLines(data.override?.require))
      setRemoveText(listToLines(data.override?.remove))
      setReason('')
    } catch (e: any) {
      const status = e?.response?.status
      if (status === 409) {
        setConflict(true)
        setError(
          t('admin.requirement_policy.conflict', {
            defaultValue: 'Someone else saved this policy. Reload and try again.',
          }),
        )
        await load()
      } else {
        const detail = e?.response?.data?.detail
        setError(
          typeof detail === 'string'
            ? detail
            : e instanceof Error
              ? e.message
              : String(e),
        )
      }
    } finally {
      setSaving(false)
    }
  }, [canWrite, load, reason, removeText, requireText, revision, t])

  const saveDisabled = useMemo(() => {
    return !canWrite || saving || loading || reason.trim().length < 3
  }, [canWrite, loading, reason, saving])

  return (
    <SettingsSubpageHeader
      className="max-w-4xl"
      backLabel={t('admin.settings.subpage.back_all')}
      kicker={t('admin.settings.sections.crm_setup.label', { defaultValue: 'CRM Setup' })}
      title={t('admin.requirement_policy.title', { defaultValue: 'Requirement Policy' })}
      subtitle={t('admin.requirement_policy.blurb', {
        defaultValue:
          'One operator job: base rule, tenant override, reason, and result — writes R5 merge that Documents already reads.',
      })}
    >
      {error ? (
        <ErrorRecoveryBanner
          title={
            conflict
              ? t('admin.requirement_policy.conflict_title', { defaultValue: 'Conflict' })
              : t('admin.requirement_policy.load_error', { defaultValue: 'Requirement policy error' })
          }
          description={error}
          onRetry={() => void load()}
        />
      ) : null}

      {loading ? (
        <div className="text-sm text-slate-500">{t('common.loading')}</div>
      ) : view ? (
        <div className="space-y-6">
          <section className="settings-panel" data-rpm-base="true">
            <h2 className="text-sm font-semibold text-slate-900">
              {t('admin.requirement_policy.base_title', { defaultValue: 'Base' })}
            </h2>
            <p className="mt-1 text-xs text-slate-600">
              {t('admin.requirement_policy.base_hint', {
                defaultValue: 'Effective platform evaluation without tenant overlay (same preview context).',
              })}
            </p>
            <pre className="mt-3 max-h-56 overflow-auto rounded-lg bg-slate-50 p-3 text-xs text-slate-700 whitespace-pre-wrap">
              {applicabilitySummary(view.base)}
            </pre>
          </section>

          <section className="settings-panel" data-rpm-override="true">
            <h2 className="text-sm font-semibold text-slate-900">
              {t('admin.requirement_policy.override_title', { defaultValue: 'Override' })}
            </h2>
            <p className="mt-1 text-xs text-slate-600">
              {t('admin.requirement_policy.override_hint', {
                defaultValue:
                  'One code per line. Empty require and remove resets to platform base. Revision {revision}.',
                values: { revision },
              })}
            </p>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <label className="block text-sm text-slate-700">
                <span className="mb-1 block text-slate-600">require</span>
                <textarea
                  className="input min-h-[120px] font-mono text-xs"
                  value={requireText}
                  onChange={(event) => setRequireText(event.target.value)}
                  disabled={!canWrite || saving}
                />
              </label>
              <label className="block text-sm text-slate-700">
                <span className="mb-1 block text-slate-600">remove</span>
                <textarea
                  className="input min-h-[120px] font-mono text-xs"
                  value={removeText}
                  onChange={(event) => setRemoveText(event.target.value)}
                  disabled={!canWrite || saving}
                />
              </label>
            </div>
          </section>

          <section className="settings-panel" data-rpm-reason="true">
            <h2 className="text-sm font-semibold text-slate-900">
              {t('admin.requirement_policy.reason_title', { defaultValue: 'Reason' })}
            </h2>
            <p className="mt-1 text-xs text-slate-600">
              {t('admin.requirement_policy.reason_hint', {
                defaultValue: 'Required for every save. Last stored reason: {stored}',
                values: { stored: view.reason || '—' },
              })}
            </p>
            <textarea
              className="input mt-3 min-h-[80px]"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              disabled={!canWrite || saving}
              placeholder={t('admin.requirement_policy.reason_placeholder', {
                defaultValue: 'Why this override?',
              })}
            />
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                type="button"
                className="btn-primary btn-sm"
                disabled={saveDisabled}
                onClick={() => void onSave()}
              >
                {saving
                  ? t('common.saving', { defaultValue: 'Saving…' })
                  : t('common.save', { defaultValue: 'Save' })}
              </button>
              <a className="btn-secondary btn-sm" href={CRM_APP_PATHS.settingsDocs}>
                {t('admin.requirement_policy.open_docs', { defaultValue: 'Document types' })}
              </a>
            </div>
          </section>

          <section className="settings-panel" data-rpm-result="true">
            <h2 className="text-sm font-semibold text-slate-900">
              {t('admin.requirement_policy.result_title', { defaultValue: 'Result' })}
            </h2>
            <p className="mt-1 text-xs text-slate-600">
              {t('admin.requirement_policy.result_hint', {
                defaultValue: 'Same R5 evaluate Documents (D4) reads after this overlay is stored.',
              })}
            </p>
            <pre className="mt-3 max-h-56 overflow-auto rounded-lg bg-slate-50 p-3 text-xs text-slate-700 whitespace-pre-wrap">
              {applicabilitySummary(view.result)}
            </pre>
            <p className="mt-2 text-xs text-slate-500" data-rpm-write-authority={view.write_authority}>
              {view.contract_id} · {view.write_authority}
            </p>
          </section>
        </div>
      ) : null}
    </SettingsSubpageHeader>
  )
}
