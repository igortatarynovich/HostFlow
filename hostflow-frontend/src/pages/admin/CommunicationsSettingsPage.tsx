import { Link } from 'react-router-dom'
import { useI18n } from '../../i18n'

export default function CommunicationsSettingsPage() {
  const { t } = useI18n()

  const cards = [
    {
      title: t('admin.settings.cards.communications_messengers.label', { defaultValue: 'Messenger settings' }),
      description: t('admin.settings.cards.communications_messengers.description', { defaultValue: 'Telegram/WhatsApp channels, templates and command presets.' }),
      to: '/app/settings/communications/messengers',
      cta: t('admin.communications_settings.open_messengers', { defaultValue: 'Open messenger settings' }),
    },
    {
      title: t('admin.settings.cards.email.label', { defaultValue: 'Email settings' }),
      description: t('admin.settings.cards.email.description', { defaultValue: 'Mailbox providers, SMTP/IMAP and inbox delivery configuration.' }),
      to: '/app/settings/email',
      cta: t('admin.communications_settings.open_email', { defaultValue: 'Open email settings' }),
    },
    {
      title: t('admin.settings.cards.communications_queue.label', { defaultValue: 'Queue settings' }),
      description: t('admin.settings.cards.communications_queue.description', { defaultValue: 'Routing strategy and manager allocation queue controls.' }),
      to: '/app/settings/communications/queue',
      cta: t('admin.communications_settings.open_queue', { defaultValue: 'Open queue settings' }),
    },
    {
      title: t('admin.settings.cards.communications_sla.label', { defaultValue: 'SLA settings' }),
      description: t('admin.settings.cards.communications_sla.description', { defaultValue: 'Escalation policy for overdue communication threads.' }),
      to: '/app/settings/communications/sla',
      cta: t('admin.communications_settings.open_sla', { defaultValue: 'Open SLA settings' }),
    },
  ]

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">{t('app.nav.items.settings_communications', { defaultValue: 'Communications settings' })}</h1>
        <p className="text-sm text-slate-500">
          {t('admin.communications_settings.subtitle', { defaultValue: 'Settings are split by domain so email, messengers and queue are managed independently.' })}
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => (
          <section key={card.to} className="rounded-lg border border-slate-200 bg-white p-4">
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
    </div>
  )
}
