/**
 * Empty pipeline (no cards after filters / load).
 */

import EmptyStatePanel from '../../components/EmptyStatePanel';
import { CRM_APP_PATHS } from '../../app/crmAppPaths';
import { useI18n } from '../../i18n';

export function PipelineMainEmptyState() {
  const { t } = useI18n();
  return (
    <div className="card p-4">
      <EmptyStatePanel
        compact
        title={t('app.candidates.pipeline.empty_title', { defaultValue: 'Pipeline is empty' })}
        description={t('app.candidates.pipeline.empty_desc', {
          defaultValue:
            'No candidates are currently in pipeline. Add candidates from leads or open candidates list.',
        })}
        whyHint={t('app.candidates.pipeline.empty_why', {
          defaultValue:
            'Pipeline is your kanban view of candidates moving through stages — from first contact to placement. Drag cards across columns to update stage, owner and SLA at once.',
        })}
        primaryAction={{
          label: t('app.candidates.pipeline.empty_cta_candidates', { defaultValue: 'Open candidates' }),
          to: CRM_APP_PATHS.candidates,
        }}
        secondaryAction={{
          label: t('app.candidates.pipeline.empty_cta_leads', { defaultValue: 'Open leads' }),
          to: CRM_APP_PATHS.leads,
        }}
      />
    </div>
  );
}
