import { useCallback, useMemo, useState } from 'react'
import { updateRecruitmentApplicationStage, listRecruitmentApplications, getRecruitmentApplication } from '../../api/applications'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useToast } from '../../components/Toast'
import { useI18n } from '../../i18n'
import { getFriendlyErrorInfo } from '../../utils/friendlyError'
import { RECRUITMENT_INBOX_PATH, recruitmentApplicationPath } from '../../app/recruitmentInboxPaths'
import { ApplicationWorkspace } from '../../platform/application-workspace/ApplicationWorkspace'
import { ApplicationRecruitmentDetailPanel } from '../../platform/application-workspace/ApplicationRecruitmentDetailPanel'
import type { ApplicationWorkspaceConfig } from '../../platform/application-workspace/types'

export function RecruitmentApplicationWorkspace() {
  const { t } = useI18n()
  const { notify } = useToast()
  const [patching, setPatching] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  const handleStageChange = useCallback(
    async (applicationId: string, stage: 'contacted' | 'qualified' | 'lost') => {
      setPatching(true)
      try {
        await updateRecruitmentApplicationStage(applicationId, { stage })
        setRefreshKey((k) => k + 1)
        notify({
          title: t('app.leads.inbox.stage_updated', { defaultValue: 'Status updated' }),
          variant: 'success',
        })
      } catch (err: unknown) {
        const info = getFriendlyErrorInfo(err, t('app.leads.detail.stage_update_failed'), t)
        notify({ title: info.title, description: [info.detail, info.hint].filter(Boolean).join(' '), variant: 'error' })
      } finally {
        setPatching(false)
      }
    },
    [notify, t],
  )

  const config: ApplicationWorkspaceConfig = useMemo(
    () => ({
      module: 'recruitment',
      objectNamePlural: t('app.application_workspace.recruitment.title', { defaultValue: 'Applications' }),
      homePath: RECRUITMENT_INBOX_PATH,
      applicationPath: recruitmentApplicationPath,
      listApplications: listRecruitmentApplications,
      getApplication: getRecruitmentApplication,
      serverTabPagination: true,
      tabs: [
        { id: 'all' as const, label: t('app.application_workspace.tabs.all', { defaultValue: 'All' }) },
        { id: 'new' as const, label: t('app.application_workspace.tabs.new', { defaultValue: 'New' }) },
        {
          id: 'in_progress' as const,
          label: t('app.application_workspace.tabs.in_progress', { defaultValue: 'In progress' }),
        },
        {
          id: 'completed' as const,
          label: t('app.application_workspace.tabs.completed', { defaultValue: 'Completed' }),
        },
      ],
      workSessionSurface: 'recruitment',
      workSessionKind: 'recruitment_call',
      heroCallTitle: (count: number) =>
        t('app.application_workspace.recruitment.hero_call_title', {
          defaultValue: 'Call {count} new applications',
          values: { count },
        }),
      heroCallHint: t('app.application_workspace.recruitment.hero_call_hint', {
        defaultValue: "We'll open applications one by one: call → decide → create candidate.",
      }),
      heroEmptyText: t('app.application_workspace.recruitment.hero_empty', {
        defaultValue: 'No new applications to call',
      }),
      listKindLabel: t('app.application_workspace.recruitment.list_kind', {
        defaultValue: 'Candidate application',
      }),
      extensionBadge: (app) => (app.extensions?.vacancy_title as string | undefined) || null,
      primaryEntityPath: (app) => {
        if (app.outcome_entity_type !== 'candidate') return undefined
        const id = String(app.outcome_entity_id || '').trim()
        return id ? `${CRM_APP_PATHS.candidates}/${encodeURIComponent(id)}` : undefined
      },
      primaryEntityLabel: t('app.candidates.detail.open_full_profile', {
        defaultValue: 'Open candidate profile',
      }),
      renderDetail: ({ application, onRefresh, onClose }) => (
        <ApplicationRecruitmentDetailPanel
          key={`${application.id}-${refreshKey}`}
          application={application}
          patching={patching}
          onClose={onClose}
          onRefresh={onRefresh}
          onStage={(stage) => void handleStageChange(application.id, stage).then(onRefresh)}
        />
      ),
    }),
    [handleStageChange, patching, refreshKey, t],
  )

  return <ApplicationWorkspace config={config} routeParam="applicationId" />
}

export default RecruitmentApplicationWorkspace
