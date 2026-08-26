import { Link } from 'react-router-dom'
import {
  IconBuildingBank,
  IconCopy,
  IconDots,
  IconFileText,
  IconMail,
  IconMapPin,
  IconPencil,
  IconPhone,
  IconPlus,
  IconUsers,
  IconBriefcase,
  IconBuilding,
  IconClipboardList,
  IconWorld,
} from '@tabler/icons-react'
import type { OwnCompanyRecord } from '../../api/client'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'
import { useToast } from '../Toast'
import {
  companyInitials,
  formatLegalAddress,
  formatLocation,
  resolveBankAccounts,
  resolveBrandColors,
  resolveBrandDomain,
  resolveBusinessType,
  resolveContacts,
  resolveIndustry,
  resolveLogoUrl,
  resolveRegon,
  resolveVatEu,
  type OwnCompanyProfileTab,
  OWN_COMPANY_PROFILE_TABS,
} from './ownCompanyProfileUtils'

type Stats = {
  employees: number | null
  vacancies: number | null
  clients: number | null
  orders: number | null
}

type Props = {
  company: OwnCompanyRecord
  tab: OwnCompanyProfileTab
  onTabChange: (tab: OwnCompanyProfileTab) => void
  onEdit: () => void
  stats: Stats
  companiesCount: number
  onSelectCompany?: (id: string) => void
  companyOptions?: Array<{ id: string; name: string }>
}

function dash(value: string | null | undefined, fallback = '—') {
  const text = String(value ?? '').trim()
  return text || fallback
}

function formatDate(value: string | null | undefined, locale: string) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString(locale, { day: 'numeric', month: 'long', year: 'numeric' })
}

function contactInitials(name: string) {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (!parts.length) return '?'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return `${parts[0][0] || ''}${parts[1][0] || ''}`.toUpperCase()
}

export function OwnCompanyProfileView({
  company,
  tab,
  onTabChange,
  onEdit,
  stats,
  companiesCount,
  onSelectCompany,
  companyOptions = [],
}: Props) {
  const { t, locale } = useI18n()
  const { notify } = useToast()
  const dateLocale = locale === 'pl' ? 'pl-PL' : locale === 'ru' ? 'ru-RU' : 'en-GB'

  const displayName = company.name || company.legal_name || '—'
  const businessType = resolveBusinessType(company)
  const industry = resolveIndustry(company)
  const location = formatLocation(company)
  const logoUrl = resolveLogoUrl(company)
  const brandColors = resolveBrandColors(company)
  const brandDomain = resolveBrandDomain(company)
  const bankAccounts = resolveBankAccounts(company)
  const contacts = resolveContacts(company)
  const regon = resolveRegon(company)
  const vatEu = resolveVatEu(company)
  const legalAddress = formatLegalAddress(company)
  const statusLabel = company.is_archived
    ? t('app.my_company.profile.status.archived', { defaultValue: 'Archived' })
    : t('app.my_company.profile.status.active', { defaultValue: 'Active' })

  const businessTypeLabel = businessType
    ? t(`app.onboarding.company_type.${businessType}`, {
        defaultValue:
          businessType === 'agency'
            ? 'Recruitment agency'
            : businessType === 'employer'
              ? 'Employer'
              : businessType === 'services'
                ? 'Services'
                : businessType,
      })
    : t('app.my_company.profile.type_unknown', { defaultValue: 'Company' })

  const copyValue = async (value: string, label: string) => {
    if (!value) return
    try {
      await navigator.clipboard.writeText(value)
      notify({
        title: t('app.my_company.profile.copied', { defaultValue: 'Copied' }),
        description: label,
        variant: 'success',
      })
    } catch {
      notify({
        title: t('app.my_company.profile.copy_failed', { defaultValue: 'Could not copy' }),
        variant: 'error',
      })
    }
  }

  const editHref = `${CRM_APP_PATHS.myCompany}/${company.id}`

  const statCards = [
    {
      key: 'employees',
      label: t('app.my_company.profile.stats.employees', { defaultValue: 'Employees' }),
      value: stats.employees,
      href: CRM_APP_PATHS.hrEmployees,
      icon: IconUsers,
      go: t('app.my_company.profile.stats.go_employees', { defaultValue: 'Go to employees' }),
    },
    {
      key: 'vacancies',
      label: t('app.my_company.profile.stats.vacancies', { defaultValue: 'Vacancies' }),
      value: stats.vacancies,
      href: CRM_APP_PATHS.vacancies,
      icon: IconBriefcase,
      go: t('app.my_company.profile.stats.go_vacancies', { defaultValue: 'Go to vacancies' }),
    },
    {
      key: 'clients',
      label: t('app.my_company.profile.stats.clients', { defaultValue: 'Clients' }),
      value: stats.clients,
      href: CRM_APP_PATHS.agencyClients,
      icon: IconBuilding,
      go: t('app.my_company.profile.stats.go_clients', { defaultValue: 'Go to clients' }),
    },
    {
      key: 'orders',
      label: t('app.my_company.profile.stats.orders', { defaultValue: 'Orders' }),
      value: stats.orders,
      href: CRM_APP_PATHS.salesOrders,
      icon: IconClipboardList,
      go: t('app.my_company.profile.stats.go_orders', { defaultValue: 'Go to orders' }),
    },
  ] as const

  const historyItems = [
    company.updated_at
      ? {
          key: 'updated',
          title: t('app.my_company.profile.history.updated', { defaultValue: 'Profile updated' }),
          at: company.updated_at,
        }
      : null,
    company.created_at
      ? {
          key: 'created',
          title: t('app.my_company.profile.history.created', { defaultValue: 'Company created' }),
          at: company.created_at,
        }
      : null,
  ].filter(Boolean) as Array<{ key: string; title: string; at: string }>

  return (
    <div className="space-y-4">
      {companiesCount > 1 && companyOptions.length > 1 ? (
        <div className="app-surface flex flex-wrap items-center gap-2 px-4 py-3">
          <span className="text-sm text-slate-500">
            {t('app.my_company.profile.switch_label', { defaultValue: 'Company profile' })}
          </span>
          <select
            className="input max-w-xs"
            value={company.id}
            onChange={(e) => onSelectCompany?.(e.target.value)}
          >
            {companyOptions.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </div>
      ) : null}

      <section className="app-surface p-5 sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex min-w-0 items-start gap-4">
            <div className="relative h-16 w-16 shrink-0 overflow-hidden rounded-full bg-brand-700 text-white shadow-sm">
              {logoUrl ? (
                <img src={logoUrl} alt="" className="h-full w-full object-cover" />
              ) : (
                <div className="flex h-full w-full items-center justify-center text-lg font-semibold tracking-wide">
                  {companyInitials(displayName)}
                </div>
              )}
            </div>
            <div className="min-w-0 space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="truncate text-2xl font-semibold text-slate-900">{displayName}</h1>
                <span
                  className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                    company.is_archived
                      ? 'bg-slate-100 text-slate-600'
                      : 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-100'
                  }`}
                >
                  {statusLabel}
                </span>
              </div>
              <p className="text-sm text-slate-500">{businessTypeLabel}</p>
              <div className="flex flex-wrap gap-x-4 gap-y-2 text-sm text-slate-600">
                {location ? (
                  <span className="inline-flex items-center gap-1.5">
                    <IconMapPin size={16} stroke={1.75} className="text-slate-400" />
                    {location}
                  </span>
                ) : null}
                {company.email ? (
                  <a href={`mailto:${company.email}`} className="inline-flex items-center gap-1.5 text-slate-600 hover:text-brand-700">
                    <IconMail size={16} stroke={1.75} className="text-slate-400" />
                    {company.email}
                  </a>
                ) : null}
                {company.phone ? (
                  <a href={`tel:${company.phone}`} className="inline-flex items-center gap-1.5 text-slate-600 hover:text-brand-700">
                    <IconPhone size={16} stroke={1.75} className="text-slate-400" />
                    {company.phone}
                  </a>
                ) : null}
                {company.website ? (
                  <a
                    href={company.website.startsWith('http') ? company.website : `https://${company.website}`}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 text-slate-600 hover:text-brand-700"
                  >
                    <IconWorld size={16} stroke={1.75} className="text-slate-400" />
                    {company.website.replace(/^https?:\/\//, '')}
                  </a>
                ) : null}
              </div>
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            <button type="button" className="btn-primary btn-sm inline-flex items-center gap-1.5" onClick={onEdit}>
              <IconPencil size={16} stroke={1.75} />
              {t('common.actions.edit', { defaultValue: 'Edit' })}
            </button>
            <Link to={editHref} className="btn-secondary btn-sm inline-flex items-center justify-center px-2" aria-label="More">
              <IconDots size={18} stroke={1.75} />
            </Link>
          </div>
        </div>

        <div className="mt-5 flex flex-wrap gap-2 border-t border-slate-100 pt-4">
          {OWN_COMPANY_PROFILE_TABS.map((key) => (
            <button
              key={key}
              type="button"
              className={`rounded-lg px-3 py-2 text-sm font-medium transition ${
                tab === key
                  ? 'bg-slate-900 text-white'
                  : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
              }`}
              onClick={() => onTabChange(key)}
            >
              {t(`app.my_company.profile.tabs.${key}`, {
                defaultValue:
                  key === 'overview'
                    ? 'Overview'
                    : key === 'requisites'
                      ? 'Requisites'
                      : key === 'bank'
                        ? 'Bank accounts'
                        : key === 'documents'
                          ? 'Documents'
                          : key === 'contacts'
                            ? 'Contacts'
                            : key === 'related'
                              ? 'Related entities'
                              : 'History',
              })}
            </button>
          ))}
        </div>
      </section>

      {tab === 'overview' ? (
        <div className="grid gap-4 xl:grid-cols-2">
          <section className="app-surface space-y-3 p-5">
            <h2 className="text-base font-semibold text-slate-900">
              {t('app.my_company.profile.basic.title', { defaultValue: 'Basic information' })}
            </h2>
            <dl className="space-y-2 text-sm">
              <Row label={t('app.my_company.profile.basic.legal_name', { defaultValue: 'Legal name' })} value={dash(company.legal_name || company.name)} />
              <Row label={t('app.my_company.profile.basic.type', { defaultValue: 'Company type' })} value={businessTypeLabel} />
              <Row label={t('app.my_company.profile.basic.industry', { defaultValue: 'Industry' })} value={dash(industry)} />
              <Row label={t('app.my_company.profile.basic.created', { defaultValue: 'Created' })} value={formatDate(company.created_at, dateLocale)} />
              <Row label={t('app.my_company.profile.basic.status', { defaultValue: 'Status' })} value={statusLabel} />
            </dl>
          </section>

          <section className="app-surface space-y-3 p-5">
            <h2 className="text-base font-semibold text-slate-900">
              {t('app.my_company.profile.stats.title', { defaultValue: 'Quick stats' })}
            </h2>
            <div className="grid gap-3 sm:grid-cols-2">
              {statCards.map((card) => {
                const Icon = card.icon
                return (
                  <div key={card.key} className="rounded-xl border border-slate-100 bg-slate-50/70 p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{card.label}</p>
                        <p className="mt-1 text-2xl font-semibold text-slate-900">
                          {card.value == null ? '—' : card.value}
                        </p>
                      </div>
                      <span className="rounded-lg bg-white p-2 text-brand-700 shadow-sm">
                        <Icon size={18} stroke={1.75} />
                      </span>
                    </div>
                    <Link to={card.href} className="mt-2 inline-block text-sm font-medium text-brand-700 hover:text-brand-800">
                      {card.go} →
                    </Link>
                  </div>
                )
              })}
            </div>
          </section>

          <section className="app-surface space-y-3 p-5">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-base font-semibold text-slate-900">
                {t('app.my_company.profile.legal.title', { defaultValue: 'Legal data' })}
              </h2>
              <button type="button" className="btn-secondary btn-sm" onClick={onEdit}>
                {t('app.my_company.profile.legal.edit', { defaultValue: 'Edit details' })}
              </button>
            </div>
            <dl className="space-y-2 text-sm">
              <CopyRow label="NIP / Tax ID" value={company.tax_id || ''} onCopy={copyValue} />
              <CopyRow label="REGON" value={regon} onCopy={copyValue} />
              <CopyRow label="VAT (EU)" value={vatEu} onCopy={copyValue} />
              <CopyRow
                label={t('app.my_company.profile.legal.address', { defaultValue: 'Legal address' })}
                value={legalAddress}
                onCopy={copyValue}
              />
            </dl>
          </section>

          <section className="app-surface space-y-3 p-5">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-base font-semibold text-slate-900">
                {t('app.my_company.profile.bank.title', { defaultValue: 'Bank accounts' })}
              </h2>
              <Link to={`${editHref}?section=bank_accounts`} className="btn-secondary btn-sm inline-flex items-center gap-1">
                <IconPlus size={14} />
                {t('app.my_company.profile.bank.add', { defaultValue: 'Add account' })}
              </Link>
            </div>
            {bankAccounts.length ? (
              <ul className="divide-y divide-slate-100">
                {bankAccounts.slice(0, 3).map((account, index) => (
                  <li key={`${account.iban}-${index}`} className="flex items-start justify-between gap-3 py-3 first:pt-0 last:pb-0">
                    <div className="min-w-0">
                      <p className="font-medium text-slate-900">{account.bank_name || account.label || '—'}</p>
                      <p className="mt-0.5 truncate font-mono text-xs text-slate-500">{account.iban || '—'}</p>
                    </div>
                    {account.currency ? (
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                        {account.currency}
                      </span>
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-500">
                {t('app.my_company.profile.bank.empty', { defaultValue: 'No bank accounts yet.' })}
              </p>
            )}
            <button type="button" className="text-sm font-medium text-brand-700 hover:text-brand-800" onClick={() => onTabChange('bank')}>
              {t('app.my_company.profile.bank.view_all', { defaultValue: 'View all accounts' })} →
            </button>
          </section>

          <section className="app-surface space-y-3 p-5">
            <h2 className="text-base font-semibold text-slate-900">
              {t('app.my_company.profile.branding.title', { defaultValue: 'Branding' })}
            </h2>
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center overflow-hidden rounded-full bg-brand-700 text-sm font-semibold text-white">
                {logoUrl ? <img src={logoUrl} alt="" className="h-full w-full object-cover" /> : companyInitials(displayName)}
              </div>
              <div className="text-sm">
                <p className="font-medium text-slate-900">{displayName}</p>
                <p className="text-slate-500">{dash(brandDomain)}</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-3 text-sm">
              <ColorSwatch label={t('app.my_company.profile.branding.primary', { defaultValue: 'Primary' })} color={brandColors.primary} />
              <ColorSwatch label={t('app.my_company.profile.branding.secondary', { defaultValue: 'Secondary' })} color={brandColors.secondary} />
            </div>
            <Link to={`${editHref}?section=branding`} className="text-sm font-medium text-brand-700 hover:text-brand-800">
              {t('app.my_company.profile.branding.edit', { defaultValue: 'Edit branding' })} →
            </Link>
          </section>

          <section className="app-surface space-y-3 p-5">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-base font-semibold text-slate-900">
                {t('app.my_company.profile.contacts.title', { defaultValue: 'Company contacts' })}
              </h2>
              <Link to={`${editHref}?section=contacts`} className="btn-secondary btn-sm inline-flex items-center gap-1">
                <IconPlus size={14} />
                {t('app.my_company.profile.contacts.add', { defaultValue: 'Add contact' })}
              </Link>
            </div>
            {contacts.length ? (
              <ul className="space-y-3">
                {contacts.slice(0, 4).map((contact, index) => (
                  <li key={`${contact.email}-${index}`} className="flex items-start gap-3">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-semibold text-slate-600">
                      {contactInitials(contact.full_name || contact.email || '?')}
                    </div>
                    <div className="min-w-0 text-sm">
                      <p className="font-medium text-slate-900">{dash(contact.full_name)}</p>
                      <p className="text-slate-500">{dash(contact.role)}</p>
                      <p className="truncate text-slate-600">{[contact.email, contact.phone].filter(Boolean).join(' · ') || '—'}</p>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-500">
                {t('app.my_company.profile.contacts.empty', { defaultValue: 'No contacts yet.' })}
              </p>
            )}
          </section>

          <section className="app-surface space-y-3 p-5">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-base font-semibold text-slate-900">
                {t('app.my_company.profile.documents.title', { defaultValue: 'Company documents' })}
              </h2>
              <button type="button" className="btn-secondary btn-sm" onClick={() => onTabChange('documents')}>
                {t('app.my_company.profile.documents.add', { defaultValue: 'Add document' })}
              </button>
            </div>
            <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50/60 px-4 py-6 text-center">
              <IconFileText className="mx-auto text-slate-400" size={28} stroke={1.5} />
              <p className="mt-2 text-sm text-slate-500">
                {t('app.my_company.profile.documents.empty', {
                  defaultValue: 'Company documents will appear here when attached to this profile.',
                })}
              </p>
            </div>
          </section>

          <section className="app-surface space-y-3 p-5">
            <h2 className="text-base font-semibold text-slate-900">
              {t('app.my_company.profile.history.title', { defaultValue: 'Recent changes' })}
            </h2>
            {historyItems.length ? (
              <ul className="space-y-3">
                {historyItems.map((item) => (
                  <li key={item.key} className="flex items-start justify-between gap-3 text-sm">
                    <div>
                      <p className="font-medium text-slate-900">{item.title}</p>
                      <p className="text-slate-500">{formatDate(item.at, dateLocale)}</p>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-500">
                {t('app.my_company.profile.history.empty', { defaultValue: 'No recent changes.' })}
              </p>
            )}
          </section>
        </div>
      ) : null}

      {tab === 'requisites' ? (
        <section className="app-surface space-y-3 p-5">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-base font-semibold text-slate-900">
              {t('app.my_company.profile.tabs.requisites', { defaultValue: 'Requisites' })}
            </h2>
            <button type="button" className="btn-primary btn-sm" onClick={onEdit}>
              {t('app.my_company.profile.legal.edit', { defaultValue: 'Edit details' })}
            </button>
          </div>
          <dl className="space-y-2 text-sm">
            <Row label={t('app.my_company.profile.basic.legal_name', { defaultValue: 'Legal name' })} value={dash(company.legal_name || company.name)} />
            <CopyRow label="NIP / Tax ID" value={company.tax_id || ''} onCopy={copyValue} />
            <CopyRow label="REGON" value={regon} onCopy={copyValue} />
            <CopyRow label="VAT (EU)" value={vatEu} onCopy={copyValue} />
            <CopyRow
              label={t('app.my_company.profile.legal.address', { defaultValue: 'Legal address' })}
              value={legalAddress}
              onCopy={copyValue}
            />
            <Row label={t('app.my_company.profile.legal.country', { defaultValue: 'Country' })} value={dash(company.country || company.country_code)} />
          </dl>
        </section>
      ) : null}

      {tab === 'bank' ? (
        <section className="app-surface space-y-3 p-5">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-base font-semibold text-slate-900">
              {t('app.my_company.profile.bank.title', { defaultValue: 'Bank accounts' })}
            </h2>
            <Link to={`${editHref}?section=bank_accounts`} className="btn-primary btn-sm inline-flex items-center gap-1">
              <IconPlus size={14} />
              {t('app.my_company.profile.bank.add', { defaultValue: 'Add account' })}
            </Link>
          </div>
          {bankAccounts.length ? (
            <ul className="divide-y divide-slate-100">
              {bankAccounts.map((account, index) => (
                <li key={`${account.iban}-${index}`} className="flex items-start gap-3 py-3 first:pt-0">
                  <span className="mt-0.5 rounded-lg bg-slate-50 p-2 text-brand-700">
                    <IconBuildingBank size={18} stroke={1.75} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium text-slate-900">{account.bank_name || account.label || '—'}</p>
                      {account.is_primary ? (
                        <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700">
                          {t('app.my_company.profile.bank.primary', { defaultValue: 'Primary' })}
                        </span>
                      ) : null}
                      {account.currency ? (
                        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                          {account.currency}
                        </span>
                      ) : null}
                    </div>
                    <p className="mt-1 font-mono text-sm text-slate-600">{account.iban || '—'}</p>
                    {account.swift_bic ? <p className="text-xs text-slate-500">SWIFT/BIC: {account.swift_bic}</p> : null}
                  </div>
                  {account.iban ? (
                    <button
                      type="button"
                      className="btn-secondary btn-sm px-2"
                      onClick={() => void copyValue(account.iban, account.iban)}
                      aria-label="Copy IBAN"
                    >
                      <IconCopy size={14} />
                    </button>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">
              {t('app.my_company.profile.bank.empty', { defaultValue: 'No bank accounts yet.' })}
            </p>
          )}
        </section>
      ) : null}

      {tab === 'documents' ? (
        <section className="app-surface space-y-3 p-5">
          <h2 className="text-base font-semibold text-slate-900">
            {t('app.my_company.profile.documents.title', { defaultValue: 'Company documents' })}
          </h2>
          <p className="text-sm text-slate-500">
            {t('app.my_company.profile.documents.empty', {
              defaultValue: 'Company documents will appear here when attached to this profile.',
            })}
          </p>
        </section>
      ) : null}

      {tab === 'contacts' ? (
        <section className="app-surface space-y-3 p-5">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-base font-semibold text-slate-900">
              {t('app.my_company.profile.contacts.title', { defaultValue: 'Company contacts' })}
            </h2>
            <Link to={`${editHref}?section=contacts`} className="btn-primary btn-sm inline-flex items-center gap-1">
              <IconPlus size={14} />
              {t('app.my_company.profile.contacts.add', { defaultValue: 'Add contact' })}
            </Link>
          </div>
          {contacts.length ? (
            <ul className="divide-y divide-slate-100">
              {contacts.map((contact, index) => (
                <li key={`${contact.email}-${index}`} className="flex items-start gap-3 py-3 first:pt-0">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-slate-100 text-sm font-semibold text-slate-600">
                    {contactInitials(contact.full_name || contact.email || '?')}
                  </div>
                  <div className="min-w-0 text-sm">
                    <p className="font-medium text-slate-900">{dash(contact.full_name)}</p>
                    <p className="text-slate-500">{dash(contact.role)}</p>
                    <p className="text-slate-600">{dash(contact.email)}</p>
                    <p className="text-slate-600">{dash(contact.phone)}</p>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">
              {t('app.my_company.profile.contacts.empty', { defaultValue: 'No contacts yet.' })}
            </p>
          )}
        </section>
      ) : null}

      {tab === 'related' ? (
        <section className="app-surface space-y-3 p-5">
          <h2 className="text-base font-semibold text-slate-900">
            {t('app.my_company.profile.tabs.related', { defaultValue: 'Related entities' })}
          </h2>
          <p className="text-sm text-slate-500">
            {t('app.my_company.profile.related.hint', {
              defaultValue: 'Clients, vacancies and orders linked to this operating company.',
            })}
          </p>
          <div className="flex flex-wrap gap-2">
            <Link className="btn-secondary btn-sm" to={CRM_APP_PATHS.agencyClients}>
              {t('app.my_company.profile.stats.go_clients', { defaultValue: 'Go to clients' })}
            </Link>
            <Link className="btn-secondary btn-sm" to={CRM_APP_PATHS.vacancies}>
              {t('app.my_company.profile.stats.go_vacancies', { defaultValue: 'Go to vacancies' })}
            </Link>
            <Link className="btn-secondary btn-sm" to={CRM_APP_PATHS.salesOrders}>
              {t('app.my_company.profile.stats.go_orders', { defaultValue: 'Go to orders' })}
            </Link>
          </div>
        </section>
      ) : null}

      {tab === 'history' ? (
        <section className="app-surface space-y-3 p-5">
          <h2 className="text-base font-semibold text-slate-900">
            {t('app.my_company.profile.history.title', { defaultValue: 'Recent changes' })}
          </h2>
          {historyItems.length ? (
            <ul className="divide-y divide-slate-100">
              {historyItems.map((item) => (
                <li key={item.key} className="py-3 first:pt-0 text-sm">
                  <p className="font-medium text-slate-900">{item.title}</p>
                  <p className="text-slate-500">{formatDate(item.at, dateLocale)}</p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">
              {t('app.my_company.profile.history.empty', { defaultValue: 'No recent changes.' })}
            </p>
          )}
        </section>
      ) : null}
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-4">
      <dt className="text-slate-500">{label}</dt>
      <dd className="max-w-[65%] text-right font-medium text-slate-900">{value}</dd>
    </div>
  )
}

function CopyRow({
  label,
  value,
  onCopy,
}: {
  label: string
  value: string
  onCopy: (value: string, label: string) => void
}) {
  const display = dash(value)
  return (
    <div className="flex items-start justify-between gap-4">
      <dt className="text-slate-500">{label}</dt>
      <dd className="flex max-w-[70%] items-center justify-end gap-2 text-right font-medium text-slate-900">
        <span className="break-all">{display}</span>
        {value ? (
          <button
            type="button"
            className="shrink-0 rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
            onClick={() => onCopy(value, label)}
            aria-label={`Copy ${label}`}
          >
            <IconCopy size={14} />
          </button>
        ) : null}
      </dd>
    </div>
  )
}

function ColorSwatch({ label, color }: { label: string; color: string }) {
  const value = color || '—'
  return (
    <div className="inline-flex items-center gap-2 rounded-lg border border-slate-100 bg-slate-50 px-2.5 py-1.5">
      <span
        className="h-4 w-4 rounded-full border border-slate-200"
        style={{ backgroundColor: color || '#e2e8f0' }}
      />
      <span className="text-slate-500">{label}</span>
      <span className="font-mono text-xs text-slate-700">{value}</span>
    </div>
  )
}
