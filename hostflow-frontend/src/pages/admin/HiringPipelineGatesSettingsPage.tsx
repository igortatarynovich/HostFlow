import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useI18n } from '../../i18n'
import { getHiringPipelineGates, patchHiringPipelineGates } from '../../api/tenants'
import type { HiringPipelineGatesPublic } from '../../api/types'
import { usePermissions } from '../../hooks/usePermissions'
import { useToast } from '../../components/Toast'
import { useHiringPipelineGates } from '../../contexts/HiringPipelineGatesContext'

function linesToList(text: string): string[] {
  return text
    .split(/\r?\n/)
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean)
}

function listToLines(items: string[]): string {
  return (items || []).join('\n')
}

export default function HiringPipelineGatesSettingsPage() {
  const { t } = useI18n()
  const { notify } = useToast()
  const { role } = usePermissions()
  const { refetch: refetchContextGates } = useHiringPipelineGates()
  const isAdmin = String(role || '').toLowerCase() === 'administrator'

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [baseline, setBaseline] = useState<HiringPipelineGatesPublic | null>(null)

  const [withoutBlock, setWithoutBlock] = useState('')
  const [verifyUploads, setVerifyUploads] = useState('')
  const [vacancyStages, setVacancyStages] = useState('')
  const [contactAttemptStages, setContactAttemptStages] = useState('')
  const [softOnly, setSoftOnly] = useState('')
  const [nonOverridableExtra, setNonOverridableExtra] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const g = await getHiringPipelineGates()
      if (!g) {
        throw new Error('API returned no data (endpoint missing or unauthorized)')
      }
      setBaseline(g)
      setWithoutBlock(listToLines(g.stages_without_doc_pipeline_block))
      setVerifyUploads(listToLines(g.stages_verify_uploads_block_forward))
      setVacancyStages(listToLines(g.stages_require_vacancy_for_forward))
      setContactAttemptStages(listToLines(g.contact_attempt_gate_stages))
      setSoftOnly(listToLines(g.stages_doc_block_soft_only))
      setNonOverridableExtra(listToLines(g.non_overridable_doc_types_extra))
    } catch (e: any) {
      notify({
        title: t('admin.hiring_gates.load_error', { defaultValue: 'Failed to load hiring pipeline gates' }),
        description: e?.message,
        variant: 'error',
      })
      setBaseline(null)
    } finally {
      setLoading(false)
    }
  }, [notify, t])

  useEffect(() => {
    void load()
  }, [load])

  const effectivePreview = useMemo(() => baseline?.effective_non_overridable_doc_types ?? [], [baseline])

  const handleSave = async () => {
    if (!isAdmin) return
    setSaving(true)
    try {
      const updated = await patchHiringPipelineGates({
        stages_without_doc_pipeline_block: linesToList(withoutBlock),
        stages_verify_uploads_block_forward: linesToList(verifyUploads),
        stages_require_vacancy_for_forward: linesToList(vacancyStages),
        contact_attempt_gate_stages: linesToList(contactAttemptStages),
        stages_doc_block_soft_only: linesToList(softOnly),
        non_overridable_doc_types_extra: linesToList(nonOverridableExtra),
      })
      setBaseline(updated)
      await refetchContextGates()
      notify({
        title: t('admin.hiring_gates.saved', { defaultValue: 'Hiring pipeline gates saved' }),
        variant: 'success',
      })
    } catch (e: any) {
      notify({
        title: t('admin.hiring_gates.save_error', { defaultValue: 'Save failed' }),
        description: e?.response?.data?.detail ?? e?.message,
        variant: 'error',
      })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('admin.hiring_gates.kicker', { defaultValue: 'CRM setup' })}
          </div>
          <h1 className="text-2xl font-bold text-slate-900">
            {t('admin.hiring_gates.title', { defaultValue: 'Hiring pipeline gates' })}
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-slate-600">
            {t('admin.hiring_gates.blurb', {
              defaultValue:
                'Configure which stages enforce document, vacancy, and contact-attempt rules. Stored in tenant settings (hiring_stage_gates_v1).',
            })}
          </p>
        </div>
        <Link to="/app/settings" className="btn-secondary btn-sm">
          {t('admin.hiring_gates.back', { defaultValue: '← Settings' })}
        </Link>
      </div>

      {loading ? (
        <div className="text-sm text-slate-500">{t('common.loading')}</div>
      ) : (
        <div className="space-y-6">
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="text-sm font-semibold text-slate-800">
              {t('admin.hiring_gates.effective_non_overridable', {
                defaultValue: 'Effective non-waivable document types (read-only)',
              })}
            </div>
            <p className="mt-1 text-xs text-slate-600">
              {t('admin.hiring_gates.effective_non_overridable_hint', {
                defaultValue: 'Global fail-safe set plus tenant extras below.',
              })}
            </p>
            <div className="mt-2 flex flex-wrap gap-1">
              {effectivePreview.length ? (
                effectivePreview.map((c) => (
                  <span
                    key={c}
                    className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] font-medium text-slate-800"
                  >
                    {c}
                  </span>
                ))
              ) : (
                <span className="text-xs text-slate-500">—</span>
              )}
            </div>
          </div>

          {[
            {
              key: 'without',
              label: t('admin.hiring_gates.field.without_block', {
                defaultValue: 'Stages without document pipeline block',
              }),
              hint: t('admin.hiring_gates.field.without_block_hint', {
                defaultValue: 'One stage code per line (e.g. new, contacted).',
              }),
              value: withoutBlock,
              onChange: setWithoutBlock,
            },
            {
              key: 'verify',
              label: t('admin.hiring_gates.field.verify_uploads', {
                defaultValue: 'Stages where unverified uploads may block forward',
              }),
              hint: t('admin.hiring_gates.field.verify_uploads_hint', {
                defaultValue: 'In-progress (awaiting review) documents can block from these stages.',
              }),
              value: verifyUploads,
              onChange: setVerifyUploads,
            },
            {
              key: 'vacancy',
              label: t('admin.hiring_gates.field.vacancy', {
                defaultValue: 'Stages requiring vacancy before forward',
              }),
              hint: t('admin.hiring_gates.field.vacancy_hint', { defaultValue: 'Typically contacted, questionnaire_submitted.' }),
              value: vacancyStages,
              onChange: setVacancyStages,
            },
            {
              key: 'contact',
              label: t('admin.hiring_gates.field.contact_attempt', {
                defaultValue: 'Contact-attempt gate stages',
              }),
              hint: t('admin.hiring_gates.field.contact_attempt_hint', {
                defaultValue: 'When policy is on, forward from these stages requires ≥1 logged attempt (default: new).',
              }),
              value: contactAttemptStages,
              onChange: setContactAttemptStages,
            },
            {
              key: 'soft',
              label: t('admin.hiring_gates.field.soft_only', {
                defaultValue: 'Soft-only document block (advisory, no server 409)',
              }),
              hint: t('admin.hiring_gates.field.soft_only_hint', {
                defaultValue: 'If a stage is listed here and would otherwise hard-block on docs, the API allows forward; UI shows advisory.',
              }),
              value: softOnly,
              onChange: setSoftOnly,
            },
            {
              key: 'extra',
              label: t('admin.hiring_gates.field.non_overridable_extra', {
                defaultValue: 'Extra non-waivable document types (tenant)',
              }),
              hint: t('admin.hiring_gates.field.non_overridable_extra_hint', {
                defaultValue: 'Canonical doc type codes, one per line.',
              }),
              value: nonOverridableExtra,
              onChange: setNonOverridableExtra,
            },
          ].map((field) => (
            <label key={field.key} className="block rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="text-sm font-semibold text-slate-800">{field.label}</div>
              <p className="mt-1 text-xs text-slate-600">{field.hint}</p>
              <textarea
                className="mt-2 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 font-mono text-xs text-slate-900 disabled:opacity-60"
                rows={6}
                value={field.value}
                onChange={(e) => field.onChange(e.target.value)}
                disabled={!isAdmin}
              />
            </label>
          ))}

          {isAdmin ? (
            <div className="flex justify-end gap-2">
              <button type="button" className="btn-secondary btn-sm" onClick={() => void load()} disabled={saving}>
                {t('common.reload', { defaultValue: 'Reload' })}
              </button>
              <button type="button" className="btn-primary btn-sm" onClick={() => void handleSave()} disabled={saving}>
                {saving ? t('common.saving', { defaultValue: 'Saving…' }) : t('common.save', { defaultValue: 'Save' })}
              </button>
            </div>
          ) : (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
              {t('admin.hiring_gates.read_only', {
                defaultValue: 'Only workspace administrators can edit these lists.',
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
