import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { formatDistanceToNow } from 'date-fns'
import { enUS, pl as plFns, ru as ruFns } from 'date-fns/locale'
import { IconArrowLeft, IconArrowRight, IconPlus } from '@tabler/icons-react'
import { listCompanyIntakeSourceProfiles, type CompanyIntakeSourceProfile } from '../../api/companyIntakeSourceProfiles'
import { clientAcquisitionChannelPath } from '../../app/clientAcquisitionPaths'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n, type LocaleCode } from '../../i18n'
import { persistLastClientChannelId } from '../../services/clientChannelSession'

function dateFnsLocale(code: LocaleCode) {
  if (code === 'pl') return plFns
  if (code === 'ru') return ruFns
  return enUS
}

export default function ClientChannelsListPage() {
  const { t, locale } = useI18n()
  const [rows, setRows] = useState<CompanyIntakeSourceProfile[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const profiles = await listCompanyIntakeSourceProfiles()
      setRows(profiles)
    } catch {
      setRows([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const dfLocale = useMemo(() => dateFnsLocale(locale), [locale])

  const handleOpen = (channelId: string) => {
    persistLastClientChannelId(channelId)
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5 px-1 sm:px-0" data-testid="m1-sales-channels-list">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link
            to={CRM_APP_PATHS.launchpad}
            className="inline-flex items-center gap-1 text-sm text-slate-600 hover:text-brand-700"
          >
            <IconArrowLeft size={14} stroke={1.9} />
            {t('app.sales_channels.back_launchpad', { defaultValue: 'Getting started' })}
          </Link>
          <h1 className="mt-3 text-2xl font-semibold text-slate-900">
            {t('app.sales_channels.title', { defaultValue: 'Client acquisition' })}
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            {t('app.sales_channels.subtitle', {
              defaultValue: 'Open a channel — link, company inquiries and next steps in one place.',
            })}
          </p>
          <p className="mt-2 text-sm text-slate-500">
            {t('app.sales_channels.explain', {
              defaultValue:
                'A channel is your link for companies. They submit an inquiry, you call, register the client and start hiring.',
            })}
          </p>
        </div>
        <Link
          to={CRM_APP_PATHS.clientAcquisitionChannelsNew}
          className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
          data-testid="m1-sales-channels-create"
        >
          <IconPlus size={16} stroke={1.9} />
          {t('app.sales_channels.create', { defaultValue: 'New channel' })}
        </Link>
      </div>

      {loading ? (
        <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading…' })}</p>
      ) : rows.length === 0 ? (
        <section className="rounded-xl border border-dashed border-slate-200 bg-white p-8 text-center shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">
            {t('app.sales_channels.empty_title', { defaultValue: 'No channels yet' })}
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            {t('app.sales_channels.empty_body', {
              defaultValue: 'Create the first channel — get a link for companies and start receiving inquiries.',
            })}
          </p>
          <Link
            to={CRM_APP_PATHS.clientAcquisitionChannelsNew}
            className="mt-4 inline-flex rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            {t('app.sales_channels.create', { defaultValue: 'New channel' })}
          </Link>
        </section>
      ) : (
        <ul className="space-y-3">
          {rows.map((row) => (
            <li key={row.id}>
              <Link
                to={clientAcquisitionChannelPath(row.id)}
                onClick={() => handleOpen(row.id)}
                className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-brand-200 hover:shadow-md"
                data-testid={`m1-sales-channel-row-${row.id}`}
              >
                <div className="min-w-0">
                  <p className="truncate font-semibold text-slate-900">{row.name}</p>
                  <p className="mt-1 text-sm text-slate-500">
                    {row.provider === 'meta'
                      ? t('app.sales_channels.meta_source', { defaultValue: 'Meta Lead Ads' })
                      : null}
                    {row.provider === 'meta' ? ' · ' : ''}
                    {row.updated_at
                      ? formatDistanceToNow(new Date(row.updated_at), { addSuffix: true, locale: dfLocale })
                      : formatDistanceToNow(new Date(row.created_at), { addSuffix: true, locale: dfLocale })}
                  </p>
                </div>
                <IconArrowRight size={18} className="shrink-0 text-slate-400" stroke={1.8} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
