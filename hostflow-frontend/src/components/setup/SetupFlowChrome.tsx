import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { IconArrowLeft, IconChecklist } from '@tabler/icons-react'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { PageHeader } from '../nav/PageHeader'
import { PageShell, PageShellHeader } from '../layout'

type SetupFlowChromeProps = {
  testId: string
  stepLabel: string
  title: string
  subtitle: string
  children: ReactNode
}

export function SetupFlowChrome({ testId, stepLabel, title, subtitle, children }: SetupFlowChromeProps) {
  const { t } = useI18n()

  return (
    <PageShell data-testid={testId}>
      <PageShellHeader>
        <PageHeader
          title={title}
          subtitle={subtitle}
          kind="browse"
          secondaryActions={
            <Link
              to={CRM_APP_PATHS.setup}
              className="btn-secondary btn-sm inline-flex items-center gap-1"
            >
              <IconArrowLeft size={14} stroke={1.9} />
              {t('app.onboarding.setup.flow.back_to_setup', { defaultValue: 'Назад к настройке' })}
            </Link>
          }
        />
      </PageShellHeader>
      <div className="mx-auto flex min-h-0 w-full max-w-2xl flex-1 flex-col gap-4 overflow-y-auto px-4 pb-4">
        <section className="rounded-2xl border border-slate-200 bg-white px-6 py-4 shadow-sm">
          <div className="inline-flex items-center gap-1 rounded-md bg-brand-50 px-2 py-1 text-xs font-medium text-brand-700">
            <IconChecklist size={14} stroke={1.9} />
            {stepLabel}
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">{children}</section>
      </div>
    </PageShell>
  )
}
