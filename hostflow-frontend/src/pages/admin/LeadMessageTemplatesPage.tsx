import { Link } from 'react-router-dom'
import { useCallback, useEffect, useState } from 'react'
import {
  createLeadMessageTemplate,
  deleteLeadMessageTemplate,
  listLeadMessageTemplates,
  updateLeadMessageTemplate,
} from '../../api/metaLeads'
import type { FriendlyErrorInfo } from '../../utils/friendlyError'
import { getFriendlyErrorInfo } from '../../utils/friendlyError'
import type { LeadMessageTemplate } from '../../api/types'
import { useI18n } from '../../i18n'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'

function applyWrap(
  value: string,
  start: number,
  end: number,
  left: string,
  right: string,
): string {
  const safeStart = Math.max(0, Math.min(start, value.length))
  const safeEnd = Math.max(safeStart, Math.min(end, value.length))
  const before = value.slice(0, safeStart)
  const selected = value.slice(safeStart, safeEnd)
  const after = value.slice(safeEnd)
  return `${before}${left}${selected}${right}${after}`
}

export default function LeadMessageTemplatesPage() {
  const { t } = useI18n()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const [templates, setTemplates] = useState<LeadMessageTemplate[]>([])
  const [newName, setNewName] = useState('')
  const [newSubject, setNewSubject] = useState('')
  const [newBody, setNewBody] = useState('')
  const [newBodyRef, setNewBodyRef] = useState<HTMLTextAreaElement | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const tpls = await listLeadMessageTemplates()
      setTemplates(Array.isArray(tpls) ? tpls : [])
    } catch (err: unknown) {
      setError(getFriendlyErrorInfo(err, t('admin.meta_leads.errors.load'), t))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const handleCreate = useCallback(async () => {
    const name = newName.trim()
    if (!name) return
    try {
      const created = await createLeadMessageTemplate({
        name,
        subject: newSubject,
        body: newBody,
        is_active: true,
      })
      setTemplates((prev) => [...prev, created].sort((a, b) => a.name.localeCompare(b.name)))
      setNewName('')
      setNewSubject('')
      setNewBody('')
      setNotice(t('admin.meta_leads.templates.saved_notice', { defaultValue: 'Template saved.' }))
    } catch (err: unknown) {
      setError(getFriendlyErrorInfo(err, t('admin.meta_leads.errors.save'), t))
    }
  }, [newBody, newName, newSubject, t])

  const saveTemplate = useCallback(
    async (row: LeadMessageTemplate) => {
      try {
        const updated = await updateLeadMessageTemplate(row.id, {
          name: row.name,
          subject: row.subject,
          body: row.body,
          is_active: row.is_active,
        })
        setTemplates((prev) => prev.map((x) => (x.id === updated.id ? updated : x)))
      } catch (err: unknown) {
        setError(getFriendlyErrorInfo(err, t('admin.meta_leads.errors.save'), t))
      }
    },
    [t],
  )

  const removeTemplate = useCallback(
    async (templateId: string) => {
      try {
        await deleteLeadMessageTemplate(templateId)
        setTemplates((prev) => prev.filter((x) => x.id !== templateId))
      } catch (err: unknown) {
        setError(getFriendlyErrorInfo(err, t('admin.meta_leads.errors.save'), t))
      }
    },
    [t],
  )

  const formatNewBody = useCallback(
    (left: string, right: string = left) => {
      if (!newBodyRef) return
      const next = applyWrap(newBody, newBodyRef.selectionStart, newBodyRef.selectionEnd, left, right)
      setNewBody(next)
    },
    [newBody, newBodyRef],
  )

  return (
    <SettingsSubpageHeader
      backLabel={t('admin.settings.subpage.back_all')}
      title={t('admin.meta_leads.settings.template_hub_title', { defaultValue: 'Lead Email Template Hub' })}
      subtitle={t('admin.meta_leads.settings.template_hub_hint', {
        defaultValue: 'Create shared templates once and bind them in the Lead lifecycle email Control Center.',
      })}
      backHref={CRM_APP_PATHS.settings}
    >
      {error ? <ErrorRecoveryBanner error={error} /> : null}
      {notice ? <div className="rounded border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{notice}</div> : null}

      <section className="rounded-lg border border-sky-200 bg-sky-50 p-4 text-sm text-sky-950">
        <p className="font-semibold">
          {t('admin.lead_lifecycle_email.bindings_moved_title', {
            defaultValue: 'Company policy lives in Communications Control Center',
          })}
        </p>
        <p className="mt-1 text-xs text-sky-900/80">
          {t('admin.lead_lifecycle_email.bindings_moved_body', {
            defaultValue:
              'Bind RODO and ops templates per company (with vacancy overrides) under Settings → Communications → Lead lifecycle email. This page is the shared template catalog.',
          })}
        </p>
        <Link
          className="mt-2 inline-flex font-medium text-brand-700 underline-offset-2 hover:underline"
          to={CRM_APP_PATHS.settingsCommunicationsLeadLifecycleEmail}
        >
          {t('admin.meta_leads.settings.open_lifecycle_email_control_center', {
            defaultValue: 'Open Lead lifecycle email Control Center',
          })}
        </Link>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h3 className="text-sm font-semibold text-slate-900">
          {t('admin.meta_leads.settings.template_create', { defaultValue: 'Create template' })}
        </h3>
        <div className="mt-2 grid gap-2 md:grid-cols-3">
          <input
            className="input"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder={t('admin.meta_leads.settings.template_name', { defaultValue: 'Template name' })}
          />
          <input
            className="input md:col-span-2"
            value={newSubject}
            onChange={(e) => setNewSubject(e.target.value)}
            placeholder={t('admin.meta_leads.settings.email_template_subject', { defaultValue: 'Email subject' })}
          />
          <textarea
            ref={(el) => setNewBodyRef(el)}
            className="input md:col-span-3 min-h-[100px]"
            value={newBody}
            onChange={(e) => setNewBody(e.target.value)}
            placeholder={t('admin.meta_leads.settings.email_template_body', { defaultValue: 'Email body' })}
          />
          <div className="md:col-span-3 flex flex-wrap gap-2 text-xs">
            <button type="button" className="btn-secondary btn-xs" onClick={() => formatNewBody('**')}>
              Bold
            </button>
            <button type="button" className="btn-secondary btn-xs" onClick={() => formatNewBody('*')}>
              Italic
            </button>
            <button type="button" className="btn-secondary btn-xs" onClick={() => formatNewBody('[', '](https://)')}>
              Link
            </button>
            <button
              type="button"
              className="btn-secondary btn-xs"
              onClick={() => setNewBody((prev) => `${prev}\n\n---\n\n`)}
            >
              Divider
            </button>
          </div>
        </div>
        <button type="button" className="btn-primary mt-2" onClick={() => void handleCreate()} disabled={loading}>
          {t('admin.meta_leads.settings.template_create', { defaultValue: 'Create template' })}
        </button>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h3 className="text-sm font-semibold text-slate-900">
          {t('admin.meta_leads.settings.template_hub_title', { defaultValue: 'Lead Email Template Hub' })}
        </h3>
        <div className="mt-2 space-y-3">
          {templates.map((tpl) => (
            <div key={tpl.id} className="rounded border border-slate-200 p-3">
              <div className="grid gap-2 md:grid-cols-3">
                <input
                  className="input"
                  value={tpl.name}
                  onChange={(e) =>
                    setTemplates((prev) => prev.map((x) => (x.id === tpl.id ? { ...x, name: e.target.value } : x)))
                  }
                />
                <input
                  className="input md:col-span-2"
                  value={tpl.subject}
                  onChange={(e) =>
                    setTemplates((prev) => prev.map((x) => (x.id === tpl.id ? { ...x, subject: e.target.value } : x)))
                  }
                />
                <textarea
                  className="input md:col-span-3 min-h-[100px]"
                  value={tpl.body}
                  onChange={(e) =>
                    setTemplates((prev) => prev.map((x) => (x.id === tpl.id ? { ...x, body: e.target.value } : x)))
                  }
                />
              </div>
              <div className="mt-2 flex items-center gap-2">
                <label className="inline-flex items-center gap-2 text-xs text-slate-600">
                  <input
                    type="checkbox"
                    checked={tpl.is_active}
                    onChange={(e) =>
                      setTemplates((prev) =>
                        prev.map((x) => (x.id === tpl.id ? { ...x, is_active: e.target.checked } : x)),
                      )
                    }
                  />
                  Active
                </label>
                <button type="button" className="btn-secondary btn-xs" onClick={() => void saveTemplate(tpl)}>
                  {t('common.actions.save', { defaultValue: 'Save' })}
                </button>
                <button type="button" className="btn-danger btn-xs" onClick={() => void removeTemplate(tpl.id)}>
                  {t('common.actions.delete', { defaultValue: 'Delete' })}
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>
    </SettingsSubpageHeader>
  )
}
