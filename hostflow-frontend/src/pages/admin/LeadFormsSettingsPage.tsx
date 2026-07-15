import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconClipboardList, IconCopy, IconPlus } from '@tabler/icons-react'
import { useI18n } from '../../i18n'
import { usePermissions } from '../../hooks/usePermissions'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'
import { useToast } from '../../components/Toast'
import { CRM_APP_PATHS, settingsLeadFormDetailPath } from '../../app/crmAppPaths'
import { listLeadForms, patchLeadForm, type TenantLeadForm } from '../../api/leadForms'
import { CreateQuestionnaireWizard } from '../../components/admin/CreateQuestionnaireWizard'
import {
  friendlyErrorBannerSecondary,
  getFriendlyErrorInfo,
  type FriendlyErrorInfo,
} from '../../utils/friendlyError'

type Draft = { title: string; public_slug: string; is_active: boolean }

function publicIntakeUrlForSlug(slug: string): string {
  if (typeof window === 'undefined') return `/public/intake?lead_form_slug=${encodeURIComponent(slug)}`
  const q = new URLSearchParams({ lead_form_slug: slug })
  return `${window.location.origin}/public/intake?${q.toString()}`
}

export default function LeadFormsSettingsPage() {
  const { t } = useI18n()
  const { role } = usePermissions()
  const { notify } = useToast()
  const canMutate = role === 'administrator'

  const [forms, setForms] = useState<TenantLeadForm[]>([])
  const [drafts, setDrafts] = useState<Record<string, Draft>>({})
  const [loading, setLoading] = useState(true)
  const [pageError, setPageError] = useState<FriendlyErrorInfo | null>(null)
  const [savingId, setSavingId] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)

  const syncDraftsFromRows = useCallback((rows: TenantLeadForm[]) => {
    setDrafts(
      Object.fromEntries(
        rows.map((r) => [
          r.id,
          {
            title: r.title || '',
            public_slug: (r.public_slug || '').trim(),
            is_active: r.is_active,
          },
        ]),
      ),
    )
  }, [])

  const load = useCallback(async () => {
    setPageError(null)
    try {
      setLoading(true)
      const rows = await listLeadForms()
      setForms(rows)
      syncDraftsFromRows(rows)
    } catch (err: unknown) {
      setPageError(
        getFriendlyErrorInfo(err, t('admin.lead_forms.errors.load', { defaultValue: 'Failed to load lead forms' }), t),
      )
      setForms([])
      setDrafts({})
    } finally {
      setLoading(false)
    }
  }, [syncDraftsFromRows, t])

  useEffect(() => {
    void load()
  }, [load])

  const updateDraft = (id: string, patch: Partial<Draft>) => {
    setDrafts((prev) => {
      const cur = prev[id]
      if (!cur) return prev
      return { ...prev, [id]: { ...cur, ...patch } }
    })
  }

  const handleSaveRow = async (row: TenantLeadForm) => {
    if (!canMutate) return
    const d = drafts[row.id]
    if (!d) return
    setPageError(null)
    setSavingId(row.id)
    try {
      const slugTrim = d.public_slug.trim()
      const updated = await patchLeadForm(row.id, {
        title: d.title.trim() || undefined,
        is_active: d.is_active,
        public_slug: slugTrim === '' ? '' : slugTrim,
      })
      setForms((prev) => prev.map((f) => (f.id === updated.id ? updated : f)))
      setDrafts((prev) => ({
        ...prev,
        [updated.id]: {
          title: updated.title || '',
          public_slug: (updated.public_slug || '').trim(),
          is_active: updated.is_active,
        },
      }))
      notify({
        title: t('admin.lead_forms.toast.saved', { defaultValue: 'Saved' }),
        variant: 'success',
      })
    } catch (err: unknown) {
      setPageError(
        getFriendlyErrorInfo(err, t('admin.lead_forms.errors.save', { defaultValue: 'Failed to save form' }), t),
      )
    } finally {
      setSavingId(null)
    }
  }

  const copyText = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      notify({
        title: t('admin.lead_forms.toast.copied', { defaultValue: 'Copied' }),
        variant: 'success',
      })
    } catch {
      notify({
        title: t('admin.lead_forms.errors.copy', { defaultValue: 'Could not copy' }),
        variant: 'error',
      })
    }
  }

  const isDirty = useCallback(
    (row: TenantLeadForm) => {
      const d = drafts[row.id]
      if (!d) return false
      return (
        d.title !== (row.title || '') ||
        d.public_slug !== (row.public_slug || '').trim() ||
        d.is_active !== row.is_active
      )
    },
    [drafts],
  )

  const sortedForms = useMemo(() => [...forms].sort((a, b) => a.created_at.localeCompare(b.created_at)), [forms])

  return (
    <SettingsSubpageHeader
      backLabel={t('admin.settings.subpage.back_all')}
      kicker={t('admin.lead_forms.header_kicker')}
      title={
        <span className="inline-flex items-center gap-2">
          <IconClipboardList size={22} stroke={1.9} className="text-brand-600" />
          {t('admin.lead_forms.title', { defaultValue: 'Анкеты' })}
        </span>
      }
      subtitle={t('admin.lead_forms.subtitle_f3', {
        defaultValue: 'Создавайте анкеты для продаж и найма. После сохранения сразу отправляйте клиентам.',
      })}
      actions={
        <Link className="text-sm font-medium text-brand-700 hover:underline" to={CRM_APP_PATHS.settingsBilling}>
          {t('admin.lead_forms.link_billing', { defaultValue: 'Billing & limits' })}
        </Link>
      }
    >
      <section className="settings-panel">
        {pageError && (
          <div className="mb-4">
            <ErrorRecoveryBanner
              info={pageError}
              {...friendlyErrorBannerSecondary(pageError, CRM_APP_PATHS.settingsBilling, t('admin.settings.cards.billing.label'))}
            />
          </div>
        )}

        {!canMutate && (
          <p className="mb-4 rounded-xl border border-amber-100 bg-amber-50/80 px-3 py-2 text-sm text-amber-900">
            {t('admin.lead_forms.read_only_hint', {
              defaultValue: 'Only workspace administrators can create or edit lead forms.',
            })}
          </p>
        )}

        {canMutate && (
          <div className="mb-6">
            {!showCreate ? (
              <button type="button" className="btn-primary inline-flex items-center gap-2" onClick={() => setShowCreate(true)}>
                <IconPlus size={16} />
                {t('admin.questionnaire.create_cta', { defaultValue: 'Создать анкету' })}
              </button>
            ) : (
              <CreateQuestionnaireWizard onCancel={() => setShowCreate(false)} />
            )}
          </div>
        )}

        {loading ? (
          <p className="text-sm text-slate-500">{t('common.loading')}</p>
        ) : sortedForms.length === 0 ? (
          <p className="text-sm text-slate-500">
            {t('admin.lead_forms.empty_f3', {
              defaultValue: 'Анкет пока нет. Нажмите «Создать анкету» и выберите направление.',
            })}
          </p>
        ) : (
          <ul className="space-y-4">
            {sortedForms.map((row) => {
              const d = drafts[row.id]
              if (!d) return null
              const slugOk = d.public_slug.trim().length >= 2
              const shareUrl = slugOk ? publicIntakeUrlForSlug(d.public_slug.trim()) : ''
              const dirty = isDirty(row)
              return (
                <li key={row.id} className="rounded-xl border border-brand-100 bg-white p-4 shadow-sm">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-slate-900">{d.title || row.title}</p>
                      <p className="mt-1 text-sm text-slate-600">
                        {d.is_active
                          ? t('admin.questionnaire_card.status_active', { defaultValue: 'Статус: Активна' })
                          : t('admin.questionnaire_card.status_inactive', { defaultValue: 'Статус: Неактивна' })}
                      </p>
                    </div>
                    <Link to={settingsLeadFormDetailPath(row.id)} className="btn-primary btn-sm">
                      {t('admin.questionnaire.open_card', { defaultValue: 'Открыть' })}
                    </Link>
                  </div>

                  <details className="mt-4 rounded-xl border border-slate-100 bg-slate-50/50 p-3">
                    <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wide text-slate-500">
                      {t('admin.lead_forms.advanced_settings', { defaultValue: 'Расширенные настройки' })}
                    </summary>
                    <div className="mt-3 grid gap-4 lg:grid-cols-[1fr_1fr]">
                      <label className="block">
                        <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                          {t('admin.lead_forms.fields.title', { defaultValue: 'Title' })}
                        </span>
                        <input
                          type="text"
                          className="input w-full"
                          value={d.title}
                          onChange={(e) => updateDraft(row.id, { title: e.target.value })}
                          disabled={!canMutate}
                        />
                      </label>
                      <label className="block">
                        <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                          {t('admin.lead_forms.fields.public_slug', { defaultValue: 'Public slug' })}
                        </span>
                        <input
                          type="text"
                          className="input w-full font-mono text-sm"
                          value={d.public_slug}
                          onChange={(e) => updateDraft(row.id, { public_slug: e.target.value })}
                          disabled={!canMutate}
                        />
                      </label>
                    </div>
                    <div className="mt-3 flex flex-wrap items-center gap-3">
                      <label className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          className="rounded border-slate-300"
                          checked={d.is_active}
                          onChange={(e) => updateDraft(row.id, { is_active: e.target.checked })}
                          disabled={!canMutate}
                        />
                        <span className="text-sm text-slate-700">
                          {t('admin.lead_forms.fields.active', { defaultValue: 'Active' })}
                        </span>
                      </label>
                      {canMutate && (
                        <button
                          type="button"
                          className="btn-secondary btn-sm"
                          disabled={!dirty || savingId === row.id}
                          onClick={() => void handleSaveRow(row)}
                        >
                          {savingId === row.id ? t('common.saving') : t('common.actions.save')}
                        </button>
                      )}
                    </div>
                    {slugOk && (
                      <div className="mt-4 rounded-xl border border-slate-100 bg-white p-3">
                        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                          {t('admin.lead_forms.share_url', { defaultValue: 'Public intake URL' })}
                        </div>
                        <div className="mt-1 flex flex-wrap items-center gap-2 break-all font-mono text-xs text-slate-800">
                          <span className="flex-1">{shareUrl}</span>
                          <button
                            type="button"
                            className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
                            onClick={() => void copyText(shareUrl)}
                          >
                            <IconCopy size={14} />
                            {t('admin.lead_forms.copy', { defaultValue: 'Copy' })}
                          </button>
                        </div>
                      </div>
                    )}
                  </details>
                </li>
              )
            })}
          </ul>
        )}
      </section>
    </SettingsSubpageHeader>
  )
}
