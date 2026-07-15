import { CRM_APP_PATHS } from '../app/crmAppPaths'
import type { Permission } from '../hooks/usePermissions'

/** Short list for “where to work” hints (Settings landing, help); aligns with main sidebar. */
export type CrmContourNavItem = {
  key: string
  path: string
  labelKey: string
  descriptionKey: string
  permission?: Permission
}

export const CRM_CONTOUR_NAV_ITEMS: CrmContourNavItem[] = [
  {
    key: 'overview',
    path: CRM_APP_PATHS.overview,
    labelKey: 'app.nav.items.overview',
    descriptionKey: 'admin.settings.crm_contours.desc.overview',
  },
  {
    key: 'work',
    path: CRM_APP_PATHS.work,
    labelKey: 'app.nav.items.work',
    descriptionKey: 'admin.settings.crm_contours.desc.work',
  },
  {
    key: 'inbox',
    path: CRM_APP_PATHS.inbox,
    labelKey: 'app.nav.items.inbox',
    descriptionKey: 'admin.settings.crm_contours.desc.inbox',
    permission: 'notifications.view',
  },
  {
    key: 'clients',
    path: CRM_APP_PATHS.clientsDirectory,
    labelKey: 'app.nav.items.clients',
    descriptionKey: 'admin.settings.crm_contours.desc.clients',
    permission: 'companies.view',
  },
  {
    key: 'candidates',
    path: CRM_APP_PATHS.candidates,
    labelKey: 'app.nav.items.candidates',
    descriptionKey: 'admin.settings.crm_contours.desc.candidates',
    permission: 'candidates.view',
  },
  {
    key: 'leads',
    path: CRM_APP_PATHS.leads,
    labelKey: 'app.nav.items.leads',
    descriptionKey: 'admin.settings.crm_contours.desc.leads',
    permission: 'leads.view',
  },
  {
    key: 'tasks',
    path: CRM_APP_PATHS.tasks,
    labelKey: 'app.nav.items.tasks',
    descriptionKey: 'admin.settings.crm_contours.desc.tasks',
    permission: 'notifications.view',
  },
]
