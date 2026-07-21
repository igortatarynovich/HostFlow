import { Link } from 'react-router-dom'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'

type SimpleCard = {
  key: string
  title: string
  description: string
  to: string
  cta: string
}

export default function CommunicationsSettingsPage() {
  const { t } = useI18n()
  const P = CRM_APP_PATHS

  const simpleCards: SimpleCard[] = [
    {
      key: 'email',
      title: t('admin.settings.cards.email.label'),
      description: t('admin.settings.cards.email.description'),
      to: P.settingsEmail,
      cta: t('admin.communications_settings.open_email'),
    },
    {
      key: 'queue',
      title: t('admin.settings.cards.communications_queue.label'),
      description: t('admin.settings.cards.communications_queue.description'),
      to: P.settingsCommunicationsQueue,
      cta: t('admin.communications_settings.open_queue'),
    },
    {
      key: 'sla',
      title: t('admin.settings.cards.communications_sla.label'),
      description: t('admin.settings.cards.communications_sla.description'),
      to: P.settingsCommunicationsSla,
      cta: t('admin.communications_settings.open_sla'),
    },
    {
      key: 'templates',
      title: t('admin.settings.cards.communications_templates.label'),
      description: t('admin.settings.cards.communications_templates.description'),
      to: P.settingsCommunicationsTemplates,
      cta: t('admin.communications_settings.open_templates', {
        defaultValue: 'Open templates',
      }),
    },
    {
      key: 'automation',
      title: t('admin.settings.cards.communications_automation.label'),
      description: t('admin.settings.cards.communications_automation.description'),
      to: P.settingsCommunicationsAutomation,
      cta: t('admin.communications_settings.open_automation', {
        defaultValue: 'Open automation',
      }),
    },
  ]

  return (
    <SettingsSubpageHeader
      backHref={P.settings}
      backLabel={t('admin.communications_settings.back_all_settings')}
      kicker={t('admin.communications_settings.header_kicker')}
      title={t('admin.communications_settings.page_title')}
      subtitle={t('admin.communications_settings.subtitle')}
      actions={
        <Link to={P.settingsIntegrations} className="btn-secondary">
          {t('admin.communications_settings.open_integrations_hub')}
        </Link>
      }
    >
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <section className="rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="text-base font-semibold text-slate-900">{t('admin.settings.cards.communications_messengers.label')}</h2>
          <p className="mt-2 text-sm text-slate-600">{t('admin.communications_settings.card_messengers_desc')}</p>
          <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:flex-wrap">
            <Link to={P.settingsIntegrations} className="btn-primary btn-sm text-center sm:inline-flex">
              {t('admin.communications_settings.messengers_hub_cta')}
            </Link>
            <Link to={P.settingsCommunicationsMessengers} className="btn-secondary btn-sm text-center sm:inline-flex">
              {t('admin.communications_settings.messengers_templates_cta')}
            </Link>
          </div>
        </section>
        {simpleCards.map((card) => (
          <section key={card.key} className="rounded-lg border border-slate-200 bg-white p-4">
            <h2 className="text-base font-semibold text-slate-900">{card.title}</h2>
            <p className="mt-2 text-sm text-slate-600">{card.description}</p>
            <div className="mt-4">
              <Link to={card.to} className="btn-secondary">
                {card.cta}
              </Link>
            </div>
          </section>
        ))}
      </div>
    </SettingsSubpageHeader>
  )
}
