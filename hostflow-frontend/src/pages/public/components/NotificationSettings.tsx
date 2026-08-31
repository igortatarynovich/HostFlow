/**
 * Component for managing notification subscriptions in Candidate Portal
 */

import { useState, useEffect } from 'react'
import {
  subscribeToNotifications,
  unsubscribeFromNotifications,
  subscribeToPush,
  unsubscribeFromPush,
} from '../../../api/publicNotifications'
import { useToast } from '../../../components/Toast'
import { useI18n } from '../../../i18n'
import type { NotificationSubscriptionRequest } from '../../../api/publicNotifications'
import {
  isPushSupported,
  getNotificationPermission,
  requestNotificationPermission,
  registerServiceWorker,
  getPushSubscription,
  subscribeToPush as subscribeToPushUtil,
  subscriptionToJSON,
} from '../../../utils/pushNotifications'
import http from '../../../api/http'

interface NotificationSettingsProps {
  token: string
  initialEmail?: string | null
  initialPhone?: string | null
  initialSubscribed?: boolean
}

export function NotificationSettings({
  token,
  initialEmail = '',
  initialPhone = '',
  initialSubscribed = false,
}: NotificationSettingsProps) {
  const { t } = useI18n()
  const { notify } = useToast()
  const [email, setEmail] = useState(initialEmail ?? '')
  const [phone, setPhone] = useState(initialPhone ?? '')
  const [subscribed, setSubscribed] = useState(initialSubscribed)
  const [subscribeDocumentStatus, setSubscribeDocumentStatus] = useState(true)
  const [subscribeStageChanges, setSubscribeStageChanges] = useState(true)
  const [subscribeReminders, setSubscribeReminders] = useState(true)
  const [loading, setLoading] = useState(false)
  const [pushSupported, setPushSupported] = useState(false)
  const [pushPermission, setPushPermission] = useState<NotificationPermission>('default')
  const [pushSubscribed, setPushSubscribed] = useState(false)
  const [swRegistration, setSwRegistration] = useState<ServiceWorkerRegistration | null>(null)

  // Check push support and permission on mount
  useEffect(() => {
    const checkPushSupport = async () => {
      const supported = isPushSupported()
      setPushSupported(supported)

      if (supported) {
        const permission = await getNotificationPermission()
        setPushPermission(permission)

        // Register service worker
        const registration = await registerServiceWorker()
        if (registration) {
          setSwRegistration(registration)

          // Check if already subscribed
          const subscription = await getPushSubscription(registration)
          setPushSubscribed(!!subscription)
        }
      }
    }

    checkPushSupport()
  }, [])

  const handleSubscribe = async () => {
    if (!email && !phone) {
      notify({
        title: t('public.notifications.errors.email_or_phone_required', {
          defaultValue: 'Email или телефон обязательны',
        }),
        variant: 'error',
      })
      return
    }

    setLoading(true)
    try {
      const payload: NotificationSubscriptionRequest = {
        token,
        email: email || undefined,
        phone: phone || undefined,
        subscribe_document_status: subscribeDocumentStatus,
        subscribe_stage_changes: subscribeStageChanges,
        subscribe_reminders: subscribeReminders,
      }
      const response = await subscribeToNotifications(payload)
      setSubscribed(true)
      notify({
        title: t('public.notifications.success.subscribed', {
          defaultValue: 'Подписка оформлена',
        }),
        description: response.message,
        variant: 'success',
      })
    } catch (err: any) {
      notify({
        title: t('public.notifications.errors.subscribe_failed', {
          defaultValue: 'Ошибка подписки',
        }),
        description: err?.response?.data?.detail || err?.message || 'Не удалось оформить подписку',
        variant: 'error',
      })
    } finally {
      setLoading(false)
    }
  }

  const handleUnsubscribe = async (channel?: 'email' | 'phone' | 'push' | 'all') => {
    setLoading(true)
    try {
      if (channel === 'push' || channel === 'all') {
        if (swRegistration) {
          const subscription = await getPushSubscription(swRegistration)
          if (subscription) {
            await unsubscribeFromPush(token)
            await subscription.unsubscribe()
            setPushSubscribed(false)
          }
        }
      }

      if (channel !== 'push') {
        await unsubscribeFromNotifications({ token, channel })
      }

      if (channel === 'all' || !channel) {
        setSubscribed(false)
        setPushSubscribed(false)
      }

      notify({
        title: t('public.notifications.success.unsubscribed', {
          defaultValue: 'Подписка отменена',
        }),
        variant: 'success',
      })
    } catch (err: any) {
      notify({
        title: t('public.notifications.errors.unsubscribe_failed', {
          defaultValue: 'Ошибка отписки',
        }),
        description: err?.response?.data?.detail || err?.message || 'Не удалось отменить подписку',
        variant: 'error',
      })
    } finally {
      setLoading(false)
    }
  }

  const handleSubscribePush = async () => {
    if (!swRegistration) {
      notify({
        title: t('public.notifications.errors.push_not_supported', {
          defaultValue: 'Push-уведомления не поддерживаются',
        }),
        variant: 'error',
      })
      return
    }

    setLoading(true)
    try {
      // Request permission
      if (pushPermission !== 'granted') {
        const permission = await requestNotificationPermission()
        setPushPermission(permission)

        if (permission !== 'granted') {
          notify({
            title: t('public.notifications.errors.permission_denied', {
              defaultValue: 'Разрешение не предоставлено',
            }),
            variant: 'error',
          })
          setLoading(false)
          return
        }
      }

      // Get VAPID public key from backend
      const vapidResponse = await http.get<{ publicKey: string }>('/api/v1/public/notifications/push/vapid-key')
      const vapidPublicKey = vapidResponse.data.publicKey

      if (!vapidPublicKey) {
        notify({
          title: t('public.notifications.errors.push_not_configured', {
            defaultValue: 'Push-уведомления не настроены',
          }),
          description: t('public.notifications.errors.push_not_configured_desc', {
            defaultValue: 'VAPID ключ не настроен на сервере',
          }),
          variant: 'error',
        })
        setLoading(false)
        return
      }

      // Subscribe to push
      const subscription = await subscribeToPushUtil(swRegistration, vapidPublicKey)
      const subscriptionData = subscriptionToJSON(subscription)

      // Send to backend
      await subscribeToPush({
        token,
        ...subscriptionData,
      })

      setPushSubscribed(true)
      notify({
        title: t('public.notifications.success.push_subscribed', {
          defaultValue: 'Push-уведомления включены',
        }),
        variant: 'success',
      })
    } catch (err: any) {
      notify({
        title: t('public.notifications.errors.push_subscribe_failed', {
          defaultValue: 'Ошибка подписки на push',
        }),
        description: err?.response?.data?.detail || err?.message || 'Не удалось подписаться на push-уведомления',
        variant: 'error',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-slate-900">
        {t('public.notifications.title', { defaultValue: 'Уведомления' })}
      </h3>
      <p className="mt-2 text-sm text-slate-600">
        {t('public.notifications.description', {
          defaultValue: 'Получайте уведомления об изменении статуса ваших документов и заявки',
        })}
      </p>

      {!subscribed ? (
        <div className="mt-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700">
              {t('public.notifications.email', { defaultValue: 'Email' })}
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              placeholder={t('public.notifications.placeholders.email', { defaultValue: 'your@email.com' })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">
              {t('public.notifications.phone', { defaultValue: 'Телефон' })}
            </label>
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              placeholder="+48 123 456 789"
            />
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-medium text-slate-700">
              {t('public.notifications.subscribe_to', { defaultValue: 'Подписаться на' })}
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={subscribeDocumentStatus}
                onChange={(e) => setSubscribeDocumentStatus(e.target.checked)}
                className="rounded border-slate-300"
              />
              <span className="text-sm text-slate-700">
                {t('public.notifications.document_status', { defaultValue: 'Изменения статуса документов' })}
              </span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={subscribeStageChanges}
                onChange={(e) => setSubscribeStageChanges(e.target.checked)}
                className="rounded border-slate-300"
              />
              <span className="text-sm text-slate-700">
                {t('public.notifications.stage_changes', { defaultValue: 'Изменения этапа заявки' })}
              </span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={subscribeReminders}
                onChange={(e) => setSubscribeReminders(e.target.checked)}
                className="rounded border-slate-300"
              />
              <span className="text-sm text-slate-700">
                {t('public.notifications.reminders', { defaultValue: 'Напоминания' })}
              </span>
            </label>
          </div>

          <button
            onClick={handleSubscribe}
            disabled={loading || (!email && !phone)}
            className="w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:opacity-50"
          >
            {loading
              ? t('common.loading', { defaultValue: 'Загрузка...' })
              : t('public.notifications.subscribe', { defaultValue: 'Подписаться' })}
          </button>
        </div>
      ) : (
        <div className="mt-4 space-y-3">
          <div className="rounded-lg bg-green-50 p-3 text-sm text-green-700">
            {t('public.notifications.subscribed', {
              defaultValue: 'Вы подписаны на уведомления',
            })}
          </div>
          {email && (
            <div className="text-sm text-slate-600">
              <span className="font-medium">{t('public.notifications.labels.email_colon', { defaultValue: 'Email:' })}</span> {email}
            </div>
          )}
          {phone && (
            <div className="text-sm text-slate-600">
              <span className="font-medium">{t('public.notifications.labels.phone_colon')}</span> {phone}
            </div>
          )}

          {/* Push notifications section */}
          {pushSupported && (
            <div className="mt-4 space-y-2 rounded-lg border border-slate-200 bg-slate-50 p-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-900">
                    {t('public.notifications.push.title', { defaultValue: 'Push-уведомления' })}
                  </p>
                  <p className="text-xs text-slate-500">
                    {t('public.notifications.push.description', {
                      defaultValue: 'Получайте уведомления даже когда браузер закрыт',
                    })}
                  </p>
                </div>
                {pushSubscribed ? (
                  <span className="rounded-full bg-green-100 px-2 py-1 text-xs font-semibold text-green-700">
                    {t('public.notifications.push.active', { defaultValue: 'Активно' })}
                  </span>
                ) : (
                  <span className="rounded-full bg-slate-200 px-2 py-1 text-xs font-semibold text-slate-600">
                    {t('public.notifications.push.inactive', { defaultValue: 'Неактивно' })}
                  </span>
                )}
              </div>
              {!pushSubscribed ? (
                <button
                  onClick={handleSubscribePush}
                  disabled={loading || pushPermission === 'denied'}
                  className="w-full rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white transition hover:bg-blue-700 disabled:opacity-50"
                >
                  {loading
                    ? t('common.loading', { defaultValue: 'Загрузка...' })
                    : t('public.notifications.push.enable', { defaultValue: 'Включить push' })}
                </button>
              ) : (
                <button
                  onClick={() => handleUnsubscribe('push')}
                  disabled={loading}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-50"
                >
                  {loading
                    ? t('common.loading', { defaultValue: 'Загрузка...' })
                    : t('public.notifications.push.disable', { defaultValue: 'Отключить push' })}
                </button>
              )}
              {pushPermission === 'denied' && (
                <p className="text-xs text-red-600">
                  {t('public.notifications.push.permission_denied', {
                    defaultValue: 'Разрешение на уведомления отклонено. Разрешите в настройках браузера.',
                  })}
                </p>
              )}
            </div>
          )}

          <button
            onClick={() => handleUnsubscribe('all')}
            disabled={loading}
            className="mt-4 w-full rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-50"
          >
            {loading
              ? t('common.loading', { defaultValue: 'Загрузка...' })
              : t('public.notifications.unsubscribe', { defaultValue: 'Отписаться от всех' })}
          </button>
        </div>
      )}
    </div>
  )
}
