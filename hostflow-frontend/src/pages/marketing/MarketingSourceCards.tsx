/**
 * Human Source cards for Campaign Detail (Acquisition PR2).
 * Terminology: Lead Form (Meta) · Анкета HostFlow · Source · Connection.
 */
import { useState, type ReactNode } from 'react'
import type { CampaignFormLink, CampaignIntakeSourceLink } from '../../api/platformCampaigns'
import { formPublicUrl } from './marketingPresentation'
import { useI18n, type TranslateFn } from '../../i18n'

function publicationLabel(status: string | null | undefined, t: TranslateFn): string {
  switch (String(status || '').toLowerCase()) {
    case 'published':
      return t('app.marketing.source_card.published')
    case 'draft':
      return t('app.marketing.source_card.draft')
    case 'inactive':
      return t('app.marketing.source_card.inactive')
    default:
      return status || '—'
  }
}

function bindingLabel(status: string | null | undefined, t: TranslateFn): string {
  switch (String(status || '').toLowerCase()) {
    case 'bound':
      return t('app.marketing.source_card.bound')
    case 'bound_inactive_profile':
      return t('app.marketing.source_card.bound')
    case 'unbound':
      return t('app.marketing.source_card.no_public_link')
    default:
      return status || '—'
  }
}

function providerLabel(provider: string | null | undefined): string {
  const p = String(provider || '').toLowerCase()
  if (p === 'meta') return 'Meta'
  if (p === 'public_intake') return 'HostFlow'
  return provider || '—'
}

function formatRelativeOrDash(iso: string | null | undefined, locale: string, neverLabel: string): string {
  if (!iso) return neverLabel
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return neverLabel
  try {
    return new Intl.DateTimeFormat(locale, {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(d)
  } catch {
    return d.toISOString()
  }
}

function StatusPill({
  tone,
  children,
}: {
  tone: 'ok' | 'warn' | 'muted'
  children: ReactNode
}) {
  const cls =
    tone === 'ok'
      ? 'bg-emerald-50 text-emerald-800 ring-emerald-200'
      : tone === 'warn'
        ? 'bg-amber-50 text-amber-900 ring-amber-200'
        : 'bg-slate-100 text-slate-700 ring-slate-200'
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs ring-1 ring-inset ${cls}`}>
      {children}
    </span>
  )
}

function DetailsToggle({
  open,
  onToggle,
  children,
  testId,
}: {
  open: boolean
  onToggle: () => void
  children: ReactNode
  testId?: string
}) {
  const { t } = useI18n()
  return (
    <div className="mt-2 border-t border-slate-100 pt-2">
      <button
        type="button"
        className="text-xs font-medium text-brand-700 underline-offset-2 hover:underline"
        onClick={onToggle}
        data-testid={testId}
        aria-expanded={open}
      >
        {open ? t('app.marketing.source_card.hide_details') : t('app.marketing.source_card.details')}
      </button>
      {open ? <div className="mt-2 space-y-1 text-xs text-slate-500">{children}</div> : null}
    </div>
  )
}

export function HostFlowFormSourceCard({
  link,
  locale,
}: {
  link: CampaignFormLink
  locale: string
}) {
  const { t } = useI18n()
  const [open, setOpen] = useState(false)
  const publicUrl = formPublicUrl(link.public_slug)
  const pub = link.publication_status || (link.public_slug ? 'published' : 'draft')
  const active = link.is_active && (link.form_is_active ?? true)

  return (
    <li
      className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm"
      data-testid={`marketing-source-form-${link.id}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
            {t('app.marketing.source_card.hostflow_source')}
          </div>
          <div className="mt-1 font-semibold text-slate-900">{link.title || 'Без названия'}</div>
        </div>
        <div className="flex flex-wrap gap-1">
          <StatusPill tone={active ? 'ok' : 'muted'}>
            {active ? 'Active binding' : 'Inactive binding'}
          </StatusPill>
          <StatusPill tone={pub === 'published' ? 'ok' : pub === 'inactive' ? 'muted' : 'warn'}>
            {publicationLabel(pub, t)}
          </StatusPill>
          {link.is_public || link.public_slug ? (
            <StatusPill tone="ok">{t('app.marketing.source_card.public_form')}</StatusPill>
          ) : (
            <StatusPill tone="muted">{t('app.marketing.source_card.no_public_link')}</StatusPill>
          )}
        </div>
      </div>

      <dl className="mt-3 grid gap-1 text-xs text-slate-600 sm:grid-cols-2">
        <div>
          <dt className="text-slate-500">{t('app.marketing.source_card.last_submission')}</dt>
          <dd className="font-medium text-slate-800">
            {formatRelativeOrDash(link.last_submission_at, locale, t('app.marketing.source_card.never'))}
          </dd>
        </div>
        {publicUrl ? (
          <div>
            <dt className="text-slate-500">{t('app.marketing.source_card.public_link')}</dt>
            <dd>
              <a
                href={publicUrl}
                target="_blank"
                rel="noreferrer"
                className="break-all font-medium text-brand-700 underline"
              >
                {t('app.marketing.source_card.open_form')}
              </a>
            </dd>
          </div>
        ) : null}
      </dl>

      <DetailsToggle open={open} onToggle={() => setOpen((v) => !v)} testId={`marketing-form-details-${link.id}`}>
        <div>form_id: {link.form_id}</div>
        <div>binding role: {link.role}</div>
        {link.public_slug ? <div>public_slug: {link.public_slug}</div> : null}
      </DetailsToggle>
    </li>
  )
}

export function MetaLeadFormSourceCard({
  link,
  locale,
}: {
  link: CampaignIntakeSourceLink
  locale: string
}) {
  const { t } = useI18n()
  const [open, setOpen] = useState(false)
  const title =
    link.display_title ||
    link.lead_form_name ||
    link.name ||
    'Lead Form (Meta)'
  const pageLine = link.page_name || null
  const binding = link.binding_status || (link.is_active ? 'bound' : 'unbound')
  const active = link.is_active && (link.profile_is_active ?? true)

  return (
    <li
      className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm"
      data-testid={`marketing-source-intake-${link.id}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Lead Form (Meta) · Source
          </div>
          <div className="mt-1 font-semibold text-slate-900">{title}</div>
        </div>
        <div className="flex flex-wrap gap-1">
          <StatusPill tone={active ? 'ok' : 'muted'}>
            {active ? 'Active' : 'Inactive'}
          </StatusPill>
          <StatusPill tone={binding === 'bound' ? 'ok' : binding === 'unbound' ? 'warn' : 'muted'}>
            {bindingLabel(binding, t)}
          </StatusPill>
        </div>
      </div>

      <dl className="mt-3 grid gap-1 text-xs text-slate-600 sm:grid-cols-2">
        <div>
          <dt className="text-slate-500">Provider</dt>
          <dd className="font-medium text-slate-800">{providerLabel(link.provider)}</dd>
        </div>
        <div>
          <dt className="text-slate-500">{t('app.marketing.source_card.facebook_page')}</dt>
          <dd className="font-medium text-slate-800">
            {pageLine || (link.page_id ? 'ID скрыт в подробностях' : '—')}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500">Lead Form</dt>
          <dd className="font-medium text-slate-800">
            {link.lead_form_name || title}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500">{t('app.marketing.source_card.last_lead')}</dt>
          <dd className="font-medium text-slate-800">
            {formatRelativeOrDash(link.last_submission_at, locale, t('app.marketing.source_card.never'))}
          </dd>
        </div>
      </dl>

      <DetailsToggle
        open={open}
        onToggle={() => setOpen((v) => !v)}
        testId={`marketing-meta-details-${link.id}`}
      >
        <div>intake_source_profile_id: {link.intake_source_profile_id}</div>
        {link.meta_form_id ? <div>meta form_id: {link.meta_form_id}</div> : null}
        {link.page_id ? <div>page_id: {link.page_id}</div> : null}
        {link.code ? <div>code: {link.code}</div> : null}
        <div>binding role: {link.role}</div>
        <div>active bindings: {link.active_binding_count ?? 0}</div>
      </DetailsToggle>
    </li>
  )
}
