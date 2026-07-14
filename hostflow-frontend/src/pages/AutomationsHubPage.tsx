import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  IconBell,
  IconBolt,
  IconChecklist,
  IconClipboardList,
  IconCreditCard,
  IconFileText,
  IconHistory,
  IconLayoutGrid,
  IconRoute,
  IconSettings,
  IconShield,
} from '@tabler/icons-react'
import type { Icon as TablerIcon } from '@tabler/icons-react'
import { useI18n } from '../i18n'
import { usePermissions } from '../hooks/usePermissions'
import { useCommunicationsAccess } from '../hooks/useCommunicationsAccess'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { PageHeader } from '../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../components/layout'

type PolicyCard = {
  key: string
  to: string
  title: string
  description: string
  Icon: TablerIcon
}

export default function AutomationsHubPage() {
  const { t } = useI18n()
  const { can } = usePermissions()
  const { canUseCommunicationsFeature } = useCommunicationsAccess()
  const showLeadsDistribution = can('leads.view')
  const showMetaLeadPlaybook = can('admin.metaLeads')

  const policyCards = useMemo((): PolicyCard[] => {
    const out: PolicyCard[] = []
    if (can('settings.view')) {
      out.push({
        key: 'risk',
        to: CRM_APP_PATHS.settingsRiskIntel,
        title: t('app.automations.hub.policy_risk_title', { defaultValue: 'Risk intelligence' }),
        description: t('app.automations.hub.policy_risk_desc', {
          defaultValue: 'Hourly risk model, shadow cohorts, stage gate, digest email — team policy in Settings.',
        }),
        Icon: IconShield,
      })
      out.push({
        key: 'gates',
        to: CRM_APP_PATHS.settingsHiringPipelineGates,
        title: t('app.automations.hub.policy_gates_title', { defaultValue: 'Hiring pipeline gates' }),
        description: t('app.automations.hub.policy_gates_desc', {
          defaultValue: 'Stage requirements, documents, and forward guards before candidates advance.',
        }),
        Icon: IconChecklist,
      })
    }
    if (can('admin.ruleset')) {
      out.push({
        key: 'ruleset',
        to: CRM_APP_PATHS.settingsRuleset,
        title: t('app.automations.hub.policy_ruleset_title', { defaultValue: 'Ruleset versions' }),
        description: t('app.automations.hub.policy_ruleset_desc', {
          defaultValue: 'Compliance / document rulesets and published versions used across the tenant.',
        }),
        Icon: IconSettings,
      })
    }
    if (can('documents.manage')) {
      out.push({
        key: 'docs',
        to: CRM_APP_PATHS.settingsDocs,
        title: t('app.automations.hub.policy_docs_title', { defaultValue: 'Document types' }),
        description: t('app.automations.hub.policy_docs_desc', {
          defaultValue: 'Templates and document intelligence configuration (automation inputs for readiness).',
        }),
        Icon: IconFileText,
      })
    }
    if (can('admin.users') && canUseCommunicationsFeature('communicationsAdmin')) {
      out.push({
        key: 'comms_sla',
        to: CRM_APP_PATHS.settingsCommunicationsSla,
        title: t('app.automations.hub.policy_comms_sla_title', { defaultValue: 'Communications SLA' }),
        description: t('app.automations.hub.policy_comms_sla_desc', {
          defaultValue: 'Escalation and overdue policy for conversation threads (ops automation).',
        }),
        Icon: IconBell,
      })
    }
    if (can('settings.view')) {
      out.push({
        key: 'settings',
        to: CRM_APP_PATHS.settings,
        title: t('app.automations.hub.policy_settings_title', { defaultValue: 'All settings' }),
        description: t('app.automations.hub.policy_settings_desc', {
          defaultValue: 'Full settings index — integrations, email, users, billing, and more.',
        }),
        Icon: IconLayoutGrid,
      })
    }
    return out
  }, [can, canUseCommunicationsFeature, t])

  const opsCards = useMemo((): PolicyCard[] => {
    if (!can('services.view')) return []
    return [
      {
        key: 'orders',
        to: CRM_APP_PATHS.orders,
        title: t('app.automations.hub.ops_orders_title', { defaultValue: 'Service orders' }),
        description: t('app.automations.hub.ops_orders_desc', {
          defaultValue: 'Orders tab — next steps, blocking work, and invoice linkage.',
        }),
        Icon: IconClipboardList,
      },
      {
        key: 'invoices',
        to: CRM_APP_PATHS.invoices,
        title: t('app.automations.hub.ops_invoices_title', { defaultValue: 'Invoices' }),
        description: t('app.automations.hub.ops_invoices_desc', {
          defaultValue: 'Outstanding balance, aging queues, and correction workflows.',
        }),
        Icon: IconCreditCard,
      },
    ]
  }, [can, t])

  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader
          title={t('app.automations.hub.title', { defaultValue: 'Automations' })}
          subtitle={t('app.automations.hub.subtitle', {
            defaultValue: 'Rules, logs, and lead routing — one place to start; details open on their own screens.',
          })}
          kind="browse"
        />
      </PageShellHeader>

      <div className="flex min-h-0 flex-1 flex-col gap-6 overflow-y-auto px-4 pb-4 sm:px-6">
      <section className="max-w-4xl rounded-xl border border-brand-200/80 bg-brand-50/40 p-4 text-sm text-slate-800 shadow-sm">
        <h2 className="text-base font-semibold text-slate-900">
          {t('app.automations.hub.meta_leads_fit_title')}
        </h2>
        <p className="mt-2 leading-relaxed text-slate-700">{t('app.automations.hub.meta_leads_fit_intro')}</p>
        <ol className="mt-3 list-decimal space-y-1.5 pl-5 text-slate-700">
          <li>{t('app.automations.hub.meta_leads_fit_step_vacancy')}</li>
          <li>{t('app.automations.hub.meta_leads_fit_step_meta')}</li>
          <li>{t('app.automations.hub.meta_leads_fit_step_rules')}</li>
        </ol>
        <div className="mt-4 flex flex-wrap gap-2">
          {showMetaLeadPlaybook ? (
            <Link
              to={`${CRM_APP_PATHS.settingsIntegrationsMeta}?tab=settings`}
              className="btn-secondary inline-flex items-center rounded-lg px-3 py-1.5 text-xs font-medium"
            >
              {t('app.automations.hub.meta_leads_fit_link_meta')}
            </Link>
          ) : null}
          <Link
            to={CRM_APP_PATHS.automationRules}
            className="btn-secondary inline-flex items-center rounded-lg px-3 py-1.5 text-xs font-medium"
          >
            {t('app.automations.hub.meta_leads_fit_link_rules')}
          </Link>
          <Link
            to={CRM_APP_PATHS.vacancies}
            className="btn-secondary inline-flex items-center rounded-lg px-3 py-1.5 text-xs font-medium"
          >
            {t('app.automations.hub.meta_leads_fit_link_vacancies')}
          </Link>
        </div>
      </section>

      <div className="grid gap-4 md:grid-cols-2">
        <Link
          to={CRM_APP_PATHS.automationRules}
          className="group rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:border-brand-300 hover:shadow-md"
        >
          <div className="flex items-start gap-4">
            <span className="rounded-xl bg-brand-50 p-3 text-brand-700 ring-1 ring-brand-100">
              <IconBolt size={28} stroke={1.6} />
            </span>
            <div className="min-w-0 flex-1">
              <h2 className="text-lg font-semibold text-slate-900 group-hover:text-brand-800">
                {t('app.automations.hub.card_rules_title', { defaultValue: 'Automation rules' })}
              </h2>
              <p className="mt-1 text-sm leading-relaxed text-slate-600">
                {t('app.automations.hub.card_rules_desc', {
                  defaultValue:
                    'Triggers → actions (e.g. reminders on stage change, expiring documents, risk band). Minimal builder; advanced policy also lives in settings.',
                })}
              </p>
              <span className="mt-3 inline-block text-sm font-medium text-brand-600 group-hover:underline">
                {t('app.automations.hub.open', { defaultValue: 'Open' })} →
              </span>
            </div>
          </div>
        </Link>

        <Link
          to={CRM_APP_PATHS.automationLog}
          className="group rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:border-brand-300 hover:shadow-md"
        >
          <div className="flex items-start gap-4">
            <span className="rounded-xl bg-slate-50 p-3 text-slate-700 ring-1 ring-slate-200">
              <IconHistory size={28} stroke={1.6} />
            </span>
            <div className="min-w-0 flex-1">
              <h2 className="text-lg font-semibold text-slate-900 group-hover:text-brand-800">
                {t('app.automations.hub.card_log_title', { defaultValue: 'Automation log' })}
              </h2>
              <p className="mt-1 text-sm leading-relaxed text-slate-600">
                {t('app.automations.hub.card_log_desc', {
                  defaultValue: 'Audit trail of automation-fired actions. Filter by target, time range, and action prefix.',
                })}
              </p>
              <span className="mt-3 inline-block text-sm font-medium text-brand-600 group-hover:underline">
                {t('app.automations.hub.open', { defaultValue: 'Open' })} →
              </span>
            </div>
          </div>
        </Link>

        {showLeadsDistribution ? (
          <>
            <Link
              to={CRM_APP_PATHS.leadsDistribution}
              className="group rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:border-brand-300 hover:shadow-md"
            >
              <div className="flex items-start gap-4">
                <span className="rounded-xl bg-violet-50 p-3 text-violet-700 ring-1 ring-violet-100">
                  <IconRoute size={28} stroke={1.6} />
                </span>
                <div className="min-w-0 flex-1">
                  <h2 className="text-lg font-semibold text-slate-900 group-hover:text-brand-800">
                    {t('app.nav.items.leads_distribution', { defaultValue: 'Lead distribution' })}
                  </h2>
                  <p className="mt-1 text-sm leading-relaxed text-slate-600">
                    {t('app.automations.hub.card_leads_dist_desc', {
                      defaultValue: 'Team routing, capacity, and assignment — main distribution screen.',
                    })}
                  </p>
                  <span className="mt-3 inline-block text-sm font-medium text-brand-600 group-hover:underline">
                    {t('app.automations.hub.open', { defaultValue: 'Open' })} →
                  </span>
                </div>
              </div>
            </Link>
            <Link
              to={CRM_APP_PATHS.leadsDistributionRules}
              className="group rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:border-brand-300 hover:shadow-md"
            >
              <div className="flex items-start gap-4">
                <span className="rounded-xl bg-slate-50 p-3 text-slate-700 ring-1 ring-slate-200">
                  <IconRoute size={28} stroke={1.6} />
                </span>
                <div className="min-w-0 flex-1">
                  <h2 className="text-lg font-semibold text-slate-900 group-hover:text-brand-800">
                    {t('app.nav.items.leads_distribution_rules', { defaultValue: 'Distribution rules' })}
                  </h2>
                  <p className="mt-1 text-sm leading-relaxed text-slate-600">
                    {t('app.automations.hub.card_leads_rules_desc', {
                      defaultValue: 'Strategy, criteria order, and language routing.',
                    })}
                  </p>
                  <span className="mt-3 inline-block text-sm font-medium text-brand-600 group-hover:underline">
                    {t('app.automations.hub.open', { defaultValue: 'Open' })} →
                  </span>
                </div>
              </div>
            </Link>
          </>
        ) : null}
      </div>

      {opsCards.length > 0 ? (
        <section className="space-y-3">
          <h2 className="text-sm font-semibold text-slate-800">
            {t('app.automations.hub.ops_section', { defaultValue: 'Fulfillment & billing (execution)' })}
          </h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {opsCards.map((card) => (
              <Link
                key={card.key}
                to={card.to}
                className="group rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-brand-200 hover:bg-brand-50/30"
              >
                <div className="flex items-start gap-3">
                  <span className="rounded-lg bg-slate-50 p-2 text-slate-600 ring-1 ring-slate-100 group-hover:text-brand-700">
                    <card.Icon size={22} stroke={1.7} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <h3 className="text-sm font-semibold text-slate-900 group-hover:text-brand-800">{card.title}</h3>
                    <p className="mt-1 text-xs leading-relaxed text-slate-600">{card.description}</p>
                    <span className="mt-2 inline-block text-xs font-medium text-brand-600 group-hover:underline">
                      {t('app.automations.hub.open', { defaultValue: 'Open' })} →
                    </span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </section>
      ) : null}

      {policyCards.length > 0 ? (
        <section className="space-y-3">
          <h2 className="text-sm font-semibold text-slate-800">
            {t('app.automations.hub.policy_section', { defaultValue: 'Policy & enforcement (settings)' })}
          </h2>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {policyCards.map((card) => (
              <Link
                key={card.key}
                to={card.to}
                className="group rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-brand-200 hover:bg-brand-50/30"
              >
                <div className="flex items-start gap-3">
                  <span className="rounded-lg bg-slate-50 p-2 text-slate-600 ring-1 ring-slate-100 group-hover:text-brand-700">
                    <card.Icon size={22} stroke={1.7} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <h3 className="text-sm font-semibold text-slate-900 group-hover:text-brand-800">{card.title}</h3>
                    <p className="mt-1 text-xs leading-relaxed text-slate-600">{card.description}</p>
                    <span className="mt-2 inline-block text-xs font-medium text-brand-600 group-hover:underline">
                      {t('app.automations.hub.open', { defaultValue: 'Open' })} →
                    </span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </section>
      ) : null}
      </div>
    </PageShell>
  )
}
