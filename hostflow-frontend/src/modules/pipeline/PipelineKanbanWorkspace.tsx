/**
 * Main pipeline column: toolbar, errors, empty state slot, bulk bar slot, kanban slot.
 */

import type { ReactNode, RefObject } from 'react';
import clsx from 'clsx';
import { IconLayoutSidebarLeftExpand, IconX } from '@tabler/icons-react';
import { PageHeader } from '../../components/nav/PageHeader';
import { PageShell, PageShellHeader } from '../../components/layout';
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner';
import { CRM_APP_PATHS } from '../../app/crmAppPaths';
import type { FriendlyErrorInfo } from '../../utils/friendlyError';
import { friendlyErrorBannerSecondary } from '../../utils/friendlyError';
import { PipelineMainEmptyState } from './PipelineMainEmptyState';

export type PipelineKanbanWorkspaceProps = {
  sidebarOpen: boolean;
  tableContainerRef: RefObject<HTMLDivElement | null>;
  onToggleSidebar: () => void;
  /** Shown when sidebar is open (close action). */
  closeSidebarLabel: string;
  /** Shown when sidebar is closed (open action). */
  openSidebarLabel: string;
  error: FriendlyErrorInfo | null;
  onRetryLoad: () => void;
  retryLabel: string;
  candidatesNavLabel: string;
  showMainEmpty: boolean;
  loading: boolean;
  bulkBar: ReactNode;
  kanban: ReactNode;
};

export function PipelineKanbanWorkspace({
  sidebarOpen,
  tableContainerRef,
  onToggleSidebar,
  closeSidebarLabel,
  openSidebarLabel,
  error,
  onRetryLoad,
  retryLabel,
  candidatesNavLabel,
  showMainEmpty,
  loading,
  bulkBar,
  kanban,
}: PipelineKanbanWorkspaceProps) {
  const sidebarToggle = (
    <button
      type="button"
      onClick={onToggleSidebar}
      className="flex items-center gap-2 rounded-md border border-slate-200 px-3 py-1.5 text-sm text-slate-700 transition hover:bg-slate-50"
      title={sidebarOpen ? closeSidebarLabel : openSidebarLabel}
      aria-label={sidebarOpen ? closeSidebarLabel : openSidebarLabel}
    >
      {sidebarOpen ? (
        <>
          <IconX size={18} stroke={2} />
          <span className="hidden sm:inline">{closeSidebarLabel}</span>
        </>
      ) : (
        <>
          <IconLayoutSidebarLeftExpand size={18} stroke={2} />
          <span className="hidden sm:inline">{openSidebarLabel}</span>
        </>
      )}
    </button>
  );

  return (
    <div
      className={clsx(
        'flex min-h-0 flex-1 flex-col overflow-hidden transition-all duration-300',
        sidebarOpen ? 'mr-0 sm:mr-96' : 'mr-0',
      )}
    >
      <PageShell data-hf-ui="candidates-pipeline-kanban">
        <PageShellHeader className="pb-1 pt-2">
          <PageHeader kind="browse" secondaryActions={sidebarToggle} />
        </PageShellHeader>
        <div
          ref={tableContainerRef}
          className="flex min-h-0 flex-1 flex-col overflow-hidden"
        >
        {error && (
          <ErrorRecoveryBanner
            info={error}
            onRetry={onRetryLoad}
            retryLabel={retryLabel}
            {...friendlyErrorBannerSecondary(
              error,
              CRM_APP_PATHS.candidates,
              candidatesNavLabel,
            )}
            compact
          />
        )}

        {showMainEmpty && !loading && <PipelineMainEmptyState />}

        {bulkBar}

        {kanban}
        </div>
      </PageShell>
    </div>
  );
}
