/**
 * Empty pipeline (no cards after filters / load).
 */

import EmptyStatePanel from '../../components/EmptyStatePanel'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'

export function PipelineMainEmptyState() {
  const { t } = useI18n()
  return (
    <div className="card p-4">
      <EmptyStatePanel
        compact
        title={t('app.candidates.pipeline.empty_title', {
          defaultValue: 'Nobody in the pipeline yet',
        })}
        description={t('app.candidates.pipeline.empty_desc', {
          defaultValue:
            'Process a lead into a candidate — then move them across stages here until the vacancy is closed.',
        })}
        whyHint={t('app.candidates.pipeline.empty_why', {
          defaultValue: 'Pipeline shows who is stuck and what to do next. Start from leads.',
        })}
        primaryAction={{
          label: t('app.candidates.pipeline.empty_cta_leads', { defaultValue: 'Open leads' }),
          to: CRM_APP_PATHS.leads,
        }}
        secondaryAction={{
          label: t('app.candidates.pipeline.empty_cta_vacancy', {
            defaultValue: 'Create vacancy',
          }),
          to: CRM_APP_PATHS.setupClient,
        }}
      />
    </div>
  )
}
