import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { getCommunicationsSettings, patchCommunicationsSettings } from '../../api/communications'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import type { FriendlyErrorInfo } from '../../utils/friendlyError'
import { friendlyErrorBannerSecondary, friendlyFormHintError, getFriendlyErrorInfo } from '../../utils/friendlyError'
import { usePlanLimitModal } from '../../contexts/PlanLimitModalContext'

const CHANNEL_OPTIONS = ['telegram', 'whatsapp', 'viber', 'messenger', 'instagram', 'email', 'sms'] as const
const RESERVED_ESCALATION_TARGETS = new Set(['all', 'none', 'default', 'system', 'auto', 'role', 'queue', 'user'])

export default function CommunicationsSlaSettingsPage() {
  const { t } = useI18n()
  const planLimitModal = usePlanLimitModal()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [saveNotice, setSaveNotice] = useState<string | null>(null)
  const [saveBusy, setSaveBusy] = useState(false)
  const [settings, setSettings] = useState<any | null>(null)
  const [escalationTargets, setEscalationTargets] = useState<string[]>([])
  const [newEscalationTarget, setNewEscalationTarget] = useState('')

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        const cfg = await getCommunicationsSettings()
        if (mounted) {
          setSettings(cfg)
          const targets = Array.isArray(cfg?.sla?.escalationTargets) ? cfg.sla.escalationTargets : []
          setEscalationTargets(
            Array.from(new Set(targets.map((x: any) => String(x || '').trim()).filter(Boolean))),
          )
          setNewEscalationTarget('')
        }
      } catch (err: any) {
        if (mounted) {
          if (
            !planLimitModal?.showPlanLimitIfNeeded(
              err,
              t('admin.communications_sla.errors.load', { defaultValue: 'Failed to load SLA settings' }),
            )
          ) {
            setError(getFriendlyErrorInfo(err, t('admin.communications_sla.errors.load', { defaultValue: 'Failed to load SLA settings' }), t))
          }
        }
      } finally {
        if (mounted) setLoading(false)
      }
    })()
    return () => { mounted = false }
  }, [planLimitModal, t])

  const sla = settings?.sla || null

  useEffect(() => {
    if (!sla) return
    const targets = Array.isArray(sla.escalationTargets) ? sla.escalationTargets : []
    setEscalationTargets(
      Array.from(new Set(targets.map((x: any) => String(x || '').trim()).filter(Boolean))),
    )
    setNewEscalationTarget('')
  }, [sla])

  const saveSlaSettings = useCallback(async (nextSla: any) => {
    setSaveBusy(true)
    setSaveNotice(null)
    setError(null)
    try {
      const patched = await patchCommunicationsSettings({ sla: nextSla })
      setSettings(patched)
      setSaveNotice(t('common.saved', { defaultValue: 'Saved' }))
    } catch (err: any) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('admin.communications_sla.errors.save', { defaultValue: 'Failed to save SLA settings' }),
        )
      ) {
        setError(getFriendlyErrorInfo(err, t('admin.communications_sla.errors.save', { defaultValue: 'Failed to save SLA settings' }), t))
      }
    } finally {
      setSaveBusy(false)
    }
  }, [planLimitModal, t])

  const patchSla = useCallback((partial: Record<string, any>) => {
    if (!sla) return
    void saveSlaSettings({ ...sla, ...partial })
  }, [sla, saveSlaSettings])

  const toggleMutedChannel = (channel: string, enabled: boolean) => {
    if (!sla) return
    const current = Array.isArray(sla.mutedChannels) ? sla.mutedChannels.map((x: any) => String(x).toLowerCase()) : []
    const next = enabled ? Array.from(new Set([...current, channel])) : current.filter((x) => x !== channel)
    patchSla({ mutedChannels: next })
  }

  const normalizeTargetId = (value: string): string => {
    return String(value || '')
      .trim()
      .toLowerCase()
      .replace(/\s+/g, '_')
      .replace(/[^a-z0-9_-]/g, '')
      .slice(0, 64)
  }

  const validateTargetId = (normalized: string): string | null => {
    if (!normalized) return t('admin.communications_sla.escalation_targets_error_invalid', { defaultValue: 'Use only latin letters, numbers, `_` or `-`.' })
    if (!/^[a-z][a-z0-9_-]{1,63}$/.test(normalized)) {
      return t('admin.communications_sla.escalation_targets_error_format', {
        defaultValue: 'Queue ID must start with a letter and be 2-64 chars: `a-z`, `0-9`, `_`, `-`.',
      })
    }
    if (RESERVED_ESCALATION_TARGETS.has(normalized)) {
      return t('admin.communications_sla.escalation_targets_error_reserved', { defaultValue: 'This queue ID is reserved.' })
    }
    return null
  }

  const normalizedDraftTarget = useMemo(() => normalizeTargetId(newEscalationTarget), [newEscalationTarget])
  const draftTargetError = useMemo(() => {
    if (!newEscalationTarget.trim()) return null
    const baseError = validateTargetId(normalizedDraftTarget)
    if (baseError) return baseError
    if (escalationTargets.includes(normalizedDraftTarget)) {
      return t('admin.communications_sla.escalation_targets_error_duplicate', { defaultValue: 'This queue ID already exists.' })
    }
    return null
  }, [newEscalationTarget, normalizedDraftTarget, escalationTargets, t])

  const invalidTargets = useMemo(
    () => escalationTargets.filter((target) => Boolean(validateTargetId(String(target || '').trim().toLowerCase()))),
    [escalationTargets, t],
  )

  const addEscalationTarget = () => {
    const normalized = normalizedDraftTarget
    if (!normalized) return
    const validationError = validateTargetId(normalized)
    if (validationError) {
      setError(friendlyFormHintError(validationError, t))
      return
    }
    if (escalationTargets.includes(normalized)) {
      setError(
        friendlyFormHintError(
          t('admin.communications_sla.escalation_targets_error_duplicate', { defaultValue: 'This queue ID already exists.' }),
          t,
        ),
      )
      return
    }
    setError(null)
    setEscalationTargets((prev) => (prev.includes(normalized) ? prev : [...prev, normalized]))
    setNewEscalationTarget('')
  }

  const removeEscalationTarget = (target: string) => {
    setEscalationTargets((prev) => prev.filter((x) => x !== target))
  }

  const saveEscalationTargets = () => {
    if (!sla) return
    if (invalidTargets.length > 0) {
      setError(
        friendlyFormHintError(
          t('admin.communications_sla.escalation_targets_error_invalid_existing', {
            defaultValue: 'Remove or fix invalid queue IDs before saving escalation targets.',
          }),
          t,
        ),
      )
      return
    }
    const parsed = Array.from(new Set(escalationTargets.map((x) => normalizeTargetId(x)).filter(Boolean)))
    patchSla({ escalationTargets: parsed })
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">{t('admin.communications_sla.title', { defaultValue: 'SLA settings' })}</h1>
          <p className="text-sm text-slate-500">{t('admin.communications_sla.subtitle', { defaultValue: 'Escalation policy for overdue communication threads.' })}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to={CRM_APP_PATHS.settingsCommunications} className="btn-secondary">
            {t('admin.communications_sla.actions.all', { defaultValue: 'All communication settings' })}
          </Link>
          <Link to={CRM_APP_PATHS.settingsCommunicationsQueue} className="btn-secondary">
            {t('admin.settings.cards.communications_queue.label', { defaultValue: 'Queue settings' })}
          </Link>
        </div>
      </div>

      {loading && <div className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading...' })}</div>}
      {error && (
        <ErrorRecoveryBanner
          info={error}
          onRetry={() => window.location.reload()}
          retryLabel={t('common.actions.refresh', { defaultValue: 'Refresh' })}
          {...friendlyErrorBannerSecondary(
            error,
            CRM_APP_PATHS.settingsCommunications,
            t('admin.communications_sla.actions.all', { defaultValue: 'All communication settings' }),
          )}
          compact
        />
      )}
      {saveNotice && <div className="alert-success">{saveNotice}</div>}

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold text-slate-900">{t('admin.communications_sla.policy_title', { defaultValue: 'SLA escalation policy' })}</h2>
        {sla ? (
          <div className="space-y-3 text-sm">
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="space-y-1">
                <span className="text-xs font-medium text-slate-600">{t('admin.communications_sla.recipient_mode', { defaultValue: 'Recipient mode' })}</span>
                <select
                  value={String(sla.recipientMode || 'assignee_or_owner')}
                  onChange={(e) => patchSla({ recipientMode: e.target.value })}
                  disabled={saveBusy}
                  className="input"
                >
                  <option value="assignee_or_owner">
                    {t('admin.communications_sla.recipient_modes.assignee_or_owner', { defaultValue: 'assignee_or_owner' })}
                  </option>
                  <option value="assignee_only">
                    {t('admin.communications_sla.recipient_modes.assignee_only', { defaultValue: 'assignee_only' })}
                  </option>
                  <option value="owner_only">
                    {t('admin.communications_sla.recipient_modes.owner_only', { defaultValue: 'owner_only' })}
                  </option>
                </select>
              </label>
              <div className="rounded border border-slate-200 px-3 py-2 text-xs text-slate-600">
                {t('admin.communications_sla.recipient_mode_help', { defaultValue: 'Controls who receives `communications_sla_overdue` events.' })}
              </div>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              {[
                ['enabled', t('admin.communications_sla.toggles.enabled', { defaultValue: 'Enable SLA escalations' })],
                ['createNotifications', t('admin.communications_sla.toggles.notifications', { defaultValue: 'Create in-app notifications' })],
                ['createReminders', t('admin.communications_sla.toggles.reminders', { defaultValue: 'Create reminder tasks' })],
              ].map(([key, label]) => (
                <label key={key} className="flex items-center gap-2 rounded border border-slate-200 px-3 py-2">
                  <input
                    type="checkbox"
                    checked={Boolean(sla[key])}
                    onChange={(e) => patchSla({ [key]: e.target.checked })}
                    disabled={saveBusy}
                  />
                  <span>{label}</span>
                </label>
              ))}
            </div>
            <div className="space-y-2">
              <div className="text-xs font-medium text-slate-600">{t('admin.communications_sla.muted_channels', { defaultValue: 'Muted channels for SLA' })}</div>
              <div className="grid gap-2 sm:grid-cols-2">
                {CHANNEL_OPTIONS.map((channel) => {
                  const checked = Array.isArray(sla.mutedChannels) && sla.mutedChannels.map((x: any) => String(x).toLowerCase()).includes(channel)
                  return (
                    <label key={channel} className="flex items-center gap-2 rounded border border-slate-200 px-3 py-2">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={(e) => toggleMutedChannel(channel, e.target.checked)}
                        disabled={saveBusy}
                      />
                      <span>{channel}</span>
                    </label>
                  )
                })}
              </div>
            </div>
            <div className="space-y-2">
              <div className="text-xs font-medium text-slate-600">
                {t('admin.communications_sla.escalation_targets', { defaultValue: 'Escalation queue targets' })}
              </div>
              <div className="rounded border border-slate-200 bg-slate-50 p-2">
                <div className="mb-2 flex flex-wrap gap-2">
                  {escalationTargets.length > 0 ? escalationTargets.map((target) => (
                    <span
                      key={target}
                      className={[
                        'badge border bg-white font-mono',
                        invalidTargets.includes(target)
                          ? 'border-rose-300 text-rose-700'
                          : 'border-slate-300 text-slate-700',
                      ].join(' ')}
                    >
                      {target}
                      <button
                        type="button"
                        onClick={() => removeEscalationTarget(target)}
                        disabled={saveBusy}
                        className="btn-secondary btn-xs px-1.5 py-0 disabled:opacity-50"
                        aria-label={t('common.actions.delete', { defaultValue: 'Delete' })}
                      >
                        ×
                      </button>
                    </span>
                  )) : (
                    <span className="text-xs text-slate-500">
                      {t('admin.communications_sla.escalation_targets_empty', { defaultValue: 'No escalation targets configured.' })}
                    </span>
                  )}
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <input
                    value={newEscalationTarget}
                    onChange={(e) => setNewEscalationTarget(e.target.value)}
                    disabled={saveBusy}
                    className={[
                      'input min-w-[220px] flex-1 font-mono text-xs',
                      draftTargetError ? 'border-rose-300' : 'border-slate-300',
                    ].join(' ')}
                    placeholder={t('admin.communications_sla.escalation_targets_placeholder', {
                      defaultValue: 'priority or manual_review',
                    })}
                  />
                  <button
                    type="button"
                    onClick={addEscalationTarget}
                    disabled={saveBusy || !normalizedDraftTarget || Boolean(draftTargetError)}
                    className="btn-secondary btn-sm disabled:opacity-50"
                  >
                    {t('common.actions.add', { defaultValue: 'Add' })}
                  </button>
                </div>
                {draftTargetError && (
                  <div className="text-xs text-rose-600">{draftTargetError}</div>
                )}
                {!draftTargetError && newEscalationTarget.trim() && normalizedDraftTarget && normalizedDraftTarget !== newEscalationTarget.trim().toLowerCase() && (
                  <div className="text-xs text-slate-500">
                    {t('admin.communications_sla.escalation_targets_normalized_preview', {
                      defaultValue: 'Will be saved as: {value}',
                      values: { value: normalizedDraftTarget },
                    })}
                  </div>
                )}
              </div>
              <div className="flex items-center justify-between gap-2">
                <div className="text-xs text-slate-500">
                  {t('admin.communications_sla.escalation_targets_help', {
                    defaultValue: 'Escalation targets are used in Messages escalation modal. Use short queue IDs like `priority` or `manual_review`.',
                  })}
                </div>
                <button
                  type="button"
                  onClick={saveEscalationTargets}
                  disabled={saveBusy || invalidTargets.length > 0}
                  className="btn-secondary btn-sm disabled:opacity-50"
                >
                  {t('common.actions.save', { defaultValue: 'Save' })}
                </button>
              </div>
              {invalidTargets.length > 0 && (
                <div className="text-xs text-rose-600">
                  {t('admin.communications_sla.escalation_targets_invalid_list', {
                    defaultValue: 'Invalid targets: {items}',
                    values: { items: invalidTargets.join(', ') },
                  })}
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading...' })}</div>
        )}
      </div>
    </div>
  )
}
