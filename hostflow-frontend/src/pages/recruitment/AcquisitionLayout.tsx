import { Link, NavLink, Outlet } from 'react-router-dom'
import clsx from 'clsx'
import { IconPlus } from '@tabler/icons-react'
import {
  recruitmentSearchAcquisitionPath,
  recruitmentSearchAcquisitionNewPath,
} from '../../app/crmAppPaths'
import { Toolbar } from '../../components/layout'
import { useI18n } from '../../i18n'
import { useSearchWorkspace } from './searchWorkspaceContext'
import { useAcquisitionData } from '../../hooks/useAcquisitionData'
import { AcquisitionSyncStatus } from '../../components/recruitment/AcquisitionSyncStatus'

const subTabClass = ({ isActive }: { isActive: boolean }) =>
  clsx(
    'rounded-md px-3 py-1.5 text-xs font-medium transition',
    isActive ? 'bg-brand-600 text-white' : 'text-slate-600 hover:bg-slate-100',
  )

export default function AcquisitionLayout() {
  const { t } = useI18n()
  const { searchId } = useSearchWorkspace()
  const acquisitionBase = recruitmentSearchAcquisitionPath(searchId)
  const { snapshot, loading, syncing, refresh } = useAcquisitionData(searchId)

  return (
    <div className="space-y-4" data-testid="m1-acquisition-layout">
      <Toolbar>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <AcquisitionSyncStatus snapshot={snapshot} syncing={syncing} />
          <Link
            to={recruitmentSearchAcquisitionNewPath(searchId)}
            className="btn-primary btn-sm inline-flex items-center gap-1.5"
          >
            <IconPlus size={16} stroke={1.9} />
            {t('app.acquisition.launch', { defaultValue: 'Запустить рекламу' })}
          </Link>
        </div>
        <nav
          className="mt-3 flex flex-wrap gap-1 rounded-lg border border-slate-200 bg-white p-1"
          aria-label={t('app.acquisition.tabs_aria', { defaultValue: 'Разделы привлечения' })}
        >
          <NavLink to={`${acquisitionBase}/activities`} end className={subTabClass}>
            {t('app.acquisition.tab_activities', { defaultValue: 'Активности' })}
          </NavLink>
          <NavLink to={`${acquisitionBase}/journal`} className={subTabClass}>
            {t('app.acquisition.tab_journal', { defaultValue: 'Журнал' })}
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
