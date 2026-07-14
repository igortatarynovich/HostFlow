import { useCallback, useEffect, useMemo, useState, type Dispatch, type SetStateAction } from 'react'
import clsx from 'clsx'
import { Link } from 'react-router-dom'
import {
  createCommunicationAccount,
  deleteTelegramAccountWebhook,
  setTelegramAccountWebhook,
  listCommunicationAccounts,
  patchCommunicationAccount,
  testCommunicationAccountConnection,
  type CommunicationChannelAccount,
  type CommunicationCommandActionType,
  type CommunicationCommandAudit,
  type CommunicationCommandTemplate,
  type CommunicationMessageTemplate,
  getCommunicationsSettings,
  listCommunicationCommandAudit,
  patchCommunicationsSettings,
} from '../../api/communications'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import type { FriendlyErrorInfo } from '../../utils/friendlyError'
import { friendlyErrorBannerSecondary, getFriendlyErrorInfo } from '../../utils/friendlyError'
import { useAuth } from '../../store/auth'
import { usePlanLimitModal } from '../../contexts/PlanLimitModalContext'
import { MESSENGER_CHANNELS, type MessengerChannel } from './communicationsMessengerChannels'

const CHANNELS = MESSENGER_CHANNELS

type ChannelMeta = {
  titleKey: string
  titleDefault: string
  subtitleKey: string
  subtitleDefault: string
  connectLabelKey: string
  connectLabelDefault: string
}

const CHANNEL_META: Record<MessengerChannel, ChannelMeta> = {
  telegram: {
    titleKey: 'admin.communications_messengers.channels.telegram.title',
    titleDefault: 'Telegram',
    subtitleKey: 'admin.communications_messengers.channels.telegram.subtitle',
    subtitleDefault: 'Bot token and webhook',
    connectLabelKey: 'admin.communications_messengers.channels.telegram.connect',
    connectLabelDefault: 'Connect Telegram',
  },
  whatsapp: {
    titleKey: 'admin.communications_messengers.channels.whatsapp.title',
    titleDefault: 'WhatsApp',
    subtitleKey: 'admin.communications_messengers.channels.whatsapp.subtitle',
    subtitleDefault: 'Meta Cloud API (phone number id + token)',
    connectLabelKey: 'admin.communications_messengers.channels.whatsapp.connect',
    connectLabelDefault: 'Connect WhatsApp',
  },
  viber: {
    titleKey: 'admin.communications_messengers.channels.viber.title',
    titleDefault: 'Viber',
    subtitleKey: 'admin.communications_messengers.channels.viber.subtitle',
    subtitleDefault: 'Bot token',
    connectLabelKey: 'admin.communications_messengers.channels.viber.connect',
    connectLabelDefault: 'Connect Viber',
  },
  messenger: {
    titleKey: 'admin.communications_messengers.channels.messenger.title',
    titleDefault: 'Facebook Messenger',
    subtitleKey: 'admin.communications_messengers.channels.messenger.subtitle',
    subtitleDefault: 'Page token integration',
    connectLabelKey: 'admin.communications_messengers.channels.messenger.connect',
    connectLabelDefault: 'Connect Messenger',
  },
  instagram: {
    titleKey: 'admin.communications_messengers.channels.instagram.title',
    titleDefault: 'Instagram',
    subtitleKey: 'admin.communications_messengers.channels.instagram.subtitle',
    subtitleDefault: 'Instagram Graph API',
    connectLabelKey: 'admin.communications_messengers.channels.instagram.connect',
    connectLabelDefault: 'Connect Instagram',
  },
}

const COMMAND_ACTION_OPTIONS: Array<{ value: CommunicationCommandActionType; label: string }> = [
  { value: 'mark_read', label: 'Mark read' },
  { value: 'archive', label: 'Archive' },
  { value: 'unarchive', label: 'Unarchive' },
  { value: 'delete', label: 'Delete' },
  { value: 'restore', label: 'Restore' },
  { value: 'priority_high', label: 'Priority high' },
  { value: 'priority_normal', label: 'Priority normal' },
  { value: 'tag_add', label: 'Add tag' },
  { value: 'tag_remove', label: 'Remove tag' },
  { value: 'move_folder', label: 'Move to folder' },
]

const DEFAULT_COMMAND_PRESETS: CommunicationCommandTemplate[] = [
  {
    id: 'cmd_archive_done',
    label: 'Archive completed',
    target: 'both',
    enabled: true,
    actions: [{ type: 'mark_read' }, { type: 'archive' }],
  },
  {
    id: 'cmd_escalate_high',
    label: 'Escalate priority',
    target: 'both',
    enabled: true,
    actions: [{ type: 'priority_high' }, { type: 'tag_add', value: 'escalation' }],
  },
  {
    id: 'cmd_handoff_ready',
    label: 'Ready for handoff',
    target: 'both',
    enabled: true,
    actions: [{ type: 'tag_add', value: 'handoff_ready' }, { type: 'mark_read' }],
  },
]

function commandActionNeedsValue(type: CommunicationCommandActionType): boolean {
  return type === 'tag_add' || type === 'tag_remove' || type === 'move_folder'
}

function connectionStatusOf(account: CommunicationChannelAccount): string {
  const raw = String(account.settings_json?.connection?.status || '').toLowerCase()
  if (!raw) return account.is_active ? 'not_tested' : 'disabled'
  return raw
}

function statusBadgeClass(status: string): string {
  if (status === 'ok' || status === 'connected') return 'border-emerald-200 bg-emerald-50 text-emerald-700'
  if (status === 'error' || status === 'failed') return 'border-rose-200 bg-rose-50 text-rose-700'
  if (status === 'disabled') return 'border-slate-200 bg-slate-100 text-slate-600'
  return 'border-amber-200 bg-amber-50 text-amber-700'
}

type HubIntegrationStatus = 'needs_account' | 'disabled' | 'pending' | 'error' | 'live'

type MessengerHubWizardPanelProps = {
  channel: MessengerChannel
  t: (key: any, opts?: any) => string
  hubIntegrationStatus: HubIntegrationStatus
  wizardStepHighlight: number
  hubStatusHeadline: string
  hubCanSubmitCredentials: boolean
  primaryAccount: CommunicationChannelAccount | null
  selectedAccounts: CommunicationChannelAccount[]
  telegramForm: { accountLabel: string; botToken: string; externalRef: string }
  setTelegramForm: Dispatch<SetStateAction<{ accountLabel: string; botToken: string; externalRef: string }>>
  whatsappForm: { accountLabel: string; phoneNumberId: string; accessToken: string; businessAccountId: string; externalRef: string }
  setWhatsappForm: Dispatch<
    SetStateAction<{ accountLabel: string; phoneNumberId: string; accessToken: string; businessAccountId: string; externalRef: string }>
  >
  viberForm: { accountLabel: string; botToken: string; externalRef: string }
  setViberForm: Dispatch<SetStateAction<{ accountLabel: string; botToken: string; externalRef: string }>>
  messengerForm: { accountLabel: string; pageId: string; accessToken: string; appSecret: string; externalRef: string }
  setMessengerForm: Dispatch<
    SetStateAction<{ accountLabel: string; pageId: string; accessToken: string; appSecret: string; externalRef: string }>
  >
  instagramForm: { accountLabel: string; accountId: string; accessToken: string; externalRef: string }
  setInstagramForm: Dispatch<SetStateAction<{ accountLabel: string; accountId: string; accessToken: string; externalRef: string }>>
  connectionBusyKey: string | null
  runConnectionAction: (key: string, action: () => Promise<void>, successText: string) => void
  handleHubConnect: () => Promise<void>
  enableMessengerIntegration: () => Promise<void>
  disableMessengerIntegration: () => Promise<void>
  copyText: (value: string, successText: string) => Promise<void>
  runAccountTest: (account: CommunicationChannelAccount) => Promise<void>
  runTelegramWebhookSet: (account: CommunicationChannelAccount) => Promise<void>
  runTelegramWebhookDelete: (account: CommunicationChannelAccount) => Promise<void>
  showMetaChecklist: boolean
}

function MessengerHubWizardPanel({
  channel,
  t,
  hubIntegrationStatus,
  wizardStepHighlight,
  hubStatusHeadline,
  hubCanSubmitCredentials,
  primaryAccount,
  selectedAccounts,
  telegramForm,
  setTelegramForm,
  whatsappForm,
  setWhatsappForm,
  viberForm,
  setViberForm,
  messengerForm,
  setMessengerForm,
  instagramForm,
  setInstagramForm,
  connectionBusyKey,
  runConnectionAction,
  handleHubConnect,
  enableMessengerIntegration,
  disableMessengerIntegration,
  copyText,
  runAccountTest,
  runTelegramWebhookSet,
  runTelegramWebhookDelete,
  showMetaChecklist,
}: MessengerHubWizardPanelProps) {
  const meta = CHANNEL_META[channel]
  const stepKeys = ['step_credentials', 'step_verify', 'step_active'] as const
  const pa = primaryAccount
  const providerResult = pa?.settings_json?.connection?.provider_result || {}
  const webhookUrl = String(providerResult?.webhook_url || '').trim()
  const verifyToken =
    String(providerResult?.webhook_verify_token || '').trim() ||
    String(pa?.settings_json?.whatsapp?.webhook_verify_token || '').trim() ||
    String(pa?.settings_json?.messenger?.webhook_verify_token || '').trim() ||
    String(pa?.settings_json?.instagram?.webhook_verify_token || '').trim()
  const lastError = String(pa?.settings_json?.connection?.last_error || '').trim()
  const techStatus = pa ? connectionStatusOf(pa) : 'none'
  const testKey = pa ? `hub-test-${pa.id}` : ''

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-4 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
        <div className="min-w-0">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('admin.communications_messengers.integration_wizard.connection_status')}
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            {pa ? (
              <span className={clsx('badge', statusBadgeClass(techStatus))}>
                {t(`admin.communications_messengers.integration_wizard.tech_status.${techStatus}` as any, { defaultValue: techStatus })}
              </span>
            ) : (
              <span className="badge border-slate-200 bg-slate-100 text-slate-600">
                {t('admin.communications_messengers.integration_wizard.tech_status.none')}
              </span>
            )}
            <span className="text-sm text-slate-700">{hubStatusHeadline}</span>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {hubIntegrationStatus === 'disabled' && pa ? (
            <button
              type="button"
              className="btn-primary"
              disabled={connectionBusyKey !== null}
              onClick={() =>
                void runConnectionAction(
                  'hub-enable',
                  enableMessengerIntegration,
                  t('admin.communications_messengers.integration_wizard.notices.enabled', { defaultValue: 'Integration enabled' }),
                )
              }
            >
              {t('admin.communications_messengers.integration_wizard.connect')}
            </button>
          ) : null}
          {hubIntegrationStatus === 'live' || hubIntegrationStatus === 'pending' || hubIntegrationStatus === 'error' ? (
            <button
              type="button"
              className="btn-secondary border-rose-200 text-rose-800 hover:bg-rose-50"
              disabled={connectionBusyKey !== null}
              onClick={() =>
                void runConnectionAction(
                  'hub-disconnect',
                  disableMessengerIntegration,
                  t('admin.communications_messengers.integration_wizard.notices.disconnected', { defaultValue: 'Integration disconnected' }),
                )
              }
            >
              {t('admin.communications_messengers.integration_wizard.disconnect')}
            </button>
          ) : null}
        </div>
      </div>

      <ol className="mt-6 grid gap-2 sm:grid-cols-3">
        {stepKeys.map((sk, idx) => {
          const n = idx + 1
          return (
            <li
              key={sk}
              className={clsx(
                'rounded-lg border px-3 py-2 text-center text-sm font-medium',
                wizardStepHighlight === n ? 'border-brand-500 bg-brand-50 text-brand-900' : 'border-slate-200 text-slate-500',
              )}
            >
              <span className="mr-1 font-normal text-slate-400">{n}.</span>
              {t(`admin.communications_messengers.integration_wizard.${sk}`)}
            </li>
          )
        })}
      </ol>

      <div className="mt-6 space-y-4 rounded-lg border border-slate-200 p-4">
        <h2 className="text-sm font-semibold text-slate-900">
          {t('admin.communications_messengers.integration_wizard.step_credentials_heading')}
        </h2>
        <p className="text-xs text-slate-600">
          {t(meta.subtitleKey as any, { defaultValue: meta.subtitleDefault })}
        </p>
        {selectedAccounts.length === 0 ? (
          <>
            {channel === 'telegram' && (
              <div className="grid max-w-3xl gap-3 sm:grid-cols-2">
                <input
                  value={telegramForm.accountLabel}
                  onChange={(e) => setTelegramForm((p) => ({ ...p, accountLabel: e.target.value }))}
                  className="input"
                  placeholder={t('admin.communications_messengers.fields.account_label', { defaultValue: 'Account label' })}
                />
                <input
                  type="password"
                  value={telegramForm.botToken}
                  onChange={(e) => setTelegramForm((p) => ({ ...p, botToken: e.target.value }))}
                  className="input"
                  placeholder={t('admin.communications_messengers.fields.bot_token', { defaultValue: 'Bot token' })}
                />
                <input
                  value={telegramForm.externalRef}
                  onChange={(e) => setTelegramForm((p) => ({ ...p, externalRef: e.target.value }))}
                  className="input sm:col-span-2"
                  placeholder={t('admin.communications_messengers.fields.external_ref', { defaultValue: 'External ref' })}
                />
              </div>
            )}
            {channel === 'whatsapp' && (
              <div className="grid max-w-3xl gap-3 sm:grid-cols-2">
                <input
                  value={whatsappForm.accountLabel}
                  onChange={(e) => setWhatsappForm((p) => ({ ...p, accountLabel: e.target.value }))}
                  className="input"
                  placeholder={t('admin.communications_messengers.fields.account_label', { defaultValue: 'Account label' })}
                />
                <input
                  value={whatsappForm.phoneNumberId}
                  onChange={(e) => setWhatsappForm((p) => ({ ...p, phoneNumberId: e.target.value }))}
                  className="input"
                  placeholder={t('admin.communications_messengers.fields.phone_number_id', { defaultValue: 'Phone number ID' })}
                />
                <input
                  type="password"
                  value={whatsappForm.accessToken}
                  onChange={(e) => setWhatsappForm((p) => ({ ...p, accessToken: e.target.value }))}
                  className="input sm:col-span-2"
                  placeholder={t('admin.communications_messengers.fields.access_token', { defaultValue: 'Access token' })}
                />
                <input
                  value={whatsappForm.businessAccountId}
                  onChange={(e) => setWhatsappForm((p) => ({ ...p, businessAccountId: e.target.value }))}
                  className="input sm:col-span-2"
                  placeholder={t('admin.communications_messengers.fields.business_account_id', { defaultValue: 'Business account ID' })}
                />
                <input
                  value={whatsappForm.externalRef}
                  onChange={(e) => setWhatsappForm((p) => ({ ...p, externalRef: e.target.value }))}
                  className="input sm:col-span-2"
                  placeholder={t('admin.communications_messengers.fields.external_ref', { defaultValue: 'External ref' })}
                />
              </div>
            )}
            {channel === 'viber' && (
              <div className="grid max-w-3xl gap-3 sm:grid-cols-2">
                <input
                  value={viberForm.accountLabel}
                  onChange={(e) => setViberForm((p) => ({ ...p, accountLabel: e.target.value }))}
                  className="input"
                  placeholder={t('admin.communications_messengers.fields.account_label', { defaultValue: 'Account label' })}
                />
                <input
                  type="password"
                  value={viberForm.botToken}
                  onChange={(e) => setViberForm((p) => ({ ...p, botToken: e.target.value }))}
                  className="input"
                  placeholder={t('admin.communications_messengers.fields.bot_token', { defaultValue: 'Bot token' })}
                />
                <input
                  value={viberForm.externalRef}
                  onChange={(e) => setViberForm((p) => ({ ...p, externalRef: e.target.value }))}
                  className="input sm:col-span-2"
                  placeholder={t('admin.communications_messengers.fields.external_ref', { defaultValue: 'External ref' })}
                />
              </div>
            )}
            {channel === 'messenger' && (
              <div className="grid max-w-3xl gap-3 sm:grid-cols-2">
                <input
                  value={messengerForm.accountLabel}
                  onChange={(e) => setMessengerForm((p) => ({ ...p, accountLabel: e.target.value }))}
                  className="input"
                  placeholder={t('admin.communications_messengers.fields.account_label', { defaultValue: 'Account label' })}
                />
                <input
                  value={messengerForm.pageId}
                  onChange={(e) => setMessengerForm((p) => ({ ...p, pageId: e.target.value }))}
                  className="input"
                  placeholder={t('admin.communications_messengers.fields.page_id', { defaultValue: 'Page ID' })}
                />
                <input
                  type="password"
                  value={messengerForm.accessToken}
                  onChange={(e) => setMessengerForm((p) => ({ ...p, accessToken: e.target.value }))}
                  className="input"
                  placeholder={t('admin.communications_messengers.fields.page_access_token', { defaultValue: 'Page access token' })}
                />
                <input
                  type="password"
                  value={messengerForm.appSecret}
                  onChange={(e) => setMessengerForm((p) => ({ ...p, appSecret: e.target.value }))}
                  className="input"
                  placeholder={t('admin.communications_messengers.fields.app_secret', { defaultValue: 'App secret' })}
                />
                <input
                  value={messengerForm.externalRef}
                  onChange={(e) => setMessengerForm((p) => ({ ...p, externalRef: e.target.value }))}
                  className="input sm:col-span-2"
                  placeholder={t('admin.communications_messengers.fields.external_ref', { defaultValue: 'External ref' })}
                />
              </div>
            )}
            {channel === 'instagram' && (
              <div className="grid max-w-3xl gap-3 sm:grid-cols-2">
                <input
                  value={instagramForm.accountLabel}
                  onChange={(e) => setInstagramForm((p) => ({ ...p, accountLabel: e.target.value }))}
                  className="input"
                  placeholder={t('admin.communications_messengers.fields.account_label', { defaultValue: 'Account label' })}
                />
                <input
                  value={instagramForm.accountId}
                  onChange={(e) => setInstagramForm((p) => ({ ...p, accountId: e.target.value }))}
                  className="input"
                  placeholder={t('admin.communications_messengers.fields.instagram_account_id', { defaultValue: 'Instagram account ID' })}
                />
                <input
                  type="password"
                  value={instagramForm.accessToken}
                  onChange={(e) => setInstagramForm((p) => ({ ...p, accessToken: e.target.value }))}
                  className="input sm:col-span-2"
                  placeholder={t('admin.communications_messengers.fields.access_token', { defaultValue: 'Access token' })}
                />
                <input
                  value={instagramForm.externalRef}
                  onChange={(e) => setInstagramForm((p) => ({ ...p, externalRef: e.target.value }))}
                  className="input sm:col-span-2"
                  placeholder={t('admin.communications_messengers.fields.external_ref', { defaultValue: 'External ref' })}
                />
              </div>
            )}
            <div className="pt-2">
              <button
                type="button"
                className="btn-primary"
                disabled={connectionBusyKey !== null || !hubCanSubmitCredentials}
                onClick={() =>
                  void runConnectionAction(
                    'hub-connect',
                    handleHubConnect,
                    t('admin.communications_messengers.integration_wizard.notices.connected', { defaultValue: 'Connected and enabled' }),
                  )
                }
              >
                {t('admin.communications_messengers.integration_wizard.connect')}
              </button>
            </div>
          </>
        ) : (
          <p className="text-sm text-slate-600">
            {t('admin.communications_messengers.integration_wizard.credentials_saved', {
              defaultValue: 'Credentials are stored for “{name}”. Use verify below or disconnect to stop using this channel.',
              values: { name: pa?.account_label || '—' },
            })}
          </p>
        )}
      </div>

      {pa ? (
        <div className="mt-4 space-y-4 rounded-lg border border-slate-200 p-4">
          <h2 className="text-sm font-semibold text-slate-900">
            {t('admin.communications_messengers.integration_wizard.step_verify_heading')}
          </h2>
          {showMetaChecklist ? (
            <p className="text-xs text-slate-600">
              {t('admin.communications_messengers.integration_wizard.hint_meta_verify')}
            </p>
          ) : null}
          {channel === 'telegram' ? (
            <p className="text-xs text-slate-600">
              {t('admin.communications_messengers.integration_wizard.hint_telegram_webhook')}
            </p>
          ) : null}
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() =>
                void runConnectionAction(
                  testKey,
                  () => runAccountTest(pa),
                  t('admin.communications_messengers.notices.connection_test_completed', { defaultValue: 'Connection test completed' }),
                )
              }
              disabled={connectionBusyKey !== null}
              className="btn-secondary btn-sm disabled:opacity-60"
            >
              {connectionBusyKey === testKey ? t('common.loading') : t('admin.communications_messengers.integration_wizard.verify_connection')}
            </button>
            {channel === 'telegram' ? (
              <>
                <button
                  type="button"
                  onClick={() =>
                    void runConnectionAction(
                      `hub-tg-set-${pa.id}`,
                      () => runTelegramWebhookSet(pa),
                      t('admin.communications_messengers.notices.telegram_webhook_set', { defaultValue: 'Telegram webhook set' }),
                    )
                  }
                  disabled={connectionBusyKey !== null}
                  className="btn-secondary btn-sm disabled:opacity-60"
                >
                  {connectionBusyKey === `hub-tg-set-${pa.id}`
                    ? t('common.loading')
                    : t('admin.communications_messengers.account.set_webhook', { defaultValue: 'Set webhook' })}
                </button>
                <button
                  type="button"
                  onClick={() =>
                    void runConnectionAction(
                      `hub-tg-del-${pa.id}`,
                      () => runTelegramWebhookDelete(pa),
                      t('admin.communications_messengers.notices.telegram_webhook_deleted', { defaultValue: 'Telegram webhook deleted' }),
                    )
                  }
                  disabled={connectionBusyKey !== null}
                  className="btn-secondary btn-sm disabled:opacity-60"
                >
                  {connectionBusyKey === `hub-tg-del-${pa.id}`
                    ? t('common.loading')
                    : t('admin.communications_messengers.account.delete_webhook', { defaultValue: 'Delete webhook' })}
                </button>
              </>
            ) : null}
          </div>
          {webhookUrl ? (
            <div className="break-all text-xs text-slate-600">
              {t('admin.communications_messengers.account.webhook', { defaultValue: 'Webhook' })}: {webhookUrl}
            </div>
          ) : null}
          {verifyToken ? (
            <div className="break-all text-xs text-slate-600">
              {t('admin.communications_messengers.account.verify_token', { defaultValue: 'Verify token' })}: {verifyToken}
            </div>
          ) : null}
          {(webhookUrl || verifyToken) && (
            <div className="flex flex-wrap gap-2">
              {webhookUrl ? (
                <button
                  type="button"
                  onClick={() => void copyText(webhookUrl, t('admin.communications_messengers.notices.webhook_copied', { defaultValue: 'Webhook URL copied' }))}
                  className="btn-secondary btn-xs"
                >
                  {t('admin.communications_messengers.account.copy_webhook', { defaultValue: 'Copy webhook URL' })}
                </button>
              ) : null}
              {verifyToken ? (
                <button
                  type="button"
                  onClick={() =>
                    void copyText(verifyToken, t('admin.communications_messengers.notices.verify_token_copied', { defaultValue: 'Verify token copied' }))
                  }
                  className="btn-secondary btn-xs"
                >
                  {t('admin.communications_messengers.account.copy_verify_token', { defaultValue: 'Copy verify token' })}
                </button>
              ) : null}
            </div>
          )}
          {lastError ? (
            <div className="text-xs text-rose-700">
              {t('admin.communications_messengers.account.last_error', { defaultValue: 'Last error' })}: {lastError}
            </div>
          ) : null}
          {hubIntegrationStatus === 'live' ? (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
              {t('admin.communications_messengers.integration_wizard.step_active_done')}
            </div>
          ) : null}
        </div>
      ) : null}

      {selectedAccounts.length > 1 ? (
        <p className="mt-4 text-xs text-slate-500">
          {t('admin.communications_messengers.integration_wizard.multiple_accounts_hint_before')}{' '}
          <Link className="font-medium text-brand-700 hover:underline" to={CRM_APP_PATHS.settingsCommunicationsMessengers}>
            {t('admin.communications_messengers.actions.all_messengers')}
          </Link>
          {t('admin.communications_messengers.integration_wizard.multiple_accounts_hint_after')}
        </p>
      ) : null}
    </section>
  )
}

export type CommunicationsMessengerSettingsPageProps = {
  /** When set, only this channel is shown (Integration hub entry); shared templates stay on the combined screen. */
  lockedChannel?: MessengerChannel
}

export default function CommunicationsMessengerSettingsPage({ lockedChannel }: CommunicationsMessengerSettingsPageProps) {
  const { t } = useI18n()
  const { me } = useAuth()
  const planLimitModal = usePlanLimitModal()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [saveNotice, setSaveNotice] = useState<string | null>(null)
  const [saveBusy, setSaveBusy] = useState(false)
  const [connectionBusyKey, setConnectionBusyKey] = useState<string | null>(null)

  const [settings, setSettings] = useState<any | null>(null)
  const [accounts, setAccounts] = useState<CommunicationChannelAccount[]>([])
  const [selectedChannel, setSelectedChannel] = useState<MessengerChannel>(lockedChannel ?? 'whatsapp')

  useEffect(() => {
    if (lockedChannel) setSelectedChannel(lockedChannel)
  }, [lockedChannel])

  const [commandAudit, setCommandAudit] = useState<CommunicationCommandAudit[]>([])
  const [commandDraftLabel, setCommandDraftLabel] = useState('')
  const [commandDraftTarget, setCommandDraftTarget] = useState<'email' | 'messages' | 'both'>('both')
  const [messageTemplateDraftLabel, setMessageTemplateDraftLabel] = useState('')
  const [messageTemplateDraftBody, setMessageTemplateDraftBody] = useState('')
  const [messageTemplateDraftVisibility, setMessageTemplateDraftVisibility] = useState<'private' | 'company'>('private')

  const [telegramForm, setTelegramForm] = useState({ accountLabel: 'Main Telegram bot', botToken: '', externalRef: '' })
  const [whatsappForm, setWhatsappForm] = useState({ accountLabel: 'Main WhatsApp', phoneNumberId: '', accessToken: '', businessAccountId: '', externalRef: '' })
  const [viberForm, setViberForm] = useState({ accountLabel: 'Main Viber bot', botToken: '', externalRef: '' })
  const [messengerForm, setMessengerForm] = useState({ accountLabel: 'Main FB Messenger', pageId: '', accessToken: '', appSecret: '', externalRef: '' })
  const [instagramForm, setInstagramForm] = useState({ accountLabel: 'Main Instagram', accountId: '', accessToken: '', externalRef: '' })

  const loadAll = useCallback(async () => {
    const [cfg, cmdAuditResp, accResp] = await Promise.all([
      getCommunicationsSettings(),
      lockedChannel
        ? Promise.resolve({ items: [] as CommunicationCommandAudit[] })
        : listCommunicationCommandAudit({ limit: 30 }).catch(() => ({ items: [] as CommunicationCommandAudit[] })),
      listCommunicationAccounts(lockedChannel ? { channel: lockedChannel } : undefined).catch(() => ({
        items: [] as CommunicationChannelAccount[],
      })),
    ])
    setSettings(cfg)
    setCommandAudit(Array.isArray(cmdAuditResp?.items) ? cmdAuditResp.items : [])
    const rows = Array.isArray(accResp?.items) ? accResp.items : []
    setAccounts(rows.filter((x) => CHANNELS.includes(String(x.channel || '').toLowerCase() as MessengerChannel)))
  }, [lockedChannel])

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        await loadAll()
      } catch (err: any) {
        if (mounted) {
          if (
            !planLimitModal?.showPlanLimitIfNeeded(
              err,
              t('admin.communications_messengers.errors.load_failed', { defaultValue: 'Failed to load messenger settings' }),
            )
          ) {
            setError(
              getFriendlyErrorInfo(
                err,
                t('admin.communications_messengers.errors.load_failed', { defaultValue: 'Failed to load messenger settings' }),
                t,
              ),
            )
          }
        }
      } finally {
        if (mounted) setLoading(false)
      }
    })()
    return () => {
      mounted = false
    }
  }, [loadAll, planLimitModal, t])

  const commands: CommunicationCommandTemplate[] = Array.isArray(settings?.commands?.items)
    ? settings.commands.items
    : []
  const messageTemplates: CommunicationMessageTemplate[] = Array.isArray(settings?.messageTemplates?.items)
    ? settings.messageTemplates.items
    : []

  const channelsConfig = useMemo(() => {
    const rows = Array.isArray(settings?.channels?.channels) ? settings.channels.channels : []
    const map = new Map<string, any>()
    for (const row of rows) {
      const key = String(row?.key || '').toLowerCase()
      if (CHANNELS.includes(key as MessengerChannel)) map.set(key, row)
    }
    return map
  }, [settings])

  const accountsByChannel = useMemo(() => {
    const out: Record<MessengerChannel, CommunicationChannelAccount[]> = {
      telegram: [],
      whatsapp: [],
      viber: [],
      messenger: [],
      instagram: [],
    }
    for (const account of accounts) {
      const key = String(account.channel || '').toLowerCase() as MessengerChannel
      if (CHANNELS.includes(key)) out[key].push(account)
    }
    return out
  }, [accounts])

  const channelSummaries = useMemo(() => {
    return CHANNELS.map((channel) => {
      const rows = accountsByChannel[channel]
      const active = rows.filter((x) => Boolean(x.is_active)).length
      const connected = rows.filter((x) => connectionStatusOf(x) === 'ok' || connectionStatusOf(x) === 'connected').length
      const cfg = channelsConfig.get(channel)
      return {
        channel,
        total: rows.length,
        active,
        connected,
        enabled: Boolean(cfg?.enabled),
      }
    })
  }, [accountsByChannel, channelsConfig])

  const selectedCfg = channelsConfig.get(selectedChannel)
  const selectedAccounts = accountsByChannel[selectedChannel] || []
  const showMetaChecklist = selectedChannel === 'whatsapp' || selectedChannel === 'messenger' || selectedChannel === 'instagram'

  const primaryAccount = useMemo(() => {
    if (!selectedAccounts.length) return null
    return selectedAccounts.find((a) => a.is_active) || selectedAccounts[0]
  }, [selectedAccounts])

  const hubIntegrationStatus = useMemo(() => {
    if (!primaryAccount) return 'needs_account' as const
    const st = connectionStatusOf(primaryAccount)
    const channelOn = Boolean(selectedCfg?.enabled)
    const accountOn = Boolean(primaryAccount.is_active)
    if (!channelOn || !accountOn) return 'disabled' as const
    if (st === 'ok' || st === 'connected') return 'live' as const
    if (st === 'error' || st === 'failed') return 'error' as const
    return 'pending' as const
  }, [primaryAccount, selectedCfg])

  const wizardStepHighlight = useMemo(() => {
    if (hubIntegrationStatus === 'needs_account') return 1
    if (hubIntegrationStatus === 'disabled') return 1
    if (hubIntegrationStatus === 'live') return 3
    return 2
  }, [hubIntegrationStatus])

  const hubStatusHeadline = useMemo(() => {
    if (!lockedChannel) return ''
    switch (hubIntegrationStatus) {
      case 'needs_account':
        return t('admin.communications_messengers.integration_wizard.summary.needs_account')
      case 'disabled':
        return t('admin.communications_messengers.integration_wizard.summary.disabled')
      case 'pending':
        return t('admin.communications_messengers.integration_wizard.summary.pending')
      case 'error':
        return t('admin.communications_messengers.integration_wizard.summary.error')
      case 'live':
        return t('admin.communications_messengers.integration_wizard.summary.live')
      default:
        return ''
    }
  }, [hubIntegrationStatus, lockedChannel, t])

  const hubCanSubmitCredentials = useMemo(() => {
    if (!lockedChannel) return false
    switch (selectedChannel) {
      case 'telegram':
        return telegramForm.botToken.trim().length > 0
      case 'whatsapp':
        return Boolean(whatsappForm.phoneNumberId.trim() && whatsappForm.accessToken.trim())
      case 'viber':
        return viberForm.botToken.trim().length > 0
      case 'messenger':
        return Boolean(messengerForm.pageId.trim() && messengerForm.accessToken.trim())
      case 'instagram':
        return Boolean(instagramForm.accountId.trim() && instagramForm.accessToken.trim())
      default:
        return false
    }
  }, [instagramForm, lockedChannel, messengerForm, selectedChannel, telegramForm, viberForm, whatsappForm])

  const runConnectionAction = useCallback(async (key: string, action: () => Promise<void>, successText: string) => {
    setConnectionBusyKey(key)
    setError(null)
    setSaveNotice(null)
    try {
      await action()
      await loadAll()
      setSaveNotice(successText)
    } catch (err: any) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('admin.communications_messengers.errors.connection_failed', { defaultValue: 'Connection operation failed' }),
        )
      ) {
        setError(
          getFriendlyErrorInfo(
            err,
            t('admin.communications_messengers.errors.connection_failed', { defaultValue: 'Connection operation failed' }),
            t,
          ),
        )
      }
    } finally {
      setConnectionBusyKey(null)
    }
  }, [loadAll, planLimitModal, t])

  const copyText = useCallback(async (value: string, successText: string) => {
    const text = String(value || '').trim()
    if (!text) return
    try {
      await navigator.clipboard.writeText(text)
      setSaveNotice(successText)
      setError(null)
    } catch (err: any) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('admin.communications_messengers.errors.copy_failed', { defaultValue: 'Failed to copy value' }),
        )
      ) {
        setError(
          getFriendlyErrorInfo(
            err,
            t('admin.communications_messengers.errors.copy_failed', { defaultValue: 'Failed to copy value' }),
            t,
          ),
        )
      }
    }
  }, [planLimitModal, t])

  const patchChannelFlags = useCallback(async (channelKey: MessengerChannel, patch: Record<string, any>) => {
    const channels = Array.isArray(settings?.channels?.channels) ? settings.channels.channels : []
    const nextChannels = channels.map((row: any) => {
      const key = String(row?.key || '').toLowerCase()
      if (key !== channelKey) return row
      return { ...row, ...patch }
    })
    setSaveBusy(true)
    setSaveNotice(null)
    setError(null)
    try {
      const patched = await patchCommunicationsSettings({
        channels: {
          ...(settings?.channels || {}),
          channels: nextChannels,
        },
      } as any)
      setSettings(patched)
      setSaveNotice(
        t('admin.communications_messengers.notices.channel_switches_updated', {
          defaultValue: '{channel}: switches updated',
          values: {
            channel: t(CHANNEL_META[channelKey].titleKey as any, { defaultValue: CHANNEL_META[channelKey].titleDefault }),
          },
        }),
      )
    } catch (err: any) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('admin.communications_messengers.errors.update_switches_failed', {
            defaultValue: 'Failed to update {channel} switches',
            values: { channel: channelKey },
          }),
        )
      ) {
        setError(
          getFriendlyErrorInfo(
            err,
            t('admin.communications_messengers.errors.update_switches_failed', {
              defaultValue: 'Failed to update {channel} switches',
              values: { channel: channelKey },
            }),
            t,
          ),
        )
      }
    } finally {
      setSaveBusy(false)
    }
  }, [planLimitModal, settings, t])

  const applyChannelPatchFresh = useCallback(async (channelKey: MessengerChannel, patch: Record<string, any>) => {
    const cfg = await getCommunicationsSettings()
    const channels = Array.isArray(cfg?.channels?.channels) ? cfg.channels.channels : []
    const nextChannels = channels.map((row: any) => {
      const key = String(row?.key || '').toLowerCase()
      if (key !== channelKey) return row
      return { ...row, ...patch }
    })
    const patched = await patchCommunicationsSettings({
      channels: {
        ...(cfg?.channels || {}),
        channels: nextChannels,
      },
    } as any)
    setSettings(patched)
    return patched
  }, [])

  const enableMessengerIntegration = useCallback(async () => {
    await applyChannelPatchFresh(selectedChannel, { enabled: true, inboundEnabled: true, outboundEnabled: true })
    const { items } = await listCommunicationAccounts(lockedChannel ? { channel: lockedChannel } : undefined)
    const forCh = items.filter((x) => String(x.channel || '').toLowerCase() === selectedChannel)
    for (const acc of forCh) {
      await patchCommunicationAccount(acc.id, { is_active: true })
    }
  }, [applyChannelPatchFresh, lockedChannel, selectedChannel])

  const disableMessengerIntegration = useCallback(async () => {
    const { items } = await listCommunicationAccounts(lockedChannel ? { channel: lockedChannel } : undefined)
    const forCh = items.filter((x) => String(x.channel || '').toLowerCase() === selectedChannel)
    for (const acc of forCh) {
      await patchCommunicationAccount(acc.id, { is_active: false })
    }
    await applyChannelPatchFresh(selectedChannel, { enabled: false, inboundEnabled: false, outboundEnabled: false })
  }, [applyChannelPatchFresh, lockedChannel, selectedChannel])

  const createTelegramAccount = useCallback(async () => {
    await createCommunicationAccount({
      channel: 'telegram',
      account_label: telegramForm.accountLabel.trim() || 'Telegram bot',
      external_account_ref: telegramForm.externalRef.trim() || undefined,
      settings_json: {
        provider: 'telegram_bot',
        telegram: {
          bot_token: telegramForm.botToken.trim() || undefined,
        },
      },
    })
    setTelegramForm((p) => ({ ...p, botToken: '' }))
  }, [telegramForm])

  const createWhatsappAccount = useCallback(async () => {
    await createCommunicationAccount({
      channel: 'whatsapp',
      account_label: whatsappForm.accountLabel.trim() || 'WhatsApp',
      external_account_ref: whatsappForm.externalRef.trim() || undefined,
      settings_json: {
        provider: 'whatsapp_cloud_api',
        whatsapp: {
          phone_number_id: whatsappForm.phoneNumberId.trim() || undefined,
          access_token: whatsappForm.accessToken.trim() || undefined,
          business_account_id: whatsappForm.businessAccountId.trim() || undefined,
        },
      },
    })
    setWhatsappForm((p) => ({ ...p, accessToken: '' }))
  }, [whatsappForm])

  const createViberAccount = useCallback(async () => {
    await createCommunicationAccount({
      channel: 'viber',
      account_label: viberForm.accountLabel.trim() || 'Viber bot',
      external_account_ref: viberForm.externalRef.trim() || undefined,
      settings_json: {
        provider: 'viber_bot',
        viber: {
          bot_token: viberForm.botToken.trim() || undefined,
        },
      },
    })
    setViberForm((p) => ({ ...p, botToken: '' }))
  }, [viberForm])

  const createMessengerAccount = useCallback(async () => {
    await createCommunicationAccount({
      channel: 'messenger',
      account_label: messengerForm.accountLabel.trim() || 'Messenger page',
      external_account_ref: messengerForm.externalRef.trim() || undefined,
      settings_json: {
        provider: 'facebook_messenger',
        messenger: {
          page_id: messengerForm.pageId.trim() || undefined,
          access_token: messengerForm.accessToken.trim() || undefined,
          app_secret: messengerForm.appSecret.trim() || undefined,
        },
      },
    })
    setMessengerForm((p) => ({ ...p, accessToken: '', appSecret: '' }))
  }, [messengerForm])

  const createInstagramAccount = useCallback(async () => {
    await createCommunicationAccount({
      channel: 'instagram',
      account_label: instagramForm.accountLabel.trim() || 'Instagram',
      external_account_ref: instagramForm.externalRef.trim() || undefined,
      settings_json: {
        provider: 'instagram_graph',
        instagram: {
          account_id: instagramForm.accountId.trim() || undefined,
          access_token: instagramForm.accessToken.trim() || undefined,
        },
      },
    })
    setInstagramForm((p) => ({ ...p, accessToken: '' }))
  }, [instagramForm])

  const setAccountActive = useCallback(async (account: CommunicationChannelAccount, isActive: boolean) => {
    await patchCommunicationAccount(account.id, { is_active: isActive })
  }, [])

  const runAccountTest = useCallback(async (account: CommunicationChannelAccount) => {
    await testCommunicationAccountConnection(account.id)
  }, [])

  const runTelegramWebhookSet = useCallback(async (account: CommunicationChannelAccount) => {
    await setTelegramAccountWebhook(account.id)
  }, [])

  const runTelegramWebhookDelete = useCallback(async (account: CommunicationChannelAccount) => {
    await deleteTelegramAccountWebhook(account.id)
  }, [])

  const saveCommands = useCallback(async (items: CommunicationCommandTemplate[]) => {
    setSaveBusy(true)
    setSaveNotice(null)
    setError(null)
    try {
      const patched = await patchCommunicationsSettings({ commands: { items } })
      setSettings(patched)
      setSaveNotice(t('common.saved', { defaultValue: 'Saved' }))
    } catch (err: any) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('admin.communications_messengers.errors.save_commands_failed', { defaultValue: 'Failed to save command templates' }),
        )
      ) {
        setError(
          getFriendlyErrorInfo(
            err,
            t('admin.communications_messengers.errors.save_commands_failed', { defaultValue: 'Failed to save command templates' }),
            t,
          ),
        )
      }
    } finally {
      setSaveBusy(false)
    }
  }, [planLimitModal, t])

  const saveMessageTemplates = useCallback(async (items: CommunicationMessageTemplate[]) => {
    setSaveBusy(true)
    setSaveNotice(null)
    setError(null)
    try {
      const patched = await patchCommunicationsSettings({ messageTemplates: { items } } as any)
      setSettings(patched)
      setSaveNotice(t('common.saved', { defaultValue: 'Saved' }))
    } catch (err: any) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('admin.communications_messengers.errors.save_message_templates_failed', { defaultValue: 'Failed to save message templates' }),
        )
      ) {
        setError(
          getFriendlyErrorInfo(
            err,
            t('admin.communications_messengers.errors.save_message_templates_failed', { defaultValue: 'Failed to save message templates' }),
            t,
          ),
        )
      }
    } finally {
      setSaveBusy(false)
    }
  }, [planLimitModal, t])

  const addCommand = useCallback(() => {
    const label = commandDraftLabel.trim()
    if (!label) return
    const id = `cmd_${Date.now()}`
    void saveCommands([
      ...commands,
      {
        id,
        label,
        target: commandDraftTarget,
        enabled: true,
        actions: [{ type: 'mark_read' }, { type: 'archive' }],
      },
    ])
    setCommandDraftLabel('')
  }, [commandDraftLabel, commandDraftTarget, commands, saveCommands])

  const patchCommand = useCallback((id: string, patch: Partial<CommunicationCommandTemplate>) => {
    const next = commands.map((cmd) => (cmd.id === id ? { ...cmd, ...patch } : cmd))
    void saveCommands(next)
  }, [commands, saveCommands])

  const removeCommand = useCallback((id: string) => {
    const next = commands.filter((cmd) => cmd.id !== id)
    void saveCommands(next)
  }, [commands, saveCommands])

  const addCommandAction = useCallback((id: string) => {
    const next = commands.map((cmd) => {
      if (cmd.id !== id) return cmd
      return {
        ...cmd,
        actions: [...(Array.isArray(cmd.actions) ? cmd.actions : []), { type: 'mark_read' as CommunicationCommandActionType }],
      }
    })
    void saveCommands(next)
  }, [commands, saveCommands])

  const patchCommandAction = useCallback((id: string, idx: number, patch: { type?: CommunicationCommandActionType; value?: string | null }) => {
    const next = commands.map((cmd) => {
      if (cmd.id !== id) return cmd
      const actions = Array.isArray(cmd.actions) ? [...cmd.actions] : []
      const prev = actions[idx]
      if (!prev) return cmd
      const nextType = patch.type || prev.type
      actions[idx] = {
        type: nextType,
        value: commandActionNeedsValue(nextType) ? (patch.value ?? prev.value ?? '') : null,
      }
      return { ...cmd, actions }
    })
    void saveCommands(next)
  }, [commands, saveCommands])

  const removeCommandAction = useCallback((id: string, idx: number) => {
    const next = commands.map((cmd) => {
      if (cmd.id !== id) return cmd
      const actions = (Array.isArray(cmd.actions) ? cmd.actions : []).filter((_, i) => i !== idx)
      return { ...cmd, actions }
    })
    void saveCommands(next)
  }, [commands, saveCommands])

  const moveCommandAction = useCallback((id: string, idx: number, direction: 'up' | 'down') => {
    const next = commands.map((cmd) => {
      if (cmd.id !== id) return cmd
      const actions = Array.isArray(cmd.actions) ? [...cmd.actions] : []
      const target = direction === 'up' ? idx - 1 : idx + 1
      if (idx < 0 || target < 0 || idx >= actions.length || target >= actions.length) return cmd
      const tmp = actions[idx]
      actions[idx] = actions[target]
      actions[target] = tmp
      return { ...cmd, actions }
    })
    void saveCommands(next)
  }, [commands, saveCommands])

  const addMissingDefaultPresets = useCallback(() => {
    const byId = new Set(commands.map((c) => c.id))
    const add = DEFAULT_COMMAND_PRESETS.filter((preset) => !byId.has(preset.id))
    if (!add.length) return
    void saveCommands([...commands, ...add])
  }, [commands, saveCommands])

  const addMessageTemplate = useCallback(() => {
    const label = messageTemplateDraftLabel.trim()
    const body = messageTemplateDraftBody.trim()
    if (!label || !body) return
    const id = `msg_tpl_${Date.now()}`
    void saveMessageTemplates([
      ...messageTemplates,
      {
        id,
        label,
        body,
        visibility: messageTemplateDraftVisibility,
        target: 'messages',
        ownerUserId: messageTemplateDraftVisibility === 'private' ? (me?.sub || null) : null,
        enabled: true,
      },
    ])
    setMessageTemplateDraftLabel('')
    setMessageTemplateDraftBody('')
  }, [
    me?.sub,
    messageTemplateDraftBody,
    messageTemplateDraftLabel,
    messageTemplateDraftVisibility,
    messageTemplates,
    saveMessageTemplates,
  ])

  const patchMessageTemplate = useCallback((id: string, patch: Partial<CommunicationMessageTemplate>) => {
    const next = messageTemplates.map((tpl) => {
      if (tpl.id !== id) return tpl
      const merged = { ...tpl, ...patch, target: 'messages' as const }
      if (merged.visibility === 'private' && !merged.ownerUserId) merged.ownerUserId = me?.sub || null
      if (merged.visibility === 'company') merged.ownerUserId = null
      return merged
    })
    void saveMessageTemplates(next)
  }, [me?.sub, messageTemplates, saveMessageTemplates])

  const removeMessageTemplate = useCallback((id: string) => {
    void saveMessageTemplates(messageTemplates.filter((tpl) => tpl.id !== id))
  }, [messageTemplates, saveMessageTemplates])

  const createForSelectedChannel = useCallback(async () => {
    if (selectedChannel === 'telegram') return await createTelegramAccount()
    if (selectedChannel === 'whatsapp') return await createWhatsappAccount()
    if (selectedChannel === 'viber') return await createViberAccount()
    if (selectedChannel === 'instagram') return await createInstagramAccount()
    return await createMessengerAccount()
  }, [createInstagramAccount, createMessengerAccount, createTelegramAccount, createViberAccount, createWhatsappAccount, selectedChannel])

  const handleHubConnect = useCallback(async () => {
    await createForSelectedChannel()
    await applyChannelPatchFresh(selectedChannel, { enabled: true, inboundEnabled: true, outboundEnabled: true })
    const { items } = await listCommunicationAccounts(lockedChannel ? { channel: lockedChannel } : undefined)
    const forCh = items.filter((x) => String(x.channel || '').toLowerCase() === selectedChannel)
    const newest =
      forCh.length > 0
        ? [...forCh].sort((a, b) => (String(a.created_at) < String(b.created_at) ? 1 : -1))[0]
        : null
    if (newest) await patchCommunicationAccount(newest.id, { is_active: true })
  }, [applyChannelPatchFresh, createForSelectedChannel, lockedChannel, selectedChannel])

  const messengerHeaderProps = lockedChannel
    ? {
        backHref: CRM_APP_PATHS.settingsIntegrations,
        backLabel: t('admin.integrations_hub.back_to_hub'),
        kicker: t('admin.integrations_hub.integration_kicker', { defaultValue: 'Integration' }),
        title: t(CHANNEL_META[lockedChannel].titleKey as any, {
          defaultValue: CHANNEL_META[lockedChannel].titleDefault,
        }),
        subtitle: t(CHANNEL_META[lockedChannel].subtitleKey as any, {
          defaultValue: CHANNEL_META[lockedChannel].subtitleDefault,
        }),
        actions: (
          <Link to={CRM_APP_PATHS.settingsCommunicationsMessengers} className="btn-secondary">
            {t('admin.communications_messengers.actions.all_messengers', {
              defaultValue: 'All messengers & shared templates',
            })}
          </Link>
        ),
      }
    : {
        backHref: CRM_APP_PATHS.settingsCommunications,
        backLabel: t('admin.communications_messengers.actions.all_settings', {
          defaultValue: 'All communication settings',
        }),
        kicker: t('admin.settings.cards.communications_messengers.label', { defaultValue: 'Messengers' }),
        title: t('admin.communications_messengers.title', { defaultValue: 'Messenger settings' }),
        subtitle: t('admin.communications_messengers.subtitle', {
          defaultValue:
            'Compact setup by channel name: Telegram, WhatsApp, Viber, Facebook Messenger, Instagram.',
        }),
        actions: (
          <Link to={CRM_APP_PATHS.inboxMessagesScoped} className="btn-secondary">
            {t('admin.communications_messengers.actions.open_messages', { defaultValue: 'Open messages' })}
          </Link>
        ),
      }

  return (
    <SettingsSubpageHeader {...messengerHeaderProps}>

      {loading && <div className="text-sm text-slate-500">{t('common.loading')}</div>}
      {error && (
        <ErrorRecoveryBanner
          info={error}
          onRetry={() => {
            setError(null)
            void loadAll()
          }}
          retryLabel={t('common.actions.refresh')}
          {...friendlyErrorBannerSecondary(
            error,
            CRM_APP_PATHS.settingsCommunications,
            t('admin.communications_sla.actions.all', { defaultValue: 'All communication settings' }),
          )}
          compact
        />
      )}
      {saveNotice && <div className="alert-success">{saveNotice}</div>}

      {lockedChannel ? (
        <MessengerHubWizardPanel
          channel={lockedChannel}
          t={t}
          hubIntegrationStatus={hubIntegrationStatus}
          wizardStepHighlight={wizardStepHighlight}
          hubStatusHeadline={hubStatusHeadline}
          hubCanSubmitCredentials={hubCanSubmitCredentials}
          primaryAccount={primaryAccount}
          selectedAccounts={selectedAccounts}
          telegramForm={telegramForm}
          setTelegramForm={setTelegramForm}
          whatsappForm={whatsappForm}
          setWhatsappForm={setWhatsappForm}
          viberForm={viberForm}
          setViberForm={setViberForm}
          messengerForm={messengerForm}
          setMessengerForm={setMessengerForm}
          instagramForm={instagramForm}
          setInstagramForm={setInstagramForm}
          connectionBusyKey={connectionBusyKey}
          runConnectionAction={runConnectionAction}
          handleHubConnect={handleHubConnect}
          enableMessengerIntegration={enableMessengerIntegration}
          disableMessengerIntegration={disableMessengerIntegration}
          copyText={copyText}
          runAccountTest={runAccountTest}
          runTelegramWebhookSet={runTelegramWebhookSet}
          runTelegramWebhookDelete={runTelegramWebhookDelete}
          showMetaChecklist={showMetaChecklist}
        />
      ) : (
      <section className="rounded-lg border border-slate-200 bg-white p-4">
        {!lockedChannel ? (
          <div className="mb-3 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
            {channelSummaries.map((item) => (
              <button
                key={item.channel}
                type="button"
                onClick={() => setSelectedChannel(item.channel)}
                className={clsx(
                  'rounded-lg border px-3 py-2 text-left transition focus:ring-4 focus:ring-brand-100',
                  selectedChannel === item.channel ? 'border-brand-500 bg-brand-50' : 'border-slate-200 bg-white hover:bg-slate-50',
                )}
              >
                <div className="text-sm font-semibold text-slate-900">
                  {t(CHANNEL_META[item.channel].titleKey as any, { defaultValue: CHANNEL_META[item.channel].titleDefault })}
                </div>
                <div className="mt-1 text-xs text-slate-500">
                  {t('admin.communications_messengers.channel_summary', {
                    defaultValue: '{total} account(s) · {active} active · {connected} connected',
                    values: { total: item.total, active: item.active, connected: item.connected },
                  })}
                </div>
                <div className="mt-1 text-[11px] text-slate-600">
                  {t('admin.communications_messengers.channel_state', {
                    defaultValue: 'channel: {state}',
                    values: {
                      state: item.enabled
                        ? t('admin.communications_messengers.states.enabled', { defaultValue: 'enabled' })
                        : t('admin.communications_messengers.states.disabled', { defaultValue: 'disabled' }),
                    },
                  })}
                </div>
              </button>
            ))}
          </div>
        ) : null}

        <div className="rounded border border-slate-200 p-3">
          <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
            {!lockedChannel ? (
              <div>
                <h2 className="text-base font-semibold text-slate-900">
                  {t(CHANNEL_META[selectedChannel].titleKey as any, { defaultValue: CHANNEL_META[selectedChannel].titleDefault })}
                </h2>
                <p className="text-xs text-slate-500">
                  {t(CHANNEL_META[selectedChannel].subtitleKey as any, { defaultValue: CHANNEL_META[selectedChannel].subtitleDefault })}
                </p>
              </div>
            ) : (
              <div className="text-xs font-medium text-slate-600">
                {t('admin.integrations_hub.messenger_channel_controls_kicker', { defaultValue: 'Connection & channel switches' })}
              </div>
            )}
            <div className="grid gap-1 text-xs">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={Boolean(selectedCfg?.enabled)}
                  onChange={(e) => { void patchChannelFlags(selectedChannel, { enabled: e.target.checked }) }}
                  disabled={saveBusy}
                />
                {t('admin.communications_messengers.toggles.enabled', { defaultValue: 'Enabled' })}
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={Boolean(selectedCfg?.inboundEnabled)}
                  onChange={(e) => { void patchChannelFlags(selectedChannel, { inboundEnabled: e.target.checked }) }}
                  disabled={saveBusy}
                />
                {t('admin.communications_messengers.toggles.inbound', { defaultValue: 'Inbound' })}
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={Boolean(selectedCfg?.outboundEnabled)}
                  onChange={(e) => { void patchChannelFlags(selectedChannel, { outboundEnabled: e.target.checked }) }}
                  disabled={saveBusy}
                />
                {t('admin.communications_messengers.toggles.outbound', { defaultValue: 'Outbound' })}
              </label>
            </div>
          </div>

          {selectedChannel === 'telegram' && (
            <div className="mb-3 grid gap-2 md:grid-cols-4">
              <input value={telegramForm.accountLabel} onChange={(e) => setTelegramForm((p) => ({ ...p, accountLabel: e.target.value }))} className="input" placeholder={t('admin.communications_messengers.fields.account_label', { defaultValue: 'Account label' })} />
              <input type="password" value={telegramForm.botToken} onChange={(e) => setTelegramForm((p) => ({ ...p, botToken: e.target.value }))} className="input" placeholder={t('admin.communications_messengers.fields.bot_token', { defaultValue: 'Bot token' })} />
              <input value={telegramForm.externalRef} onChange={(e) => setTelegramForm((p) => ({ ...p, externalRef: e.target.value }))} className="input" placeholder={t('admin.communications_messengers.fields.external_ref', { defaultValue: 'External ref' })} />
              <button type="button" onClick={() => void runConnectionAction(`create-${selectedChannel}`, createForSelectedChannel, t('admin.communications_messengers.notices.telegram_created', { defaultValue: 'Telegram account created' }))} disabled={connectionBusyKey !== null} className="btn-secondary btn-sm disabled:opacity-60">{t(CHANNEL_META[selectedChannel].connectLabelKey as any, { defaultValue: CHANNEL_META[selectedChannel].connectLabelDefault })}</button>
            </div>
          )}

          {selectedChannel === 'whatsapp' && (
            <div className="mb-3 space-y-2">
              <div className="grid gap-2 md:grid-cols-3">
                <input value={whatsappForm.accountLabel} onChange={(e) => setWhatsappForm((p) => ({ ...p, accountLabel: e.target.value }))} className="input" placeholder={t('admin.communications_messengers.fields.account_label', { defaultValue: 'Account label' })} />
                <input value={whatsappForm.phoneNumberId} onChange={(e) => setWhatsappForm((p) => ({ ...p, phoneNumberId: e.target.value }))} className="input" placeholder={t('admin.communications_messengers.fields.phone_number_id', { defaultValue: 'Phone number ID' })} />
                <input type="password" value={whatsappForm.accessToken} onChange={(e) => setWhatsappForm((p) => ({ ...p, accessToken: e.target.value }))} className="input" placeholder={t('admin.communications_messengers.fields.access_token', { defaultValue: 'Access token' })} />
                <input value={whatsappForm.businessAccountId} onChange={(e) => setWhatsappForm((p) => ({ ...p, businessAccountId: e.target.value }))} className="input" placeholder={t('admin.communications_messengers.fields.business_account_id', { defaultValue: 'Business account ID' })} />
                <input value={whatsappForm.externalRef} onChange={(e) => setWhatsappForm((p) => ({ ...p, externalRef: e.target.value }))} className="input" placeholder={t('admin.communications_messengers.fields.external_ref', { defaultValue: 'External ref' })} />
                <button type="button" onClick={() => void runConnectionAction(`create-${selectedChannel}`, createForSelectedChannel, t('admin.communications_messengers.notices.whatsapp_created', { defaultValue: 'WhatsApp account created' }))} disabled={connectionBusyKey !== null} className="btn-secondary btn-sm disabled:opacity-60">{t(CHANNEL_META[selectedChannel].connectLabelKey as any, { defaultValue: CHANNEL_META[selectedChannel].connectLabelDefault })}</button>
              </div>
              <div className="rounded border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
                {t('admin.communications_messengers.whatsapp_flow_hint', { defaultValue: 'WhatsApp flow: create account, click Test, then copy webhook URL and verify token to Meta Webhook settings.' })}
              </div>
            </div>
          )}

          {selectedChannel === 'viber' && (
            <div className="mb-3 grid gap-2 md:grid-cols-4">
              <input value={viberForm.accountLabel} onChange={(e) => setViberForm((p) => ({ ...p, accountLabel: e.target.value }))} className="input" placeholder={t('admin.communications_messengers.fields.account_label', { defaultValue: 'Account label' })} />
              <input type="password" value={viberForm.botToken} onChange={(e) => setViberForm((p) => ({ ...p, botToken: e.target.value }))} className="input" placeholder={t('admin.communications_messengers.fields.bot_token', { defaultValue: 'Bot token' })} />
              <input value={viberForm.externalRef} onChange={(e) => setViberForm((p) => ({ ...p, externalRef: e.target.value }))} className="input" placeholder={t('admin.communications_messengers.fields.external_ref', { defaultValue: 'External ref' })} />
              <button type="button" onClick={() => void runConnectionAction(`create-${selectedChannel}`, createForSelectedChannel, t('admin.communications_messengers.notices.viber_created', { defaultValue: 'Viber account created' }))} disabled={connectionBusyKey !== null} className="btn-secondary btn-sm disabled:opacity-60">{t(CHANNEL_META[selectedChannel].connectLabelKey as any, { defaultValue: CHANNEL_META[selectedChannel].connectLabelDefault })}</button>
            </div>
          )}

          {selectedChannel === 'messenger' && (
            <div className="mb-3 grid gap-2 md:grid-cols-3">
              <input value={messengerForm.accountLabel} onChange={(e) => setMessengerForm((p) => ({ ...p, accountLabel: e.target.value }))} className="input" placeholder={t('admin.communications_messengers.fields.account_label', { defaultValue: 'Account label' })} />
              <input value={messengerForm.pageId} onChange={(e) => setMessengerForm((p) => ({ ...p, pageId: e.target.value }))} className="input" placeholder={t('admin.communications_messengers.fields.page_id', { defaultValue: 'Page ID' })} />
              <input type="password" value={messengerForm.accessToken} onChange={(e) => setMessengerForm((p) => ({ ...p, accessToken: e.target.value }))} className="input" placeholder={t('admin.communications_messengers.fields.page_access_token', { defaultValue: 'Page access token' })} />
              <input type="password" value={messengerForm.appSecret} onChange={(e) => setMessengerForm((p) => ({ ...p, appSecret: e.target.value }))} className="input" placeholder={t('admin.communications_messengers.fields.app_secret', { defaultValue: 'App secret' })} />
              <input value={messengerForm.externalRef} onChange={(e) => setMessengerForm((p) => ({ ...p, externalRef: e.target.value }))} className="input" placeholder={t('admin.communications_messengers.fields.external_ref', { defaultValue: 'External ref' })} />
              <button type="button" onClick={() => void runConnectionAction(`create-${selectedChannel}`, createForSelectedChannel, t('admin.communications_messengers.notices.messenger_created', { defaultValue: 'Messenger account created' }))} disabled={connectionBusyKey !== null} className="btn-secondary btn-sm disabled:opacity-60">{t(CHANNEL_META[selectedChannel].connectLabelKey as any, { defaultValue: CHANNEL_META[selectedChannel].connectLabelDefault })}</button>
            </div>
          )}

          {selectedChannel === 'instagram' && (
            <div className="mb-3 space-y-2">
              <div className="grid gap-2 md:grid-cols-4">
                <input value={instagramForm.accountLabel} onChange={(e) => setInstagramForm((p) => ({ ...p, accountLabel: e.target.value }))} className="input" placeholder={t('admin.communications_messengers.fields.account_label', { defaultValue: 'Account label' })} />
                <input value={instagramForm.accountId} onChange={(e) => setInstagramForm((p) => ({ ...p, accountId: e.target.value }))} className="input" placeholder={t('admin.communications_messengers.fields.instagram_account_id', { defaultValue: 'Instagram account ID' })} />
                <input type="password" value={instagramForm.accessToken} onChange={(e) => setInstagramForm((p) => ({ ...p, accessToken: e.target.value }))} className="input" placeholder={t('admin.communications_messengers.fields.access_token', { defaultValue: 'Access token' })} />
                <input value={instagramForm.externalRef} onChange={(e) => setInstagramForm((p) => ({ ...p, externalRef: e.target.value }))} className="input" placeholder={t('admin.communications_messengers.fields.external_ref', { defaultValue: 'External ref' })} />
              </div>
              <button type="button" onClick={() => void runConnectionAction(`create-${selectedChannel}`, createForSelectedChannel, t('admin.communications_messengers.notices.instagram_created', { defaultValue: 'Instagram account created' }))} disabled={connectionBusyKey !== null} className="btn-secondary btn-sm disabled:opacity-60">{t(CHANNEL_META[selectedChannel].connectLabelKey as any, { defaultValue: CHANNEL_META[selectedChannel].connectLabelDefault })}</button>
            </div>
          )}

          <div className="space-y-2">
            {selectedAccounts.map((acc) => {
              const status = connectionStatusOf(acc)
              const key = `acc-${acc.id}`
              const providerResult = acc.settings_json?.connection?.provider_result || {}
              const webhookUrl = String(providerResult?.webhook_url || '').trim()
              const verifyToken =
                String(providerResult?.webhook_verify_token || '').trim() ||
                String(acc.settings_json?.whatsapp?.webhook_verify_token || '').trim() ||
                String(acc.settings_json?.messenger?.webhook_verify_token || '').trim() ||
                String(acc.settings_json?.instagram?.webhook_verify_token || '').trim()
              const lastError = String(acc.settings_json?.connection?.last_error || '').trim()
              return (
                <div key={acc.id} className="rounded border border-slate-200 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <div className="text-sm font-medium text-slate-900">{acc.account_label}</div>
                      <div className="text-xs text-slate-500">{t('admin.communications_messengers.account.id', { defaultValue: 'id' })}: {acc.id}</div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={clsx('badge', statusBadgeClass(status))}>{status}</span>
                      <label className="inline-flex items-center gap-1 text-xs text-slate-700">
                        <input
                          type="checkbox"
                          checked={Boolean(acc.is_active)}
                          onChange={(e) => { void runConnectionAction(`toggle-${key}`, () => setAccountActive(acc, e.target.checked), t('admin.communications_messengers.notices.account_state_updated', { defaultValue: 'Account state updated' })) }}
                          disabled={connectionBusyKey !== null}
                        />
                        {t('admin.communications_messengers.account.active', { defaultValue: 'Active' })}
                      </label>
                      <button
                        type="button"
                        onClick={() => void runConnectionAction(`test-${key}`, () => runAccountTest(acc), t('admin.communications_messengers.notices.connection_test_completed', { defaultValue: 'Connection test completed' }))}
                        disabled={connectionBusyKey !== null}
                        className="btn-secondary btn-xs disabled:opacity-60"
                      >
                        {connectionBusyKey === `test-${key}` ? t('common.loading') : t('admin.communications_messengers.account.test', { defaultValue: 'Test' })}
                      </button>
                      {selectedChannel === 'telegram' && (
                        <>
                          <button
                            type="button"
                            onClick={() => void runConnectionAction(`tg-set-${key}`, () => runTelegramWebhookSet(acc), t('admin.communications_messengers.notices.telegram_webhook_set', { defaultValue: 'Telegram webhook set' }))}
                            disabled={connectionBusyKey !== null}
                            className="btn-secondary btn-xs disabled:opacity-60"
                          >
                            {connectionBusyKey === `tg-set-${key}` ? t('common.loading') : t('admin.communications_messengers.account.set_webhook', { defaultValue: 'Set webhook' })}
                          </button>
                          <button
                            type="button"
                            onClick={() => void runConnectionAction(`tg-del-${key}`, () => runTelegramWebhookDelete(acc), t('admin.communications_messengers.notices.telegram_webhook_deleted', { defaultValue: 'Telegram webhook deleted' }))}
                            disabled={connectionBusyKey !== null}
                            className="btn-secondary btn-xs disabled:opacity-60"
                          >
                            {connectionBusyKey === `tg-del-${key}` ? t('common.loading') : t('admin.communications_messengers.account.delete_webhook', { defaultValue: 'Delete webhook' })}
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                  {webhookUrl && <div className="mt-2 break-all text-xs text-slate-600">{t('admin.communications_messengers.account.webhook', { defaultValue: 'Webhook' })}: {webhookUrl}</div>}
                  {verifyToken && <div className="mt-1 break-all text-xs text-slate-600">{t('admin.communications_messengers.account.verify_token', { defaultValue: 'Verify token' })}: {verifyToken}</div>}
                  {(webhookUrl || verifyToken) && (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {webhookUrl && (
                        <button
                          type="button"
                          onClick={() => void copyText(webhookUrl, t('admin.communications_messengers.notices.webhook_copied', { defaultValue: 'Webhook URL copied' }))}
                          className="btn-secondary btn-xs"
                        >
                          {t('admin.communications_messengers.account.copy_webhook', { defaultValue: 'Copy webhook URL' })}
                        </button>
                      )}
                      {verifyToken && (
                        <button
                          type="button"
                          onClick={() => void copyText(verifyToken, t('admin.communications_messengers.notices.verify_token_copied', { defaultValue: 'Verify token copied' }))}
                          className="btn-secondary btn-xs"
                        >
                          {t('admin.communications_messengers.account.copy_verify_token', { defaultValue: 'Copy verify token' })}
                        </button>
                      )}
                    </div>
                  )}
                  {lastError && <div className="mt-2 text-xs text-rose-700">{t('admin.communications_messengers.account.last_error', { defaultValue: 'Last error' })}: {lastError}</div>}
                </div>
              )
            })}
            {!selectedAccounts.length && <div className="text-sm text-slate-500">{t('admin.communications_messengers.account.empty', { defaultValue: 'No connected accounts for this channel.' })}</div>}
          </div>

          {showMetaChecklist && (
            <div className="mt-3 alert-info text-xs">
              <div className="font-semibold">{t('admin.communications_messengers.checklist.meta.title', { defaultValue: 'Provider setup checklist' })}</div>
              <ol className="mt-1 list-decimal space-y-1 pl-4">
                <li>{t('admin.communications_messengers.checklist.meta.step_1', { defaultValue: 'Create account with credentials and save.' })}</li>
                <li>{t('admin.communications_messengers.checklist.meta.step_2', { defaultValue: 'Run Test to fetch webhook URL/token and validate access.' })}</li>
                <li>{t('admin.communications_messengers.checklist.meta.step_3', { defaultValue: 'Copy Webhook URL and Verify token into Meta webhook settings.' })}</li>
                <li>{t('admin.communications_messengers.checklist.meta.step_4', { defaultValue: 'Subscribe required webhook fields in provider console and send a test event.' })}</li>
                <li>{t('admin.communications_messengers.checklist.meta.step_5', { defaultValue: 'Return here and run Test again to confirm status is connected.' })}</li>
              </ol>
            </div>
          )}

          {selectedChannel === 'telegram' && (
            <div className="mt-3 alert-info text-xs">
              <div className="font-semibold">{t('admin.communications_messengers.checklist.telegram.title', { defaultValue: 'Telegram setup checklist' })}</div>
              <ol className="mt-1 list-decimal space-y-1 pl-4">
                <li>{t('admin.communications_messengers.checklist.telegram.step_1', { defaultValue: 'Create Telegram account with bot token.' })}</li>
                <li>{t('admin.communications_messengers.checklist.telegram.step_2', { defaultValue: 'Use Set webhook to register CRM public endpoint in Bot API.' })}</li>
                <li>{t('admin.communications_messengers.checklist.telegram.step_3', { defaultValue: 'Run Test to verify bot access and webhook diagnostics.' })}</li>
                <li>{t('admin.communications_messengers.checklist.telegram.step_4', { defaultValue: 'Use Delete webhook when rotating or disabling integration.' })}</li>
              </ol>
            </div>
          )}
        </div>
      </section>
      )}

      {lockedChannel ? (
        <div className="rounded-lg border border-slate-200 bg-slate-50/80 p-4 text-sm text-slate-700">
          <p>
            {t('admin.integrations_hub.messenger_templates_relocated', {
              defaultValue:
                'Message templates, command templates, and command audit are shared across all messenger channels. Open the combined messengers screen to manage them.',
            })}
          </p>
          <Link to={CRM_APP_PATHS.settingsCommunicationsMessengers} className="mt-2 inline-flex font-medium text-brand-700 hover:underline">
            {t('admin.communications_messengers.actions.all_messengers', { defaultValue: 'All messengers & shared templates' })}
          </Link>
        </div>
      ) : (
        <>
          <details className="alert-info p-4" open>
            <summary className="cursor-pointer text-sm font-semibold">
              {t('admin.communications_messengers.templates.how_used', { defaultValue: 'How templates are used' })}
            </summary>
        <ul className="mt-2 list-disc space-y-1 pl-4 text-xs">
          <li>
            {t('admin.communications_messengers.templates.how_used_1', {
              defaultValue: 'Message templates appear as quick buttons in composer on',
            })}{' '}
            <code>{CRM_APP_PATHS.inboxMessagesScoped}</code>.
          </li>
          <li>
            {t('admin.communications_messengers.templates.how_used_2', {
              defaultValue: 'Click template button, text appears in reply field, then edit and send.',
            })}
          </li>
        </ul>
      </details>

      <details className="rounded-lg border border-slate-200 bg-white p-4" open>
        <summary className="cursor-pointer text-sm font-semibold text-slate-900">
          {t('admin.communications_messengers.templates.message_templates', { defaultValue: 'Message templates' })}
        </summary>
        <div className="mt-3">
          <div className="mb-3 flex items-center justify-end">
            <button
              type="button"
              onClick={() => void saveMessageTemplates(messageTemplates)}
              disabled={saveBusy}
              className="btn-secondary btn-sm disabled:opacity-60"
            >
              {t('common.save', { defaultValue: 'Save' })}
            </button>
          </div>

          <div className="mb-3 grid gap-2 md:grid-cols-[minmax(220px,1fr)_minmax(280px,2fr)_140px_auto]">
            <input
              value={messageTemplateDraftLabel}
              onChange={(e) => setMessageTemplateDraftLabel(e.target.value)}
              className="input"
              placeholder={t('admin.communications_messengers.templates.fields.template_name', { defaultValue: 'Template name' })}
            />
            <input
              value={messageTemplateDraftBody}
              onChange={(e) => setMessageTemplateDraftBody(e.target.value)}
              className="input"
              placeholder={t('admin.communications_messengers.templates.fields.template_text', { defaultValue: 'Template text' })}
            />
            <select value={messageTemplateDraftVisibility} onChange={(e) => setMessageTemplateDraftVisibility(e.target.value as 'private' | 'company')} className="input">
              <option value="private">{t('admin.communications_messengers.templates.visibility.private', { defaultValue: 'Private' })}</option>
              <option value="company">{t('admin.communications_messengers.templates.visibility.company', { defaultValue: 'Company' })}</option>
            </select>
            <button
              type="button"
              onClick={addMessageTemplate}
              disabled={saveBusy || !messageTemplateDraftLabel.trim() || !messageTemplateDraftBody.trim()}
              className="btn-secondary btn-sm disabled:opacity-60"
            >
              {t('common.actions.add', { defaultValue: 'Add' })}
            </button>
          </div>

          <div className="space-y-2">
            {messageTemplates.map((tpl) => (
              <div key={tpl.id} className="rounded border border-slate-200 p-3">
                <div className="grid gap-2 md:grid-cols-[minmax(180px,1fr)_minmax(260px,2fr)_120px_100px_auto]">
                  <input value={tpl.label} onChange={(e) => patchMessageTemplate(tpl.id, { label: e.target.value })} className="input" />
                  <input value={tpl.body} onChange={(e) => patchMessageTemplate(tpl.id, { body: e.target.value })} className="input" />
                  <select value={tpl.visibility} onChange={(e) => patchMessageTemplate(tpl.id, { visibility: e.target.value as 'private' | 'company' })} className="input">
                    <option value="private">{t('admin.communications_messengers.templates.visibility.private', { defaultValue: 'Private' })}</option>
                    <option value="company">{t('admin.communications_messengers.templates.visibility.company', { defaultValue: 'Company' })}</option>
                  </select>
                  <label className="inline-flex items-center gap-2 text-sm text-slate-700">
                    <input type="checkbox" checked={tpl.enabled} onChange={(e) => patchMessageTemplate(tpl.id, { enabled: e.target.checked })} />
                    {t('common.enabled', { defaultValue: 'Enabled' })}
                  </label>
                  <button type="button" onClick={() => removeMessageTemplate(tpl.id)} className="btn-danger btn-sm">
                    {t('common.actions.delete', { defaultValue: 'Delete' })}
                  </button>
                </div>
              </div>
            ))}
            {!messageTemplates.length && (
              <div className="text-sm text-slate-500">
                {t('admin.communications_messengers.templates.empty_messages', { defaultValue: 'No message templates yet.' })}
              </div>
            )}
          </div>
        </div>
      </details>

      <details className="rounded-lg border border-amber-200 bg-amber-50 p-4" open>
        <summary className="cursor-pointer text-sm font-semibold text-amber-900">
          {t('admin.communications_messengers.templates.what_are_command_templates', {
            defaultValue: 'What are Command templates',
          })}
        </summary>
        <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-amber-900">
          <li>
            {t('admin.communications_messengers.templates.command_desc_1', {
              defaultValue: 'Saved batch action (example: add tag + archive + set priority).',
            })}
          </li>
          <li>
            {t('admin.communications_messengers.templates.command_desc_2_before', { defaultValue: 'Now applied in' })}{' '}
            <code>{CRM_APP_PATHS.inboxEmailScoped}</code>{' '}
            {t('admin.communications_messengers.templates.command_desc_2_after', {
              defaultValue: 'for selected threads via',
            })}{' '}
            <strong>{t('admin.communications_messengers.templates.run_template', { defaultValue: 'Run template' })}</strong>.
          </li>
          <li>
            {t('admin.communications_messengers.templates.command_desc_3_before', { defaultValue: 'For' })}{' '}
            <code>{CRM_APP_PATHS.inboxMessagesScoped}</code>{' '}
            {t('admin.communications_messengers.templates.command_desc_3_after', {
              defaultValue: 'they are prepared and can be wired next as one-click actions.',
            })}
          </li>
        </ul>
      </details>

      <details className="rounded-lg border border-slate-200 bg-white p-4">
        <summary className="cursor-pointer text-sm font-semibold text-slate-900">
          {t('admin.communications_messengers.templates.command_templates', { defaultValue: 'Command templates' })}
        </summary>
        <div className="mt-3">
          <div className="mb-3 flex items-center justify-between gap-2">
            <button type="button" onClick={addMissingDefaultPresets} disabled={saveBusy} className="btn-secondary btn-sm disabled:opacity-60">
              {t('admin.communications_messengers.templates.add_defaults', { defaultValue: 'Add defaults' })}
            </button>
            <button type="button" onClick={() => void saveCommands(commands)} disabled={saveBusy} className="btn-secondary btn-sm disabled:opacity-60">
              {t('common.save', { defaultValue: 'Save' })}
            </button>
          </div>
          <div className="mb-3 grid gap-2 md:grid-cols-[minmax(220px,1fr)_180px_auto]">
            <input value={commandDraftLabel} onChange={(e) => setCommandDraftLabel(e.target.value)} className="input" placeholder={t('admin.communications_messengers.templates.fields.new_command_label', { defaultValue: 'New command label' })} />
            <select value={commandDraftTarget} onChange={(e) => setCommandDraftTarget(e.target.value as 'email' | 'messages' | 'both')} className="input">
              <option value="both">{t('admin.communications_messengers.templates.targets.both', { defaultValue: 'Both' })}</option>
              <option value="messages">{t('admin.communications_messengers.templates.targets.messages', { defaultValue: 'Messages' })}</option>
              <option value="email">{t('admin.communications_messengers.templates.targets.email', { defaultValue: 'Email' })}</option>
            </select>
            <button type="button" onClick={addCommand} disabled={saveBusy || !commandDraftLabel.trim()} className="btn-secondary btn-sm disabled:opacity-60">
              {t('admin.communications_messengers.templates.add_command', { defaultValue: 'Add command' })}
            </button>
          </div>

          <div className="space-y-2">
            {commands.map((cmd) => (
              <div key={cmd.id} className="rounded border border-slate-200 p-3">
                <div className="grid gap-2 md:grid-cols-[minmax(220px,1fr)_160px_160px_auto]">
                  <input value={cmd.label} onChange={(e) => patchCommand(cmd.id, { label: e.target.value })} className="input" />
                  <select value={cmd.target} onChange={(e) => patchCommand(cmd.id, { target: e.target.value as 'email' | 'messages' | 'both' })} className="input">
                    <option value="both">{t('admin.communications_messengers.templates.targets.both', { defaultValue: 'Both' })}</option>
                    <option value="messages">{t('admin.communications_messengers.templates.targets.messages', { defaultValue: 'Messages' })}</option>
                    <option value="email">{t('admin.communications_messengers.templates.targets.email', { defaultValue: 'Email' })}</option>
                  </select>
                  <label className="inline-flex items-center gap-2 text-sm text-slate-700">
                    <input type="checkbox" checked={cmd.enabled} onChange={(e) => patchCommand(cmd.id, { enabled: e.target.checked })} />
                    {t('common.enabled', { defaultValue: 'Enabled' })}
                  </label>
                  <button type="button" onClick={() => removeCommand(cmd.id)} className="btn-danger btn-sm">
                    {t('common.actions.delete', { defaultValue: 'Delete' })}
                  </button>
                </div>
                <div className="mt-2 space-y-2 text-xs">
                  {(cmd.actions || []).map((action, idx) => (
                    <div key={`${cmd.id}-act-${idx}`} className="grid gap-2 md:grid-cols-[220px_minmax(180px,1fr)_auto_auto_auto]">
                      <select value={action.type} onChange={(e) => patchCommandAction(cmd.id, idx, { type: e.target.value as CommunicationCommandActionType })} className="input text-xs">
                        {COMMAND_ACTION_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>{opt.label}</option>
                        ))}
                      </select>
                      <input value={String(action.value || '')} onChange={(e) => patchCommandAction(cmd.id, idx, { value: e.target.value })} disabled={!commandActionNeedsValue(action.type)} placeholder={commandActionNeedsValue(action.type) ? t('admin.communications_messengers.templates.fields.value_tag_or_folder', { defaultValue: 'Value (tag/folder)' }) : t('admin.communications_messengers.templates.fields.no_value_required', { defaultValue: 'No value required' })} className="input text-xs disabled:bg-slate-100 disabled:text-slate-400" />
                      <button type="button" onClick={() => moveCommandAction(cmd.id, idx, 'up')} disabled={idx === 0} className="btn-secondary btn-xs disabled:opacity-50">
                        {t('admin.communications_messengers.templates.actions.up', { defaultValue: 'Up' })}
                      </button>
                      <button type="button" onClick={() => moveCommandAction(cmd.id, idx, 'down')} disabled={idx >= (cmd.actions?.length || 0) - 1} className="btn-secondary btn-xs disabled:opacity-50">
                        {t('admin.communications_messengers.templates.actions.down', { defaultValue: 'Down' })}
                      </button>
                      <button type="button" onClick={() => removeCommandAction(cmd.id, idx)} className="btn-danger btn-xs">
                        {t('common.actions.remove', { defaultValue: 'Remove' })}
                      </button>
                    </div>
                  ))}
                  <button type="button" onClick={() => addCommandAction(cmd.id)} className="btn-secondary btn-xs">
                    {t('admin.communications_messengers.templates.actions.add_action', { defaultValue: 'Add action' })}
                  </button>
                </div>
              </div>
            ))}
            {!commands.length && (
              <div className="text-sm text-slate-500">
                {t('admin.communications_messengers.templates.empty_commands', { defaultValue: 'No command templates yet.' })}
              </div>
            )}
          </div>
        </div>
      </details>

      <details className="rounded-lg border border-slate-200 bg-white p-4">
        <summary className="cursor-pointer text-sm font-semibold text-slate-900">
          {t('admin.communications_messengers.audit.title', { defaultValue: 'Command audit (recent)' })}
        </summary>
        <div className="mt-3">
          <div className="mb-2 flex justify-end">
            <button
              type="button"
              onClick={() =>
                void listCommunicationCommandAudit({ limit: 30 })
                  .then((r) => setCommandAudit(r.items || []))
                  .catch((e) => {
                    if (
                      !planLimitModal?.showPlanLimitIfNeeded(
                        e,
                        t('admin.communications_messengers.errors.audit_reload_failed', {
                          defaultValue: 'Failed to reload command audit',
                        }),
                      )
                    ) {
                      setError(
                        getFriendlyErrorInfo(
                          e,
                          t('admin.communications_messengers.errors.audit_reload_failed', {
                            defaultValue: 'Failed to reload command audit',
                          }),
                          t,
                        ),
                      )
                    }
                  })
              }
              className="btn-secondary btn-sm"
            >
              {t('common.refresh', { defaultValue: 'Refresh' })}
            </button>
          </div>
          <div className="max-h-80 overflow-auto rounded border border-slate-200">
            <table className="min-w-full text-xs">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="px-2 py-1 text-left">{t('admin.communications_messengers.audit.table.at', { defaultValue: 'At' })}</th>
                  <th className="px-2 py-1 text-left">{t('admin.communications_messengers.audit.table.channel', { defaultValue: 'Channel' })}</th>
                  <th className="px-2 py-1 text-left">{t('admin.communications_messengers.audit.table.command', { defaultValue: 'Command' })}</th>
                  <th className="px-2 py-1 text-left">{t('admin.communications_messengers.audit.table.actor', { defaultValue: 'Actor' })}</th>
                  <th className="px-2 py-1 text-left">{t('admin.communications_messengers.audit.table.thread', { defaultValue: 'Thread' })}</th>
                  <th className="px-2 py-1 text-left">{t('admin.communications_messengers.audit.table.actions', { defaultValue: 'Actions' })}</th>
                </tr>
              </thead>
              <tbody>
                {commandAudit.map((row) => (
                  <tr key={row.id} className="border-t border-slate-100">
                    <td className="px-2 py-1">{row.executed_at || row.created_at || '—'}</td>
                    <td className="px-2 py-1">{row.channel}</td>
                    <td className="px-2 py-1">{row.command_label || row.command_id}</td>
                    <td className="px-2 py-1">{row.actor_user_id || '—'}</td>
                    <td className="px-2 py-1">{row.thread_id}</td>
                    <td className="px-2 py-1">{row.action_count}</td>
                  </tr>
                ))}
                {!commandAudit.length && (
                  <tr>
                    <td className="px-2 py-3 text-slate-500" colSpan={6}>{t('app.communications.states.empty', { defaultValue: 'No activity yet' })}</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </details>
        </>
      )}
    </SettingsSubpageHeader>
  )
}
