import { Link, NavLink, Outlet } from 'react-router-dom'
import clsx from 'clsx'
import { IconExternalLink, IconPlus } from '@tabler/icons-react'
import {
  CRM_APP_PATHS,
  marketingSetupWithVacancyTargetPath,
  recruitmentSearchAcquisitionPath,
} from '../../app/crmAppPaths'
import { Toolbar } from '../../components/layout'
import { useI18n } from '../../i18n'
import { useSearchWorkspace } from './searchWorkspaceContext'
import { useAcquisitionData } from '../../hooks/useAcquisitionData'
import { AcquisitionSyncStatus } from '../../components/recruitment/AcquisitionSyncStatus'

const subTabClass = ({ isActive }: { isActive: boolean }) =>
  clsx(
    'rounded-lg px-3 py-2 text-xs font-medium transition',
    isActive ? 'bg-brand-600 text-white' : 'text-slate-600 hover:bg-slate-100',
  )

export default function AcquisitionLayout() {
  const { t } = useI18n()
  const { searchId, searchName } = useSearchWorkspace()
  const acquisitionBase = recruitmentSearchAcquisitionPath(searchId)
  const { snapshot, loading, syncing, refresh } = useAcquisitionData(searchId)
  const marketingHref =
    snapshot?.marketing_setup_path ||
    marketingSetupWithVacancyTargetPath(searchId, { name: searchName || undefined })
  const linkedCampaignId = snapshot?.reconciliation?.linked_campaign_id
  const linkedCampaignHref = linkedCampaignId
    ? `${CRM_APP_PATHS.marketing}/${encodeURIComponent(linkedCampaignId)}`
    : null

  return (
    <div className="space-y-4" data-testid="m1-acquisition-layout">
      <section
        className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
        data-testid="acquisition-legacy-banner"
      >
        <p className="font-medium">
          {t('app.acquisition.legacy_readonly_title')}
        </p>
        <p className="mt-1 text-amber-900/90">
          {t('app.acquisition.legacy_readonly_body')}
        </p>
        {snapshot?.reconciliation?.status === 'linked' && linkedCampaignHref ? (
          <p className="mt-2">
            <Link
              to={linkedCampaignHref}
              className="inline-flex items-center gap-1 font-medium text-brand-700 underline"
              data-testid="acquisition-linked-campaign"
            >
              {t('app.acquisition.open_linked_campaign')}
              {snapshot.reconciliation.linked_campaign_name
                ? `: ${snapshot.reconciliation.linked_campaign_name}`
                : ''}
              <IconExternalLink size={14} stroke={1.9} />
            </Link>
          </p>
        ) : null}
        {snapshot?.reconciliation?.status === 'unresolved' ? (
          <p className="mt-2 text-amber-900/80" data-testid="acquisition-reconciliation-unresolved">
            {t('app.acquisition.reconciliation_unresolved')}
          </p>
        ) : null}
      </section>

      <Toolbar>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <AcquisitionSyncStatus snapshot={snapshot} syncing={syncing} />
          <Link
            to={marketingHref}
            className="btn-primary btn-sm inline-flex items-center gap-2"
            data-testid="acquisition-go-marketing-setup"
          >
            <IconPlus size={16} stroke={1.9} />
            {t('app.acquisition.launch_in_marketing')}
          </Link>
        </div>
        <nav
          className="mt-3 flex flex-wrap gap-1 rounded-lg border border-slate-200 bg-white p-1"
          aria-label={t('app.acquisition.tabs_aria')}
        >
          <NavLink to={`${acquisitionBase}/activities`} end className={subTabClass}>
            {t('app.acquisition.tab_activities')}
          </NavLink>
          <NavLink to={`${acquisitionBase}/journal`} className={subTabClass}>
            {t('app.acquisition.tab_journal')}
          </NavLink>
        </nav>
      </Toolbar>

      <Outlet context={{ snapshot, loading, syncing, refresh }} />
    </div>
  )
}

export type AcquisitionOutletContext = {
  snapshot: ReturnType<typeof useAcquisitionData>['snapshot']
  loading: boolean
  syncing: boolean
  refresh: ReturnType<typeof useAcquisitionData>['refresh']
}
