import clsx from 'clsx'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { enUS, ru as ruLocale, pl as plLocale } from 'date-fns/locale'
import { listNotifications, markNotificationsRead } from '../api/client'
import type { NotificationItem, NotificationListResponse } from '../api/types'
import { useAuth } from '../store/useAuth'
import { filterRelevantNotifications, isNotificationRelevant } from '../utils/notifications'
import { useI18n } from '../i18n'

const EVENT_LABEL_KEYS: Record<string, string> = {
  'lead.processed': 'app.reminders.events.lead_processed',
  'lead.needs_routing': 'app.reminders.events.lead_needs_routing',
  'lead.failed': 'app.reminders.events.lead_failed',
  'candidate.created': 'app.reminders.events.candidate_created',
  'candidate.updated': 'app.reminders.events.candidate_updated',
  'candidate.stage_changed': 'app.reminders.events.candidate_stage_changed',
  'candidate.intake_submitted': 'app.reminders.events.candidate_intake_submitted',
  'document.updated': 'app.reminders.events.document_updated',
  'document.requested': 'app.reminders.events.document_requested',
  'service.order.created': 'app.reminders.events.service_order_created',
}

const DATE_LOCALES = {
  en: enUS,
  ru: ruLocale,
  pl: plLocale,
}

type LoadingState = 'idle' | 'loading' | 'error'

type ScopeFilter = 'direct' | 'all'

type ReadFilter = 'unread' | 'all'

export default function RemindersPage() {
  const { t, locale } = useI18n()
  const { me } = useAuth()
  const [items, setItems] = useState<NotificationItem[]>([])
  const [loading, setLoading] = useState<LoadingState>('idle')
  const [error, setError] = useState<string | null>(null)
  const [scope, setScope] = useState<ScopeFilter>('direct')
  const [readFilter, setReadFilter] = useState<ReadFilter>('unread')
  const dateLocale = DATE_LOCALES[locale] || enUS

  const load = useCallback(
    async (showRead = readFilter, currentScope = scope) => {
      setLoading('loading')
      setError(null)
      try {
        const data = (await listNotifications({
          includeRead: showRead === 'all',
          limit: 150,
          scope: currentScope,
        })) as NotificationListResponse
        const next = Array.isArray(data?.items) ? data.items : []
        setItems(next)
        setLoading('idle')
      } catch (err: any) {
        setLoading('error')
        setError(t('app.reminders.errors.load'))
      }
    },
    [readFilter, scope, t]
  )

  useEffect(() => {
    void load(readFilter, scope)
  }, [load, readFilter, scope])

  const visibleItems = useMemo(() => {
    if (scope === 'direct') {
      const direct = filterRelevantNotifications(items, me, { includeUnassigned: true })
      return direct
    }
    return items
  }, [items, scope, me])

  const unreadCount = useMemo(
    () => visibleItems.filter((item) => !item.is_read).length,
    [visibleItems]
  )

  const markOne = async (id: string) => {
    try {
      await markNotificationsRead({ ids: [id] })
      await load(readFilter, scope)
    } catch (err: any) {
      setError(t('app.reminders.errors.mark_one'))
    }
  }

  const markAll = async () => {
    try {
      await markNotificationsRead({ markAll: true })
      await load(readFilter, scope)
    } catch (err: any) {
      setError(t('app.reminders.errors.mark_all'))
    }
  }

  const hasItems = visibleItems.length > 0
  const scopeLabel = t(`app.reminders.scope_labels.${scope}`, { defaultValue: scope })
  const subtitle = t('app.reminders.subtitle', {
    values: {
      scope: scopeLabel,
      total: visibleItems.length,
      unread: unreadCount,
    },
  })

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">{t('app.reminders.title')}</h1>
          <p className="text-sm text-gray-500">{subtitle}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="inline-flex rounded-lg border border-gray-200 bg-white p-1 shadow-sm">
            <button
              type="button"
              className={clsx(
                'rounded-md px-3 py-1.5 text-sm font-medium transition',
                scope === 'direct' ? 'bg-brand-600 text-white' : 'text-gray-600 hover:bg-gray-100'
              )}
              onClick={() => setScope('direct')}
            >
              {t('app.reminders.scopes.direct')}
            </button>
            <button
              type="button"
              className={clsx(
                'rounded-md px-3 py-1.5 text-sm font-medium transition',
                scope === 'all' ? 'bg-brand-600 text-white' : 'text-gray-600 hover:bg-gray-100'
              )}
              onClick={() => setScope('all')}
            >
              {t('app.reminders.scopes.all')}
            </button>
          </div>

          <div className="inline-flex rounded-lg border border-gray-200 bg-white p-1 shadow-sm">
            <button
              type="button"
              className={clsx(
                'rounded-md px-3 py-1.5 text-sm font-medium transition',
                readFilter === 'unread' ? 'bg-gray-900 text-white' : 'text-gray-600 hover:bg-gray-100'
              )}
              onClick={() => setReadFilter('unread')}
            >
              {t('app.reminders.filters.unread')}
            </button>
            <button
              type="button"
              className={clsx(
                'rounded-md px-3 py-1.5 text-sm font-medium transition',
                readFilter === 'all' ? 'bg-gray-900 text-white' : 'text-gray-600 hover:bg-gray-100'
              )}
              onClick={() => setReadFilter('all')}
            >
              {t('app.reminders.filters.all')}
            </button>
          </div>

          <button
            type="button"
            className="btn-secondary"
            onClick={() => load(readFilter, scope)}
            disabled={loading === 'loading'}
          >
            {t('app.reminders.actions.refresh')}
          </button>
          <button
            type="button"
            className="btn-primary"
            onClick={markAll}
            disabled={items.length === 0}
          >
            {t('app.reminders.actions.mark_all')}
          </button>
        </div>
      </header>

      {loading === 'loading' && <div className="text-gray-500">{t('app.reminders.states.loading')}</div>}
      {loading === 'error' && error && <div className="text-rose-600">{error}</div>}

      {!hasItems && loading === 'idle' && (
        <div className="rounded border border-dashed border-gray-300 bg-white p-6 text-center text-gray-500">
          {t('app.reminders.states.empty')}
        </div>
      )}

      {hasItems && (
        <ul className="space-y-3">
          {visibleItems.map((item) => {
            const labelKey = EVENT_LABEL_KEYS[item.event_type] || 'app.reminders.events.unknown'
            const label = t(labelKey, { values: { event: item.event_type } })
            const createdAt = item.created_at ? new Date(item.created_at) : null
            const relative = createdAt
              ? formatDistanceToNow(createdAt, { addSuffix: true, locale: dateLocale })
              : ''
            const isDirect = isNotificationRelevant(item, me)
            const payload = item.payload ?? {}
            const friendlyPairs: Array<[string, string]> = []
            const add = (labelKey: string, value?: any) => {
              if (value === null || value === undefined || value === '') return
              friendlyPairs.push([t(labelKey), String(value)])
            }
            add('app.reminders.payload.candidate', payload.candidate_name || payload.candidate_id)
            add('app.reminders.payload.vacancy', payload.vacancy_name || payload.vacancy_id)
            add('app.reminders.payload.company', payload.company_name || payload.company_id)
            add('app.reminders.payload.manager', payload.manager_name || payload.manager_id)
            add('app.reminders.payload.recruiter', payload.recruiter_name || payload.recruiter_id)
            add('app.reminders.payload.stage', payload.stage_label || payload.stage)
            const otherEntries = Object.entries(payload).filter(
              ([key]) => ![
                'candidate_id','candidate_name','vacancy_id','vacancy_name','company_id','company_name',
                'manager_id','manager_name','recruiter_id','recruiter_name','stage','stage_label'
              ].includes(key)
            )
            return (
              <li
                key={item.id}
                className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-sm font-semibold text-gray-900">{label}</h2>
                      {isDirect && (
                        <span className="rounded bg-emerald-100 px-2 py-0.5 text-[11px] font-semibold text-emerald-700">
                          {t('app.reminders.states.badge_direct')}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500">{relative}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    {!item.is_read && (
                      <span className="rounded bg-blue-100 px-2 py-0.5 text-xs text-blue-700">
                        {t('app.reminders.states.badge_new')}
                      </span>
                    )}
                    <button
                      type="button"
                      className="btn-ghost btn-xs"
                      onClick={() => markOne(item.id)}
                    >
                      {t('app.reminders.actions.mark_one')}
                    </button>
                  </div>
                </div>
                {(friendlyPairs.length > 0 || otherEntries.length > 0) && (
                  <dl className="mt-3 grid gap-2 text-xs text-gray-600 sm:grid-cols-2">
                    {friendlyPairs.map(([label, value]) => (
                      <div key={label} className="flex gap-2">
                        <dt className="font-medium text-gray-500">{label}</dt>
                        <dd className="truncate text-gray-700">{value}</dd>
                      </div>
                    ))}
                    {otherEntries.map(([key, value]) => (
                      <div key={key} className="flex gap-2">
                        <dt className="font-medium text-gray-500">{key}</dt>
                        <dd className="truncate text-gray-700">{String(value)}</dd>
                      </div>
                    ))}
                  </dl>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
