import type { LeadMessageTemplate } from '../../../api/types'
import { useI18n } from '../../../i18n'
import LeadTemplateSelectField from './LeadTemplateSelectField'

type Bindings = {
  lead_rodo_message_template_id?: string | null
  application_received_template_id?: string | null
  rejection_notice_template_id?: string | null
  moving_forward_template_id?: string | null
  lead_communication_enabled?: boolean
  send_application_received?: boolean
  send_rejection_notice?: boolean
  send_moving_forward_notice?: boolean
}

type Props = {
  templates: LeadMessageTemplate[]
  value: Bindings
  onChange: (next: Bindings) => void
  includeRodoTemplate?: boolean
}

export default function LeadOperationalEmailBindingsCard({
  templates,
  value,
  onChange,
  includeRodoTemplate = true,
}: Props) {
  const { t } = useI18n()
  const commEnabled = value.lead_communication_enabled ?? false
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="text-sm font-semibold text-slate-900">
        {t('admin.meta_leads.settings.lead_communication_title', { defaultValue: 'Lead operational emails' })}
      </h3>
      <p className="mt-1 text-xs text-slate-600">
        {t('admin.meta_leads.settings.lead_communication_hint', {
          defaultValue: 'Separate from RODO / art. 14. Candidate-facing status messages only.',
        })}
      </p>
      <div className="mt-2 grid gap-2 md:grid-cols-2">
        {includeRodoTemplate ? (
          <LeadTemplateSelectField
            label={t('admin.meta_leads.settings.lead_rodo_message_template_label', { defaultValue: 'RODO email template' })}
            value={value.lead_rodo_message_template_id ?? null}
            templates={templates}
            noneLabel={t('admin.meta_leads.settings.template_none', { defaultValue: 'Default built-in text' })}
            onChange={(templateId) => onChange({ ...value, lead_rodo_message_template_id: templateId })}
          />
        ) : (
          <div />
        )}
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={commEnabled}
            onChange={(e) => onChange({ ...value, lead_communication_enabled: e.target.checked })}
          />
          {t('admin.meta_leads.settings.lead_communication_enabled', { defaultValue: 'Enable lead operational emails' })}
        </label>
        <label className={`flex items-center gap-2 text-sm ${commEnabled ? 'text-slate-700' : 'text-slate-500'}`}>
          <input
            type="checkbox"
            disabled={!commEnabled}
            checked={commEnabled ? (value.send_application_received ?? false) : false}
            onChange={(e) => onChange({ ...value, send_application_received: e.target.checked })}
          />
          {t('admin.meta_leads.settings.send_application_received', { defaultValue: 'Application received (on new lead ingest)' })}
        </label>
        <label className={`flex items-center gap-2 text-sm ${commEnabled ? 'text-slate-700' : 'text-slate-500'}`}>
          <input
            type="checkbox"
            disabled={!commEnabled}
            checked={commEnabled ? (value.send_rejection_notice ?? false) : false}
            onChange={(e) => onChange({ ...value, send_rejection_notice: e.target.checked })}
          />
          {t('admin.meta_leads.settings.send_rejection_notice', { defaultValue: 'Rejection notice (on intake reject)' })}
        </label>
        <label className={`flex items-center gap-2 text-sm md:col-span-2 ${commEnabled ? 'text-slate-700' : 'text-slate-500'}`}>
          <input
            type="checkbox"
            disabled={!commEnabled}
            checked={commEnabled ? (value.send_moving_forward_notice ?? false) : false}
            onChange={(e) => onChange({ ...value, send_moving_forward_notice: e.target.checked })}
          />
          {t('admin.meta_leads.settings.send_moving_forward_notice', {
            defaultValue: 'Moving forward (on Lead → Candidate conversion)',
          })}
        </label>
        <LeadTemplateSelectField
          label={t('admin.meta_leads.settings.send_application_received', { defaultValue: 'Application received (on new lead ingest)' })}
          value={value.application_received_template_id ?? null}
          templates={templates}
          disabled={!commEnabled}
          noneLabel={t('admin.meta_leads.settings.template_none', { defaultValue: 'Default built-in text' })}
          onChange={(templateId) => onChange({ ...value, application_received_template_id: templateId })}
        />
        <LeadTemplateSelectField
          label={t('admin.meta_leads.settings.send_rejection_notice', { defaultValue: 'Rejection notice (on intake reject)' })}
          value={value.rejection_notice_template_id ?? null}
          templates={templates}
          disabled={!commEnabled}
          noneLabel={t('admin.meta_leads.settings.template_none', { defaultValue: 'Default built-in text' })}
          onChange={(templateId) => onChange({ ...value, rejection_notice_template_id: templateId })}
        />
        <div className="md:col-span-2">
          <LeadTemplateSelectField
            label={t('admin.meta_leads.settings.send_moving_forward_notice', {
              defaultValue: 'Moving forward (on Lead → Candidate conversion)',
            })}
            value={value.moving_forward_template_id ?? null}
            templates={templates}
            disabled={!commEnabled}
            noneLabel={t('admin.meta_leads.settings.template_none', { defaultValue: 'Default built-in text' })}
            onChange={(templateId) => onChange({ ...value, moving_forward_template_id: templateId })}
          />
        </div>
      </div>
    </section>
  )
}
