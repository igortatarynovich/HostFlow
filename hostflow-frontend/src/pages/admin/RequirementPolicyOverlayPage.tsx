import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  getDocumentPolicyOverlay,
  putDocumentPolicyOverlay,
  type DocumentPolicyOverlay,
} from '../../api/documentPolicyOverlay'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'
import { useToast } from '../../components/Toast'
import { useI18n } from '../../i18n'

function pretty(value: unknown): string {
  try {
    return JSON.stringify(value ?? {}, null, 2)
  } catch {
    return '{}'
  }
}

export default function RequirementPolicyOverlayPage() {
  const { t } = useI18n()
  const { notify } = useToast()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [overlay, setOverlay] = useState<DocumentPolicyOverlay | null>(null)
  const [deltaJson, setDeltaJson] = useState('{}')
  const [reason, setReason] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getDocumentPolicyOverlay()
      setOverlay(data)
      setDeltaJson(pretty(data.tenant_delta))
      setReason(data.reason || '')
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      setError(msg)
      setOverlay(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const resolvedJson = useMemo(() => pretty(overlay?.resolved_policy), [overlay])

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      let parsed: Record<string, unknown>
      try {
        const value = JSON.parse(deltaJson)
        if (!value || typeof value !== 'object' || Array.isArray(value)) {
          throw new Error('tenant_delta must be an object')
        }
        parsed = value as Record<string, unknown>
      } catch (parseError: unknown) {
        const msg = parseError instanceof Error ? parseError.message : String(parseError)
        setError(msg)
        return
      }
      const data = await putDocumentPolicyOverlay({
        tenant_delta: parsed,
        reason: reason.trim(),
      })
      setOverlay(data)
      setDeltaJson(pretty(data.tenant_delta))
      setReason(data.reason || '')
      notify({
        title: t('admin.requirement_policy.saved', { defaultValue: 'Overlay saved' }),
        variant: 'success',
      })
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      setError(msg)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div data-rpm-operator="true" data-rpm-evaluator="false">
      <SettingsSubpageHeader
        className="max-w-4xl"
        backLabel={t('admin.settings.subpage.back_all')}
        kicker={t('admin.settings.sections.crm_setup.label', { defaultValue: 'CRM Setup' })}
        title={t('admin.requirement_policy.title', { defaultValue: 'Requirement policy overlay' })}
        subtitle={t('admin.requirement_policy.blurb', {
          defaultValue:
            'One overlay of the platform document pack. Writes tenant_delta into the existing R5 merge. Reason is metadata, not part of the delta.',
        })}
      >
      {error ? (
        <ErrorRecoveryBanner
          title={t('admin.requirement_policy.load_error', {
            defaultValue: 'Failed to load requirement policy overlay',
          })}
          description={error}
          onRetry={() => void load()}
        />
      ) : null}

      {loading ? (
        <div className="text-sm text-slate-500">{t('common.loading')}</div>
      ) : overlay ? (
        <div className="max-w-4xl space-y-6">
          <section className="settings-panel">
            <h2 className="text-sm font-semibold text-slate-900">
              {t('admin.requirement_policy.base_title', { defaultValue: 'Base pack' })}
            </h2>
            <p className="mt-1 text-sm text-slate-600" data-pack-version={overlay.pack_version}>
              {overlay.pack_version}
            </p>
          </section>

          <section className="settings-panel">
            <h2 className="text-sm font-semibold text-slate-900">
              {t('admin.requirement_policy.delta_title', { defaultValue: 'tenant_delta' })}
            </h2>
            <p className="mt-1 text-xs text-slate-600">
              {t('admin.requirement_policy.delta_hint', {
                defaultValue: 'candidate.overrides / vacancy.additions / validity only.',
              })}
            </p>
            <textarea
              className="mt-3 w-full min-h-[220px] rounded-lg border border-slate-200 p-3 font-mono text-xs"
              value={deltaJson}
              onChange={(event) => setDeltaJson(event.target.value)}
              spellCheck={false}
            />
          </section>

          <section className="settings-panel">
            <h2 className="text-sm font-semibold text-slate-900">
              {t('admin.requirement_policy.reason_title', { defaultValue: 'Reason' })}
            </h2>
            <textarea
              className="mt-3 w-full min-h-[80px] rounded-lg border border-slate-200 p-3 text-sm"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
            />
          </section>

          <section className="settings-panel">
            <h2 className="text-sm font-semibold text-slate-900">
              {t('admin.requirement_policy.resolved_title', { defaultValue: 'resolved_policy' })}
            </h2>
            <p className="mt-1 text-xs text-slate-600">
              {t('admin.requirement_policy.resolved_hint', {
                defaultValue: 'Output of merge_resolved_policy(pack, tenant_delta). Not a candidate evaluation.',
              })}
            </p>
            <pre
              className="mt-3 overflow-auto rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs"
              data-resolved-policy="true"
            >
              {resolvedJson}
            </pre>
          </section>

          <button
            type="button"
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            onClick={() => void handleSave()}
            disabled={saving || reason.trim().length < 3}
          >
            {saving
              ? t('common.saving', { defaultValue: 'Saving' })
              : t('common.save', { defaultValue: 'Save overlay' })}
          </button>
        </div>
      ) : null}
      </SettingsSubpageHeader>
    </div>
  )
}
