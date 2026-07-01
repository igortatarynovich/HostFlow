/**
 * Empty column in kanban (no cards in this stage).
 */

import EmptyStatePanel from '../../components/EmptyStatePanel';
import { useI18n } from '../../i18n';

export function PipelineColumnEmptyState({ viewInListHref }: { viewInListHref: string }) {
  const { t } = useI18n();
  return (
    <div className="py-4">
      <EmptyStatePanel
        compact
        title={t('app.candidates.pipeline.column_empty_title', { defaultValue: 'No candidates in this stage' })}
        description={t('app.candidates.pipeline.column_empty_desc', {
          defaultValue: 'Move candidates to this stage or adjust filters.',
        })}
        primaryAction={{
          label: t('app.candidates.pipeline.column_empty_cta_candidates', { defaultValue: 'Open candidates' }),
          to: viewInListHref,
        }}
      />
    </div>
  );
}
