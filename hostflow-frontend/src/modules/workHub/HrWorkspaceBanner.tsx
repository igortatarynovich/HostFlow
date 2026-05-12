import { Link } from 'react-router-dom'
import { IconArrowRight } from '@tabler/icons-react'

import { CRM_APP_DRILLDOWN_HREFS, CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'

/** Entry strip on `/app/work` for roles with `workforce.view`. */
export function HrWorkspaceBanner() {
  const { t } = useI18n()

  return (
    <section className="rounded-2xl border border-emerald-200/80 bg-gradient-to-br from-emerald-50/90 to-white p-6 shadow-sm">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0 space-y-1">
          <h2 className="text-base font-bold text-slate-900">
            {t('app.work.hub.hr_banner_title', { defaultValue: 'HR workspace' })}
          </h2>
          <p className="text-sm text-slate-600">
            {t('app.work.hub.hr_banner_body', {
              defaultValue:
                'Employee records after hire: payroll fields, ZUS, contracts, and onboarding tasks.',
            })}
          </p>
        </div>
        <div className="flex shrink-0 flex-col gap-2 sm:flex-row sm:items-center">
          <Link
            to={CRM_APP_PATHS.hrEmployees}
            className="inline-flex h-11 items-center justify-center rounded-xl bg-emerald-700 px-4 text-sm font-semibold text-white shadow-sm hover:bg-emerald-800"
          >
            {t('app.work.hub.hr_banner_employees', { defaultValue: 'Employees' })}
            <IconArrowRight size={18} className="ml-1 opacity-90" aria-hidden />
          </Link>
          <Link
            to={CRM_APP_DRILLDOWN_HREFS.candidatesStageEmploymentPending}
            className="inline-flex h-11 items-center justify-center rounded-xl border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-800 hover:bg-slate-50"
          >
            {t('app.work.hub.hr_banner_pending', { defaultValue: 'Pending handoff to HR' })}
            <IconArrowRight size={18} className="ml-1 opacity-60" aria-hidden />
          </Link>
        </div>
      </div>
    </section>
  )
}
