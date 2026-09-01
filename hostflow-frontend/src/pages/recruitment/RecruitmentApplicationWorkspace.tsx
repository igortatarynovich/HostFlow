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
        notify({ title: t('app.leads.inbox.stage_updated'), variant: 'success' })
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
      objectNamePlural: t('app.recruitment_inquiry.workspace.applications'),
      homePath: RECRUITMENT_INBOX_PATH,
      applicationPath: recruitmentApplicationPath,
      listApplications: listRecruitmentApplications,
      getApplication: getRecruitmentApplication,
      serverTabPagination: true,
      tabs: [
        { id: 'all' as const, label: t('app.recruitment_inquiry.workspace.tab_all') },
        { id: 'new' as const, label: t('app.recruitment_inquiry.workspace.tab_new') },
        { id: 'in_progress' as const, label: t('app.recruitment_inquiry.workspace.tab_in_progress') },
        { id: 'completed' as const, label: t('app.recruitment_inquiry.workspace.tab_completed') },
      ],
      workSessionSurface: 'recruitment',
      workSessionKind: 'recruitment_call',
      heroCallTitle: (count: number) =>
        t('app.recruitment_inquiry.workspace.hero_call_title', { values: { count } }),
      heroCallHint: t('app.recruitment_inquiry.workspace.hero_call_hint'),
      heroEmptyText: t('app.recruitment_inquiry.workspace.hero_empty'),
      listKindLabel: t('app.recruitment_inquiry.workspace.list_kind'),
      extensionBadge: (app) => (app.extensions?.vacancy_title as string | undefined) || null,
      primaryEntityPath: (app) => {
        if (app.outcome_entity_type !== 'candidate') return undefined
        const id = String(app.outcome_entity_id || '').trim()
        return id ? `${CRM_APP_PATHS.candidates}/${encodeURIComponent(id)}` : undefined
      },
      primaryEntityLabel: t('app.candidates.detail.open_full_profile'),
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
