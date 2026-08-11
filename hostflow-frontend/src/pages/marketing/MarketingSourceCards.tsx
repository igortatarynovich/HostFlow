/**
 * Human Source cards for Campaign Detail (Acquisition PR2).
 * Terminology: Lead Form (Meta) · HostFlow form · Source · Connection.
 */
import { useState, type ReactNode } from 'react'
import type { TranslateFn } from '../../i18n'
import type { CampaignFormLink, CampaignIntakeSourceLink } from '../../api/platformCampaigns'
import { formPublicUrl } from './marketingPresentation'

function publicationLabel(status: string | null | undefined, t: TranslateFn): string {
  switch (String(status || '').toLowerCase()) {
    case 'published':
      return t('app.marketing.cards.publication.published', { defaultValue: 'Published' })
    case 'draft':
      return t('app.marketing.cards.publication.draft', { defaultValue: 'Draft' })
    case 'inactive':
      return t('app.marketing.cards.publication.inactive', { defaultValue: 'Inactive' })
    default:
      return status || '—'
  }
}

function bindingLabel(status: string | null | undefined, t: TranslateFn): string {
  switch (String(status || '').toLowerCase()) {
    case 'bound':
      return t('app.marketing.cards.binding.bound', { defaultValue: 'Bound' })
    case 'bound_inactive_profile':
      return t('app.marketing.cards.binding.bound_inactive', {
        defaultValue: 'Bound · profile off',
      })
    case 'unbound':
      return t('app.marketing.cards.binding.unbound', { defaultValue: 'No binding' })
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

function formatRelativeOrDash(iso: string | null | undefined, locale: string, t: TranslateFn): string {
  if (!iso) return t('app.marketing.cards.never', { defaultValue: 'never' })
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return t('app.marketing.cards.never', { defaultValue: 'never' })
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
  t,
}: {
  open: boolean
  onToggle: () => void
  children: ReactNode
  testId?: string
  t: TranslateFn
}) {
  return (
    <div className="mt-2 border-t border-slate-100 pt-2">
      <button
        type="button"
        className="text-xs font-medium text-brand-700 underline-offset-2 hover:underline"
        onClick={onToggle}
        data-testid={testId}
        aria-expanded={open}
      >
        {open
          ? t('app.marketing.cards.details_hide', { defaultValue: 'Hide details' })
          : t('app.marketing.cards.details_show', { defaultValue: 'Details' })}
      </button>
      {open ? <div className="mt-2 space-y-1 text-xs text-slate-500">{children}</div> : null}
    </div>
  )
}

export function HostFlowFormSourceCard({
  link,
  locale,
  t,
}: {
  link: CampaignFormLink
  locale: string
  t: TranslateFn
}) {
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
            {t('app.marketing.cards.hostflow_badge', {
              defaultValue: 'HostFlow form · Source',
            })}
          </div>
          <div className="mt-1 font-semibold text-slate-900">
            {link.title || t('app.marketing.cards.untitled', { defaultValue: 'Untitled' })}
          </div>
        </div>
        <div className="flex flex-wrap gap-1">
          <StatusPill tone={active ? 'ok' : 'muted'}>
            {active ? 'Active binding' : 'Inactive binding'}
          </StatusPill>
          <StatusPill tone={pub === 'published' ? 'ok' : pub === 'inactive' ? 'muted' : 'warn'}>
            {publicationLabel(pub, t)}
          </StatusPill>
          {link.is_public || link.public_slug ? (
            <StatusPill tone="ok">
              {t('app.marketing.cards.public_form', { defaultValue: 'Public form' })}
            </StatusPill>
          ) : (
            <StatusPill tone="muted">
              {t('app.marketing.cards.no_public_link', { defaultValue: 'No public link' })}
            </StatusPill>
          )}
        </div>
      </div>

      <dl className="mt-3 grid gap-1 text-xs text-slate-600 sm:grid-cols-2">
        <div>
          <dt className="text-slate-500">
            {t('app.marketing.cards.last_submission', { defaultValue: 'Last application' })}
          </dt>
          <dd className="font-medium text-slate-800">
            {formatRelativeOrDash(link.last_submission_at, locale, t)}
          </dd>
        </div>
        {publicUrl ? (
          <div>
            <dt className="text-slate-500">
              {t('app.marketing.cards.public_link', { defaultValue: 'Public link' })}
            </dt>
            <dd>
              <a
                href={publicUrl}
                target="_blank"
                rel="noreferrer"
                className="break-all font-medium text-brand-700 underline"
              >
                {t('app.marketing.cards.open_form', { defaultValue: 'Open form' })}
              </a>
            </dd>
          </div>
        ) : null}
      </dl>

      <DetailsToggle
        open={open}
        onToggle={() => setOpen((v) => !v)}
        testId={`marketing-form-details-${link.id}`}
        t={t}
      >
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
  t,
}: {
  link: CampaignIntakeSourceLink
  locale: string
  t: TranslateFn
}) {
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
          <dt className="text-slate-500">
            {t('app.marketing.cards.facebook_page', { defaultValue: 'Facebook page' })}
          </dt>
          <dd className="font-medium text-slate-800">
            {pageLine ||
              (link.page_id
                ? t('app.marketing.cards.page_id_hidden', {
                    defaultValue: 'ID hidden in details',
                  })
                : '—')}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500">Lead Form</dt>
          <dd className="font-medium text-slate-800">
            {link.lead_form_name || title}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500">
            {t('app.marketing.cards.last_lead', { defaultValue: 'Last lead' })}
          </dt>
          <dd className="font-medium text-slate-800">
            {formatRelativeOrDash(link.last_submission_at, locale, t)}
          </dd>
        </div>
      </dl>

      <DetailsToggle
        open={open}
        onToggle={() => setOpen((v) => !v)}
        testId={`marketing-meta-details-${link.id}`}
        t={t}
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
